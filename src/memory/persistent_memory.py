"""
Sistema de Memoria Persistente para BMO — Backend MongoDB exclusivo.

Reglas de negocio:
  1. Solo se guarda historial de personas con cara registrada (persona != None).
     Sin cara reconocida → la sesión se descarta, no persiste nada.
  2. Máximo 6 mensajes por persona (sliding window).
     Al llegar el 7mo, el más viejo se borra automáticamente.
  3. Se guarda solo el contexto (primeros ~120 chars), no el mensaje completo.
  4. Anónimo: solo el último intercambio en RAM, nunca toca MongoDB.

Requiere MongoDB corriendo en localhost:27017 (o URI configurada en config.json).
"""
import json
import logging
from pathlib import Path
from datetime import datetime

from src.storage.mongo_store import _contexto as _truncar
from src.storage import mongo_store

log = logging.getLogger("BMO.Memory")

# ── Constantes ────────────────────────────────────────────────────────────────

MAX_MSGS_PERSONA   = 6     # sliding window
MAX_CHARS_CONTEXTO = 120   # truncar al guardar

_SYSTEM_CONTENT = (
    "Eres BMO, un robot asistente creado por Zambrano, "
    "un joven programador del SENA apasionado por la tecnología. "
    "Responde siempre en español. Sé amable y directo. "
    "Máximo 2 oraciones para preguntas simples, 4 para explicaciones. "
    "Sin listas, sin markdown, solo texto natural. "
    "Si no sabes algo o la pregunta no tiene sentido, di exactamente: "
    "'No tengo esa información.' y no agregues nada más. "
    "Bandera de Colombia: amarillo arriba, azul medio, rojo abajo. "
    "Capital de Brasil: Brasilia. "
    "Siete maravillas del mundo: la Gran Muralla China, Petra, Cristo Redentor, Machu Picchu, Chichén Itzá, El Coliseo y el Taj Mahal."
)

_SYSTEM_MSG = {"role": "system", "content": _SYSTEM_CONTENT}


# ══════════════════════════════════════════════════════════════════════════════
# Backend MongoDB (único)
# ══════════════════════════════════════════════════════════════════════════════

class _MongoMemory:
    """
    Memoria basada en MongoDB con sliding window de MAX_MSGS_PERSONA mensajes.
    Solo persiste mensajes de personas con cara registrada.
    """

    def __init__(self):
        self.session_memory: list[dict] = []

    def add_user_message(self, content: str, persona: str | None = None):
        if persona:
            self.session_memory.append({"role": "user", "content": content, "persona": persona})
        else:
            # Anónimo: solo el último mensaje en RAM, nunca persiste
            self.session_memory = [{"role": "user", "content": content}]

    def add_assistant_message(self, content: str, persona: str | None = None):
        self.session_memory.append({"role": "assistant", "content": content})

    def get_context_for_llm(self, persona: str | None = None) -> list[dict]:
        system = {**_SYSTEM_MSG}
        if persona:
            system["content"] += f" El usuario se llama {persona}."
        ctx = [system]
        if persona:
            # Historial persistente desde MongoDB (últimos MAX_MSGS_PERSONA)
            ctx.extend(mongo_store.obtener_historial(persona, limit=MAX_MSGS_PERSONA))
            # Sesión actual (últimos 4 mensajes)
            ctx.extend(self.session_memory[-4:])
        else:
            # Anónimo: solo el último mensaje
            ctx.extend(self.session_memory[-1:] if self.session_memory else [])
        return ctx

    def commit_session_to_permanent(self, persona: str | None = None):
        """
        Persiste la sesión en MongoDB.
        Sin persona → descarta todo, no guarda nada.
        """
        if not self.session_memory:
            return
        if persona is None:
            log.debug("[MEMORY] Sin cara reconocida — sesión descartada")
            self.session_memory = []
            return
        for msg in self.session_memory:
            mongo_store.guardar_mensaje(
                role=msg["role"],
                content=msg["content"],
                persona=persona,
            )
        total = mongo_store.contar_mensajes(persona)
        log.debug("[MEMORY] Sesión de '%s' persistida (%d msgs en DB)", persona, total)
        self.session_memory = []

    def clear_session(self):
        self.session_memory = []

    def save_memory(self):
        pass  # MongoDB persiste en tiempo real

    def get_memory_stats(self) -> dict:
        return {"backend": "mongodb", **mongo_store.stats()}


# ── Memoria en RAM para fallback / tests ───────────────────────────────────────

