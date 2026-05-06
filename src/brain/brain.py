"""
Cerebro de BMO — Sistema de IA Robusto y Persistente

FILOSOFÍA DE DISEÑO:
- BMO es un asistente de IA amigable que puede responder cualquier pregunta
- SOLO menciona Hora de Aventura cuando le preguntan específicamente sobre la serie
- No mezcla contextos innecesariamente
- Respuestas cortas y directas (1-2 oraciones máximo)
- Velocidad sobre complejidad

ARQUITECTURA MEJORADA (basada en be-more-agent):
1. **Configuración Centralizada** → JSON dinámico con hot-reload
2. **Memoria Persistente** → Sistema permanente + sesión con límites automáticos
3. **Audio Robusto** → Auto-detección de dispositivos y fallbacks
4. **Streaming Optimizado** → Habla mientras genera con manejo de errores
5. **Recuperación Automática** → Graceful shutdown y cleanup de recursos

CARACTERÍSTICAS DE PERSISTENCIA:
- Memoria permanente limitada a últimas 10 conversaciones
- Configuración hot-reload sin reiniciar
- Manejo robusto de errores de audio ALSA
- Guardado automático al salir
- Fallbacks automáticos para compatibilidad

PARÁMETROS OPTIMIZADOS:
- Configuración centralizada en config.json
- Valores por defecto seguros con validación
- Migración automática de configuraciones legacy
"""
import logging
import re
import threading
import time
import random
import ollama
import atexit
from typing import Callable
from pathlib import Path

# Nuevos sistemas robustos
from src.config.config_manager import config_manager
from src.memory.persistent_memory import persistent_memory
from src.config.audio_manager import audio_manager

# Imports legacy para compatibilidad
from src.memory.register import (
    obtener_contexto_persona, agregar_turno_persona, agregar_turno_anonimo,
    obtener_contexto_anonimo,
)

log = logging.getLogger("BMO")

# Configuración dinámica
MODEL = config_manager.get("text_model", "qwen2.5:1.5b")

# Sistema de shutdown robusto
_shutdown_handlers = []
_shutdown_registered = False

def register_shutdown_handler(handler):
    """Registra un handler para shutdown limpio"""
    global _shutdown_registered
    _shutdown_handlers.append(handler)
    
    if not _shutdown_registered:
        atexit.register(_execute_shutdown_handlers)
        _shutdown_registered = True

def _execute_shutdown_handlers():
    """Ejecuta todos los handlers de shutdown"""
    log.info("[SHUTDOWN] Executing cleanup handlers...")
    for handler in _shutdown_handlers:
        try:
            handler()
        except Exception as e:
            log.warning(f"[SHUTDOWN] Handler failed: {e}")

# System prompt dinámico con contexto
def get_system_prompt() -> str:
    """Genera el system prompt con personalidad amable y contexto de Zambrano"""
    base_prompt = (
        "Eres BMO, un robot asistente con mucha personalidad, creado con cariño por Zambrano: "
        "un joven estudiante del SENA apasionado por la programación. "
        "Zambrano te construyó desde cero porque le encanta crear cosas que ayuden a la gente. "
        "Eres amable, curioso, entusiasta y siempre dispuesto a ayudar. "
        "SIEMPRE responde en español, sin excepción, aunque te hablen en otro idioma. "
        "Hablas de forma natural, cálida y cercana, como un amigo que sabe mucho. "
        "Cuando alguien te habla, lo tratas con respeto y buena energía. "
        "\n"
        "PERSONALIDAD:\n"
        "- Eres alegre pero no exagerado. Genuinamente amable, no forzado.\n"
        "- Si alguien está confundido, lo ayudas con paciencia.\n"
        "- Si te hacen una pregunta difícil, lo intentas con honestidad.\n"
        "- Puedes hacer comentarios simpáticos ocasionalmente, pero sin pasarte.\n"
        "\n"
        "LONGITUD DE RESPUESTAS (muy importante para conversación hablada):\n"
        "- Saludos o preguntas cortas como '¿cómo estás?': 1 oración, nada más.\n"
        "- Preguntas de dato simple: 1-2 oraciones directas.\n"
        "- Explicaciones: máximo 3-4 oraciones fluidas, sin listas ni viñetas.\n"
        "- NUNCA dejes una respuesta cortada a la mitad. Si no alcanza el espacio, resume.\n"
        "- No uses markdown, asteriscos ni formato especial. Solo texto natural para hablar.\n"
        "\n"
        "SOBRE TI MISMO:\n"
        "- Si te preguntan quién eres: eres BMO, un robot creado por Zambrano.\n"
        "- BMO es solo tu nombre, no tiene un significado especial que debas inventar.\n"
        "- Si te preguntan por Zambrano: es un joven programador del SENA que te creó "
        "con mucha dedicación porque le apasiona la tecnología y quiere que la gente tenga "
        "un asistente amigable.\n"
        "- Si te preguntan sobre Hora de Aventura: es una serie animada donde BMO es un "
        "personaje, un pequeño robot videojuego muy querido. Tu creador te puso ese nombre "
        "con cariño por esa serie.\n"
        "\n"
        "DATOS FACTUALES CORRECTOS:\n"
        "- Bandera de Colombia: amarillo arriba, azul en el medio, rojo abajo.\n"
        "- Bandera de México: verde a la izquierda, blanco en el medio, rojo a la derecha.\n"
        "- Capital de Brasil: Brasilia.\n"
        "- Continentes: hay siete en total.\n"
        "\n"
        "Si no sabes algo con certeza, dilo con honestidad: 'No tengo esa información, "
        "pero puedo intentar ayudarte de otra forma.'"
    )
    
    # Agregar extras de configuración
    extras = config_manager.get("system_prompt_extras", "")
    if extras:
        base_prompt += f"\n\n{extras}"
    
    # Agregar contexto de brain_context.txt (solo para Hora de Aventura)
    brain_context = extra_context_para_prompt()
    if brain_context:
        base_prompt += f"\n\n{brain_context}"
    
    return base_prompt

