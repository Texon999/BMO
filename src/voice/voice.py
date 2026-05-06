"""
Módulo de voz de BMO — Entrada (STT) y salida (TTS) de audio.

STT — Reconocimiento de voz:
  Usa faster-whisper con el modelo configurado (por defecto: base, español).
  La grabación funciona con VAD (detección de actividad de voz):
    - Espera en silencio hasta detectar voz (nivel > VAD_THRESHOLD)
    - Graba mientras hay voz activa
    - Termina cuando hay VAD_SILENCE_SEC segundos de silencio
    - O cuando se alcanza VAD_MAX_SEC segundos de grabación
  Esto evita grabar en loop fijo y reduce el tiempo de espera.

TTS — Síntesis de voz:
  Usa Piper TTS con la voz es_ES-sharvard-medium (español de España).
  El archivo de voz debe estar en voices/es_ES-sharvard-medium.onnx.
  Si no existe, BMO solo imprime el texto en consola (modo silencioso).
  Se agrega un pequeño silencio al final de cada oración para evitar cortes.

Autodetección de micrófono:
  Si MIC_DEVICE = -1, prueba cada dispositivo de entrada disponible
  grabando 0.3 segundos y verificando que capture audio real.
  Usa el primero que funcione.

Configuración:
  Todos los parámetros se leen desde src/config/runtime.py via variables de entorno.
"""
import json
import time
import numpy as np
import sounddevice as sd
from pathlib import Path
from faster_whisper import WhisperModel
from src.config.runtime import (
    WHISPER_MODEL,
    WHISPER_LANG,
    SAMPLE_RATE,
    MIC_DEVICE,
    OUTPUT_DEVICE,
    STT_BEAM_SIZE,
    STT_BEST_OF,
    VAD_THRESHOLD,
    VAD_SILENCE_SEC,
    VAD_MAX_SEC,
    VAD_MIN_SEC,
    CHUNK_SEC,
)

VOICE_ONNX   = Path("voices/es_ES-sharvard-medium.onnx")
VOICE_CONFIG = Path("voices/es_ES-sharvard-medium.onnx.json")


