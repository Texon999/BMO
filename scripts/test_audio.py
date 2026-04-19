"""
Test de audio: genera un tono y luego prueba Piper TTS.
Ejecutar: python scripts/test_audio.py
"""
import numpy as np
import sounddevice as sd
import soundfile as sf
import wave, io, json
from pathlib import Path

# ── Test 1: tono puro ─────────────────────────────────────────────────────────
print("Test 1: Tono de 440Hz por 1 segundo...")
sr = 22050
t  = np.linspace(0, 1, sr, dtype="float32")
tone = 0.3 * np.sin(2 * np.pi * 440 * t)
sd.play(tone, sr)
sd.wait()
print("  ¿Escuchaste el tono? Si no, el problema es sounddevice/altavoces.\n")

# ── Test 2: Piper TTS ─────────────────────────────────────────────────────────
onnx   = Path("voices/es_ES-sharvard-medium.onnx")
config = Path("voices/es_ES-sharvard-medium.onnx.json")

if not onnx.exists():
    print("✗ Voz no encontrada. Ejecuta: python scripts/download_voice.py")
    exit(1)

with open(config, encoding="utf-8") as f:
    cfg = json.load(f)
tts_rate = cfg.get("audio", {}).get("sample_rate", 22050)
print(f"Test 2: Piper TTS — sample_rate del modelo: {tts_rate}Hz")

from piper.voice import PiperVoice
tts = PiperVoice.load(str(onnx), config_path=str(config))

texto = "Hola! Soy BMO. Hora de aventura!"
print(f"  Sintetizando: '{texto}'")

chunks = list(tts.synthesize(texto))
if not chunks:
    print("  ✗ Sin chunks de audio!")
else:
    data = np.concatenate([c.audio_float_array for c in chunks])
    sr_read = chunks[0].sample_rate
    print(f"  Audio generado: {len(data)} samples @ {sr_read}Hz = {len(data)/sr_read:.2f}s")
    print(f"  Amplitud max: {np.abs(data).max():.4f}")
    print(f"  Reproduciendo...")
    sd.play(data, sr_read)
    sd.wait()
    print("  ¿Escuchaste a BMO?")