class _RamMemory:
    """Memoria en RAM pura para cuando MongoDB no está disponible."""

    def __init__(self):
        self.session_memory: list[dict] = []
        self._historial: dict[str, list[dict]] = {}

    def add_user_message(self, content: str, persona: str | None = None):
        if persona:
            self.session_memory.append({"role": "user", "content": content})
        else:
            self.session_memory = [{"role": "user", "content": content}]

    def add_assistant_message(self, content: str, persona: str | None = None):
        self.session_memory.append({"role": "assistant", "content": content})

    def get_context_for_llm(self, persona: str | None = None) -> list[dict]:
        system = {**_SYSTEM_MSG}
        if persona:
            system["content"] += f" El usuario se llama {persona}."
        ctx = [system]
        if persona:
            ctx.extend(self._historial.get(persona, []))
            ctx.extend(self.session_memory[-4:])
        else:
            ctx.extend(self.session_memory[-1:] if self.session_memory else [])
        return ctx

    def commit_session_to_permanent(self, persona: str | None = None):
        if not self.session_memory or persona is None:
            self.session_memory = []
            return
        if persona not in self._historial:
            self._historial[persona] = []
        for msg in self.session_memory:
            self._historial[persona].append({"role": msg["role"], "content": _truncar(msg["content"])})
            if len(self._historial[persona]) > MAX_MSGS_PERSONA:
                self._historial[persona].pop(0)
        self.session_memory = []

    def clear_session(self):
        self.session_memory = []

    def save_memory(self):
        pass

    def get_memory_stats(self) -> dict:
        return {"backend": "ram", "personas": len(self._historial)}


# ══════════════════════════════════════════════════════════════════════════════
# Instancia global
# ══════════════════════════════════════════════════════════════════════════════

def _cargar_extras_system_prompt():
    """Agrega system_prompt_extras desde config.json al _SYSTEM_CONTENT."""
    global _SYSTEM_CONTENT, _SYSTEM_MSG
    try:
        cfg_path = Path("config.json")
        if cfg_path.exists():
            with open(cfg_path, encoding="utf-8") as f:
                cfg = json.load(f)
            extras = cfg.get("system_prompt_extras", "")
            if extras:
                _SYSTEM_CONTENT = _SYSTEM_CONTENT.strip() + "\n\n" + extras.strip()
                _SYSTEM_MSG = {"role": "system", "content": _SYSTEM_CONTENT}
    except Exception:
        pass


def _crear_memoria():
    _cargar_extras_system_prompt()
    try:
        from src.config.config_manager import config_manager
        uri = config_manager.get("mongo_uri", "mongodb://localhost:27017")
        db  = config_manager.get("mongo_db",  "bmo_db")
    except Exception:
        uri, db = "mongodb://localhost:27017", "bmo_db"

    if mongo_store.connect(uri, db):
        log.info("[MEMORY] Backend: MongoDB (%s/%s)", uri, db)
        return _MongoMemory()

    log.warning("[MEMORY] MongoDB no disponible, usando RAM")
    return _RamMemory()


persistent_memory = _crear_memoria()


# ══════════════════════════════════════════════════════════════════════════════
# Clase pública para tests (instancias independientes)
# ══════════════════════════════════════════════════════════════════════════════

class PersistentMemory:
    """
    Instancias independientes para tests.
    Usa MongoDB si está disponible, o simula en RAM si no.
    """

    def __init__(self, memory_file: str = "data/chat_memory.json", max_conversations: int = 10):
        # Para tests: usar MongoDB si está disponible, sino simular en RAM
        if mongo_store.is_available():
            self._impl = _MongoMemory()
            self._test_persona_prefix = f"_test_{id(self)}_"
        else:
            # Simulación en RAM para tests sin MongoDB
            self._impl = _RamMemory()
            self._test_persona_prefix = ""

    def add_user_message(self, content, persona=None):
        self._impl.add_user_message(content, persona)

    def add_assistant_message(self, content, persona=None):
        self._impl.add_assistant_message(content, persona)

    def get_context_for_llm(self, persona=None):
        return self._impl.get_context_for_llm(persona)

    def commit_session_to_permanent(self, persona=None):
        self._impl.commit_session_to_permanent(persona)

    def clear_session(self):
        self._impl.clear_session()

    def save_memory(self):
        self._impl.save_memory()

    def get_memory_stats(self):
        return self._impl.get_memory_stats()

    @property
    def session_memory(self):
        return self._impl.session_memory

    @property
    def permanent_memory(self):
        # Compatibilidad con tests que leen permanent_memory
        return [_SYSTEM_MSG] + self._impl.session_memory

