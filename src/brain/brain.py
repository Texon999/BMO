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
from src.brain.classifier import categorizar_pregunta, num_predict_para, max_oraciones_para, length_hint_para, sin_acentos

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


# ── Respuestas predefinidas para preguntas comunes ───────────────────────────

_RESPUESTAS_PREDEFINIDAS: list[tuple[re.Pattern, str]] = [
    # Minecraft
    (re.compile(r'\b(qué es|que es|explica|explicame|cuéntame|cuentame|dime sobre).*minecraft\b', re.IGNORECASE),
        "Minecraft es un videojuego sandbox donde construyes con bloques. Puedes explorar mundos generados aleatoriamente y sobrevivir enfrentando enemigos. Es uno de los juegos más populares del mundo."),
    
    # Pi - dígitos
    (re.compile(r'\b(cuántos|cuantos).*digitos.*\b(pi|p)\b', re.IGNORECASE),
        "Pi tiene infinitos dígitos decimales. Es un número irracional que empieza con 3.14159 y nunca termina ni se repite."),
    
    # Pi - qué es
    (re.compile(r'\b(qué es|que es|explica|explicame).*\b(pi|número pi|numero pi)\b', re.IGNORECASE),
        "Pi es un número matemático irracional con infinitos dígitos decimales. Representa la relación entre la circunferencia y el diámetro de un círculo. Empieza con 3.14159."),
    
    # Pi - valor
    (re.compile(r'\b(cuál es|cual es|valor de|cuánto es|cuanto es).*\b(pi|número pi|numero pi)\b', re.IGNORECASE),
        "Pi vale aproximadamente 3.14159. Es un número irracional con infinitos dígitos decimales que nunca se repiten."),
    
    # Bandera Colombia
    (re.compile(r'\bbandera.*colombia\b', re.IGNORECASE),
        "La bandera de Colombia tiene tres franjas horizontales. Amarillo arriba ocupando la mitad, azul en el medio y rojo abajo."),

    # Capital de Brasil
    (re.compile(r'\bcapital.*brasil\b', re.IGNORECASE),
        "La capital de Brasil es Brasilia, una ciudad planificada inaugurada en 1960."),
    
    # Siete maravillas
    (re.compile(r'\b(siete maravillas|7 maravillas)\b', re.IGNORECASE),
        "Las siete maravillas del mundo moderno son: la Gran Muralla China, Petra, el Cristo Redentor, Machu Picchu, Chichén Itzá, el Coliseo y el Taj Mahal."),
    
    # Preguntas sobre configuración
    (re.compile(r'\b(cómo|como).*configur(a|ación).*\b(enciende|apaga|luces|cámara|camara|modo|idioma|volumen)\b', re.IGNORECASE),
        "Puedo ayudarte con eso! Revisa la configuración en el archivo config.json. Pregúntame algo específico y te guiaré."),
    
    # ¿Qué hora es?
    (re.compile(r'\b(qué hora|que hora|hora actual|hora es)\b', re.IGNORECASE),
        "No tengo acceso a la hora actual. Necesito que me digas la hora o revisa el reloj de tu dispositivo."),
    
    # Preguntas sobre Zambrano (creador)
    (re.compile(r'\b(quién te creo|quien te creo|quién te hizo|quien te hizo|tu creador|zambrano)\b', re.IGNORECASE),
        "Fui creado por Zambrano, un joven programador del SENA apasionado por la tecnología y la inteligencia artificial."),
    
    # Preguntas sobre SENA
    (re.compile(r'\b(sena|qué es el sena|que es el sena)\b', re.IGNORECASE),
        "El SENA es el Servicio Nacional de Aprendizaje de Colombia. Ofrece formación técnica y tecnológica gratuita."),
    
    # Preguntas sobre tecnología
    (re.compile(r'\b(qué es|que es).*(ia|inteligencia artificial|machine learning|aprendizaje automatico)\b', re.IGNORECASE),
        "La inteligencia artificial es una tecnología que permite a las máquinas aprender y tomar decisiones. Se usa en asistentes como yo para entender y responder preguntas."),
    
    # Qué es un asistente virtual
    (re.compile(r'\b(qué es|que es).*(asistente virtual|asistente de voz|chatbot)\b', re.IGNORECASE),
        "Un asistente virtual es un programa que usa inteligencia artificial para conversar y ayudar. Yo soy un ejemplo de ello: puedo responder preguntas, recordar información y ejecutar comandos."),
    
    # API
    (re.compile(r'\b(qué es|que es).*api\b', re.IGNORECASE),
        "Una API es una interfaz que permite que dos programas se comuniquen. Funciona como un menú: defines qué puedes pedir y cómo pedirlo. Es fundamental para conectar servicios."),
    
    # Internet
    (re.compile(r'\b(cómo funciona|como funciona).*internet\b', re.IGNORECASE),
        "Internet es una red global de computadoras conectadas. Cuando visitas una web, tu computadora pide datos a un servidor. El servidor responde enviando la información a través de cables y routers."),
    
    # BMO (sobre sí mismo)
    (re.compile(r'\b(quién eres|quien eres|qué eres|que eres|cuéntame de ti|cuentame de ti)\b', re.IGNORECASE),
        "Soy BMO, un robot asistente creado por Zambrano. Puedo conversar contigo, responder preguntas y ayudarte con información. Estoy aquí para ser tu amigo."),
    
    # Hora de Aventura
    (re.compile(r'\b(hora de aventura|adventure time|finn|jake)\b', re.IGNORECASE),
        "Hora de Aventura es una serie animada. BMO es un personaje de esa serie, un robot que vive con Finn el humano y Jake el perro. Es un videojuego viviente muy adorable."),
]


