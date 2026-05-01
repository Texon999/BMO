"""
Comprobacion rapida del entorno sin arrancar BMO (sin camara ni microfono).

Ejecutar desde la raiz del repo:
  python scripts/smoke_check.py

No importa src.brain: ese modulo precarga Ollama al cargarse; aqui se prueba Ollama aparte.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def warn(msg: str) -> None:
    print(f"  [!!] {msg}")


def fail(msg: str) -> None:
    print(f"  [XX] {msg}")


def main() -> int:
    print("=== BMO smoke check ===\n")
    errors = 0

    try:
        import cv2  # noqa: F401
        ok(f"OpenCV {cv2.__version__}")
    except Exception as e:
        fail(f"OpenCV: {e}")
        errors += 1

    try:
        import numpy as np  # noqa: F401
        ok(f"NumPy {np.__version__}")
    except Exception as e:
        fail(f"NumPy: {e}")
        errors += 1

    try:
        import sounddevice as sd  # noqa: F401
        ok(f"sounddevice, dispositivos: {len(sd.query_devices())}")
    except Exception as e:
        fail(f"sounddevice: {e}")
        errors += 1

    try:
        from faster_whisper import WhisperModel  # noqa: F401
        ok("faster-whisper importable")
    except Exception as e:
        fail(f"faster-whisper: {e}")
        errors += 1

    voice_onnx = ROOT / "voices" / "es_ES-sharvard-medium.onnx"
    if voice_onnx.exists():
        ok(f"Piper voz presente: {voice_onnx.name}")
    else:
        warn(f"Falta voz Piper (ejecuta: python scripts/download_voice.py): {voice_onnx}")

    try:
        import ollama

        models = ollama.list()
        ok("Ollama responde (ollama.list)")
        if hasattr(models, "models") and models.models:
            names = [getattr(m, "model", str(m)) for m in models.models[:5]]
            print(f"       (ejemplos de modelos: {', '.join(names)})")
    except Exception as e:
        fail(f"Ollama no disponible: {e}")
        errors += 1

    try:
        from src.config import runtime as rt

        ok(
            f"runtime: vision N={rt.VISION_PROCESS_EVERY_N}, "
            f"brain_hot_reload={rt.BRAIN_CONTEXT_HOT_RELOAD}"
        )
    except Exception as e:
        fail(f"src.config.runtime: {e}")
        errors += 1

    try:
        from src.memory import register as reg  # noqa: F401

        ok("src.memory.register importable")
    except Exception as e:
        fail(f"memory.register: {e}")
        errors += 1

    print()
    if errors:
        print(f"Fallos: {errors}. Revisa dependencias y que Ollama este en marcha.")
        return 1
    print("Todo lo critico paso. Puedes ejecutar: python -m src.main")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
