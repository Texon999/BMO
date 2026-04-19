"""
Descarga las caras oficiales de BMO desde el repo brenpoly/be-more-agent.
Ejecutar: python scripts/download_faces.py
"""
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/brenpoly/be-more-agent/main/faces"

FACES = {
    "idle":      ["idle 01.png"],
    "listening": ["listen 01.png", "listen 02.png"],
    "thinking":  ["thinking 01.png", "thinking 02.png", "thinking 03.png", "thinking 04.png"],
    "speaking":  ["speaking 01.png", "speaking 02.png", "speaking 03.png"],
    "warmup":    ["warmup 01.png"],
    "error":     ["error 01.png"],
}

for estado, archivos in FACES.items():
    dest_dir = Path(f"assets/faces/{estado}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    for fname in archivos:
        out = dest_dir / fname
        if out.exists():
            print(f"✓ Ya existe: {out}")
            continue
        url = f"{BASE}/{estado}/{fname.replace(' ', '%20')}"
        print(f"⬇ {url}")
        try:
            urllib.request.urlretrieve(url, out)
            print(f"  → {out}")
        except Exception as e:
            print(f"  ✗ Error: {e}")

print("\n✓ Caras descargadas en assets/faces/")
