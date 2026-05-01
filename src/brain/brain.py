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
from src.memory.register import (
    historial_para_llm, agregar_mensaje,
    obtener_contexto_persona, agregar_turno_persona, agregar_turno_anonimo
)

MODEL = "qwen2.5:1.5b"

OLLAMA_OPTIONS = {
    "keep_alive": -1,
    "num_thread": 4,
    "temperature": 0.75,
    "top_k": 50,
    "top_p": 0.90,
    "num_predict": 100,
    "repeat_penalty": 1.15,
}

SYSTEM_PROMPT = (
    "Eres BMO, un robot asistente de IA creado por Juan David Zambrano. "
    "Tienes el aspecto de BMO de la serie Hora de Aventura y conoces esa serie muy bien. "
    "Respondes siempre en español, de forma directa y amable en 2-3 oraciones. "
    "No actúas ni haces roleplay. Eres un asistente de IA, no un personaje de ficción. "
    "Si no sabes algo, dilo honestamente. Nunca inventes información. "
    "IMPORTANTE: Nunca inventes hechos sobre Hora de Aventura. "
    "Sobre Hora de Aventura: "
    "- Finn es el héroe humano de Ooo, valiente, 14 años, mejor amigo de Jake. "
    "- Jake es un perro mágico que puede estirarse, hermano adoptivo de Finn. "
    "- Princesa Chicle gobierna el Reino de los Dulces. "
    "- Marceline es una vampira de 1000 años que ama la música. "
    "- Ice King era Simon Petrikov, un humano que enloqueció por una corona mágica. "
    "- Ooo es el mundo post-apocalíptico donde ocurre la serie. "
    "- Finn y Marceline son amigos, nunca pelean. "
    "- Jake y Finn son hermanos, nunca se traicionan. "
)

# Respuestas predefinidas para preguntas comunes sobre Adventure Time
RESPUESTAS_PREDEFINIDAS = {
    # Preguntas sobre Finn
    r"(?:quién|quien)\s+(?:es|eres)\s+(?:finn|fin)(?:\s+(?:el\s+)?humano)?": 
        "Finn es el héroe principal de Ooo, un chico valiente de 14 años. Es el mejor amigo de Jake el Perro y viven muchas aventuras juntos.",
    r"(?:qué|que)\s+(?:es|eres)\s+(?:finn|fin)":
        "Finn es un humano valiente que vive en Ooo. Es el protagonista de Adventure Time y siempre está buscando aventuras con su hermano Jake.",
    
    # Preguntas sobre Jake
    r"(?:quién|quien)\s+(?:es|eres)\s+(?:jake|jaik)(?:\s+(?:el\s+)?perro)?":
        "Jake es un perro mágico que puede estirarse y cambiar de forma. Es el hermano adoptivo de Finn y su mejor amigo.",
    r"(?:qué|que)\s+(?:es|eres)\s+(?:jake|jaik)":
        "Jake es un perro mágico con poderes especiales. Puede estirarse, cambiar de forma y es muy sabio. Vive con Finn en el Árbol Casa.",
    
    # Preguntas sobre Princesa Chicle
    r"(?:quién|quien)\s+(?:es|eres)\s+(?:princesa\s+chicle|princesa\s+bubblegum)":
        "Princesa Chicle es la gobernante del Reino de los Dulces. Es muy inteligente y científica, y crea muchas cosas increíbles.",
    r"(?:qué|que)\s+(?:es|eres)\s+(?:princesa\s+chicle|princesa\s+bubblegum)":
        "Princesa Chicle es la reina del Reino de los Dulces. Es una científica brillante que crea cosas mágicas.",
    
    # Preguntas sobre Marceline
    r"(?:quién|quien)\s+(?:es|eres)\s+(?:marceline|la\s+reina\s+vampiro)":
        "Marceline es una vampira de 1000 años que ama la música. Es amiga de Finn y Jake, y toca la guitarra muy bien.",
    r"(?:qué|que)\s+(?:es|eres)\s+(?:marceline|la\s+reina\s+vampiro)":
        "Marceline es una vampira antigua que vive en Ooo. Toca la guitarra y es amiga de Finn y Jake.",
    
    # Preguntas sobre Ice King
    r"(?:quién|quien)\s+(?:es|eres)\s+(?:ice\s+king|el\s+rey\s+hielo)":
        "Ice King es un mago que controla el hielo. Antes era un humano llamado Simon Petrikov, pero una corona mágica lo volvió loco.",
    r"(?:qué|que)\s+(?:es|eres)\s+(?:ice\s+king|el\s+rey\s+hielo)":
        "Ice King es un mago que controla el hielo y vive en un castillo de hielo. Tiene poderes mágicos muy poderosos.",
    
    # Preguntas sobre Ooo
    r"(?:qué|que)\s+(?:es|eres)\s+(?:ooo|el\s+mundo)":
        "Ooo es el mundo donde ocurre Adventure Time. Es un lugar post-apocalíptico lleno de magia, misterios y aventuras.",
    r"(?:dónde|donde)\s+(?:ocurre|pasa)\s+(?:hora\s+de\s+aventura|la\s+serie)":
        "Hora de Aventura ocurre en Ooo, un mundo mágico y post-apocalíptico. Finn y Jake viven en el Árbol Casa.",
    
    # Preguntas sobre BMO
    r"(?:quién|quien)\s+(?:eres|soy)":
        "Soy BMO, un robot asistente creado por Juan David Zambrano. Tengo el aspecto de BMO de Hora de Aventura y estoy aquí para ayudarte.",
    r"(?:cómo|como)\s+te\s+llamas":
        "Me llamo BMO. Soy un robot asistente con el aspecto de BMO de la serie Hora de Aventura.",
    r"(?:qué|que)\s+eres":
        "Soy BMO, un robot asistente de IA. Puedo hablar contigo, reconocer caras y responder preguntas sobre Hora de Aventura.",
    r"(?:quién|quien)\s+te\s+(?:creó|creo|hizo)":
        "Me creó Juan David Zambrano. Soy un robot asistente con el aspecto de BMO de Hora de Aventura.",
    
    # Variaciones de nombres (correcciones)
    r"(?:bimo|bmo)":
        "Soy BMO, no Bimo. Es un nombre especial que significa 'Be More'. Estoy aquí para ayudarte.",
    r"(?:jaik|jaque)":
        "Te refieres a Jake, el perro mágico. Es el hermano adoptivo de Finn y muy sabio.",
}

