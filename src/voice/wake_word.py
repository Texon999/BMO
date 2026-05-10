"""
Wake word detector para BMO.

Funciona como Alexa: BMO escucha continuamente en modo pasivo (bajo consumo),
y solo activa el procesamiento completo cuando detecta su nombre.

Variantes que reconoce (Whisper en español confunde mucho):
  "bmo", "bimo", "vimo", "bemo", "bmo", "b.m.o", "bi mo", "vi mo"

Flujo:
  1. escuchar_pasivo() → graba chunks cortos, transcribe rápido
  2. Si detecta wake word → reproduce sonido "tín" y devuelve True
  3. El ciclo principal llama a escuchar() normal para capturar el prompt

Sonido "tín":
  Generado con numpy (sin archivos externos).
  Dos tonos cortos ascendentes, como los asistentes de voz comerciales.
"""
import re
import logging
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

log = logging.getLogger("BMO.WakeWord")

# ── Variantes del wake word ───────────────────────────────────────────────────
# Whisper en español transcribe "BMO" de muchas formas distintas.
# Esta lista cubre las más comunes observadas en pruebas.

_WAKE_PATTERNS = re.compile(
    r"\b("
    r"b\.?m\.?o\.?"      # BMO, B.M.O, bmo
    r"|bimo"             # bimo (muy común en español)
    r"|vimo"             # vimo
    r"|bemo"             # bemo
    r"|bi\s*mo"          # bi mo
    r"|vi\s*mo"          # vi mo
    r"|bumo"             # bumo
    r"|bmo"              # bmo sin puntos
    r")\b",
    re.IGNORECASE,
)

# Parámetros de escucha pasiva (más agresivos para bajo consumo)
_PASIVO_CHUNK_SEC  = 0.3    # chunks más cortos para latencia baja
_PASIVO_MAX_SEC    = 3.0    # máximo de grabación pasiva por ciclo
_PASIVO_SILENCE    = 0.8    # silencio para cortar grabación pasiva
_PASIVO_THRESHOLD  = 0.012  # umbral VAD pasivo (ligeramente más sensible)


def _generar_tin(sample_rate: int = 22050) -> np.ndarray:
    """
    Genera el sonido "tín" de activación.
    Dos tonos cortos ascendentes (440Hz → 880Hz), 80ms cada uno.
    """
    duracion = 0.08   # segundos por tono
    fade     = 0.01   # fade in/out para evitar clicks
    t        = np.linspace(0, duracion, int(sample_rate * duracion), endpoint=False)

    def tono(freq: float) -> np.ndarray:
        onda = 0.35 * np.sin(2 * np.pi * freq * t).astype(np.float32)
        # Fade in/out
        fade_n = int(sample_rate * fade)
        onda[:fade_n]  *= np.linspace(0, 1, fade_n)
        onda[-fade_n:] *= np.linspace(1, 0, fade_n)
        return onda

    silencio = np.zeros(int(sample_rate * 0.03), dtype=np.float32)
    return np.concatenate([tono(440), silencio, tono(880)])


def reproducir_tin(sample_rate: int = 22050):
    """Reproduce el sonido de activación de wake word."""
    try:
        audio = _generar_tin(sample_rate)
        sd.play(audio, sample_rate)
        sd.wait()
    except Exception as e:
        log.warning("[WAKE] Error reproduciendo tín: %s", e)


def es_wake_word(texto: str) -> bool:
    """Devuelve True si el texto contiene el wake word de BMO."""
    return bool(_WAKE_PATTERNS.search(texto.strip()))


def extraer_prompt(texto: str) -> str:
    """
    Extrae el prompt que viene después del wake word.
    Ejemplo: "BMO qué hora es" → "qué hora es"
    Si no hay nada después, devuelve cadena vacía.
    """
    m = _WAKE_PATTERNS.search(texto)
    if not m:
        return texto.strip()
    resto = texto[m.end():].strip()
    # Limpiar signos de puntuación al inicio
    resto = re.sub(r"^[,.:;!?¿¡\s]+", "", resto)
    return resto


class WakeWordDetector:
    """
    Detector de wake word para BMO.
    Escucha en modo pasivo y activa cuando detecta el nombre.
    """

    def __init__(self, stt: WhisperModel, mic_device: int, sample_rate: int = 16000,
                 tts_rate: int = 22050):
        self._stt         = stt
        self._mic         = mic_device
        self._sample_rate = sample_rate
        self._tts_rate    = tts_rate

    def escuchar_pasivo(self) -> tuple[bool, str]:
        """
        Escucha en modo pasivo (chunks cortos, transcripción rápida).
        Devuelve (wake_detectado, texto_completo).

        Si detecta wake word:
          - Reproduce el sonido "tín"
          - Devuelve (True, prompt_extraído)
        Si no:
          - Devuelve (False, "")
        """
        chunk_size   = int(_PASIVO_CHUNK_SEC * self._sample_rate)
        buffer       = []
        grabando     = False
        silencio_acc = 0.0
        total_acc    = 0.0

        try:
            with sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="float32",
                device=self._mic,
                blocksize=chunk_size,
            ) as stream:
                while total_acc < _PASIVO_MAX_SEC:
                    chunk, _ = stream.read(chunk_size)
                    chunk_np  = chunk.flatten()
                    nivel     = float(np.abs(chunk_np).max())

                    if not grabando:
                        if nivel > _PASIVO_THRESHOLD:
                            grabando     = True
                            buffer       = [chunk_np]
                            total_acc    = _PASIVO_CHUNK_SEC
                            silencio_acc = 0.0
                    else:
                        buffer.append(chunk_np)
                        total_acc += _PASIVO_CHUNK_SEC
                        if nivel < _PASIVO_THRESHOLD:
                            silencio_acc += _PASIVO_CHUNK_SEC
                        else:
                            silencio_acc = 0.0
                        if silencio_acc >= _PASIVO_SILENCE:
                            break

        except Exception as e:
            log.warning("[WAKE] Error de stream: %s", e)
            return False, ""

        if not buffer or total_acc < 0.2:
            return False, ""

        audio_np = np.concatenate(buffer)

        # Transcripción rápida (beam_size=1 para velocidad)
        try:
            segments, _ = self._stt.transcribe(
                audio_np,
                language="es",
                beam_size=1,
                best_of=1,
                vad_filter=True,
                condition_on_previous_text=False,
                no_speech_threshold=0.7,
            )
            texto = " ".join(s.text for s in segments if s.no_speech_prob < 0.7).strip()
            texto = texto.replace("[BLANK_AUDIO]", "").strip()
        except Exception as e:
            log.warning("[WAKE] Error STT: %s", e)
            return False, ""

        if not texto:
            return False, ""

        log.debug("[WAKE] Escuché pasivo: '%s'", texto)

        if es_wake_word(texto):
            prompt = extraer_prompt(texto)
            log.info("[WAKE] Wake word detectado! Prompt: '%s'", prompt or "(vacío)")
            reproducir_tin(self._tts_rate)
            return True, prompt

        return False, ""
