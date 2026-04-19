"""
Módulo de voz de BMO.
- STT: faster-whisper (modelo tiny/base, corre local)
- TTS: piper-tts con voz española es_ES-sharvard-medium
"""
import io
import queue
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
from pathlib import Path

# faster-whisper
from faster_whisper import WhisperModel

# piper
from piper.voice import PiperVoice


# ── Configuración ─────────────────────────────────────────────────────────────

WHISPER_MODEL   = "tiny"          # "tiny" para Pi, "base" para PC
WHISPER_LANG    = "es"
SAMPLE_RATE     = 16000           # Hz requerido por Whisper
RECORD_SECONDS  = 5               # segundos de grabación por turno
VOICE_MODEL     = Path("voices/es_ES-sharvard-medium.onnx")
VOICE_CONFIG    = Path("voices/es_ES-sharvard-medium.onnx.json")


class VozBMO:
    def __init__(self):
        print("⏳ Cargando Whisper...")
        self.stt = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        print("✓ Whisper listo")

        self._tts = None
        if VOICE_MODEL.exists():
            print("⏳ Cargando Piper TTS...")
            self._tts = PiperVoice.load(str(VOICE_MODEL), config_path=str(VOICE_CONFIG))
            print("✓ Piper TTS listo")
        else:
            print(f"⚠ Voz no encontrada en {VOICE_MODEL}. Ejecuta scripts/download_voice.py")

    # ── STT ───────────────────────────────────────────────────────────────────

    def escuchar(self, segundos: int = RECORD_SECONDS) -> str:
        """Graba audio del micrófono y devuelve el texto transcrito."""
        print(f"🎙 Escuchando {segundos}s...")
        audio = sd.rec(
            int(segundos * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
        )
        sd.wait()
        audio_np = audio.flatten()

        segments, _ = self.stt.transcribe(
            audio_np,
            language=WHISPER_LANG,
            beam_size=1,
            vad_filter=True,          # ignora silencios
        )
        texto = " ".join(s.text for s in segments).strip()
        print(f"👂 Escuché: '{texto}'")
        return texto

    # ── TTS ───────────────────────────────────────────────────────────────────

    def hablar(self, texto: str):
        """Sintetiza texto con Piper y lo reproduce por el altavoz."""
        if not self._tts:
            print(f"[BMO]: {texto}")
            return

        print(f"🔊 BMO dice: '{texto}'")
        buf = io.BytesIO()
        with sf.SoundFile(buf, mode="w", samplerate=self._tts.config.sample_rate,
                          channels=1, format="WAV") as wav:
            self._tts.synthesize(texto, wav)

        buf.seek(0)
        data, sr = sf.read(buf, dtype="float32")
        sd.play(data, sr)
        sd.wait()
