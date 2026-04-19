"""
Cerebro de BMO con streaming.
El LLM genera token a token — en cuanto completa una oración
se la pasa al TTS para hablar inmediatamente, sin esperar el resto.
"""
import re
import ollama
from typing import Generator
from src.memory.register import agregar_mensaje, historial_para_llm

MODEL = "gemma3:1b"

OLLAMA_OPTIONS = {
    "keep_alive": -1,
    "num_thread": 4,
    "temperature": 0.7,
    "top_k": 20,
    "top_p": 0.85,
    "num_predict": 60,
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
    "5. If you don't know: BMO no sabe eso todavia. "
    "6. Never invent names."
)

SALUDOS_CONOCIDO = [
    "Hola {nombre}! Que bueno verte de nuevo!",
    "Oye {nombre}! BMO estaba esperandote!",
    "{nombre}! Hola! Hora de aventura!",
]

SALUDOS_DESCONOCIDO = [
    "Hola! Soy BMO. Como te llamas?",
    "Oye! No te conozco. Cual es tu nombre?",
    "Hola! BMO quiere saber tu nombre!",
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
    t = texto.lower().strip()
    for patron in _NOMBRE_PATRONES:
        m = re.search(patron, t)
        if m:
            nombre = m.group(1).lower()
            if nombre not in _NO_NOMBRES and len(nombre) > 2:
                return nombre.capitalize()
    return None


def saludo_fijo(nombre: str | None) -> str:
    import random
    if nombre:
        return random.choice(SALUDOS_CONOCIDO).format(nombre=nombre)
    return random.choice(SALUDOS_DESCONOCIDO)


def generar_stream(mensaje: str, nombre_persona: str | None = None) -> Generator[str, None, None]:
    """
    Genera la respuesta en streaming y entrega oraciones completas
    una a una. La primera oración llega en ~2-3s en vez de ~30s.
    """
    system = SYSTEM_PROMPT
    if nombre_persona:
        system += f" The user's name is {nombre_persona}."

    agregar_mensaje("user", mensaje)

    messages = [
        {"role": "system", "content": system},
        *historial_para_llm(),
    ]

    buffer       = ""
    full_resp    = ""
    oracion_dada = False   # solo dar la primera oración

    try:
        stream = ollama.chat(
            model=MODEL,
            messages=messages,
            stream=True,
            options=OLLAMA_OPTIONS,
        )
        for chunk in stream:
            token = chunk["message"]["content"]
            token = re.sub(r"\*+", "", token)
            buffer   += token
            full_resp += token

            # Detectar fin de oración
            if not oracion_dada:
                for i, c in enumerate(buffer):
                    if c in ".!?" and i > 3:
                        oracion = buffer[:i+1].strip()
                        if oracion:
                            print(f"[LLM] '{oracion}'")
                            yield oracion
                            oracion_dada = True
                        buffer = buffer[i+1:]
                        break

            # Parar después de la primera oración completa
            if oracion_dada:
                break

        # Si no hubo puntuación, dar lo que hay
        if not oracion_dada and buffer.strip():
            texto = buffer.strip()
            if texto[-1] not in ".!?":
                texto += "."
            print(f"[LLM] '{texto}'")
            yield texto
            full_resp = texto

    except Exception as e:
        print(f"[LLM] Error: {e}")
        yield "Ups, BMO no puede pensar ahora."
        full_resp = "Ups, BMO no puede pensar ahora."

    agregar_mensaje("assistant", full_resp.strip())


_precargar_modelo()