def _encontrar_microfono() -> int:
    """Encuentra el primer micrófono que realmente capta audio."""
    devices = sd.query_devices()
    candidatos = [i for i, d in enumerate(devices) if d.get("max_input_channels", 0) > 0]
    for idx in candidatos:
        try:
            info = sd.query_devices(idx)
            if info["max_input_channels"] < 1:
                continue
            # Prueba rápida de 0.3s
            audio = sd.rec(int(0.3 * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                           channels=1, dtype="float32", device=idx)
            sd.wait()
            if np.abs(audio).max() > 0.001:
                print(f"[MIC] Usando dispositivo [{idx}]: {info['name']}")
                return idx
        except Exception:
            continue
    print("[MIC] No se encontró micrófono funcional, usando default")
    default_in = sd.default.device[0]
    return default_in if default_in is not None else 0


class VozBMO:
    def __init__(self, mic_device: int = MIC_DEVICE):
        print(f"[VOZ] Cargando Whisper {WHISPER_MODEL}...")
        self.stt = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        print("[VOZ] Whisper listo")

        # Detectar micrófono
        if mic_device < 0:
            self._mic = _encontrar_microfono()
        else:
            self._mic = mic_device
            print(f"[MIC] Usando dispositivo [{mic_device}]: {sd.query_devices(mic_device)['name']}")

        if OUTPUT_DEVICE >= 0:
            sd.default.device = (self._mic, OUTPUT_DEVICE)
            print(f"[AUDIO] Salida forzada a dispositivo [{OUTPUT_DEVICE}]")

        # TTS
        self._tts      = None
        self._tts_rate = 22050
        if VOICE_ONNX.exists():
            print("[VOZ] Cargando Piper TTS...")
            try:
                from piper.voice import PiperVoice
                self._tts = PiperVoice.load(str(VOICE_ONNX), config_path=str(VOICE_CONFIG))
                with open(VOICE_CONFIG, encoding="utf-8") as f:
                    cfg = json.load(f)
                self._tts_rate = cfg.get("audio", {}).get("sample_rate", 22050)
                print(f"[VOZ] Piper listo — {self._tts_rate}Hz")
            except Exception as e:
                print(f"[VOZ] Error Piper: {e}")
        else:
            print(f"[VOZ] Voz no encontrada: {VOICE_ONNX}")

    # ── STT con VAD ───────────────────────────────────────────────────────────

    def escuchar(self) -> str:
        """
        Escucha hasta detectar voz, graba hasta que haya silencio,
        luego transcribe. No graba en loop fijo.
        """
        chunk_size   = int(CHUNK_SEC * SAMPLE_RATE)
        buffer       = []
        grabando     = False
        silencio_acc = 0.0
        total_acc    = 0.0

        print("[STT] Esperando voz...")

        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                                dtype="float32", device=self._mic,
                                blocksize=chunk_size) as stream:
                while True:
                    chunk, _ = stream.read(chunk_size)
                    chunk_np  = chunk.flatten()
                    nivel     = np.abs(chunk_np).max()

                    if not grabando:
                        if nivel > VAD_THRESHOLD:
                            print("[STT] Voz detectada, grabando...")
                            grabando = True
                            buffer   = [chunk_np]
                            total_acc = CHUNK_SEC
                            silencio_acc = 0.0
                    else:
                        buffer.append(chunk_np)
                        total_acc += CHUNK_SEC

                        if nivel < VAD_THRESHOLD:
                            silencio_acc += CHUNK_SEC
                        else:
                            silencio_acc = 0.0

                        # Terminar si hay suficiente silencio o se alcanzó el máximo
                        if silencio_acc >= VAD_SILENCE_SEC or total_acc >= VAD_MAX_SEC:
                            print(f"[STT] Fin de voz ({total_acc:.1f}s grabados)")
                            break

        except Exception as e:
            print(f"[STT] Error de stream: {e}")
            return ""

        if total_acc < VAD_MIN_SEC or not buffer:
            print("[STT] Audio muy corto, ignorando")
            return ""

        audio_np = np.concatenate(buffer)

        segments, _ = self.stt.transcribe(
            audio_np,
            language=WHISPER_LANG,
            beam_size=STT_BEAM_SIZE,
            best_of=STT_BEST_OF,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
            log_prob_threshold=-0.8,
        )
        # Filtrar segmentos con baja confianza (ruido transcrito como texto)
        texto = " ".join(
            s.text for s in segments if s.no_speech_prob < 0.6
        ).strip()
        texto = texto.replace("[BLANK_AUDIO]", "").replace("(Música)", "").strip()

        if texto:
            print(f"[STT] '{texto}'")
        else:
            print("[STT] Sin habla reconocida")
        return texto

    # ── TTS ───────────────────────────────────────────────────────────────────

    def hablar(self, texto: str):
        if not self._tts:
            print(f"[BMO]: {texto}")
            return
        print(f"[TTS] '{texto[:70]}'")
        try:
            chunks   = list(self._tts.synthesize(texto))
            if not chunks:
                return
            audio_np = np.concatenate([c.audio_float_array for c in chunks])
            sr       = chunks[0].sample_rate
            # Silencio pre (0.05s) y post (0.5s) para evitar cortes de palabras
            silencio_pre  = np.zeros(int(0.05 * sr), dtype="float32")
            silencio_post = np.zeros(int(0.5  * sr), dtype="float32")
            audio_np = np.concatenate([silencio_pre, audio_np, silencio_post])
            print(f"[TTS] {len(audio_np)/sr:.1f}s")
            sd.play(audio_np *0.5, sr) 
            # La multiplicación por 0.5 es para reducir el volumen, ya que algunas voces pueden ser muy fuerte
            sd.wait()
        except Exception as e:
            print(f"[TTS] Error: {e}")