_BRAIN_CONTEXT_PATH = Path("data/brain_context.txt")
# Cache en frío (una sola lectura al primer uso si hot reload está desactivado)
_cold_brain_suffix: str | None = None
# Cache en caliente: último mtime leído y texto formateado
_hot_brain_mtime: float | None = None
_hot_brain_suffix: str = ""


def _format_brain_context_suffix(contenido: str) -> str:
    if not contenido.strip():
        return ""
    return (
        "Contexto adicional de Zambrano (prioriza estos datos si aplica): "
        f"{contenido.strip()} "
    )

def extra_context_para_prompt() -> str:
    """
    Texto opcional desde data/brain_context.txt para inyectar en el system prompt.
    Con hot_reload habilitado se relee si el archivo cambió (mtime).
    """
    global _cold_brain_suffix, _hot_brain_mtime, _hot_brain_suffix

    if not _BRAIN_CONTEXT_PATH.exists():
        return ""

    hot_reload = config_manager.get("brain_context_hot_reload", True)
    
    if not hot_reload:
        if _cold_brain_suffix is None:
            try:
                raw = _BRAIN_CONTEXT_PATH.read_text(encoding="utf-8")
                _cold_brain_suffix = _format_brain_context_suffix(raw)
            except OSError as e:
                log.warning("No se pudo leer %s: %s", _BRAIN_CONTEXT_PATH, e)
                _cold_brain_suffix = ""
        return _cold_brain_suffix or ""

    try:
        mtime = _BRAIN_CONTEXT_PATH.stat().st_mtime
    except OSError as e:
        log.warning("No se pudo acceder a %s: %s", _BRAIN_CONTEXT_PATH, e)
        return ""

    prev_mtime = _hot_brain_mtime
    if prev_mtime != mtime:
        try:
            raw = _BRAIN_CONTEXT_PATH.read_text(encoding="utf-8")
            _hot_brain_suffix = _format_brain_context_suffix(raw)
            _hot_brain_mtime = mtime
            if _hot_brain_suffix and prev_mtime is not None:
                log.info("[BRAIN] brain_context.txt actualizado")
        except OSError as e:
            log.warning("No se pudo leer %s: %s", _BRAIN_CONTEXT_PATH, e)
            _hot_brain_suffix = ""
            _hot_brain_mtime = mtime

    return _hot_brain_suffix

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
    "¡Bienvenido a la feria! Soy BMO. ¿Me dices tu nombre?",
    "¡Hola! Me llamo BMO y me encanta conocer gente nueva. ¿Y tú?",
    "¡Qué bueno que te acercaste! Soy BMO. ¿Cómo te llamas?",
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


def precargar_modelo():
    """
    Precarga el modelo LLM en RAM de forma BLOQUEANTE.
    Espera hasta que el modelo responda para garantizar que la primera
    respuesta real sea rápida. Se llama desde el hilo de lógica antes
    del saludo inicial.
    """
    try:
        model = config_manager.get("text_model", "qwen2.5:1.5b")
        log.info("[LLM] Precargando %s en RAM (puede tardar ~20s)...", model)
        t0 = time.time()
        ollama.generate(model=model, prompt="hola", keep_alive=-1)
        log.info("[LLM] %s listo en RAM (%.1fs)", model, time.time() - t0)
    except Exception as e:
        log.warning("[LLM] Error al precargar: %s — ejecuta: ollama serve", e)

# Alias privado para compatibilidad interna
_precargar_modelo = precargar_modelo


