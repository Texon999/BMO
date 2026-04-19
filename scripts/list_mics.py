import sounddevice as sd
import numpy as np

devices = sd.query_devices()
default_in = sd.default.device[0]

print("=== MICRÓFONOS DISPONIBLES ===\n")
for i, d in enumerate(devices):
    if d["max_input_channels"] > 0:
        marker = " [DEFAULT]" if i == default_in else ""
        print(f"  [{i}] {d['name']}{marker}")

print(f"\nDefault input index: {default_in}")
print("\n=== TEST DE NIVEL DE AUDIO (3s) ===")
print("Habla ahora para ver si el micrófono capta algo...\n")

try:
    audio = sd.rec(int(3 * 16000), samplerate=16000, channels=1, dtype="float32")
    sd.wait()
    nivel = np.abs(audio).max()
    rms   = np.sqrt(np.mean(audio**2))
    print(f"  Nivel máximo : {nivel:.4f}")
    print(f"  RMS          : {rms:.4f}")
    if nivel < 0.01:
        print("  ⚠ Muy bajo — el micrófono no está captando nada")
    elif nivel < 0.05:
        print("  ⚠ Bajo — habla más fuerte o acércate al micrófono")
    else:
        print("  ✓ Nivel OK")
except Exception as e:
    print(f"  ✗ Error: {e}")
