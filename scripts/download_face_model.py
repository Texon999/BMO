#!/usr/bin/env python3
"""
Descarga el modelo ONNX buffalo_sc (MobileFaceNet) de InsightFace.
Uso: python scripts/download_face_model.py
"""

import sys
import zipfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlretrieve

MODEL_URL = "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_sc.zip"
DEST_PATH = Path(__file__).parent.parent / "data" / "face_model.onnx"
ZIP_PATH  = DEST_PATH.parent / "buffalo_sc.zip"

# Nombre del archivo .onnx dentro del zip
ONNX_FILENAME = "det_500m.onnx"  # buffalo_sc contiene det_500m.onnx y w600k_mbf.onnx
EMBED_FILENAME = "w600k_mbf.onnx"  # MobileFaceNet para embeddings (512-dim)


def _progress(block_num: int, block_size: int, total_size: int) -> None:
    downloaded = block_num * block_size
    if total_size > 0:
        pct = min(downloaded / total_size * 100, 100)
        print(f"\r  Descargando... {pct:.1f}%", end="", flush=True)


def download() -> None:
    DEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"Descargando buffalo_sc desde:\n  {MODEL_URL}")
    try:
        urlretrieve(MODEL_URL, ZIP_PATH, reporthook=_progress)
        print()  # nueva línea tras el progreso
    except URLError as e:
        print(f"\nError de red al descargar el modelo: {e.reason}", file=sys.stderr)
        print("Comprueba tu conexión a internet e inténtalo de nuevo.", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"\nError al guardar el archivo: {e}", file=sys.stderr)
        sys.exit(1)

    print("Descomprimiendo...")
    try:
        with zipfile.ZipFile(ZIP_PATH, "r") as zf:
            names = zf.namelist()
            # Buscar el archivo de embeddings MobileFaceNet
            target = next((n for n in names if EMBED_FILENAME in n), None)
            if target is None:
                # Fallback: cualquier .onnx que no sea el detector
                target = next((n for n in names if n.endswith(".onnx")), None)
            if target is None:
                print("No se encontró ningún archivo .onnx en el zip.", file=sys.stderr)
                sys.exit(1)
            data = zf.read(target)
    except zipfile.BadZipFile as e:
        print(f"El archivo descargado está corrupto: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        ZIP_PATH.unlink(missing_ok=True)

    DEST_PATH.write_bytes(data)

    if DEST_PATH.stat().st_size == 0:
        print("Error: el archivo descargado está vacío.", file=sys.stderr)
        DEST_PATH.unlink()
        sys.exit(1)

    print(f"Modelo guardado en: {DEST_PATH.resolve()}")


if __name__ == "__main__":
    download()
