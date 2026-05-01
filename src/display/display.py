"""
Módulo de display de BMO — Animación de la cara en pantalla.

Muestra una ventana con la cara animada de BMO según el estado actual:
  - warmup:    Cara de inicio mientras carga
  - idle:      Cara en reposo, esperando
  - listening: Cara escuchando (micrófono activo)
  - thinking:  Cara pensando (LLM procesando)
  - speaking:  Cara hablando (TTS reproduciendo)

Las imágenes se cargan desde assets/faces/{estado}/*.png al iniciar.
Si no hay imágenes para un estado, se usa un rectángulo de color como fallback.
Las imágenes PNG con canal alfa (RGBA) se componen sobre un fondo oscuro.

Modo headless (BMO_HEADLESS=true):
  No abre ninguna ventana. Útil para ejecutar BMO sin pantalla (servidor, SSH).
  tick() simplemente duerme 30ms y devuelve True.

Overlay de nombre:
  Cuando BMO reconoce a alguien por cámara, muestra "Hola, {nombre}!"
  en la parte inferior de la pantalla durante los estados idle y speaking.

Controles:
  Q → cierra la ventana y apaga BMO.
"""
import cv2
import numpy as np
import time
from pathlib import Path
from enum import Enum, auto
from src.config.runtime import HEADLESS


FACE_DIR   = Path("assets/faces")
WIN_NAME   = "BMO"
WIN_W, WIN_H = 480, 480
FPS_ANIM   = 4   # menor = animación más lenta (cambio de frame cada 1/FPS_ANIM s)


class Estado(Enum):
    WARMUP    = "warmup"
    IDLE      = "idle"
    LISTENING = "listening"
    THINKING  = "thinking"
    SPEAKING  = "speaking"


class DisplayBMO:
    def __init__(self):
        self._frames: dict[str, list[np.ndarray]] = {}
        self._load_faces()

        self.estado   = Estado.WARMUP
        self._idx     = 0
        self._last_t  = time.time()
        self._nombre  = None   # nombre de la persona detectada

        self._headless = HEADLESS
        if not self._headless:
            cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(WIN_NAME, WIN_W, WIN_H)

    # ── Carga de imágenes ─────────────────────────────────────────────────────

    def _load_faces(self):
        for estado in Estado:
            folder = FACE_DIR / estado.value
            pngs = sorted(folder.glob("*.png")) if folder.exists() else []
            if pngs:
                self._frames[estado.value] = [
                    cv2.imread(str(p), cv2.IMREAD_UNCHANGED) for p in pngs
                ]
            else:
                # Fallback: rectángulo de color sólido
                color = {
                    "warmup":    (40, 40, 40),
                    "idle":      (60, 120, 60),
                    "listening": (60, 120, 180),
                    "thinking":  (120, 80, 40),
                    "speaking":  (40, 160, 80),
                }.get(estado.value, (80, 80, 80))
                fb = np.full((WIN_H, WIN_W, 3), color, dtype=np.uint8)
                self._frames[estado.value] = [fb]

    # ── Actualización ─────────────────────────────────────────────────────────

    def set_estado(self, estado: Estado, nombre: str | None = None):
        if estado != self.estado:
            self.estado = estado
            self._idx   = 0
        if nombre is not None:
            self._nombre = nombre

    def tick(self) -> bool:
        """Avanza la animación y muestra el frame. Devuelve False si se presiona Q."""
        if self._headless:
            time.sleep(0.03)
            return True

        now = time.time()
        if now - self._last_t >= 1.0 / FPS_ANIM:
            frames = self._frames[self.estado.value]
            self._idx = (self._idx + 1) % len(frames)
            self._last_t = now

        frame = self._frames[self.estado.value][self._idx].copy()

        # Convertir RGBA → BGR si es necesario
        if frame.shape[2] == 4:
            bgr  = frame[:, :, :3]
            alpha = frame[:, :, 3:4] / 255.0
            bg   = np.full_like(bgr, 30)
            frame = (bgr * alpha + bg * (1 - alpha)).astype(np.uint8)

        # Resize por si acaso
        frame = cv2.resize(frame, (WIN_W, WIN_H))

        # Overlay de nombre
        if self._nombre and self.estado in (Estado.IDLE, Estado.SPEAKING):
            cv2.putText(frame, f"Hola, {self._nombre}!",
                        (15, WIN_H - 20), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (100, 255, 100), 2)
        label = self.estado.value.upper()
        cv2.putText(frame, label, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        cv2.imshow(WIN_NAME, frame)
        key = cv2.waitKey(1) & 0xFF
        return key != ord("q")

    def cerrar(self):
        if not self._headless:
            cv2.destroyAllWindows()
