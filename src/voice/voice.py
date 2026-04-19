"""
Módulo de voz de BMO.
STT: faster-whisper (tiny, español)
TTS: piper-tts — API correcta con AudioChunk iterable
"""
import json
import numpy as np
import sounddevice as sd
from pathlib import Path
from faster_whisper import WhisperModel

WHISPER_MODEL  = "tiny"
WHISPER_LANG   = "es"
SAMPLE_RATE    = 16000
RECORD_SECONDS = 3   # VAD corta antes si hay silencio

VOICE_ONNX   = Path("voices/es_ES-sharvard-medium.onnx")
VOICE_CONFIG = Path("voices/es_ES-sharvard-medium.onnx.json")


class VozBMO:
    def __init__(self):
        print("[VOZ] Cargando Whisper tiny...")
        self.stt = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        print("[VOZ] Whisper listo")

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
                print(f"[VOZ] Piper listo — sample_rate={self._tts_rate}Hz")
            except Exception as e:
                print(f"[VOZ] Error cargando Piper: {e}")
        else:
            print(f"[VOZ] Voz no encontrada: {VOICE_ONNX}")
            print("[VOZ] Ejecuta: python scripts/download_voice.py")

    # ── STT ───────────────────────────────────────────────────────────────────

    def escuchar(self, segundos: int = RECORD_SECONDS) -> str:
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
        if np.abs(audio_np).max() < 0.01:
            print("[STT] Silencio detectado")
            return ""

        segments, _ = self.stt.transcribe(
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
        if not self._tts:
            print(f"[TTS] (sin voz) BMO: {texto}")
            return

        label = texto[:60] + "..." if len(texto) > 60 else texto
        print(f"[TTS] Sintetizando: '{label}'")

        try:
            # Piper devuelve AudioChunk iterables — concatenar todos
            chunks = list(self._tts.synthesize(texto))
            if not chunks:
                print("[TTS] Sin audio generado")
                return

            audio_np = np.concatenate([c.audio_float_array for c in chunks])
            sr = chunks[0].sample_rate

            duracion = len(audio_np) / sr
            print(f"[TTS] Reproduciendo {duracion:.1f}s @ {sr}Hz")
            sd.play(audio_np, sr)
            sd.wait()
            print("[TTS] Listo")
        except Exception as e:
            print(f"[TTS] Error: {e}")
            print(f"[TTS] BMO: {texto}")
