"""
Sistema de Memoria Persistente para BMO.

Reglas de negocio:
  1. Solo se guarda historial de personas con cara registrada (persona != None).
     Sin cara reconocida → la sesión se descarta al terminar, no persiste nada.
  2. Máximo 6 mensajes por persona (sliding window).
     Al llegar el 7mo, el más viejo se borra automáticamente.
  3. Se guarda solo el contexto (primeros ~120 chars), no el mensaje completo.
  4. Anónimo: solo el último intercambio en RAM, nunca toca disco ni MongoDB.

Backends:
  - MongoDB (preferido): colección chat_history con sliding window
  - JSON (fallback):     data/chat_memory.json cuando MongoDB no está disponible
"""
import json
import logging
from pathlib import Path
from datetime import datetime
import atexit

from src.storage import mongo_store

log = logging.getLogger("BMO.Memory")

# ── Constantes ────────────────────────────────────────────────────────────────

JSON_FILE          = Path("data/chat_memory.json")
MAX_MSGS_PERSONA   = 6     # sliding window — máximo mensajes guardados por persona
MAX_CHARS_CONTEXTO = 120   # truncar mensajes al guardar (solo contexto)

_SYSTEM_CONTENT = (
    "Eres BMO, un robot asistente creado por Zambrano, "
    "un joven programador del SENA apasionado por la tecnología. "
    "Responde siempre en español. Sé amable y directo. "
    "Máximo 2 oraciones para preguntas simples, 4 para explicaciones. "
    "Sin listas, sin markdown, solo texto natural. "
    "Si no sabes algo o la pregunta no tiene sentido, di exactamente: "
    "'No tengo esa información.' y no agregues nada más. "
    "Bandera de Colombia: amarillo arriba, azul medio, rojo abajo. "
    "Capital de Brasil: Brasilia."
)

_SYSTEM_MSG = {"role": "system", "content": _SYSTEM_CONTENT}


def _truncar(texto: str) -> str:
    """Guarda solo el contexto esencial, no el mensaje completo."""
    texto = texto.strip()
    if len(texto) <= MAX_CHARS_CONTEXTO:
        return texto
    corte = texto.rfind(" ", 0, MAX_CHARS_CONTEXTO)
    if corte < MAX_CHARS_CONTEXTO // 2:
        corte = MAX_CHARS_CONTEXTO
    return texto[:corte] + "…"


# ══════════════════════════════════════════════════════════════════════════════
# Backend JSON (fallback cuando MongoDB no está disponible)
# ══════════════════════════════════════════════════════════════════════════════

