"""
BMO — Agente local autónomo
Flujo completamente autónomo:
  1. Warmup → muestra animación de inicio
  2. Idle   → espera detectar una cara
  3. Al ver cara → saluda (con nombre si lo conoce, o pregunta si no)
  4. Listening → graba voz del usuario
  5. Thinking  → procesa con LLM
  6. Speaking  → reproduce respuesta con Piper
  7. Si el usuario dice su nombre → lo registra automáticamente con fotos
  8. Vuelve a Idle/Listening en loop

Logs detallados en consola. Sin teclas necesarias (Q cierra la ventana).
"""
import threading
import time
import logging

from src.display.display import DisplayBMO, Estado
from src.vision.vision   import VisionBMO
from src.voice.voice     import VozBMO
from src.brain.brain     import generar_respuesta, detectar_registro, saludo_inicial
from src.memory.register import guardar_persona, obtener_nombre, nombres_a_ids

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("BMO")

# ── Configuración ─────────────────────────────────────────────────────────────
IDLE_TIMEOUT      = 3.0   # segundos sin cara antes de volver a idle puro
GREETING_COOLDOWN = 30.0  # segundos entre saludos a la misma persona
LISTEN_SECONDS    = 5     # segundos de grabación por turno
CAPTURE_FRAMES    = 25    # fotos para registrar un rostro


