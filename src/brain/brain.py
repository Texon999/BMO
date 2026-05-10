"""
Cerebro de BMO — Generación de respuestas con LLM y pipeline TTS.
"""
import logging
import re
import threading
import time
import random
import ollama
import atexit
from typing import Callable

from src.config.config_manager import config_manager
from src.memory.persistent_memory import persistent_memory

log = logging.getLogger("BMO")

# ── Shutdown ──────────────────────────────────────────────────────────────────

_shutdown_handlers: list = []
_shutdown_registered = False


def register_shutdown_handler(handler):
    global _shutdown_registered
    _shutdown_handlers.append(handler)
    if not _shutdown_registered:
        atexit.register(_execute_shutdown_handlers)
        _shutdown_registered = True


def _execute_shutdown_handlers():
    for handler in _shutdown_handlers:
        try:
            handler()
        except Exception as e:
            log.warning("[SHUTDOWN] Handler falló: %s", e)


# ── System prompt ─────────────────────────────────────────────────────────────

def get_system_prompt() -> str:
    """
    Prompt minimalista para qwen2.5:1.5b.
    Cuanto más corto, menos alucina el modelo.
    """
    base = (
        "Eres BMO, un robot asistente creado por Zambrano, "
        "un joven programador del SENA apasionado por la tecnología. "
        "Responde siempre en español. Sé amable y directo. "
        "Máximo 2 oraciones para preguntas simples, 4 para explicaciones. "
        "Sin listas, sin markdown, solo texto natural. "
        "Si no sabes algo, di 'No tengo esa información'. "
        "Bandera de Colombia: amarillo arriba, azul medio, rojo abajo. "
        "Capital de Brasil: Brasilia. "
        "Hora de Aventura: BMO es un personaje de esa serie, un robot que vive con Finn y Jake."
    )
    extras = config_manager.get("system_prompt_extras", "")
    if extras:
        base += f" {extras}"
    return base


# ── Saludos ───────────────────────────────────────────────────────────────────

SALUDOS_CONOCIDO = [
    "¡{nombre}! ¡Qué alegría verte de nuevo! ¿Cómo estás?",
    "¡Oye, {nombre}! ¡BMO te estaba esperando! ¿Qué cuentas?",
    "¡{nombre}! ¡Hola hola! ¡Hora de aventura contigo!",
    "¡Bienvenido de nuevo, {nombre}! Me alegra mucho verte.",
    "¡{nombre}! ¡Qué bueno que volviste! ¿En qué te puedo ayudar hoy?",
]

SALUDOS_DESCONOCIDO = [
    "¡Hola! Soy BMO, un robot de IA. ¿Cómo te llamas?",
    "¡Oye, hola! No te conozco todavía. ¿Cuál es tu nombre?",
    "¡Bienvenido! Soy BMO. ¿Me dices tu nombre?",
    "¡Hola! Me llamo BMO y me encanta conocer gente nueva. ¿Y tú?",
    "¡Qué bueno que te acercaste! Soy BMO. ¿Cómo te llamas?",
]


def saludo_fijo(nombre: str | None) -> str:
    if nombre:
        return random.choice(SALUDOS_CONOCIDO).format(nombre=nombre)
    return random.choice(SALUDOS_DESCONOCIDO)


# ── Detección de nombres ──────────────────────────────────────────────────────

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


def detectar_nombre(texto: str) -> str | None:
    t = texto.lower().strip()
    for patron in _NOMBRE_PATRONES:
        m = re.search(patron, t)
        if m:
            nombre = m.group(1).lower()
            if nombre not in _NO_NOMBRES and len(nombre) > 2:
                return nombre.capitalize()
    return None


# ── Normalización de texto para TTS ──────────────────────────────────────────
# Piper TTS (español) no pronuncia bien ciertos símbolos y palabras en inglés.
# Esta función los convierte a su equivalente hablado en español antes de sintetizar.

_TTS_REEMPLAZOS = [
    # Símbolo matemático π → "pí" (con tilde para que Piper lo pronuncie como vocal tónica)
    (re.compile(r"π"),                          " pí "),
    # La palabra "pi" sola o seguida de número/espacio en contexto matemático
    (re.compile(r"\bpi\b", re.IGNORECASE),      "pí"),
    # Otros símbolos matemáticos comunes
    (re.compile(r"√"),                          "raíz cuadrada de"),
    (re.compile(r"∞"),                          "infinito"),
    (re.compile(r"≈"),                          "aproximadamente"),
    (re.compile(r"≠"),                          "distinto de"),
    (re.compile(r"≤"),                          "menor o igual que"),
    (re.compile(r"≥"),                          "mayor o igual que"),
    (re.compile(r"²"),                          " al cuadrado"),
    (re.compile(r"³"),                          " al cubo"),
    # Siglas y palabras en inglés que Piper pronuncia mal
    (re.compile(r"\bOK\b"),                     "okey"),
    (re.compile(r"\bok\b"),                     "okey"),
    # Limpiar asteriscos y markdown que el LLM a veces genera
    (re.compile(r"\*+"),                        ""),
    (re.compile(r"#+\s*"),                      ""),
    (re.compile(r"`+"),                         ""),
]


