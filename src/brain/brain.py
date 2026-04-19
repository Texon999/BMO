"""
Cerebro de BMO — ollama SDK, keep_alive=-1, prompt minimalista.
"""
import re
import ollama
from src.memory.register import agregar_mensaje, historial_para_llm

MODEL = "llama3.2:1b"

OLLAMA_OPTIONS = {
    "keep_alive": -1,
    "num_thread": 4,
    "temperature": 0.7,
    "top_k": 40,
    "top_p": 0.9,
    "num_predict": 60,   # corto = rápido
}

# Prompt minimalista — modelos pequeños responden mejor a instrucciones simples
SYSTEM_PROMPT = """You are BMO, a cute robot from Adventure Time. Always reply in Spanish.
Rules: max 2 short sentences. No asterisks. No emojis. Be playful and friendly."""

_NOMBRE_PATRONES = [
    r"me llamo (\w+)",
    r"\bsoy (\w+)\b",
    r"mi nombre es (\w+)",
    r"llámame (\w+)",
    r"puedes llamarme (\w+)",
    r"me puedes llamar (\w+)",
    r"me dicen (\w+)",
]

# Palabras que no son nombres (falsos positivos comunes)
_NO_NOMBRES = {"bien", "mal", "aqui", "ahi", "bmo", "hola", "yo", "tu", "el", "ella",
               "feliz", "triste", "cansado", "listo", "bueno", "nuevo", "solo"}


def _precargar_modelo():
    try:
        ollama.generate(model=MODEL, prompt="hi", keep_alive=-1)
        print(f"[LLM] {MODEL} cargado en RAM")
    except Exception as e:
        print(f"[LLM] Error precargando: {e} — asegurate de que Ollama este corriendo")


def detectar_nombre(texto: str) -> str | None:
    t = texto.lower().strip()
    for patron in _NOMBRE_PATRONES:
        m = re.search(patron, t)
        if m:
            nombre = m.group(1).lower()
            if nombre not in _NO_NOMBRES and len(nombre) > 2:
                return nombre.capitalize()
    return None


def generar_respuesta(mensaje: str, nombre_persona: str | None = None) -> str:
    system = SYSTEM_PROMPT
    if nombre_persona:
        system += f" The person talking to you is called {nombre_persona}."

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
        # Limpiar asteriscos y markdown que el modelo a veces añade
        respuesta = re.sub(r"\*+", "", respuesta).strip()
    except Exception as e:
        print(f"[LLM] Error: {e}")
        respuesta = "Ups, BMO no puede pensar ahora mismo."

    agregar_mensaje("assistant", respuesta)
    return respuesta


_precargar_modelo()