class AgenteBMO:
    def __init__(self):
        log.info("=== Iniciando BMO ===")
        self.display = DisplayBMO()
        self.vision  = VisionBMO(camera_index=0)
        self.voz     = VozBMO()

        self._running        = True
        self._persona_actual: str | None = None   # nombre de quien está frente
        self._id_actual:      int | None = None
        self._ultimo_saludo: dict[str, float] = {}  # {nombre: timestamp}
        self._registrando    = False
        self._hablando       = False

        log.info("=== BMO listo ===")

    # ── Loop principal ────────────────────────────────────────────────────────

    def run(self):
        self._warmup()

        while self._running:
            # Capturar frame de cámara (silencioso, sin mostrar)
            ret, frame = self.vision.cap.read()
            if not ret:
                log.warning("No se pudo leer frame de cámara")
                time.sleep(0.1)
                continue

            _, detecciones = self.vision.procesar_rostro(frame)

            # Actualizar quién está frente a BMO
            self._actualizar_persona(detecciones)

            # Máquina de estados
            if not self._hablando and not self._registrando:
                self._ciclo_conversacion()

            # Tick de animación (también maneja Q para salir)
            if not self.display.tick():
                self._running = False

        self._apagar()

    # ── Warmup ────────────────────────────────────────────────────────────────

    def _warmup(self):
        log.info("Warmup...")
        self.display.set_estado(Estado.WARMUP)
        start = time.time()
        while time.time() - start < 3.0:
            if not self.display.tick():
                self._running = False
                return
        self.display.set_estado(Estado.IDLE)
        log.info("BMO despierto")

    # ── Actualizar persona detectada ──────────────────────────────────────────

    def _actualizar_persona(self, detecciones: list):
        reconocidos = [(d["id"], d["nombre"]) for d in detecciones if d["id"] is not None]
        if reconocidos:
            id_det, nombre_det = reconocidos[0]
            if nombre_det != self._persona_actual:
                log.info(f"Persona detectada: {nombre_det} (ID {id_det})")
            self._id_actual      = id_det
            self._persona_actual = nombre_det
            self.display.set_estado(self.display.estado, nombre=nombre_det)
        else:
            if self._persona_actual is not None:
                log.info("Nadie frente a BMO")
            self._id_actual      = None
            self._persona_actual = None
            self.display.set_estado(Estado.IDLE, nombre=None)

    # ── Ciclo de conversación ─────────────────────────────────────────────────

    def _ciclo_conversacion(self):
        # Si hay alguien y no lo hemos saludado recientemente → saludar
        if self._persona_actual or self._hay_cara_desconocida():
            nombre = self._persona_actual
            ahora  = time.time()
            ultimo = self._ultimo_saludo.get(nombre or "__desconocido__", 0)

            if ahora - ultimo > GREETING_COOLDOWN:
                self._ultimo_saludo[nombre or "__desconocido__"] = ahora
                self._saludar(nombre)
                return

            # Ya saludamos → escuchar
            self._escuchar_y_responder()
        else:
            # Nadie → idle
            self.display.set_estado(Estado.IDLE)
            time.sleep(0.05)

    def _hay_cara_desconocida(self) -> bool:
        """Devuelve True si hay una cara en cámara aunque no esté registrada."""
        ret, frame = self.vision.cap.read()
        if not ret:
            return False
        gray  = __import__("cv2").cvtColor(frame, __import__("cv2").COLOR_BGR2GRAY)
        faces = self.vision.face_cascade.detectMultiScale(gray, 1.1, 8, minSize=(60, 60))
        return len(faces) > 0

    # ── Saludo ────────────────────────────────────────────────────────────────

    def _saludar(self, nombre: str | None):
        log.info(f"Saludando a: {nombre or 'desconocido'}")
        self._hablando = True
        self.display.set_estado(Estado.THINKING)

        def _tarea():
            texto = saludo_inicial(nombre)
            self.display.set_estado(Estado.SPEAKING)
            self.voz.hablar(texto)
            self.display.set_estado(Estado.IDLE)
            self._hablando = False

        threading.Thread(target=_tarea, daemon=True).start()
        # Esperar a que termine el saludo antes de continuar
        while self._hablando:
            self.display.tick()
            time.sleep(0.05)

    # ── Escuchar y responder ──────────────────────────────────────────────────

    def _escuchar_y_responder(self):
        self.display.set_estado(Estado.LISTENING)
        log.info("Escuchando...")

        texto = self.voz.escuchar(LISTEN_SECONDS)

        if not texto:
            self.display.set_estado(Estado.IDLE)
            return

        # Detectar si quiere registrarse
        es_registro, nombre_nuevo = detectar_registro(texto)
        if es_registro and nombre_nuevo:
            log.info(f"Intención de registro detectada: '{nombre_nuevo}'")
            self._registrar_persona(nombre_nuevo)
            return

        # Respuesta normal
        self._hablando = True
        self.display.set_estado(Estado.THINKING)
        log.info(f"Procesando: '{texto}'")

        def _tarea():
            respuesta = generar_respuesta(texto, self._persona_actual)
            log.info(f"BMO responde: '{respuesta}'")
            self.display.set_estado(Estado.SPEAKING)
            self.voz.hablar(respuesta)
            self.display.set_estado(Estado.IDLE)
            self._hablando = False

        threading.Thread(target=_tarea, daemon=True).start()
        while self._hablando:
            self.display.tick()
            time.sleep(0.05)

    # ── Registro automático ───────────────────────────────────────────────────

    def _registrar_persona(self, nombre: str):
        import cv2
        import numpy as np

        self._registrando = True
        siguiente_id = self.vision.siguiente_id()
        log.info(f"Registrando '{nombre}' como ID {siguiente_id}")

        # BMO anuncia que va a tomar fotos
        self.display.set_estado(Estado.SPEAKING)
        self.voz.hablar(f"Genial! Voy a recordar tu cara, {nombre}. Mira hacia aqui!")
        self.display.set_estado(Estado.LISTENING)

        capturas = []
        count    = 0
        timeout  = time.time() + 15  # máximo 15 segundos

        while count < CAPTURE_FRAMES and time.time() < timeout:
            ret, f = self.vision.cap.read()
            if not ret:
                break
            gray  = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
            gray  = cv2.equalizeHist(gray)
            faces = self.vision.face_cascade.detectMultiScale(gray, 1.1, 8, minSize=(60, 60))

            for (x, y, w, h) in faces:
                roi = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
                capturas.append(roi)
                count += 1

            self.display.tick()
            time.sleep(0.05)

        if capturas:
            self.vision.aprender_rostro(siguiente_id, nombre, capturas)
            self._persona_actual = nombre
            self._id_actual      = siguiente_id
            self.display.set_estado(Estado.SPEAKING, nombre=nombre)
            confirmacion = generar_respuesta(
                f"Acabas de registrar a {nombre} en tu memoria. Dile algo emocionante.",
                nombre
            )
            log.info(f"Registro exitoso: {nombre} (ID {siguiente_id})")
            self.voz.hablar(confirmacion)
        else:
            log.warning("No se capturaron suficientes fotos")
            self.voz.hablar("Hmm, no pude verte bien. Intentalo de nuevo!")

        self.display.set_estado(Estado.IDLE)
        self._registrando = False

    # ── Apagado ───────────────────────────────────────────────────────────────

    def _apagar(self):
        log.info("Apagando BMO...")
        self.vision.liberar()
        self.display.cerrar()
        log.info("BMO desconectado")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    agente = AgenteBMO()
    try:
        agente.run()
    except KeyboardInterrupt:
        log.info("Interrupción por teclado")
        agente._apagar()


if __name__ == "__main__":
    main()