def buscar_respuesta_predefinida(texto: str) -> str | None:
    texto_lower = sin_acentos(texto.lower())
    for patron, respuesta in _RESPUESTAS_PREDEFINIDAS:
        if patron.search(texto_lower):
            log.info(f"[PREDEFINIDA] Usando respuesta predefinida para: '{texto[:50]}'")
            return respuesta
    return None


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
    r"ll[aá]mame (\w+)",
    r"me dicen (\w+)",
    r"me puedes llamar (\w+)",
    r"puedes llamarme (\w+)",
    r"soy (\w+)",
    r"me llaman (\w+)",
    r"reg[ií]str[aá](?:me)? como (\w+)",
    r"gu[aá]rda(?:me)? como (\w+)",
    r"recu[eé]rda(?:me)? como (\w+)",
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
    (re.compile(r"√"),                          "raíz cuadrada de "),
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


# ── Normalización de texto ───────────────────────────────────────────────────

def normalizar_texto_entrada(texto: str) -> str:
    """
    Normaliza el texto de entrada antes de enviarlo al LLM.
    Corrige errores comunes de transcripción de Whisper.
    """
    texto_original = texto
    
    # Normalizar "número p" o "número P-I" a "número pi" (más agresivo)
    texto = re.sub(r'número\s+p\b', 'número pi', texto, flags=re.IGNORECASE)
    texto = re.sub(r'número\s+p-i\b', 'número pi', texto, flags=re.IGNORECASE)
    texto = re.sub(r'número\s+p\.', 'número pi', texto, flags=re.IGNORECASE)
    texto = re.sub(r'número\s+pi\b', 'número pi', texto, flags=re.IGNORECASE)  # Ya normalizado
    
    # Normalizar "el p" a "el pi" (cuando se refiere al número)
    texto = re.sub(r'\bel\s+p\b', 'el pi', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\bel\s+p-i\b', 'el pi', texto, flags=re.IGNORECASE)
    
    # Normalizar "de p" a "de pi"
    texto = re.sub(r'\bde\s+p\b', 'de pi', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\bde\s+p-i\b', 'de pi', texto, flags=re.IGNORECASE)
    
    # Normalizar "tiene el número p" a "tiene el número pi"
    texto = re.sub(r'tiene\s+el\s+número\s+p\b', 'tiene el número pi', texto, flags=re.IGNORECASE)
    texto = re.sub(r'tiene\s+el\s+número\s+p-i\b', 'tiene el número pi', texto, flags=re.IGNORECASE)
    
    # Normalizar "dígitos tiene" variantes
    texto = re.sub(r'dijitos', 'dígitos', texto, flags=re.IGNORECASE)
    
    if texto != texto_original:
        log.info(f"[NORMALIZACIÓN] '{texto_original}' → '{texto}'")
    
    return texto


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
    # Normalizar el texto de entrada
    mensaje = normalizar_texto_entrada(mensaje)
    
    # Buscar respuesta predefinida primero
    respuesta_predefinida = buscar_respuesta_predefinida(mensaje)
    if respuesta_predefinida:
        persistent_memory.add_user_message(mensaje, nombre_persona)
        persistent_memory.add_assistant_message(respuesta_predefinida, nombre_persona)
        
        if on_start_speaking:
            on_start_speaking()
        
        # Dividir en oraciones y hablar
        oraciones = re.split(r'[.!?]+', respuesta_predefinida)
        for oracion in oraciones:
            oracion = oracion.strip()
            if oracion:
                log.info("[PREDEFINIDA→TTS] '%s'", oracion)
                hablar_fn(oracion + ".")
        return
    
    # Clasificar la pregunta para optimizar la respuesta
    categoria = categorizar_pregunta(mensaje)
    num_predict = num_predict_para(mensaje)
    max_oraciones = max_oraciones_para(mensaje)
    length_hint = length_hint_para(mensaje)
    
    log.info(f"[CLASSIFY] '{mensaje[:50]}...' → {categoria} (max {num_predict} tokens, {max_oraciones} oraciones)")
    
    persistent_memory.add_user_message(mensaje, nombre_persona)
    messages = persistent_memory.get_context_for_llm(nombre_persona)
    
    # Agregar length_hint al system prompt
    if messages and messages[0].get("role") == "system":
        messages[0]["content"] += f" {length_hint}"

    model = config_manager.get("text_model", "qwen2.5:1.5b")
    options = config_manager.get_ollama_options()
    options["num_predict"] = num_predict  # Limitar tokens según categoría

    tts_queue: list[str] = []
    tts_lock  = threading.Lock()
    tts_done  = threading.Event()
    full_resp: list[str] = []
    oraciones_habladas = 0

    SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+')

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

            # Dividir el buffer completo por puntuación real
            segments = SENTENCE_SPLIT.split(sentence_buffer)

            if len(segments) > 1:
                complete = segments[:-1]
                sentence_buffer = segments[-1]

                for s in complete:
                    s = s.strip()
                    if s and re.search(r"[a-záéíóúñ]{3,}", s, re.IGNORECASE):
                        s = normalizar_para_tts(s)  # ✅ FIX: Normalizar TTS para pronunciación correcta
                        log.info("[LLM→TTS] '%s'", s)
                        with tts_lock:
                            tts_queue.append(s)
                        oraciones_habladas += 1

                        if oraciones_habladas >= max_oraciones:
                            break

                if oraciones_habladas >= max_oraciones:
                    log.info(f"[CLASSIFY] Límite de {max_oraciones} oraciones alcanzado, deteniendo stream")
                    break

        # Residuo sin puntuación al final del stream
        resto = sentence_buffer.strip()
        if resto and oraciones_habladas < max_oraciones:
            if resto[-1] not in ".!?":
                resto += "."
            if re.search(r"[a-záéíóúñ]{3,}", resto, re.IGNORECASE):
                resto = normalizar_para_tts(resto)  # ✅ FIX: Normalizar TTS
                with tts_lock:
                    tts_queue.append(resto)

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