def normalizar_para_tts(texto: str) -> str:
    """
    Convierte símbolos y palabras problemáticas a su equivalente hablado en español,
    para que Piper TTS los pronuncie correctamente.
    """
    for patron, reemplazo in _TTS_REEMPLAZOS:
        texto = patron.sub(reemplazo, texto)
    # Colapsar espacios múltiples que puedan quedar
    texto = re.sub(r"  +", " ", texto).strip()
    return texto


# ── LLM ───────────────────────────────────────────────────────────────────────

def precargar_modelo():
    """
    Precarga el modelo en RAM de forma bloqueante.
    Se llama durante el WARMUP para que la primera respuesta real sea rápida.
    """
    try:
        model = config_manager.get("text_model", "qwen2.5:1.5b")
        log.info("[LLM] Precargando %s en RAM...", model)
        t0 = time.time()
        ollama.generate(model=model, prompt="hola", keep_alive=-1)
        log.info("[LLM] %s listo en RAM (%.1fs)", model, time.time() - t0)
    except Exception as e:
        log.warning("[LLM] Error al precargar: %s — ejecuta: ollama serve", e)


def cleanup_llm():
    """Descarga el modelo de RAM al apagar BMO."""
    try:
        model = config_manager.get("text_model", "qwen2.5:1.5b")
        ollama.generate(model=model, prompt="", keep_alive=0)
        log.info("[LLM] Modelo descargado de RAM")
    except Exception:
        pass


# ── Pipeline principal: LLM → TTS ─────────────────────────────────────────────

def responder_con_tts(
    mensaje: str,
    hablar_fn: Callable[[str], None],
    on_start_speaking: Callable[[], None] | None = None,
    nombre_persona: str | None = None,
):
    """
    Genera respuesta con el LLM en streaming y la habla en tiempo real.
    El texto pasa por normalizar_para_tts() antes de llegar a Piper.
    """
    persistent_memory.add_user_message(mensaje, nombre_persona)
    messages = persistent_memory.get_context_for_llm(nombre_persona)

    model = config_manager.get("text_model", "qwen2.5:1.5b")
    options = config_manager.get_ollama_options()

    tts_queue: list[str] = []
    tts_lock  = threading.Lock()
    tts_done  = threading.Event()
    full_resp: list[str] = []

    def _tts_worker():
        while True:
            texto = None
            with tts_lock:
                if tts_queue:
                    texto = tts_queue.pop(0)
            if texto:
                if on_start_speaking:
                    on_start_speaking()
                hablar_fn(texto)
            elif tts_done.is_set():
                break
            else:
                time.sleep(0.05)

    worker = threading.Thread(target=_tts_worker, daemon=True)
    worker.start()

    sentence_buffer = ""

    try:
        stream = ollama.chat(
            model=model,
            messages=messages,
            stream=True,
            options=options,
        )

        for chunk in stream:
            content = chunk["message"]["content"]
            full_resp.append(content)
            sentence_buffer += content

            if any(p in content for p in ".!?\n"):
                oracion = normalizar_para_tts(sentence_buffer.strip())
                sentence_buffer = ""
                if oracion and re.search(r"[a-záéíóúñ]{3,}", oracion, re.IGNORECASE):
                    log.info("[LLM→TTS] '%s'", oracion)
                    with tts_lock:
                        tts_queue.append(oracion)

        # Resto sin puntuación al final del stream
        if sentence_buffer.strip():
            oracion = normalizar_para_tts(sentence_buffer.strip())
            if oracion and oracion[-1] not in ".!?":
                oracion += "."
            if oracion and re.search(r"[a-záéíóúñ]{3,}", oracion, re.IGNORECASE):
                with tts_lock:
                    tts_queue.append(oracion)

    except Exception as e:
        log.warning("[LLM] Error: %s", e)
        with tts_lock:
            tts_queue.append("Ups, BMO no puede pensar ahora.")

    tts_done.set()
    worker.join()

    respuesta_completa = "".join(full_resp).strip()
    persistent_memory.add_assistant_message(respuesta_completa, nombre_persona)

    if nombre_persona and len(persistent_memory.session_memory) >= 4:
        persistent_memory.commit_session_to_permanent(nombre_persona)


# ── Inicialización ────────────────────────────────────────────────────────────

register_shutdown_handler(cleanup_llm)
register_shutdown_handler(persistent_memory.save_memory)
