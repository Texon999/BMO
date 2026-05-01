"""
Módulo de memoria de BMO.
- Cada persona registrada tiene su propio resumen de conversación.
- No hay historial global — evita contaminar el contexto del LLM.
- El resumen se actualiza al final de cada conversación con una persona.
"""
import json
import datetime
from pathlib import Path

MEMORY_FILE = Path("data/memory.json")
MAX_TURNS   = 6   # turnos recientes para generar el resumen (user+assistant)


def _load() -> dict:
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(data: dict):
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ── Personas ──────────────────────────────────────────────────────────────────

def cargar_personas() -> dict:
    return _load()


def guardar_persona(id_persona: int, nombre: str):
    memoria = _load()
    key = str(id_persona)
    visitas = memoria.get(key, {}).get("visitas", 0) + 1
    entrada = memoria.get(key, {})
    entrada.update({
        "nombre": nombre,
        "visitas": visitas,
        "ultima_vez": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    if "resumen" not in entrada:
        entrada["resumen"] = ""
    if "turnos_recientes" not in entrada:
        entrada["turnos_recientes"] = []
    memoria[key] = entrada
    _save(memoria)


def obtener_nombre(id_persona: int) -> str | None:
    memoria = _load()
    entry = memoria.get(str(id_persona))
    return entry["nombre"] if entry else None


def nombres_a_ids() -> dict:
    memoria = _load()
    return {k: v["nombre"] for k, v in memoria.items()}


# ── Resumen por persona ───────────────────────────────────────────────────────

def obtener_contexto_persona(nombre: str) -> str:
    """
    Devuelve un string de contexto para el LLM basado en el resumen
    guardado de la persona. Vacío si no hay historial previo.
    """
    memoria = _load()
    for entry in memoria.values():
        if entry.get("nombre", "").lower() == nombre.lower():
            resumen = entry.get("resumen", "").strip()
            if resumen:
                return f"Lo último que hablaste con {nombre}: {resumen}"
            return ""
    return ""


def agregar_turno_persona(nombre: str, user_msg: str, assistant_msg: str):
    """
    Agrega un turno (user + assistant) a los turnos recientes de la persona.
    Mantiene solo los últimos MAX_TURNS turnos.
    """
    memoria = _load()
    key = None
    for k, entry in memoria.items():
        if entry.get("nombre", "").lower() == nombre.lower():
            key = k
            break
    if key is None:
        return  # persona no registrada, no guardar

    turnos = memoria[key].get("turnos_recientes", [])
    turnos.append({"user": user_msg, "assistant": assistant_msg})
    if len(turnos) > MAX_TURNS:
        turnos = turnos[-MAX_TURNS:]
    memoria[key]["turnos_recientes"] = turnos

    # Actualizar resumen como texto plano compacto
    lineas = []
    for t in turnos:
        lineas.append(f"Usuario: {t['user']} | BMO: {t['assistant']}")
    memoria[key]["resumen"] = " / ".join(lineas)

    _save(memoria)


def agregar_turno_anonimo(user_msg: str, assistant_msg: str):
    """Turno sin persona identificada — se descarta, no se guarda."""
    pass


# ── Compatibilidad con brain.py ───────────────────────────────────────────────

def historial_para_llm() -> list:
    """
    Ya no se usa historial global.
    Devuelve lista vacía — el contexto se inyecta via system prompt en brain.py.
    """
    return []


def agregar_mensaje(role: str, content: str):
    """Stub de compatibilidad — no hace nada, reemplazado por agregar_turno_persona."""
    pass


def limpiar_historial():
    pass
