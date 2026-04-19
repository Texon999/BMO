"""
Descarga la voz española es_ES-sharvard-medium de Piper desde HuggingFace.
Ejecutar una sola vez: python scripts/download_voice.py
"""
import urllib.request
from pathlib import Path

BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/sharvard/medium"
FILES = [
    "es_ES-sharvard-medium.onnx",
    "es_ES-sharvard-medium.onnx.json",
]

dest = Path("voices")
dest.mkdir(exist_ok=True)

for fname in FILES:
    out = dest / fname
    if out.exists():
        print(f"✓ Ya existe: {out}")
        continue
    url = f"{BASE_URL}/{fname}"
    print(f"⬇ Descargando {fname}...")
    urllib.request.urlretrieve(url, out)
    print(f"✓ Guardado en {out}")

print("\n✓ Listo. Puedes ejecutar BMO.")
