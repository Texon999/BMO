"""
Capa de almacenamiento MongoDB para BMO.

Colecciones:
  - personas     : datos + embeddings de caras
  - chat_history : últimos 6 mensajes por persona (sliding window)

Reglas de negocio:
  - Solo se guarda historial de personas con cara registrada (persona != None)
  - Máximo 6 mensajes por persona — al llegar el 7mo se borra el más viejo
  - Se guarda solo el contexto (primeros 120 chars), no el mensaje completo
  - Sin cara reconocida → no se persiste nada

Búsqueda de embeddings:
  MongoDB Community no tiene $vectorSearch local (solo Atlas/cloud).
  Para BMO (~50 personas, vectores 512 dims) la búsqueda coseno con numpy
  es instantánea y no necesita ANN.

Fallback:
  Si MongoDB no está disponible, is_available() devuelve False y el resto
  del sistema usa JSON automáticamente.
"""
import logging
import numpy as np
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger("BMO.Storage")

# ── Conexión ──────────────────────────────────────────────────────────────────

_client    = None
_db        = None
_available = False

# Límite de mensajes guardados por persona (sliding window)
MAX_MSGS_POR_PERSONA = 6


def connect(uri: str = "mongodb://localhost:27017", db_name: str = "bmo_db") -> bool:
    """
    Intenta conectar a MongoDB. Devuelve True si tuvo éxito.
    Seguro de llamar múltiples veces — reutiliza la conexión existente.
    """
    global _client, _db, _available
    if _available:
        return True
    try:
        from pymongo import MongoClient
        client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
        _client    = client
        _db        = client[db_name]
        _available = True
        _ensure_indexes()
        log.info("[MONGO] Conectado a %s / %s", uri, db_name)
        return True
    except Exception as e:
        log.warning("[MONGO] No disponible (%s) — usando JSON como fallback", e)
        _available = False
        return False


def is_available() -> bool:
    return _available


def _col(name: str):
    if not _available or _db is None:
        raise RuntimeError("MongoDB no disponible")
    return _db[name]


def _ensure_indexes():
    """Crea índices al conectar. Idempotente."""
    try:
        # TTL de 90 días sobre 'ts' (limpieza automática de mensajes viejos)
        _col("chat_history").create_index(
            "ts", expireAfterSeconds=90 * 24 * 3600, background=True,
        )
        # Índice compuesto (persona, ts) para queries y ordenamiento eficiente
        _col("chat_history").create_index(
            [("persona", 1), ("ts", 1)], background=True,
        )
        # Personas: índice único por nombre (case-insensitive español)
        _col("personas").create_index(
            [("nombre", 1)],
            unique=True,
            collation={"locale": "es", "strength": 2},
            background=True,
        )
        log.debug("[MONGO] Índices verificados")
    except Exception as e:
        log.warning("[MONGO] Error creando índices: %s", e)


# ── Utilidad: truncar contenido ───────────────────────────────────────────────

def _contexto(texto: str, max_chars: int = 120) -> str:
    """
    Guarda solo el contexto esencial del mensaje, no el texto completo.
    Trunca a max_chars y agrega '…' si fue recortado.
    """
    texto = texto.strip()
    if len(texto) <= max_chars:
        return texto
    # Cortar en el último espacio antes del límite para no partir palabras
    corte = texto.rfind(" ", 0, max_chars)
    if corte < max_chars // 2:
        corte = max_chars
    return texto[:corte] + "…"


# ══════════════════════════════════════════════════════════════════════════════
# PERSONAS
# ══════════════════════════════════════════════════════════════════════════════

def guardar_persona(id_persona: int, nombre: str) -> bool:
    """Crea o actualiza el documento de una persona."""
    try:
        _col("personas").update_one(
            {"_id": id_persona},
            {
                "$set":         {"nombre": nombre, "ultima_vez": datetime.now(timezone.utc)},
                "$inc":         {"visitas": 1},
                "$setOnInsert": {"_id": id_persona, "embeddings": []},
            },
            upsert=True,
        )
        return True
    except Exception as e:
        log.error("[MONGO] guardar_persona: %s", e)
        return False


def obtener_persona(id_persona: int) -> Optional[dict]:
    try:
        return _col("personas").find_one({"_id": id_persona})
    except Exception as e:
        log.error("[MONGO] obtener_persona: %s", e)
        return None


def obtener_nombre(id_persona: int) -> Optional[str]:
    doc = obtener_persona(id_persona)
    return doc["nombre"] if doc else None


