"""
Capa de almacenamiento MongoDB para BMO.

Reemplaza los archivos JSON planos por colecciones MongoDB:
  - personas     : datos de personas + embeddings de caras (reemplaza memory.json)
  - chat_history : historial de conversaciones por persona (con TTL automático)
  - sesiones     : sesión activa actual (reemplaza chat_memory.json en RAM)

Búsqueda de similitud de embeddings:
  MongoDB Community no tiene $vectorSearch (eso es solo Atlas/cloud).
  Para BMO (máximo ~50 personas) la búsqueda coseno con numpy es instantánea
  y no necesita ANN. Los embeddings se guardan como arrays en MongoDB y la
  comparación la hace Python igual que antes.

Fallback automático:
  Si MongoDB no está disponible, el sistema sigue funcionando con los JSON
  originales. Esto garantiza que BMO arranque siempre.
"""
import logging
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Optional

log = logging.getLogger("BMO.Storage")

# ── Conexión ──────────────────────────────────────────────────────────────────

_client = None
_db     = None
_available = False   # False hasta que connect() tenga éxito


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
        from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
        client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        # Ping para verificar que el servidor responde
        client.admin.command("ping")
        _client = client
        _db     = client[db_name]
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
    """Devuelve la colección o lanza si MongoDB no está disponible."""
    if not _available or _db is None:
        raise RuntimeError("MongoDB no disponible")
    return _db[name]


def _ensure_indexes():
    """Crea índices necesarios una sola vez al conectar."""
    try:
        # chat_history: TTL de 30 días sobre el campo 'ts'
        _col("chat_history").create_index(
            "ts",
            expireAfterSeconds=30 * 24 * 3600,
            background=True,
        )
        # chat_history: índice por persona para queries rápidas
        _col("chat_history").create_index("persona", background=True)
        # personas: índice único por nombre (case-insensitive)
        _col("personas").create_index(
            [("nombre", 1)],
            unique=True,
            collation={"locale": "es", "strength": 2},
            background=True,
        )
        log.debug("[MONGO] Índices verificados")
    except Exception as e:
        log.warning("[MONGO] Error creando índices: %s", e)


# ══════════════════════════════════════════════════════════════════════════════
# PERSONAS — reemplaza memory.json
# ══════════════════════════════════════════════════════════════════════════════

def guardar_persona(id_persona: int, nombre: str) -> bool:
    """Crea o actualiza el documento de una persona."""
    try:
        _col("personas").update_one(
            {"_id": id_persona},
            {
                "$set": {
                    "nombre": nombre,
                    "ultima_vez": datetime.now(timezone.utc),
                },
                "$inc": {"visitas": 1},
                "$setOnInsert": {
                    "_id": id_persona,
                    "embeddings": [],
                    "resumen": "",
                },
            },
            upsert=True,
        )
        return True
    except Exception as e:
        log.error("[MONGO] guardar_persona: %s", e)
        return False


def obtener_persona(id_persona: int) -> Optional[dict]:
    """Devuelve el documento completo de una persona o None."""
    try:
        return _col("personas").find_one({"_id": id_persona})
    except Exception as e:
        log.error("[MONGO] obtener_persona: %s", e)
        return None


def obtener_nombre(id_persona: int) -> Optional[str]:
    """Devuelve solo el nombre de una persona."""
    doc = obtener_persona(id_persona)
    return doc["nombre"] if doc else None


def listar_personas() -> dict[int, str]:
    """Devuelve {id: nombre} de todas las personas registradas."""
    try:
        return {
            doc["_id"]: doc["nombre"]
            for doc in _col("personas").find({}, {"nombre": 1})
        }
    except Exception as e:
        log.error("[MONGO] listar_personas: %s", e)
        return {}


def guardar_embeddings(nombre: str, embeddings: list[np.ndarray]) -> bool:
    """
    Guarda los embeddings de cara de una persona.
    Los arrays numpy se serializan como listas de floats para BSON.
    """
    try:
        serialized = [emb.tolist() for emb in embeddings]
        result = _col("personas").update_one(
            {"nombre": {"$regex": f"^{nombre}$", "$options": "i"}},
            {"$set": {"embeddings": serialized}},
        )
        if result.matched_count == 0:
            log.warning("[MONGO] guardar_embeddings: persona '%s' no encontrada", nombre)
            return False
        return True
    except Exception as e:
        log.error("[MONGO] guardar_embeddings: %s", e)
        return False


