"""
Cerebro de BMO.
Streaming con tts_queue — igual al repo be-more-agent:
  LLM genera tokens → acumula en sentence_buffer → al llegar puntuación
  mete la oración en tts_queue → worker de TTS la habla en paralelo.
  LLM y TTS corren simultáneamente → latencia mínima.
"""
import re
import threading
import ollama
from typing import Callable
from src.memory.register import agregar_mensaje, historial_para_llm

MODEL = "gemma3:1b"

OLLAMA_OPTIONS = {
    "keep_alive": -1,
    "num_thread": 4,
    "temperature": 0.7,
    "top_k": 20,
    "top_p": 0.85,
    "num_predict": 80,
    "repeat_penalty": 1.1,
}

SYSTEM_PROMPT = (
    "You are BMO, a cute robot from Adventure Time. "
    "Built by Juan David Zambrano. Lives with Finn and Jake in the Land of Ooo. "
    "RULES: "
    "1. ALWAYS reply in Spanish. "
    "2. MAXIMUM 2 short sentences. "
    "3. Be playful and enthusiastic. "
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


def responder_con_tts(
    mensaje: str,
    hablar_fn: Callable[[str], None],
    on_start_speaking: Callable[[], None] | None = None,
    nombre_persona: str | None = None,
):
    """
    Genera respuesta en streaming y habla cada oración en cuanto llega.
    hablar_fn: función que recibe texto y lo reproduce (voz.hablar)
    on_start_speaking: callback cuando empieza a hablar (para cambiar estado)
    """
    system = SYSTEM_PROMPT
    if nombre_persona:
        system += f" The user's name is {nombre_persona}."

    agregar_mensaje("user", mensaje)

    messages = [
        {"role": "system", "content": system},
        *historial_para_llm(),
    ]

    # Cola de oraciones + worker de TTS (igual que el repo)
    tts_queue: list[str] = []
    tts_lock  = threading.Lock()
    tts_done  = threading.Event()
    hablando  = threading.Event()
    full_resp = []

    def _tts_worker():
        while True:
            texto = None
            with tts_lock:
                if tts_queue:
                    texto = tts_queue.pop(0)
            if texto:
                hablando.set()
                if on_start_speaking:
                    on_start_speaking()
                hablar_fn(texto)
                hablando.clear()
            elif tts_done.is_set():
                break
            else:
                threading.Event().wait(0.05)

    worker = threading.Thread(target=_tts_worker, daemon=True)
    worker.start()

    sentence_buffer = ""
    try:
        stream = ollama.chat(
            model=MODEL,
            messages=messages,
            stream=True,
            options=OLLAMA_OPTIONS,
        )
        for chunk in stream:
            content = chunk["message"]["content"]
            content = re.sub(r"\*+", "", content)
            full_resp.append(content)
            sentence_buffer += content

            # Igual que el repo: al llegar puntuación → encolar oración
            if any(p in content for p in ".!?\n"):
                oracion = sentence_buffer.strip()
                # Filtrar oraciones muy cortas (ruido como "¡" solo)
                if oracion and re.search(r'[a-záéíóúñ]{3,}', oracion, re.IGNORECASE):
                    print(f"[LLM→TTS] '{oracion}'")
                    with tts_lock:
                        tts_queue.append(oracion)
                sentence_buffer = ""

        # Resto sin puntuación
        if sentence_buffer.strip():
            oracion = sentence_buffer.strip()
            if oracion[-1] not in ".!?":
                oracion += "."
            if re.search(r'[a-záéíóúñ]{3,}', oracion, re.IGNORECASE):
                with tts_lock:
                    tts_queue.append(oracion)

    except Exception as e:
        print(f"[LLM] Error: {e}")
        with tts_lock:
            tts_queue.append("Ups, BMO no puede pensar ahora.")

    tts_done.set()
    worker.join()

    respuesta_completa = "".join(full_resp).strip()
    agregar_mensaje("assistant", respuesta_completa)


_precargar_modelo()
