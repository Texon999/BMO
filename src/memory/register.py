"""
Registro de personas y embeddings faciales para BMO.

Usa MongoDB si está disponible (via mongo_store), JSON como fallback.
La interfaz pública es idéntica en ambos casos.

Estructura MongoDB (colección 'personas'):
  {
    _id:        int,          # ID numérico de la persona
    nombre:     str,
    visitas:    int,
    ultima_vez: datetime,
    embeddings: [[float, ...], ...]   # arrays de 512 dims
  }

Estructura JSON fallback (data/memory.json):
  { "0": { nombre, visitas, ultima_vez, embeddings: [[...]] }, ... }
"""
import json
import logging
import datetime
from pathlib import Path

import numpy as np

from src.storage import mongo_store

log = logging.getLogger("BMO")

MEMORY_FILE    = Path("data/memory.json")
MAX_TURNS      = 6
ANON_MAX_TURNS = 6

# Caché JSON en RAM
_memoria_cache: dict | None = None


# ── Helpers JSON ──────────────────────────────────────────────────────────────

def _load() -> dict:
    global _memoria_cache
    if _memoria_cache is not None:
        return _memoria_cache
    if MEMORY_FILE.exists():
        try:
            _memoria_cache = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
            return _memoria_cache
        except json.JSONDecodeError as e:
            log.error("memory.json corrupto: %s", e)
    _memoria_cache = {}
    return {}


def _save(data: dict):
    global _memoria_cache
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
    _memoria_cache = None


# ── Personas ──────────────────────────────────────────────────────────────────

def guardar_persona(id_persona: int, nombre: str):
    """Registra o actualiza una persona."""
    if mongo_store.is_available():
        mongo_store.guardar_persona(id_persona, nombre)
    # Siempre actualiza JSON también (sirve de backup y para vision.py)
    memoria = _load()
    key = str(id_persona)
    entrada = memoria.get(key, {})
    entrada.update({
        "nombre":     nombre,
        "visitas":    entrada.get("visitas", 0) + 1,
        "ultima_vez": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    entrada.setdefault("embeddings", [])
    memoria[key] = entrada
    _save(memoria)


def obtener_nombre(id_persona: int) -> str | None:
    if mongo_store.is_available():
        nombre = mongo_store.obtener_nombre(id_persona)
        if nombre:
            return nombre
    memoria = _load()
    entry = memoria.get(str(id_persona))
    return entry["nombre"] if entry else None


def nombres_a_ids() -> dict[str, str]:
    """Devuelve {id_str: nombre} de todas las personas."""
    if mongo_store.is_available():
        mongo_personas = mongo_store.listar_personas()
        if mongo_personas:
            return {str(k): v for k, v in mongo_personas.items()}
    memoria = _load()
    return {k: v["nombre"] for k, v in memoria.items() if isinstance(v, dict) and "nombre" in v}


def cargar_personas() -> dict:
    return _load()


# ── Embeddings ────────────────────────────────────────────────────────────────

def guardar_embeddings_persona(nombre: str, embeddings: list[np.ndarray]) -> None:
    """
    Guarda los embeddings de cara de una persona.
    Persiste en MongoDB Y en JSON (doble escritura para robustez).
    """
    if mongo_store.is_available():
        mongo_store.guardar_embeddings(nombre, embeddings)

    # JSON backup
    memoria = _load()
    for key, entry in memoria.items():
        if entry.get("nombre", "").lower() == nombre.lower():
            memoria[key]["embeddings"] = [emb.tolist() for emb in embeddings]
            _save(memoria)
            return
    log.warning("guardar_embeddings_persona: '%s' no encontrada en JSON", nombre)


def cargar_embeddings_todos() -> dict[str, list[np.ndarray]]:
    """
    Carga todos los embeddings para reconocimiento facial.
    Prefiere MongoDB; cae a JSON si no está disponible.
    """
    if mongo_store.is_available():
        resultado = mongo_store.cargar_embeddings_todos()
        if resultado:
            return resultado
        # MongoDB disponible pero vacío → intentar JSON como fuente inicial
        log.debug("[REGISTER] MongoDB sin embeddings, intentando JSON")

    memoria = _load()
    resultado: dict[str, list[np.ndarray]] = {}
    for key, entry in memoria.items():
        if key == "_anonimo" or "embeddings" not in entry:
            continue
        nombre = entry.get("nombre", key)
        resultado[nombre] = [np.array(e, dtype=np.float32) for e in entry["embeddings"]]
    return resultado


# ── Contexto de conversación (legacy, usado por vision.py) ───────────────────

def obtener_contexto_persona(nombre: str) -> str:
    memoria = _load()
    for entry in memoria.values():
        if isinstance(entry, dict) and entry.get("nombre", "").lower() == nombre.lower():
            resumen = entry.get("resumen", "").strip()
            return f"Lo último que hablaste con {nombre}: {resumen}" if resumen else ""
    return ""


def agregar_turno_persona(nombre: str, user_msg: str, assistant_msg: str):
    memoria = _load()
    key = next(
        (k for k, e in memoria.items()
         if isinstance(e, dict) and e.get("nombre", "").lower() == nombre.lower()),
        None,
    )
    if key is None:
        return
    turnos = memoria[key].get("turnos_recientes", [])
    turnos.append({"user": user_msg, "assistant": assistant_msg})
    turnos = turnos[-MAX_TURNS:]
    memoria[key]["turnos_recientes"] = turnos
    memoria[key]["resumen"] = " / ".join(
        f"Usuario: {t['user']} | BMO: {t['assistant']}" for t in turnos
    )
    _save(memoria)


def agregar_turno_anonimo(user_msg: str, assistant_msg: str):
    memoria = _load()
    memoria.setdefault("_anonimo", {"turnos_recientes": []})
    turnos = memoria["_anonimo"].get("turnos_recientes", [])
    turnos.append({"user": user_msg, "assistant": assistant_msg})
    memoria["_anonimo"]["turnos_recientes"] = turnos[-ANON_MAX_TURNS:]
    _save(memoria)


def obtener_contexto_anonimo() -> str:
    memoria = _load()
    turnos = memoria.get("_anonimo", {}).get("turnos_recientes", [])
    if not turnos:
        return ""
    return "Conversación reciente: " + " / ".join(
        f"Usuario: {t['user']} | BMO: {t['assistant']}" for t in turnos
    )
