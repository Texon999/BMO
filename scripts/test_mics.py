"""Prueba cada micrófono disponible y muestra cuál capta audio."""
import sounddevice as sd
import numpy as np

candidatos = [2, 3, 10, 11, 19, 20, 24, 27]

print("Probando micrófonos — habla durante cada prueba...\n")
for idx in candidatos:
    try:
        info = sd.query_devices(idx)
        nombre = info["name"]
        audio = sd.rec(int(1.5 * 16000), samplerate=16000,
                       channels=1, dtype="float32", device=idx)
        sd.wait()
        nivel = np.abs(audio).max()
        estado = "✓ CAPTA AUDIO" if nivel > 0.01 else "✗ silencio"
        print(f"  [{idx}] {nombre[:40]:<40} nivel={nivel:.4f}  {estado}")
    except Exception as e:
        print(f"  [{idx}] Error: {e}")
