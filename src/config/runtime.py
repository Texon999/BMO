"""
Configuración de runtime para BMO mediante variables de entorno.

Permite mover el proyecto entre equipos (PC de desarrollo, Raspberry Pi 5)
sin necesidad de editar el código fuente. Todos los parámetros tienen valores
por defecto optimizados para Raspberry Pi 5 8GB.

# ─────────────────────────────────────────────────────────────────────────────
# GUÍA DE PARÁMETROS DEL LLM (para entender qué toca cada variable)
# ─────────────────────────────────────────────────────────────────────────────
#
# TEMPERATURA (BMO_LLM_TEMPERATURE) — "creatividad" del modelo
#   Controla qué tan predecible o sorprendente es la respuesta.
#   Internamente, el modelo calcula una probabilidad para cada posible
#   siguiente palabra. La temperatura escala esas probabilidades:
#
#   0.0  → siempre elige la palabra más probable (robótico, repetitivo)
#   0.5  → bastante predecible, respuestas seguras
#   0.7  → equilibrio: coherente pero con algo de variedad  ← recomendado
#   1.0  → más variedad, puede volverse impreciso
#   1.5+ → muy creativo, puede alucinar o perder coherencia
#
#   Para BMO en feria: 0.7 — respuestas naturales sin inventar cosas.
#
# TOP_K (BMO_LLM_TOP_K) — "vocabulario candidato"
#   En cada paso, el modelo solo considera las K palabras más probables.
#   Descarta el resto antes de aplicar temperatura.
#
#   10  → muy conservador, pocas opciones
#   40  → estándar, buen balance
#   60  → más variedad de vocabulario
#
#   Para BMO: 50 — suficiente variedad sin perder coherencia.
#
# TOP_P (BMO_LLM_TOP_P) — "masa de probabilidad acumulada"
#   Complementa top_k: elige las palabras cuyas probabilidades suman
#   hasta P en total. Si top_k=50 pero las primeras 5 ya suman 0.9,
#   solo usa esas 5.
#
#   0.8  → más conservador
#   0.9  → estándar
#   0.95 → más variedad
#
#   Para BMO: 0.9 — estándar, funciona bien con Qwen.
#
# NUM_PREDICT (BMO_LLM_NUM_PREDICT) — "máximo de tokens por respuesta"
#   Cuántos tokens (≈ palabras o fragmentos de palabras) puede generar
#   el modelo como máximo por respuesta.
#
#   En RPi5 con Qwen 2.5:1.5b, cada token tarda ~0.15s → 150 tokens ≈ 22s.
#   Valores típicos:
#   40-80   → respuestas cortas (1-2 oraciones)
#   150-200 → respuestas normales (2-4 oraciones)
#   300+    → respuestas largas (párrafos completos)
#
# REPEAT_PENALTY (BMO_LLM_REPEAT_PENALTY) — "penalización por repetición"
#   Reduce la probabilidad de que el modelo repita palabras o frases
#   que ya usó en la misma respuesta.
#
#   1.0  → sin penalización (puede repetirse)
#   1.1  → penalización suave
#   1.15 → estándar para conversación
#   1.3+ → muy agresivo, puede sonar forzado
#
# NUM_THREAD (BMO_LLM_NUM_THREAD) — "hilos de CPU para inferencia"
#   Cuántos núcleos del procesador usa Ollama para calcular.
#   RPi5 tiene 4 núcleos físicos (8 con hyperthreading).
#   Usar 4 deja margen para los otros hilos (cámara, audio, display).
#
# KEEP_ALIVE (BMO_LLM_KEEP_ALIVE) — "tiempo en RAM tras inactividad"
#   -1 → el modelo nunca se descarga (recomendado para feria)
#    0 → se descarga inmediatamente tras cada respuesta
#  300 → se descarga tras 5 minutos sin uso
#
# ─────────────────────────────────────────────────────────────────────────────

Variables de entorno disponibles:

  Hardware:
    BMO_CAMERA_INDEX          Índice de cámara (default: 0)
    BMO_MIC_DEVICE            Índice de micrófono, -1 = autodetectar (default: -1)
    BMO_OUTPUT_DEVICE         Índice de salida de audio, -1 = default del sistema (default: -1)
    BMO_HEADLESS              Sin ventana gráfica, útil en servidores (default: false)

  STT — Reconocimiento de voz (Whisper):
    BMO_WHISPER_MODEL         Modelo de Whisper: tiny, base, small (default: base)
    BMO_WHISPER_LANG          Idioma de transcripción (default: es)
    BMO_STT_BEAM_SIZE         Tamaño de búsqueda beam (default: 2)
    BMO_STT_BEST_OF           Candidatos a evaluar (default: 2)
    BMO_SAMPLE_RATE           Frecuencia de muestreo en Hz (default: 16000)

  VAD — Detección de actividad de voz:
    BMO_VAD_THRESHOLD         Nivel mínimo de amplitud para considerar voz (default: 0.015)
    BMO_VAD_SILENCE_SEC       Segundos de silencio para terminar grabación (default: 1.2)
    BMO_VAD_MAX_SEC           Máximo de segundos grabados por turno (default: 10.0)
    BMO_VAD_MIN_SEC           Mínimo de segundos para procesar el audio (default: 0.3)
    BMO_CHUNK_SEC             Tamaño de cada chunk de lectura en segundos (default: 0.05)

  LLM — Modelo de lenguaje (Ollama):
    BMO_LLM_MODEL             Modelo Ollama a usar (default: qwen2.5:1.5b)
    BMO_LLM_KEEP_ALIVE        Segundos en RAM tras inactividad, -1 = siempre (default: -1)
    BMO_LLM_NUM_THREAD        Hilos de CPU para inferencia (default: 4)
    BMO_LLM_NUM_PREDICT       Máximo de tokens fallback — el clasificador lo sobreescribe (default: 180)
    BMO_LLM_TEMPERATURE       Creatividad del modelo, 0=determinista (default: 0.65)
    BMO_LLM_TOP_K             Candidatos de vocabulario por token (default: 40)
    BMO_LLM_TOP_P             Probabilidad acumulada de muestreo (default: 0.9)
    BMO_LLM_REPEAT_PENALTY    Penalización por repetición de tokens (default: 1.12)

  Visión:
    BMO_VISION_PROCESS_EVERY_N  Procesar rostro 1 de cada N frames (default: 2 en RPi5)
                                 Usar 1 en PC de desarrollo para máxima precisión.

  Cerebro:
    BMO_BRAIN_CONTEXT_HOT_RELOAD  Recargar data/brain_context.txt sin reiniciar (default: true)
"""
import os
from pathlib import Path