class _JsonMemory:
    """
    Memoria basada en JSON con sliding window de MAX_MSGS_PERSONA mensajes.
    Solo persiste mensajes de personas con cara registrada.
    """

    def __init__(self):
        self.session_memory: list[dict] = []
        # {persona: [msg, msg, ...]} — máx MAX_MSGS_PERSONA por persona
        self._historial: dict[str, list[dict]] = {}
        self._cargar()
        atexit.register(self._guardar)

    def _cargar(self):
        if not JSON_FILE.exists():
            return
        try:
            data = json.loads(JSON_FILE.read_text(encoding="utf-8"))
            # Formato: {"persona": [{"role":..., "content":...}, ...]}
            if isinstance(data, dict) and "historial" in data:
                self._historial = data["historial"]
            # Compatibilidad con formato antiguo (lista de mensajes)
            elif isinstance(data, list):
                log.info("[MEMORY/JSON] Formato antiguo detectado, migrando...")
                self._historial = {}
            log.info("[MEMORY/JSON] Historial cargado: %d personas", len(self._historial))
        except Exception as e:
            log.warning("[MEMORY/JSON] Error al cargar: %s", e)
            self._historial = {}

    def _guardar(self):
        try:
            JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
            JSON_FILE.write_text(
                json.dumps({"historial": self._historial}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            log.error("[MEMORY/JSON] Error al guardar: %s", e)

    def _agregar_a_historial(self, persona: str, role: str, content: str):
        """Agrega un mensaje al historial de una persona con sliding window."""
        if persona not in self._historial:
            self._historial[persona] = []
        msgs = self._historial[persona]
        msgs.append({"role": role, "content": _truncar(content)})
        # Sliding window: si supera el límite, borrar el más viejo
        if len(msgs) > MAX_MSGS_PERSONA:
            msgs.pop(0)
        self._historial[persona] = msgs

    # ── Interfaz pública ──────────────────────────────────────────────────────

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
            # Historial persistente de esta persona (últimos MAX_MSGS_PERSONA)
            ctx.extend(self._historial.get(persona, []))
            # Sesión actual (últimos 4 mensajes de la sesión en curso)
            ctx.extend(self.session_memory[-4:])
        else:
            # Anónimo: solo el último mensaje de sesión
            ctx.extend(self.session_memory[-1:] if self.session_memory else [])
        return ctx

    def commit_session_to_permanent(self, persona: str | None = None):
        """
        Persiste la sesión actual.
        Sin persona (cara no reconocida) → descarta todo, no guarda nada.
        """
        if not self.session_memory:
            return
        if persona is None:
            log.debug("[MEMORY/JSON] Sin cara reconocida — sesión descartada")
            self.session_memory = []
            return
        # Guardar cada mensaje de la sesión con sliding window
        for msg in self.session_memory:
            self._agregar_a_historial(persona, msg["role"], msg["content"])
        self.session_memory = []
        self._guardar()
        log.debug("[MEMORY/JSON] Sesión de '%s' persistida (%d msgs en historial)",
                  persona, len(self._historial.get(persona, [])))

    def clear_session(self):
        self.session_memory = []

    def save_memory(self):
        self._guardar()

    def get_memory_stats(self) -> dict:
        return {
            "backend":          "json",
            "personas":         len(self._historial),
            "session_messages": len(self.session_memory),
            "historial":        {p: len(m) for p, m in self._historial.items()},
        }


# ══════════════════════════════════════════════════════════════════════════════
# Backend MongoDB
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
            # Anónimo: solo el último mensaje en RAM
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
            # Sesión actual
            ctx.extend(self.session_memory[-4:])
        else:
            # Anónimo: solo el último mensaje
            ctx.extend(self.session_memory[-1:] if self.session_memory else [])
        return ctx

    def commit_session_to_permanent(self, persona: str | None = None):
        """
        Persiste la sesión actual en MongoDB.
        Sin persona (cara no reconocida) → descarta todo, no guarda nada.
        """
        if not self.session_memory:
            return
        if persona is None:
            log.debug("[MEMORY/MONGO] Sin cara reconocida — sesión descartada")
            self.session_memory = []
            return
        # Guardar cada mensaje — mongo_store aplica el sliding window
        for msg in self.session_memory:
            mongo_store.guardar_mensaje(
                role=msg["role"],
                content=msg["content"],
                persona=persona,
            )
        total = mongo_store.contar_mensajes(persona)
        log.debug("[MEMORY/MONGO] Sesión de '%s' persistida (%d msgs en DB)", persona, total)
        self.session_memory = []

    def clear_session(self):
        self.session_memory = []

    def save_memory(self):
        pass  # MongoDB persiste en tiempo real

    def get_memory_stats(self) -> dict:
        return {"backend": "mongodb", **mongo_store.stats()}


# ══════════════════════════════════════════════════════════════════════════════
# Instancia global — elige el backend automáticamente
# ══════════════════════════════════════════════════════════════════════════════

def _crear_memoria():
    try:
        from src.config.config_manager import config_manager
        uri = config_manager.get("mongo_uri", "mongodb://localhost:27017")
        db  = config_manager.get("mongo_db",  "bmo_db")
    except Exception:
        uri, db = "mongodb://localhost:27017", "bmo_db"

    if mongo_store.connect(uri, db):
        log.info("[MEMORY] Backend: MongoDB (%s/%s)", uri, db)
        return _MongoMemory()
    log.info("[MEMORY] Backend: JSON (%s)", JSON_FILE)
    return _JsonMemory()


persistent_memory = _crear_memoria()


# ══════════════════════════════════════════════════════════════════════════════
# Clase pública para tests (instancias independientes, siempre JSON)
# ══════════════════════════════════════════════════════════════════════════════

class PersistentMemory:
    """
    Instancias independientes para tests unitarios.
    Siempre usa el backend JSON (no depende de MongoDB).
    """

    def __init__(self, memory_file: str = "data/chat_memory.json", max_conversations: int = 10):
        impl = _JsonMemory.__new__(_JsonMemory)
        impl.session_memory = []
        impl._historial     = {}
        # Redirigir guardado al archivo de test
        _path = Path(memory_file)
        import types

        def _save_test(self_inner):
            try:
                _path.parent.mkdir(parents=True, exist_ok=True)
                _path.write_text(
                    json.dumps({"historial": self_inner._historial}, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            except Exception as e:
                log.error("[MEMORY/JSON] Error al guardar test: %s", e)

        impl._guardar    = types.MethodType(_save_test, impl)
        impl.save_memory = types.MethodType(_save_test, impl)
        self._impl = impl

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
        system = [{**_SYSTEM_MSG}]
        for msgs in self._impl._historial.values():
            system.extend(msgs)
        return system
