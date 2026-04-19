"""
Cerebro de BMO.
- Saludos con texto FIJO (sin LLM) para evitar nombres inventados
- LLM solo para respuestas de conversación
- stop tokens para forzar respuestas cortas
"""
import re
import ollama
from src.memory.register import agregar_mensaje, historial_para_llm

MODEL = "gemma3:1b"

OLLAMA_OPTIONS = {
    "keep_alive": -1,
    "num_thread": 4,
    "temperature": 0.7,
    "top_k": 20,
    "top_p": 0.85,
    "num_predict": 35,      # ~1 oración corta
    "repeat_penalty": 1.1,
}

SYSTEM_PROMPT = (
    "You are BMO, a cute robot from Adventure Time. "
    "Built by Juan David Zambrano. Lives with Finn and Jake in the Land of Ooo. "
    "RULES: "
    "1. ALWAYS reply in Spanish. "
    "2. MAXIMUM 1 sentence. Never more. "
    "3. Be short, playful and enthusiastic. "
    "4. No asterisks, no emojis, no lists. "
    "5. If you don't know: 'BMO no sabe eso todavia.' "
    "6. Never invent names."
)

# Saludos fijos — sin LLM, sin riesgo de inventar nombres
SALUDOS_CONOCIDO = [
    "Hola {nombre}! Que bueno verte de nuevo!",
    "Oye {nombre}! BMO estaba esperandote!",
    "{nombre}! Hola hola! Hora de aventura!",
]

SALUDOS_DESCONOCIDO = [
    "Hola! Soy BMO. Como te llamas?",
    "Oye! No te conozco. Cual es tu nombre?",
    "Hola amigo! BMO quiere saber tu nombre!",
]

_NOMBRE_PATRONES = [
    r"me llamo (\w+)",
    r"mi nombre es (\w+)",
    r"llámame (\w+)",
    r"me dicen (\w+)",
    r"me puedes llamar (\w+)",
    r"soy (\w+)",
]

_NO_NOMBRES = {
    "bien", "mal", "aqui", "ahi", "bmo", "hola", "yo", "tu", "el", "ella",
    "feliz", "triste", "cansado", "listo", "bueno", "nuevo", "solo", "aquí",
    "ahí", "muy", "poco", "nada", "todo", "algo", "nadie", "alguien",
}


def _precargar_modelo():
    try:
        ollama.generate(model=MODEL, prompt="hi", keep_alive=-1)
        print(f"[LLM] {MODEL} en RAM")
    except Exception as e:
        print(f"[LLM] Error: {e} — ejecuta: ollama serve")


def detectar_nombre(texto: str) -> str | None:
    """Detecta si el usuario dice su nombre. Puro regex, sin LLM."""
    t = texto.lower().strip()
    for patron in _NOMBRE_PATRONES:
        m = re.search(patron, t)
        if m:
            nombre = m.group(1).lower()
            if nombre not in _NO_NOMBRES and len(nombre) > 2:
                return nombre.capitalize()
    return None


def saludo_fijo(nombre: str | None) -> str:
    """Saludo con texto fijo — nunca inventa nombres."""
    import random
    if nombre:
        plantilla = random.choice(SALUDOS_CONOCIDO)
        return plantilla.format(nombre=nombre)
    return random.choice(SALUDOS_DESCONOCIDO)


def _truncar_primera_oracion(texto: str) -> str:
    """Devuelve solo la primera oración completa."""
    for i, c in enumerate(texto):
        if c in ".!?" and i > 5:
            return texto[:i+1].strip()
    return texto.strip()


def generar_respuesta(mensaje: str, nombre_persona: str | None = None) -> str:
    """Respuesta conversacional con LLM."""
    system = SYSTEM_PROMPT
    if nombre_persona:
        system += f" The user's name is {nombre_persona}."

    agregar_mensaje("user", mensaje)

    messages = [
        {"role": "system", "content": system},
        *historial_para_llm(),
    ]

    try:
        resp = ollama.chat(
            model=MODEL,
            messages=messages,
            stream=False,
            options=OLLAMA_OPTIONS,
        )
        respuesta = resp["message"]["content"].strip()
        respuesta = re.sub(r"\*+", "", respuesta).strip()
        respuesta = _truncar_primera_oracion(respuesta)
        if respuesta and respuesta[-1] not in ".!?":
            respuesta += "."
    except Exception as e:
        print(f"[LLM] Error: {e}")
        respuesta = "Ups, BMO no puede pensar ahora."

    agregar_mensaje("assistant", respuesta)
    return respuesta


_precargar_modelo()