# Cargar .env si existe (permite configurar BMO sin tocar el código)
# Busca .env en la raíz del proyecto (BMO/) y en el directorio de trabajo actual
def _cargar_dotenv():
    for ruta in [Path(".env"), Path(__file__).parent.parent.parent / ".env"]:
        if ruta.exists():
            try:
                with open(ruta, encoding="utf-8") as f:
                    for linea in f:
                        linea = linea.strip()
                        if not linea or linea.startswith("#") or "=" not in linea:
                            continue
                        clave, _, valor = linea.partition("=")
                        clave = clave.strip()
                        valor = valor.strip().strip('"').strip("'")
                        if clave and clave not in os.environ:
                            os.environ[clave] = valor
            except OSError:
                pass
            break

_cargar_dotenv()


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


CAMERA_INDEX = _env_int("BMO_CAMERA_INDEX", 0)
MIC_DEVICE = _env_int("BMO_MIC_DEVICE", -1)
OUTPUT_DEVICE = _env_int("BMO_OUTPUT_DEVICE", -1)
HEADLESS = _env_bool("BMO_HEADLESS", False)

WHISPER_MODEL = os.getenv("BMO_WHISPER_MODEL", "base")
WHISPER_LANG = os.getenv("BMO_WHISPER_LANG", "es")
STT_BEAM_SIZE = _env_int("BMO_STT_BEAM_SIZE", 2)
STT_BEST_OF = _env_int("BMO_STT_BEST_OF", 2)
SAMPLE_RATE = _env_int("BMO_SAMPLE_RATE", 16000)

VAD_THRESHOLD = _env_float("BMO_VAD_THRESHOLD", 0.015)
VAD_SILENCE_SEC = _env_float("BMO_VAD_SILENCE_SEC", 1.2)
VAD_MAX_SEC = _env_float("BMO_VAD_MAX_SEC", 10.0)
VAD_MIN_SEC = _env_float("BMO_VAD_MIN_SEC", 0.3)
CHUNK_SEC = _env_float("BMO_CHUNK_SEC", 0.05)

LLM_MODEL = os.getenv("BMO_LLM_MODEL", "qwen2.5:1.5b")
LLM_KEEP_ALIVE = _env_int("BMO_LLM_KEEP_ALIVE", -1)
LLM_NUM_THREAD = _env_int("BMO_LLM_NUM_THREAD", 4)
LLM_NUM_PREDICT = _env_int("BMO_LLM_NUM_PREDICT", 100)     # Valor original exitoso
LLM_TEMPERATURE = _env_float("BMO_LLM_TEMPERATURE", 0.75)   # Equilibrio perfecto
LLM_TOP_K = _env_int("BMO_LLM_TOP_K", 50)                 # Variedad adecuada
LLM_TOP_P = _env_float("BMO_LLM_TOP_P", 0.85)
LLM_REPEAT_PENALTY = _env_float("BMO_LLM_REPEAT_PENALTY", 1.1)

# Visión: 2 en RPi5 (procesa 1 de cada 2 frames → ~15 FPS efectivos, menos CPU)
# Cambiar a 1 en PC de desarrollo para máxima precisión
VISION_PROCESS_EVERY_N = max(1, _env_int("BMO_VISION_PROCESS_EVERY_N", 2))

# Recargar data/brain_context.txt cuando cambie (sin reiniciar el proceso)
BRAIN_CONTEXT_HOT_RELOAD = _env_bool("BMO_BRAIN_CONTEXT_HOT_RELOAD", True)
