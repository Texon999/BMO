"""
Módulo de memoria de BMO.
Unifica persons.json y names.json en un solo archivo data/memory.json
y gestiona el historial de conversación.
"""
import json
import datetime
from pathlib import Path


MEMORY_FILE = Path("data/memory.json")
CHAT_FILE   = Path("data/chat_history.json")
MAX_HISTORY = 20  # turnos máximos en memoria de conversación


def _load(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ── Personas ──────────────────────────────────────────────────────────────────

def cargar_personas() -> dict:
    """Devuelve {str(id): {nombre, visitas, ultima_vez}}"""
    return _load(MEMORY_FILE)


def guardar_persona(id_persona: int, nombre: str):
    """Registra o actualiza una persona en memoria."""
    memoria = cargar_personas()
    key = str(id_persona)
    visitas = memoria.get(key, {}).get("visitas", 0) + 1
    memoria[key] = {
        "nombre": nombre,
        "visitas": visitas,
        "ultima_vez": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _save(MEMORY_FILE, memoria)


def obtener_nombre(id_persona: int) -> str | None:
    memoria = cargar_personas()
    entry = memoria.get(str(id_persona))
    return entry["nombre"] if entry else None


def nombres_a_ids() -> dict:
    """Devuelve {str(id): nombre} — compatible con VisionBMO."""
    memoria = cargar_personas()
    return {k: v["nombre"] for k, v in memoria.items()}


# ── Historial de chat ─────────────────────────────────────────────────────────

def cargar_historial() -> list:
    data = _load(CHAT_FILE)
    return data.get("messages", [])


def agregar_mensaje(role: str, content: str):
    """Agrega un mensaje al historial y recorta si excede MAX_HISTORY."""
    data = _load(CHAT_FILE)
    messages = data.get("messages", [])
    messages.append({
        "role": role,
        "content": content,
        "timestamp": datetime.datetime.now().isoformat(),
    })
    # Mantener solo los últimos MAX_HISTORY turnos (user+assistant = 1 turno)
    if len(messages) > MAX_HISTORY * 2:
        messages = messages[-(MAX_HISTORY * 2):]
    _save(CHAT_FILE, {"messages": messages})


def limpiar_historial():
    _save(CHAT_FILE, {"messages": []})


def historial_para_llm() -> list:
    """Devuelve el historial en formato [{role, content}] para Ollama."""
    return [
        {"role": m["role"], "content": m["content"]}
        for m in cargar_historial()
    ]
