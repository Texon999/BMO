"""
Módulo de voz de BMO.
STT: faster-whisper modelo "base" — mucho mejor en español que "tiny"
TTS: piper-tts es_ES-sharvard-medium
"""
import json
import numpy as np
import sounddevice as sd
from pathlib import Path
from faster_whisper import WhisperModel

# "base" es ~4x más preciso que "tiny" en español, sigue siendo rápido en CPU
WHISPER_MODEL  = "base"
WHISPER_LANG   = "es"
SAMPLE_RATE    = 16000
RECORD_SECONDS = 5

VOICE_ONNX   = Path("voices/es_ES-sharvard-medium.onnx")
VOICE_CONFIG = Path("voices/es_ES-sharvard-medium.onnx.json")


class VozBMO:
    def __init__(self):
        print(f"[VOZ] Cargando Whisper {WHISPER_MODEL}...")
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
                print(f"[VOZ] Piper listo — {self._tts_rate}Hz")
            except Exception as e:
                print(f"[VOZ] Error Piper: {e}")
        else:
            print(f"[VOZ] Voz no encontrada: {VOICE_ONNX}")

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
            print(f"[STT] Error micrófono: {e}")
            return ""

        audio_np = audio.flatten()
        if np.abs(audio_np).max() < 0.005:
            print("[STT] Silencio")
            return ""

        segments, _ = self.stt.transcribe(
            audio_np,
            language=WHISPER_LANG,
            beam_size=5,           # más preciso que beam_size=1
            best_of=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
            condition_on_previous_text=False,
        )
        texto = " ".join(s.text for s in segments).strip()
        # Limpiar artefactos comunes de Whisper
        texto = texto.replace("[BLANK_AUDIO]", "").replace("(Música)", "").strip()
        if texto:
            print(f"[STT] '{texto}'")
        else:
            print("[STT] Sin habla detectada")
        return texto

    def hablar(self, texto: str):
        if not self._tts:
            print(f"[BMO]: {texto}")
            return

        print(f"[TTS] '{texto[:70]}'")
        try:
            chunks = list(self._tts.synthesize(texto))
            if not chunks:
                return
            audio_np = np.concatenate([c.audio_float_array for c in chunks])
            sr = chunks[0].sample_rate
            print(f"[TTS] {len(audio_np)/sr:.1f}s")
            sd.play(audio_np, sr)
            sd.wait()
        except Exception as e:
            print(f"[TTS] Error: {e}")
