"""
Módulo de memoria de BMO — Persistencia de personas y conversaciones con contexto personalizado.

ARQUITECTURA DE MEMORIA:
BMO mantiene un sistema de memoria personalizada donde cada persona reconocida
tiene su propio contexto de conversación independiente. Esto permite:
- Continuidad conversacional personalizada
- Evitar contaminación entre conversaciones de diferentes personas
- Contexto relevante sin sobrecargar el LLM con historial irrelevante

ESTRUCTURA DE DATOS (data/memory.json):
{
  "0": {                                    // ID numérico de la persona
    "nombre": "Juan",                       // Nombre registrado
    "visitas": 3,                          // Contador de sesiones
    "ultima_vez": "2026-04-19 13:00:00",   // Timestamp última interacción
    "resumen": "Usuario: hola | BMO: hola Juan! / ...",  // Resumen compacto
    "turnos_recientes": [                   // Buffer circular de turnos
      {"user": "hola", "assistant": "hola Juan!"},
      {"user": "cómo estás", "assistant": "muy bien, gracias"}
    ],
    "embeddings": [[0.1, 0.2, ...]]        // Embeddings faciales (512 dims)
  },
  "_anonimo": {                             // Slot especial para usuarios no reconocidos
    "turnos_recientes": [...]               // Buffer temporal para sesión anónima
  }
}

DISEÑO SIN HISTORIAL GLOBAL:
A diferencia de sistemas tradicionales, BMO NO mantiene un historial global compartido.
Cada persona tiene su propio contexto aislado por razones de:
- Privacidad: las conversaciones no se mezclan entre personas
- Relevancia: el LLM solo ve contexto pertinente a esa persona específica
- Performance: evita prompts excesivamente largos con historial irrelevante
- Escalabilidad: el sistema funciona bien con múltiples usuarios

FLUJO DE CONTEXTO PERSONALIZADO:
1. **Reconocimiento Facial**: La cámara identifica a la persona por embeddings
2. **Carga de Contexto**: Se obtiene el resumen de conversaciones previas
3. **Inyección en Prompt**: El contexto se agrega al system prompt del LLM
4. **Generación Contextual**: El LLM responde con conocimiento de interacciones pasadas
5. **Actualización de Memoria**: Se guarda el nuevo turno y se actualiza el resumen

RESUMEN INTELIGENTE:
El resumen es texto plano compacto optimizado para el LLM:
Formato: "Usuario: X | BMO: Y / Usuario: A | BMO: B"
- Mantiene solo los últimos MAX_TURNS turnos (6 por defecto)
- Se actualiza automáticamente tras cada interacción
- Proporciona contexto suficiente sin sobrecargar el prompt
- Permite continuidad natural entre sesiones

GESTIÓN DE USUARIOS ANÓNIMOS:
Cuando BMO no reconoce a nadie por cámara:
- Los turnos se guardan temporalmente en el slot "_anonimo"
- Buffer circular de ANON_MAX_TURNS turnos (6 por defecto)
- Contexto disponible durante la sesión actual
- Se descarta al finalizar (no hay persistencia a largo plazo)

INTEGRACIÓN CON EMBEDDINGS FACIALES:
- Los embeddings se serializan como listas de floats en el JSON
- Se deserializan a np.ndarray para comparación de similitud
- Cada persona puede tener múltiples embeddings (diferentes ángulos/condiciones)
- Sistema de reconocimiento por similitud coseno (threshold 0.55)

FUNCIONES PRINCIPALES:
- obtener_contexto_persona(): Devuelve resumen para inyectar en prompt
- agregar_turno_persona(): Guarda nuevo turno y actualiza resumen
- agregar_turno_anonimo(): Maneja turnos de usuarios no reconocidos
- cargar_embeddings_todos(): Carga embeddings para reconocimiento facial
- guardar_embeddings_persona(): Persiste embeddings tras registro

COMPATIBILIDAD Y MIGRACIÓN:
Las funciones historial_para_llm() y agregar_mensaje() son stubs vacíos
que mantienen compatibilidad con código antiguo pero no hacen nada.
El nuevo sistema usa contexto personalizado vía system prompt.

OPTIMIZACIÓN PARA RASPBERRY PI 5:
- JSON compacto minimiza I/O de disco
- Caché en memoria evita lecturas repetidas
- Buffer circular limita crecimiento de datos
- Resúmenes compactos reducen tamaño de prompts
"""
import json
import logging
import datetime
from pathlib import Path

import numpy as np

MEMORY_FILE = Path("data/memory.json")
MAX_TURNS      = 6   # turnos recientes para generar el resumen (user+assistant)
ANON_MAX_TURNS = 6   # turnos flotantes para sesión anónima

log = logging.getLogger("BMO")

# Caché en memoria para evitar lecturas repetidas del JSON en cada llamada
_memoria_cache: dict | None = None


def _load() -> dict:
    global _memoria_cache
    if _memoria_cache is not None:
        return _memoria_cache
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            try:
                _memoria_cache = json.load(f)
                return _memoria_cache
            except json.JSONDecodeError as e:
                log.error("memory.json corrupto, devolviendo vacío: %s", e)
                _memoria_cache = {}
                return {}
    _memoria_cache = {}
    return {}


def _save(data: dict):
    global _memoria_cache
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    # Invalidar caché tras escritura
    _memoria_cache = None


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


def guardar_embeddings_persona(nombre: str, embeddings: list[np.ndarray]) -> None:
    """Serializa embeddings como listas de floats y los guarda en memory.json."""
    memoria = _load()
    for key, entry in memoria.items():
        if entry.get("nombre", "").lower() == nombre.lower():
            memoria[key]["embeddings"] = [emb.tolist() for emb in embeddings]
            _save(memoria)
            return
    log.warning("guardar_embeddings_persona: persona '%s' no encontrada", nombre)


def cargar_embeddings_todos() -> dict[str, list[np.ndarray]]:
    """
    Carga todos los embeddings del JSON y los deserializa a np.ndarray.
    Devuelve {nombre: [emb1, emb2, ...]}
    """
    try:
        memoria = _load()
    except Exception as e:
        log.error("cargar_embeddings_todos: error al cargar memoria: %s", e)
        return {}
    resultado: dict[str, list[np.ndarray]] = {}
    for key, entry in memoria.items():
        if key == "_anonimo":
            continue
        if "embeddings" not in entry:
            continue
        nombre = entry.get("nombre", key)
        resultado[nombre] = [np.array(e, dtype=np.float32) for e in entry["embeddings"]]
    return resultado


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
    """Guarda el turno en el slot '_anonimo' con buffer circular de ANON_MAX_TURNS."""
    memoria = _load()
    if "_anonimo" not in memoria:
        memoria["_anonimo"] = {"turnos_recientes": []}
    turnos = memoria["_anonimo"].get("turnos_recientes", [])
    turnos.append({"user": user_msg, "assistant": assistant_msg})
    if len(turnos) > ANON_MAX_TURNS:
        turnos = turnos[-ANON_MAX_TURNS:]
    memoria["_anonimo"]["turnos_recientes"] = turnos
    _save(memoria)


def obtener_contexto_anonimo() -> str:
    """
    Devuelve string de contexto de la sesión anónima actual para el LLM.
    Vacío si no hay turnos anónimos.
    """
    memoria = _load()
    turnos = memoria.get("_anonimo", {}).get("turnos_recientes", [])
    if not turnos:
        return ""
    lineas = [f"Usuario: {t['user']} | BMO: {t['assistant']}" for t in turnos]
    return "Conversación reciente (sin nombre): " + " / ".join(lineas)


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
