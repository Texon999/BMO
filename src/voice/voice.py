"""
Módulo de voz de BMO.
STT : faster-whisper base (español)
TTS : piper-tts es_ES-sharvard-medium

Grabación por VAD — solo graba cuando detecta voz activa,
para en cuanto hay silencio. No graba en loop fijo.
"""
import json
import time
import numpy as np
import sounddevice as sd
from pathlib import Path
from faster_whisper import WhisperModel

# ── Configuración ─────────────────────────────────────────────────────────────
WHISPER_MODEL = "base"
WHISPER_LANG  = "es"
SAMPLE_RATE   = 16000

# Dispositivo de entrada — índice del micrófono que funciona
# -1 = autodetectar el primero que capte audio
MIC_DEVICE    = -1

# VAD settings
VAD_THRESHOLD      = 0.015   # nivel mínimo para considerar que hay voz
VAD_SILENCE_SEC    = 1.2     # segundos de silencio para terminar grabación
VAD_MAX_SEC        = 10.0    # máximo de grabación por turno
VAD_MIN_SEC        = 0.3     # mínimo de audio para procesar
CHUNK_SEC          = 0.05    # tamaño de chunk de lectura (50ms)

VOICE_ONNX   = Path("voices/es_ES-sharvard-medium.onnx")
VOICE_CONFIG = Path("voices/es_ES-sharvard-medium.onnx.json")


def _encontrar_microfono() -> int:
    """Encuentra el primer micrófono que realmente capta audio."""
    candidatos = list(range(sd.query_hostapis()[0].get("devices", [None]).__class__.__len__
                            if False else 30))
    for idx in range(30):
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
    return sd.default.device[0]


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
            beam_size=5,
            best_of=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
            condition_on_previous_text=False,
        )
        texto = " ".join(s.text for s in segments).strip()
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
            print(f"[TTS] {len(audio_np)/sr:.1f}s")
            sd.play(audio_np, sr)
            sd.wait()
        except Exception as e:
            print(f"[TTS] Error: {e}")
