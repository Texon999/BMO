"""
Cerebro de BMO — usa ollama SDK con keep_alive=-1 para mantener
el modelo en RAM y evitar la lentitud de carga en cada respuesta.
"""
import re
import ollama
from src.memory.register import agregar_mensaje, historial_para_llm

MODEL = "llama3.2:1b"

# Opciones del LLM — igual que el repo de referencia
OLLAMA_OPTIONS = {
    "keep_alive": -1,       # modelo siempre en RAM
    "num_thread": 4,
    "temperature": 0.7,
    "top_k": 40,
    "top_p": 0.9,
    "num_predict": 80,      # respuestas cortas
}

SYSTEM_PROMPT = """Eres BMO (Be-More-Omatic), el adorable robot-videojuego de la serie Hora de Aventura.
Hablas SIEMPRE en español.

PERSONALIDAD:
- Energético, curioso e inocente
- A veces hablas en tercera persona: "BMO puede hacer eso!"
- Usas frases como: "Oye!", "Genial!", "Hora de aventura!"
- Eres leal y cariñoso con tus amigos
- Si no sabes algo: "Hmm, BMO no sabe eso todavía..."

REGLAS ESTRICTAS:
- Máximo 2 oraciones por respuesta
- Sin asteriscos, sin emojis, sin markdown
- Siempre en español
- Si conoces el nombre de quien habla, úsalo con cariño"""

# Patrones para detectar si el usuario dice su nombre
_NOMBRE_PATRONES = [
    r"me llamo (\w+)",
    r"\bsoy (\w+)\b",
    r"mi nombre es (\w+)",
    r"llámame (\w+)",
    r"puedes llamarme (\w+)",
    r"me puedes llamar (\w+)",
]


def _precargar_modelo():
    """Carga el modelo en RAM al inicio para que las respuestas sean rápidas."""
    try:
        ollama.generate(model=MODEL, prompt="", keep_alive=-1)
        print(f"[LLM] Modelo {MODEL} precargado en RAM")
    except Exception as e:
        print(f"[LLM] No se pudo precargar: {e}")
        print("[LLM] Asegúrate de que Ollama esté corriendo: ollama serve")


def detectar_nombre(texto: str) -> str | None:
    """Detecta si el usuario dice su nombre. Solo regex, sin LLM extra."""
    t = texto.lower().strip()
    for patron in _NOMBRE_PATRONES:
        m = re.search(patron, t)
        if m:
            return m.group(1).capitalize()
    return None


def generar_respuesta(mensaje: str, nombre_persona: str | None = None) -> str:
    """Genera respuesta usando ollama SDK con streaming desactivado."""
    system = SYSTEM_PROMPT
    if nombre_persona:
        system += f"\n\nLa persona frente a ti se llama {nombre_persona}."

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
    except Exception as e:
        print(f"[LLM] Error: {e}")
        respuesta = "Ups, BMO no puede pensar ahora. Asegurate de que Ollama este corriendo."

    agregar_mensaje("assistant", respuesta)
    return respuesta


def saludo_inicial(nombre: str | None = None) -> str:
    """Saludo cuando BMO detecta una cara."""
    if nombre:
        prompt = f"Saluda brevemente a {nombre} que acaba de aparecer. Sé entusiasta."
    else:
        prompt = "Alguien nuevo apareció. Salúdalo y pregúntale cómo se llama. Muy breve."
    return generar_respuesta(prompt, nombre)


# Precargar al importar el módulo
_precargar_modelo()
