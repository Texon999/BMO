"""
Genera los frames de cara de BMO para cada estado.
Crea PNGs animados usando PIL/Pillow.
Ejecutar: python scripts/generate_faces.py
"""
from PIL import Image, ImageDraw
from pathlib import Path

W, H = 480, 480
BMO_GREEN  = (105, 189, 90)
BMO_DARK   = (60,  110, 50)
SCREEN_BG  = (20,  30,  20)
WHITE      = (255, 255, 255)
BLACK      = (0,   0,   0)
CYAN       = (0,   220, 220)
YELLOW     = (255, 220, 0)
RED        = (220, 50,  50)


def base_frame() -> Image.Image:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Cuerpo BMO
    d.rounded_rectangle([20, 20, W-20, H-20], radius=40, fill=BMO_GREEN, outline=BMO_DARK, width=6)
    # Pantalla
    d.rounded_rectangle([60, 60, W-60, H-100], radius=20, fill=SCREEN_BG, outline=BMO_DARK, width=4)
    return img


def draw_eyes(d: ImageDraw.Draw, style: str = "normal", frame: int = 0):
    """Dibuja ojos según el estado."""
    lx, rx = 155, 305
    ey = 180

    if style == "normal":
        # Ojos cuadrados característicos de BMO
        d.rectangle([lx-28, ey-22, lx+28, ey+22], fill=WHITE, outline=CYAN, width=3)
        d.rectangle([rx-28, ey-22, rx+28, ey+22], fill=WHITE, outline=CYAN, width=3)
        # Pupilas
        d.rectangle([lx-10, ey-8, lx+10, ey+8], fill=BLACK)
        d.rectangle([rx-10, ey-8, rx+10, ey+8], fill=BLACK)

    elif style == "happy":
        # Ojos curvados hacia arriba (feliz)
        d.arc([lx-28, ey-22, lx+28, ey+22], start=200, end=340, fill=CYAN, width=5)
        d.arc([rx-28, ey-22, rx+28, ey+22], start=200, end=340, fill=CYAN, width=5)

    elif style == "thinking":
        # Un ojo normal, otro mirando arriba
        d.rectangle([lx-28, ey-22, lx+28, ey+22], fill=WHITE, outline=CYAN, width=3)
        d.rectangle([rx-28, ey-22, rx+28, ey+22], fill=WHITE, outline=CYAN, width=3)
        offset = -8 + (frame % 6) * 2
        d.rectangle([lx-10, ey-8+offset, lx+10, ey+8+offset], fill=BLACK)
        d.rectangle([rx-10, ey-8, rx+10, ey+8], fill=BLACK)

    elif style == "listening":
        # Ojos abiertos con brillo pulsante
        pulse = 3 if frame % 4 < 2 else 0
        d.rectangle([lx-28-pulse, ey-22-pulse, lx+28+pulse, ey+22+pulse],
                    fill=WHITE, outline=YELLOW, width=3)
        d.rectangle([rx-28-pulse, ey-22-pulse, rx+28+pulse, ey+22+pulse],
                    fill=WHITE, outline=YELLOW, width=3)
        d.rectangle([lx-10, ey-8, lx+10, ey+8], fill=BLACK)
        d.rectangle([rx-10, ey-8, rx+10, ey+8], fill=BLACK)

    elif style == "speaking":
        # Ojos con brillo verde pulsante
        pulse = 4 if frame % 3 == 0 else 0
        d.rectangle([lx-28, ey-22, lx+28, ey+22], fill=WHITE, outline=CYAN, width=3)
        d.rectangle([rx-28, ey-22, rx+28, ey+22], fill=WHITE, outline=CYAN, width=3)
        d.rectangle([lx-10-pulse//2, ey-8-pulse//2, lx+10+pulse//2, ey+8+pulse//2], fill=BLACK)
        d.rectangle([rx-10-pulse//2, ey-8-pulse//2, rx+10+pulse//2, ey+8+pulse//2], fill=BLACK)

    elif style == "warmup":
        # Ojos que se "encienden" gradualmente
        alpha = min(255, frame * 30)
        color = (alpha, alpha, alpha)
        d.rectangle([lx-28, ey-22, lx+28, ey+22], fill=color, outline=CYAN, width=3)
        d.rectangle([rx-28, ey-22, rx+28, ey+22], fill=color, outline=CYAN, width=3)


def draw_mouth(d: ImageDraw.Draw, style: str = "normal", frame: int = 0):
    """Dibuja boca según el estado."""
    mx, my = W // 2, 310

    if style == "normal":
        d.arc([mx-40, my-15, mx+40, my+15], start=0, end=180, fill=CYAN, width=4)

    elif style == "happy":
        d.arc([mx-50, my-20, mx+50, my+20], start=0, end=180, fill=CYAN, width=5)

    elif style == "thinking":
        # Boca torcida
        d.line([mx-30, my+5, mx+10, my-5, mx+30, my+5], fill=CYAN, width=4)

    elif style == "listening":
        # Boca abierta pequeña
        d.ellipse([mx-15, my-10, mx+15, my+10], fill=BLACK, outline=CYAN, width=3)

    elif style == "speaking":
        # Boca que se abre y cierra
        open_h = 5 + (frame % 3) * 8
        d.ellipse([mx-30, my-open_h, mx+30, my+open_h], fill=BLACK, outline=CYAN, width=3)

    elif style == "warmup":
        # Línea recta que se convierte en sonrisa
        progress = min(1.0, frame / 8)
        if progress < 0.5:
            d.line([mx-30, my, mx+30, my], fill=CYAN, width=4)
        else:
            d.arc([mx-40, my-15, mx+40, my+15], start=0, end=int(180 * progress * 2), fill=CYAN, width=4)


def generate_state(state: str, eye_style: str, mouth_style: str, n_frames: int):
    out_dir = Path(f"assets/faces/{state}")
    out_dir.mkdir(parents=True, exist_ok=True)

    for i in range(n_frames):
        img = base_frame()
        d = ImageDraw.Draw(img)
        draw_eyes(d, eye_style, i)
        draw_mouth(d, mouth_style, i)
        img.save(out_dir / f"{state}_{i:02d}.png")

    print(f"✓ {state}: {n_frames} frames → {out_dir}")


if __name__ == "__main__":
    generate_state("idle",      "normal",    "normal",    4)
    generate_state("listening", "listening", "listening", 6)
    generate_state("thinking",  "thinking",  "thinking",  8)
    generate_state("speaking",  "speaking",  "speaking",  6)
    generate_state("warmup",    "warmup",    "warmup",    9)
    print("\n✓ Todas las caras generadas en assets/faces/")