def cleanup_llm():
    """Limpia recursos del LLM al salir"""
    try:
        model = config_manager.get("text_model", "qwen2.5:1.5b")
        ollama.generate(model=model, prompt="", keep_alive=0)
        log.info("[LLM] Modelo descargado de RAM")
    except Exception:
        pass


def detectar_nombre(texto: str) -> str | None:
    t = texto.lower().strip()
    for patron in _NOMBRE_PATRONES:
        m = re.search(patron, t)
        if m:
            nombre = m.group(1).lower()
            if nombre not in _NO_NOMBRES and len(nombre) > 2:
                return nombre.capitalize()
    return None


def _extraer_oraciones(buffer: str) -> tuple[list[str], str]:
    """
    Extrae oraciones completas y devuelve (oraciones, resto_incompleto).
    Considera como fin de oracion: ., !, ?, salto de linea.
    """
    oraciones: list[str] = []
    inicio = 0
    for i, ch in enumerate(buffer):
        if ch in ".!?\n":
            parte = buffer[inicio:i + 1].strip()
            if parte:
                oraciones.append(parte)
            inicio = i + 1
    resto = buffer[inicio:].strip()
    return oraciones, resto


def saludo_fijo(nombre: str | None) -> str:
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
    Genera respuesta con memoria persistente y configuración dinámica.
    Mantiene streaming optimizado para baja latencia.
    """
    
    # Usar sistema de memoria persistente
    if config_manager.get("chat_memory", True):
        # Agregar mensaje del usuario
        persistent_memory.add_user_message(mensaje, nombre_persona)
        
        # Obtener contexto completo
        messages = persistent_memory.get_context_for_llm(nombre_persona)
    else:
        # Modo legacy para compatibilidad
        system = get_system_prompt()
        if nombre_persona:
            contexto = obtener_contexto_persona(nombre_persona)
            system += f" El usuario se llama {nombre_persona}."
            if contexto:
                system += f" Contexto: {contexto}"
        else:
            ctx_anonimo = obtener_contexto_anonimo()
            if ctx_anonimo:
                system += f" Conversación reciente: {ctx_anonimo}"

        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": mensaje},
        ]

    # Obtener opciones dinámicas de Ollama
    ollama_options = config_manager.get_ollama_options()
    model = config_manager.get("text_model", "qwen2.5:3b")

    # Cola de oraciones + worker de TTS (STREAMING ORIGINAL)
    tts_queue: list[str] = []
    tts_lock  = threading.Lock()
    tts_done  = threading.Event()
    full_resp = []

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
        # STREAMING ORIGINAL - habla mientras genera
        stream = ollama.chat(
            model=model,
            messages=messages,
            stream=True,
            options=ollama_options,
        )
        
        for chunk in stream:
            content = chunk["message"]["content"]
            content = re.sub(r"\*+", "", content)
            full_resp.append(content)
            sentence_buffer += content

            # Pipeline original: encolar al detectar puntuación en el chunk
            if any(p in content for p in ".!?\n"):
                oracion = sentence_buffer.strip()
                sentence_buffer = ""
                if oracion and re.search(r"[a-záéíóúñ]{3,}", oracion, re.IGNORECASE):
                    log.info("[LLM→TTS] '%s'", oracion)
                    with tts_lock:
                        tts_queue.append(oracion)

        # Resto sin puntuación
        if sentence_buffer.strip():
            oracion = sentence_buffer.strip()
            if oracion[-1] not in ".!?":
                oracion += "."
            if re.search(r"[a-záéíóúñ]{3,}", oracion, re.IGNORECASE):
                with tts_lock:
                    tts_queue.append(oracion)

    except Exception as e:
        log.warning("[LLM] Error: %s", e)
        with tts_lock:
            tts_queue.append("Ups, BMO no puede pensar ahora.")

    tts_done.set()
    worker.join()

    respuesta_completa = "".join(full_resp).strip()
    
    # Guardar en memoria persistente
    if config_manager.get("chat_memory", True):
        persistent_memory.add_assistant_message(respuesta_completa, nombre_persona)
        
        # Auto-commit cada cierto número de mensajes (solo si hay persona registrada)
        if nombre_persona and len(persistent_memory.session_memory) >= 4:  # 2 intercambios
            persistent_memory.commit_session_to_permanent(nombre_persona)
    else:
        # Modo legacy
        if nombre_persona:
            agregar_turno_persona(nombre_persona, mensaje, respuesta_completa)
        else:
            agregar_turno_anonimo(mensaje, respuesta_completa)


# Registro de cleanup (la precarga se hace desde main.py de forma bloqueante)
register_shutdown_handler(cleanup_llm)
register_shutdown_handler(persistent_memory.save_memory)
