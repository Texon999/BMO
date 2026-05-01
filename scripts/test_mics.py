"""Prueba cada micrófono disponible y muestra cuál capta audio."""
import sounddevice as sd
import numpy as np

candidatos = [
    idx for idx, d in enumerate(sd.query_devices())
    if d.get("max_input_channels", 0) > 0
]

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
