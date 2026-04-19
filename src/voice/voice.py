"""
Módulo de voz de BMO.
STT: faster-whisper (tiny, español)
TTS: piper-tts es_ES-sharvard-medium
"""
import io
import wave
import numpy as np
import sounddevice as sd
import soundfile as sf
from pathlib import Path
from faster_whisper import WhisperModel

WHISPER_MODEL  = "tiny"
WHISPER_LANG   = "es"
SAMPLE_RATE    = 16000
RECORD_SECONDS = 5

VOICE_ONNX   = Path("voices/es_ES-sharvard-medium.onnx")
VOICE_CONFIG = Path("voices/es_ES-sharvard-medium.onnx.json")


class VozBMO:
    def __init__(self):
        print("[VOZ] Cargando Whisper tiny...")
        self.stt = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        print("[VOZ] Whisper listo")

        self._tts = None
        self._tts_rate = 22050
        if VOICE_ONNX.exists():
            print("[VOZ] Cargando Piper TTS...")
            try:
                from piper.voice import PiperVoice
                import json
                self._tts = PiperVoice.load(str(VOICE_ONNX), config_path=str(VOICE_CONFIG))
                # Leer sample rate del config
                with open(VOICE_CONFIG) as f:
                    cfg = json.load(f)
                self._tts_rate = cfg.get("audio", {}).get("sample_rate", 22050)
                print(f"[VOZ] Piper listo — sample_rate={self._tts_rate}")
            except Exception as e:
                print(f"[VOZ] Error cargando Piper: {e}")
        else:
            print(f"[VOZ] Voz no encontrada: {VOICE_ONNX}")
            print("[VOZ] Ejecuta: python scripts/download_voice.py")

    # ── STT ───────────────────────────────────────────────────────────────────

    def escuchar(self, segundos: int = RECORD_SECONDS) -> str:
        """Graba del micrófono y transcribe con Whisper."""
        print(f"[STT] Grabando {segundos}s...")
        try:
            audio = sd.rec(
                int(segundos * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
            )
            sd.wait()
        except Exception as e:
            print(f"[STT] Error de micrófono: {e}")
            return ""

        audio_np = audio.flatten()
        # Ignorar si el audio es casi silencio
        if np.abs(audio_np).max() < 0.01:
            print("[STT] Silencio detectado")
            return ""

        segments, info = self.stt.transcribe(
            audio_np,
            language=WHISPER_LANG,
            beam_size=1,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        texto = " ".join(s.text for s in segments).strip()
        if texto:
            print(f"[STT] Transcrito: '{texto}'")
        else:
            print("[STT] No se detectó habla")
        return texto

    # ── TTS ───────────────────────────────────────────────────────────────────

    def hablar(self, texto: str):
        """Sintetiza con Piper y reproduce."""
        if not self._tts:
            print(f"[TTS] (sin voz) BMO: {texto}")
            return

        print(f"[TTS] Sintetizando: '{texto[:60]}...' " if len(texto) > 60 else f"[TTS] Sintetizando: '{texto}'")
        try:
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self._tts_rate)
                self._tts.synthesize(texto, wav_file)

            buf.seek(0)
            data, sr = sf.read(buf, dtype="float32")
            print(f"[TTS] Reproduciendo {len(data)/sr:.1f}s de audio @ {sr}Hz")
            sd.play(data, sr)
            sd.wait()
            print("[TTS] Reproducción completa")
        except Exception as e:
            print(f"[TTS] Error: {e}")
            print(f"[TTS] (fallback) BMO: {texto}")