def cargar_embeddings_todos() -> dict[str, list[np.ndarray]]:
    """
    Carga todos los embeddings de todas las personas.
    Devuelve {nombre: [np.ndarray, ...]}

    La búsqueda de similitud la hace Python con numpy (coseno).
    Para ~50 personas con vectores de 512 dims es instantáneo.
    """
    try:
        resultado: dict[str, list[np.ndarray]] = {}
        for doc in _col("personas").find(
            {"embeddings": {"$exists": True, "$ne": []}},
            {"nombre": 1, "embeddings": 1},
        ):
            nombre = doc["nombre"]
            resultado[nombre] = [
                np.array(e, dtype=np.float32) for e in doc["embeddings"]
            ]
        return resultado
    except Exception as e:
        log.error("[MONGO] cargar_embeddings_todos: %s", e)
        return {}


def buscar_persona_por_similitud(
    embedding_query: np.ndarray,
    umbral: float = 0.55,
) -> Optional[tuple[str, float]]:
    """
    Busca la persona más similar al embedding dado usando similitud coseno.
    Devuelve (nombre, similitud) o None si no supera el umbral.

    Nota: MongoDB Community no tiene $vectorSearch (solo Atlas).
    Para BMO (~50 personas) la búsqueda numpy es suficiente y más rápida
    que una llamada de red a un servidor de vectores.
    """
    todos = cargar_embeddings_todos()
    if not todos:
        return None

    mejor_nombre: Optional[str] = None
    mejor_sim = -1.0
    q_norm = embedding_query / (np.linalg.norm(embedding_query) + 1e-9)

    for nombre, embeddings in todos.items():
        for emb in embeddings:
            e_norm = emb / (np.linalg.norm(emb) + 1e-9)
            sim = float(np.dot(q_norm, e_norm))
            if sim > mejor_sim:
                mejor_sim = sim
                mejor_nombre = nombre

    if mejor_nombre and mejor_sim >= umbral:
        return mejor_nombre, mejor_sim
    return None


# ══════════════════════════════════════════════════════════════════════════════
# HISTORIAL DE CHAT — reemplaza chat_memory.json
# ══════════════════════════════════════════════════════════════════════════════

MAX_MSGS_POR_PERSONA = 40   # máximo de mensajes guardados por persona
MAX_MSGS_CONTEXTO    = 10   # cuántos se pasan al LLM (los más recientes)


def guardar_mensaje(
    role: str,
    content: str,
    persona: Optional[str] = None,
) -> bool:
    """
    Guarda un mensaje en el historial.
    - persona=None → slot anónimo (se sobreescribe, no acumula)
    - persona=str  → historial persistente de esa persona
    """
    try:
        doc = {
            "role":    role,
            "content": content,
            "persona": persona or "_anonimo",
            "ts":      datetime.now(timezone.utc),
        }
        _col("chat_history").insert_one(doc)

        # Mantener límite de mensajes por persona
        _limpiar_historial_persona(persona or "_anonimo")
        return True
    except Exception as e:
        log.error("[MONGO] guardar_mensaje: %s", e)
        return False


def _limpiar_historial_persona(persona: str):
    """Elimina mensajes viejos si se supera MAX_MSGS_POR_PERSONA."""
    try:
        col = _col("chat_history")
        total = col.count_documents({"persona": persona})
        if total > MAX_MSGS_POR_PERSONA:
            # Obtener IDs de los más viejos a eliminar
            exceso = total - MAX_MSGS_POR_PERSONA
            viejos = list(
                col.find({"persona": persona}, {"_id": 1})
                   .sort("ts", 1)
                   .limit(exceso)
            )
            ids = [d["_id"] for d in viejos]
            col.delete_many({"_id": {"$in": ids}})
    except Exception as e:
        log.warning("[MONGO] _limpiar_historial_persona: %s", e)


def obtener_historial(
    persona: Optional[str] = None,
    limit: int = MAX_MSGS_CONTEXTO,
) -> list[dict]:
    """
    Devuelve los últimos `limit` mensajes de una persona (o anónimo).
    Formato compatible con el contexto del LLM: [{"role": ..., "content": ...}]
    """
    try:
        slot = persona or "_anonimo"
        docs = list(
            _col("chat_history")
            .find({"persona": slot}, {"role": 1, "content": 1, "_id": 0})
            .sort("ts", -1)
            .limit(limit)
        )
        # Invertir para orden cronológico (más viejo primero)
        docs.reverse()
        return docs
    except Exception as e:
        log.error("[MONGO] obtener_historial: %s", e)
        return []


def limpiar_historial_anonimo():
    """Borra todos los mensajes del slot anónimo (al cerrar sesión)."""
    try:
        _col("chat_history").delete_many({"persona": "_anonimo"})
    except Exception as e:
        log.warning("[MONGO] limpiar_historial_anonimo: %s", e)


def stats() -> dict:
    """Estadísticas de uso de la base de datos."""
    try:
        return {
            "personas":      _col("personas").count_documents({}),
            "mensajes_total": _col("chat_history").count_documents({}),
            "mensajes_anonimo": _col("chat_history").count_documents({"persona": "_anonimo"}),
        }
    except Exception as e:
        log.error("[MONGO] stats: %s", e)
        return {}