def listar_personas() -> dict[int, str]:
    try:
        return {doc["_id"]: doc["nombre"]
                for doc in _col("personas").find({}, {"nombre": 1})}
    except Exception as e:
        log.error("[MONGO] listar_personas: %s", e)
        return {}


# ── Embeddings ────────────────────────────────────────────────────────────────

def guardar_embeddings(nombre: str, embeddings: list[np.ndarray]) -> bool:
    """
    Guarda los embeddings de cara de una persona (serializa numpy → lista de floats).
    """
    try:
        serialized = [emb.tolist() for emb in embeddings]
        result = _col("personas").update_one(
            {"nombre": {"$regex": f"^{nombre}$", "$options": "i"}},
            {"$set": {"embeddings": serialized}},
        )
        if result.matched_count == 0:
            log.warning("[MONGO] guardar_embeddings: '%s' no encontrada", nombre)
            return False
        log.info("[MONGO] Embeddings guardados para '%s' (%d vectores)", nombre, len(embeddings))
        return True
    except Exception as e:
        log.error("[MONGO] guardar_embeddings: %s", e)
        return False


def cargar_embeddings_todos() -> dict[str, list[np.ndarray]]:
    """
    Carga todos los embeddings para reconocimiento facial.
    Devuelve {nombre: [np.ndarray(512), ...]}
    """
    try:
        resultado: dict[str, list[np.ndarray]] = {}
        for doc in _col("personas").find(
            {"embeddings": {"$exists": True, "$ne": []}},
            {"nombre": 1, "embeddings": 1},
        ):
            resultado[doc["nombre"]] = [
                np.array(e, dtype=np.float32) for e in doc["embeddings"]
            ]
        return resultado
    except Exception as e:
        log.error("[MONGO] cargar_embeddings_todos: %s", e)
        return {}


# ══════════════════════════════════════════════════════════════════════════════
# HISTORIAL DE CHAT — sliding window de 6 mensajes por persona
# ══════════════════════════════════════════════════════════════════════════════

def guardar_mensaje(role: str, content: str, persona: str) -> bool:
    """
    Guarda un mensaje en el historial de una persona registrada.

    IMPORTANTE: solo acepta personas con cara registrada (persona != None).
    El contenido se trunca a 120 chars (solo contexto, no mensaje completo).
    Al superar MAX_MSGS_POR_PERSONA (6), borra el más viejo automáticamente.
    """
    try:
        col = _col("chat_history")

        # Insertar el nuevo mensaje
        col.insert_one({
            "role":    role,
            "content": _contexto(content),   # solo el contexto, no el texto completo
            "persona": persona,
            "ts":      datetime.now(timezone.utc),
        })

        # Sliding window: si hay más de MAX_MSGS_POR_PERSONA, borrar el más viejo
        total = col.count_documents({"persona": persona})
        if total > MAX_MSGS_POR_PERSONA:
            mas_viejo = col.find_one(
                {"persona": persona},
                sort=[("ts", 1)],   # el más antiguo primero
            )
            if mas_viejo:
                col.delete_one({"_id": mas_viejo["_id"]})
                log.debug("[MONGO] Sliding window: borrado mensaje viejo de '%s'", persona)

        return True
    except Exception as e:
        log.error("[MONGO] guardar_mensaje: %s", e)
        return False


def obtener_historial(persona: str, limit: int = MAX_MSGS_POR_PERSONA) -> list[dict]:
    """
    Devuelve los últimos `limit` mensajes de una persona en orden cronológico.
    Formato: [{"role": "user"|"assistant", "content": "..."}]
    """
    try:
        docs = list(
            _col("chat_history")
            .find({"persona": persona}, {"role": 1, "content": 1, "_id": 0})
            .sort("ts", -1)
            .limit(limit)
        )
        docs.reverse()   # orden cronológico (más viejo primero)
        return docs
    except Exception as e:
        log.error("[MONGO] obtener_historial: %s", e)
        return []


def contar_mensajes(persona: str) -> int:
    """Cuenta cuántos mensajes tiene guardados una persona."""
    try:
        return _col("chat_history").count_documents({"persona": persona})
    except Exception as e:
        log.error("[MONGO] contar_mensajes: %s", e)
        return 0


def stats() -> dict:
    """Estadísticas de la base de datos."""
    try:
        personas_con_emb = _col("personas").count_documents(
            {"embeddings": {"$exists": True, "$ne": []}}
        )
        return {
            "personas_total":       _col("personas").count_documents({}),
            "personas_con_embeddings": personas_con_emb,
            "mensajes_total":       _col("chat_history").count_documents({}),
        }
    except Exception as e:
        log.error("[MONGO] stats: %s", e)
        return {}
