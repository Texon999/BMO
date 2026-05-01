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
    """Genera el system prompt optimizado para corregir errores específicos"""
    base_prompt = (
        "Eres BMO, un robot asistente amigable creado por Zambrano. "
        "Responde en español de forma natural y útil. "
        "Si te preguntan sobre Hora de Aventura, usa tu conocimiento de la serie. "
        "\n"
        "CORRECCIONES IMPORTANTES:\n"
        "- Bandera de Colombia: amarillo arriba, azul medio, rojo abajo\n"
        "- Bandera de México: verde izquierda, blanco medio, rojo derecha\n"
        "- Capital de Brasil: Brasilia (NO es Rio de Janeiro, NO es São Paulo)\n"
        "- Continentes: hay siete continentes en total\n"
        "\n"
        "Para otros datos, usa tu conocimiento entrenado. Si no estás seguro, "
        "di 'No tengo esa información específica'. "
        "Sé directo pero amigable, máximo 2-3 oraciones."
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


def _precargar_modelo():
    """Precarga el modelo LLM en RAM con configuración dinámica"""
    try:
        model = config_manager.get("text_model", "qwen2.5:1.5b")
        ollama.generate(model=model, prompt="hola", keep_alive=-1)
        log.info("[LLM] %s en RAM", model)
    except Exception as e:
        log.warning("[LLM] Error: %s — ejecuta: ollama serve", e)


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
        persistent_memory.add_assistant_message(respuesta_completa)
        
        # Auto-commit cada cierto número de mensajes
        if len(persistent_memory.session_memory) >= 4:  # 2 intercambios
            persistent_memory.commit_session_to_permanent()
    else:
        # Modo legacy
        if nombre_persona:
            agregar_turno_persona(nombre_persona, mensaje, respuesta_completa)
        else:
            agregar_turno_anonimo(mensaje, respuesta_completa)


# Inicialización y registro de cleanup
_precargar_modelo()
register_shutdown_handler(cleanup_llm)
register_shutdown_handler(persistent_memory.save_memory)
