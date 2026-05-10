"""
Sistema de Memoria Persistente para BMO.

Usa MongoDB si está disponible, JSON como fallback automático.
La interfaz pública es idéntica en ambos casos — el resto del código
no necesita saber qué backend está activo.

Colecciones MongoDB:
  - chat_history : mensajes con TTL de 30 días, máx 40 por persona
  - personas     : datos + embeddings (ver mongo_store.py)

Fallback JSON:
  - data/chat_memory.json : historial de sesión actual
"""
import json
import logging
from pathlib import Path
from datetime import datetime
import atexit

from src.storage import mongo_store

log = logging.getLogger("BMO.Memory")

# ── Configuración ─────────────────────────────────────────────────────────────

JSON_FILE  = Path("data/chat_memory.json")

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


# ══════════════════════════════════════════════════════════════════════════════
# Backend JSON (fallback)
# ══════════════════════════════════════════════════════════════════════════════

class _JsonMemory:
    """
    Memoria basada en JSON — idéntica al comportamiento anterior.
    Se usa cuando MongoDB no está disponible.
    """

    def __init__(self):
        self.permanent_memory: list[dict] = []
        self.session_memory:   list[dict] = []
        self._load()
        atexit.register(self.save_memory)

    def _load(self):
        if JSON_FILE.exists():
            try:
                data = json.loads(JSON_FILE.read_text(encoding="utf-8"))
                self.permanent_memory = data if isinstance(data, list) else data.get("permanent", [])
                log.info("[MEMORY/JSON] %d mensajes cargados", len(self.permanent_memory))
            except Exception as e:
                log.warning("[MEMORY/JSON] Error al cargar: %s", e)
                self.permanent_memory = []
        if not self.permanent_memory or self.permanent_memory[0].get("role") != "system":
            self.permanent_memory.insert(0, {**_SYSTEM_MSG, "timestamp": datetime.now().isoformat()})

    def add_user_message(self, content: str, persona: str | None = None):
        msg = {"role": "user", "content": content, "timestamp": datetime.now().isoformat()}
        if persona:
            msg["persona"] = persona
            self.session_memory.append(msg)
        else:
            self.session_memory = [msg]   # anónimo: sobrescribe

    def add_assistant_message(self, content: str, persona: str | None = None):
        self.session_memory.append({
            "role": "assistant", "content": content,
            "timestamp": datetime.now().isoformat(),
        })

    def get_context_for_llm(self, persona: str | None = None) -> list[dict]:
        system = {**_SYSTEM_MSG}
        if persona:
            system["content"] += f" El usuario se llama {persona}."
        ctx = [system]
        if persona:
            history = [
                m for m in self.permanent_memory[1:]
                if m.get("persona") == persona or m.get("role") == "assistant"
                   or "persona" not in m
            ]
            ctx.extend(history[-6:])
            ctx.extend(self.session_memory[-4:])
        else:
            ctx.extend(self.session_memory)
        return ctx

    def commit_session_to_permanent(self, persona: str | None = None):
        if not self.session_memory:
            return
        if persona is None:
            self.session_memory = []
            return
        for msg in self.session_memory:
            if msg.get("role") == "user" and "persona" not in msg:
                msg["persona"] = persona
        self.permanent_memory.extend(self.session_memory)
        self._trim()
        self.session_memory = []
        self.save_memory()

    def _trim(self, max_conv: int = 20):
        system = self.permanent_memory[:1]
        rest   = self.permanent_memory[1:]
        users  = [i for i, m in enumerate(rest) if m.get("role") == "user"]
        if len(users) > max_conv:
            rest = rest[users[-max_conv]:]
        self.permanent_memory = system + rest

    def save_memory(self):
        try:
            JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
            JSON_FILE.write_text(
                json.dumps(self.permanent_memory, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            log.error("[MEMORY/JSON] Error al guardar: %s", e)

    def clear_session(self):
        self.session_memory = []

    def get_memory_stats(self) -> dict:
        return {
            "backend": "json",
            "permanent_messages": len(self.permanent_memory),
            "session_messages":   len(self.session_memory),
        }


# ══════════════════════════════════════════════════════════════════════════════
# Backend MongoDB
# ══════════════════════════════════════════════════════════════════════════════

class _MongoMemory:
    """
    Memoria basada en MongoDB.
    - Historial persistente por persona en la colección chat_history.
    - Sesión activa en RAM (igual que antes), se persiste al hacer commit.
    - Anónimo: solo el último intercambio en RAM, nunca persiste.
    """

    def __init__(self):
        self.session_memory: list[dict] = []

    def add_user_message(self, content: str, persona: str | None = None):
        if persona:
            self.session_memory.append({
                "role": "user", "content": content, "persona": persona,
            })
        else:
            # Anónimo: sobrescribe la sesión
            self.session_memory = [{"role": "user", "content": content}]

    def add_assistant_message(self, content: str, persona: str | None = None):
        self.session_memory.append({"role": "assistant", "content": content})

    def get_context_for_llm(self, persona: str | None = None) -> list[dict]:
        system = {**_SYSTEM_MSG}
        if persona:
            system["content"] += f" El usuario se llama {persona}."

        ctx = [system]

        if persona:
            # Historial permanente de esta persona desde MongoDB
            history = mongo_store.obtener_historial(persona, limit=6)
            ctx.extend(history)
            # Sesión actual (últimos 4 mensajes)
            ctx.extend(self.session_memory[-4:])
        else:
            # Anónimo: solo el último mensaje de sesión
            ctx.extend(self.session_memory)

        return ctx

    def commit_session_to_permanent(self, persona: str | None = None):
        if not self.session_memory:
            return
        if persona is None:
            # Anónimo: no persiste
            self.session_memory = []
            return
        # Guardar cada mensaje de la sesión en MongoDB
        for msg in self.session_memory:
            mongo_store.guardar_mensaje(
                role=msg["role"],
                content=msg["content"],
                persona=persona,
            )
        self.session_memory = []
        log.debug("[MEMORY/MONGO] Sesión de '%s' persistida", persona)

    def clear_session(self):
        self.session_memory = []

    def save_memory(self):
        pass   # MongoDB persiste en tiempo real, no hay nada que hacer

    def get_memory_stats(self) -> dict:
        return {"backend": "mongodb", **mongo_store.stats()}


# ══════════════════════════════════════════════════════════════════════════════
# Instancia global — elige el backend automáticamente
# ══════════════════════════════════════════════════════════════════════════════

def _crear_memoria():
    """Intenta MongoDB (URI desde config.json), cae a JSON si no está disponible."""
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


# ── Clase pública para tests (instancias independientes) ─────────────────────

class PersistentMemory:
    """
    Wrapper público para crear instancias independientes en tests.
    Siempre usa JSON (no depende de MongoDB para tests unitarios).
    """

    def __init__(self, memory_file: str = "data/chat_memory.json", max_conversations: int = 10):
        self._impl = _JsonMemory.__new__(_JsonMemory)
        self._impl.permanent_memory = []
        self._impl.session_memory   = []
        self._impl.JSON_FILE = Path(memory_file)   # type: ignore[attr-defined]
        # Monkey-patch para que use el archivo correcto
        import types
        def _save(self_inner):
            try:
                self_inner.JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
                self_inner.JSON_FILE.write_text(
                    json.dumps(self_inner.permanent_memory, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            except Exception as e:
                log.error("[MEMORY/JSON] Error al guardar: %s", e)
        self._impl.save_memory = types.MethodType(_save, self._impl)
        self._impl.permanent_memory.insert(0, {
            **_SYSTEM_MSG, "timestamp": datetime.now().isoformat()
        })

    # Delegar todo al impl
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
        return self._impl.permanent_memory
