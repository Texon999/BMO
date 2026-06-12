"""
Módulo de display de BMO — Animación de la cara en pantalla.

Muestra una ventana con la cara animada de BMO según el estado actual:
  - warmup:    Cara de inicio mientras carga
  - idle:      Cara en reposo, esperando
  - listening: Cara escuchando — 6 frames, animación media
  - thinking:  Cara pensando   — 9 frames, animación media
  - speaking:  Cara hablando   — 8 frames, sincronizada con audio real

Las imágenes se cargan desde assets/faces/{estado}/*.png al iniciar.
Si no hay imágenes para un estado, se usa un rectángulo de color como fallback.
Las imágenes PNG con canal alfa (RGBA) se componen sobre un fondo oscuro.

FPS por estado (independientes):
  - warmup/idle/error : 2 FPS  — estáticos o casi estáticos
  - listening         : 8 FPS  — animación media (6 frames → ciclo ~0.75s)
  - thinking          : 8 FPS  — animación media (9 frames → ciclo ~1.1s)
  - speaking          : SINCRONIZADO CON AUDIO — la animación avanza solo cuando
                        hay sonido real, creando movimiento natural de labios.
                        Sin sonido = boca cerrada (frame 0)

Modo headless (BMO_HEADLESS=true):
  No abre ninguna ventana. tick() simplemente duerme 30ms y devuelve True.

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


FACE_DIR     = Path("assets/faces")
WIN_NAME     = "BMO"
WIN_W, WIN_H = 480, 480

# FPS de animación por estado — ajusta aquí para cambiar la velocidad
_FPS_POR_ESTADO: dict[str, float] = {
    "warmup":    2.0,
    "idle":      2.0,
    "listening": 8.0,   # 6 frames → ciclo completo ~0.75s
    "thinking":  8.0,   # 9 frames → ciclo completo ~1.1s
    "speaking":  12.0,  # 8 frames → ciclo completo ~0.67s
    "error":     2.0,
}
_FPS_DEFAULT = 4.0


class Estado(Enum):
    WARMUP    = "warmup"
    IDLE      = "idle"
    LISTENING = "listening"
    THINKING  = "thinking"
    SPEAKING  = "speaking"
    ERROR     = "error"


class DisplayBMO:
    def __init__(self):
        self._frames: dict[str, list[np.ndarray]] = {}
        self._load_faces()

        self.estado  = Estado.WARMUP
        self._idx    = 0
        self._last_t = time.time()
        self._nombre = None   # nombre de la persona detectada

        self._headless = HEADLESS
        if not self._headless:
            cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(WIN_NAME, WIN_W, WIN_H)

    # ── Carga de imágenes ─────────────────────────────────────────────────────

    def _load_faces(self):
        """
        Carga todos los frames PNG de cada estado.
        Ordena numéricamente para que '9.png' no vaya antes que '10.png'.
        """
        for estado in Estado:
            folder = FACE_DIR / estado.value
            if folder.exists():
                # Ordenar numéricamente extrayendo el primer número del nombre
                pngs = sorted(
                    folder.glob("*.png"),
                    key=lambda p: int("".join(filter(str.isdigit, p.stem)) or "0"),
                )
            else:
                pngs = []

            if pngs:
                loaded = []
                for p in pngs:
                    img = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
                    if img is not None:
                        loaded.append(img)
                if loaded:
                    self._frames[estado.value] = loaded
                    continue

            # Fallback: rectángulo de color sólido
            color = {
                "warmup":    (40,  40,  40),
                "idle":      (60,  120, 60),
                "listening": (60,  120, 180),
                "thinking":  (120, 80,  40),
                "speaking":  (40,  160, 80),
                "error":     (180, 40,  40),
            }.get(estado.value, (80, 80, 80))
            fb = np.full((WIN_H, WIN_W, 3), color, dtype=np.uint8)
            self._frames[estado.value] = [fb]

    # ── Actualización ─────────────────────────────────────────────────────────

    def set_estado(self, estado: Estado, nombre: str | None = None):
        if estado != self.estado:
            self.estado  = estado
            self._idx    = 0          # reiniciar animación al cambiar estado
            self._last_t = time.time()
        if nombre is not None:
            self._nombre = nombre

    def tick(self) -> bool:
        """
        Avanza la animación y muestra el frame actual.
        Devuelve False si el usuario presiona Q (señal de apagado).
        
        Para el estado SPEAKING, sincroniza la animación con el nivel de audio real
        en lugar de usar FPS fijo, creando una animación más natural.
        """
        if self._headless:
            time.sleep(0.03)
            return True

        # ── Lógica de animación según estado ──────────────────────────────────
        if self.estado == Estado.SPEAKING:
            # Sincronizar con audio real
            from src.voice.voice import VozBMO
            nivel_audio = VozBMO.audio_level
            
            # Si hay sonido significativo, avanzar la animación
            # Si no hay sonido, mantener el frame actual (cara cerrada)
            if nivel_audio > 0.05:  # Umbral para considerar que hay habla
                # Velocidad de animación más lenta y suave
                # Reducida para que la boca se mueva más despacio
                fps = 4.0 + (nivel_audio * 8.0)  # Entre 4 y 12 FPS según volumen (antes 8-28)
                period = 1.0 / fps
                now = time.time()
                
                if now - self._last_t >= period:
                    frames = self._frames[self.estado.value]
                    self._idx = (self._idx + 1) % len(frames)
                    self._last_t = now
            else:
                # Sin sonido, volver al primer frame (boca cerrada)
                if self._idx != 0:
                    self._idx = 0
                    self._last_t = time.time()
        else:
            # Estados normales: usar FPS fijo
            fps    = _FPS_POR_ESTADO.get(self.estado.value, _FPS_DEFAULT)
            period = 1.0 / fps
            now    = time.time()

            if now - self._last_t >= period:
                frames    = self._frames[self.estado.value]
                self._idx = (self._idx + 1) % len(frames)
                self._last_t = now

        frame = self._frames[self.estado.value][self._idx].copy()

        # Componer RGBA sobre fondo oscuro
        if frame.ndim == 3 and frame.shape[2] == 4:
            bgr   = frame[:, :, :3]
            alpha = frame[:, :, 3:4] / 255.0
            bg    = np.full_like(bgr, 30)
            frame = (bgr * alpha + bg * (1 - alpha)).astype(np.uint8)

        frame = cv2.resize(frame, (WIN_W, WIN_H))

        # Overlay: nombre de la persona reconocida
        if self._nombre and self.estado in (Estado.IDLE, Estado.SPEAKING):
            cv2.putText(
                frame, f"Hola, {self._nombre}!",
                (15, WIN_H - 20), cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (100, 255, 100), 2,
            )

        # Overlay de estado y frames deshabilitado para interfaz más limpia
        # Descomenta las siguientes líneas si necesitas debug visual:
        
        # label = self.estado.value.upper()
        # cv2.putText(
        #     frame, label,
        #     (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
        #     0.6, (200, 200, 200), 1,
        # )
        
        # frames_total = len(self._frames[self.estado.value])
        # if frames_total > 1:
        #     cv2.putText(
        #         frame, f"{self._idx + 1}/{frames_total}",
        #         (WIN_W - 55, 25), cv2.FONT_HERSHEY_SIMPLEX,
        #         0.5, (150, 150, 150), 1,
        #     )

        cv2.imshow(WIN_NAME, frame)
        key = cv2.waitKey(1) & 0xFF
        return key != ord("q")

    def cerrar(self):
        if not self._headless:
            cv2.destroyAllWindows()

