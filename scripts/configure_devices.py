"""
Ayuda a seleccionar indices de camara/microfono/salida para BMO.
No modifica archivos: imprime variables de entorno para copiar/pegar.
"""
import cv2
import sounddevice as sd


def listar_audio():
    print("=== AUDIO ===")
    devices = sd.query_devices()
    default_in, default_out = sd.default.device
    for i, d in enumerate(devices):
        if d["max_input_channels"] <= 0 and d["max_output_channels"] <= 0:
            continue
        tags = []
        if i == default_in:
            tags.append("DEFAULT IN")
        if i == default_out:
            tags.append("DEFAULT OUT")
        tipo = []
        if d["max_input_channels"] > 0:
            tipo.append("IN")
        if d["max_output_channels"] > 0:
            tipo.append("OUT")
        suffix = f" [{' | '.join(tags)}]" if tags else ""
        print(f"[{i}] {'/'.join(tipo):<6} {d['name']}{suffix}")


def listar_camaras(max_idx: int = 5):
    print("\n=== CAMARAS ===")
    found = False
    for idx in range(max_idx + 1):
        cap = cv2.VideoCapture(idx)
        ok, _ = cap.read()
        cap.release()
        if ok:
            print(f"[{idx}] Camara disponible")
            found = True
    if not found:
        print("No se detectaron camaras en indices 0..5")


def main():
    listar_audio()
    listar_camaras()
    print("\nConfig recomendada (.env o variables de entorno):")
    print("BMO_CAMERA_INDEX=0")
    print("BMO_MIC_DEVICE=-1")
    print("BMO_OUTPUT_DEVICE=-1")
    print("BMO_HEADLESS=false")
    print("BMO_WHISPER_MODEL=base")
    print("BMO_LLM_MODEL=qwen2.5:1.5b")
    print("\nSi quieres fijar dispositivos, cambia los indices segun la lista.")


if __name__ == "__main__":
    main()