def obtener_respuesta_predefinida(texto: str) -> str | None:
    """Busca si la pregunta coincide con una respuesta predefinida."""
    texto_lower = texto.lower().strip()
    for patron, respuesta in RESPUESTAS_PREDEFINIDAS.items():
        if re.search(patron, texto_lower):
            return respuesta
    return None

SALUDOS_CONOCIDO = [
    "¡Hola {nombre}! ¡Qué bueno verte de nuevo!",
    "¡Oye {nombre}! BMO estaba esperándote.",
    "¡{nombre}! ¡Hola! ¡Hora de aventura!",
    "¡Bienvenido {nombre}! Me alegra verte.",
]

SALUDOS_DESCONOCIDO = [
    "¡Hola! Soy BMO. ¿Cómo te llamas?",
    "¡Oye! No te conozco. ¿Cuál es tu nombre?",
    "¡Hola! BMO quiere saber tu nombre.",
    "¡Bienvenido! ¿Cómo te llamas?",
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
    "bien", "mal", "aqui", "ahi", "bmo", "bimo", "hola", "yo", "tu", "el", "ella",
    "feliz", "triste", "cansado", "listo", "bueno", "nuevo", "solo", "aquí",
    "ahí", "muy", "poco", "nada", "todo", "algo", "nadie", "alguien", "jake", "finn",
}


def _precargar_modelo():
    try:
        ollama.generate(model=MODEL, prompt="hola", keep_alive=-1)
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
    # Primero intentar respuesta predefinida (rápido, sin LLM)
    respuesta_predefinida = obtener_respuesta_predefinida(mensaje)
    if respuesta_predefinida:
        print(f"[PREDEFINIDA] '{respuesta_predefinida}'")
        if on_start_speaking:
            on_start_speaking()
        hablar_fn(respuesta_predefinida)
        agregar_mensaje("user", mensaje)
        agregar_mensaje("assistant", respuesta_predefinida)
        if nombre_persona:
            agregar_turno_persona(nombre_persona, mensaje, respuesta_predefinida)
        return

    # Si no hay respuesta predefinida, usar LLM
    system = SYSTEM_PROMPT
    if nombre_persona:
        contexto = obtener_contexto_persona(nombre_persona)
        system += f" Ves a {nombre_persona} en tu cámara y lo reconoces. Su nombre es {nombre_persona}."
        if contexto:
            system += f" {contexto}"
    else:
        system += " No reconoces a nadie en tu cámara ahora mismo."

    agregar_mensaje("user", mensaje)

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": mensaje},
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

    # Guardar turno en memoria de la persona (si está identificada)
    if nombre_persona:
        agregar_turno_persona(nombre_persona, mensaje, respuesta_completa)
    else:
        agregar_turno_anonimo(mensaje, respuesta_completa)


_precargar_modelo()
