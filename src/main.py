"""
BMO — Agente local autónomo
Máquina de estados limpia inspirada en be-more-agent:
  WARMUP → IDLE → (cara detectada) → LISTENING → THINKING → SPEAKING → IDLE

El loop principal corre en un hilo separado.
El hilo de display solo maneja la animación.
"""
import threading
import time
import logging
import cv2

from src.display.display import DisplayBMO, Estado
from src.vision.vision   import VisionBMO
from src.voice.voice     import VozBMO
from src.brain.brain     import generar_respuesta, detectar_nombre
from src.memory.register import guardar_persona, nombres_a_ids

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("BMO")

GREETING_COOLDOWN = 45.0   # segundos entre saludos a la misma persona
LISTEN_SECONDS    = 4      # segundos máx de grabación
CAPTURE_FRAMES    = 25     # fotos para registrar un rostro


class AgenteBMO:
    def __init__(self):
        log.info("=== Iniciando BMO ===")
        self.display = DisplayBMO()
        self.vision  = VisionBMO(camera_index=0)
        self.voz     = VozBMO()

        self._running = True
        self._ultimo_saludo: dict[str, float] = {}

        log.info("=== BMO listo ===")

    # ── Entry point ───────────────────────────────────────────────────────────

    def run(self):
        # Hilo de lógica separado del hilo de display
        hilo = threading.Thread(target=self._loop_logica, daemon=True)
        hilo.start()

        # Hilo principal: solo animación + manejo de ventana
        while self._running:
            if not self.display.tick():
                self._running = False
        
        self._apagar()

    # ── Loop de lógica (hilo separado) ────────────────────────────────────────

    def _loop_logica(self):
        # Warmup
        self.display.set_estado(Estado.WARMUP)
        time.sleep(3.0)
        log.info("BMO despierto")

        while self._running:
            try:
                self._ciclo()
            except Exception as e:
                log.error(f"Error en ciclo: {e}")
                time.sleep(1.0)

    def _ciclo(self):
        """Un ciclo completo: detectar cara → saludar → escuchar → responder."""
        # 1. Esperar a que haya una cara
        nombre, id_cara = self._esperar_cara()
        if not self._running:
            return

        # 2. Saludar si no lo hemos hecho recientemente
        clave = nombre or "__desconocido__"
        ahora = time.time()
        if ahora - self._ultimo_saludo.get(clave, 0) > GREETING_COOLDOWN:
            self._ultimo_saludo[clave] = ahora
            self._saludar(nombre)

        # 3. Escuchar y responder en loop mientras haya cara
        while self._running:
            # Verificar que sigue habiendo cara
            cara_presente, nombre_actual, _ = self._detectar_cara()
            if not cara_presente:
                log.info("Cara perdida, volviendo a idle")
                self.display.set_estado(Estado.IDLE)
                break

            # Escuchar
            self.display.set_estado(Estado.LISTENING)
            log.info("Escuchando...")
            texto = self.voz.escuchar(LISTEN_SECONDS)

            if not texto:
                # Sin audio → pequeña pausa y volver a escuchar
                self.display.set_estado(Estado.IDLE)
                time.sleep(1.0)
                continue

            log.info(f"Escuché: '{texto}'")

            # Detectar si dice su nombre → registrar
            nombre_nuevo = detectar_nombre(texto)
            if nombre_nuevo and nombre_nuevo.lower() != (nombre or "").lower():
                self._registrar_persona(nombre_nuevo)
                nombre = nombre_nuevo
                clave  = nombre
                continue

            # Responder con LLM
            self.display.set_estado(Estado.THINKING)
            log.info("Pensando...")
            respuesta = generar_respuesta(texto, nombre)
            log.info(f"BMO: '{respuesta}'")

            self.display.set_estado(Estado.SPEAKING)
            self.voz.hablar(respuesta)
            self.display.set_estado(Estado.IDLE)

    # ── Detección de cara ─────────────────────────────────────────────────────

    def _detectar_cara(self) -> tuple[bool, str | None, int | None]:
        """Lee un frame y devuelve (hay_cara, nombre, id)."""
        ret, frame = self.vision.cap.read()
        if not ret:
            return False, None, None
        _, detecciones = self.vision.procesar_rostro(frame)
        reconocidos = [(d["id"], d["nombre"]) for d in detecciones if d["id"] is not None]
        if reconocidos:
            id_det, nombre_det = reconocidos[0]
            return True, nombre_det, id_det
        # Cara sin reconocer
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.vision.face_cascade.detectMultiScale(gray, 1.1, 8, minSize=(60, 60))
        if len(faces) > 0:
            return True, None, None
        return False, None, None

    def _esperar_cara(self) -> tuple[str | None, int | None]:
        """Bloquea hasta detectar una cara. Devuelve (nombre, id)."""
        self.display.set_estado(Estado.IDLE)
        while self._running:
            hay_cara, nombre, id_cara = self._detectar_cara()
            if hay_cara:
                log.info(f"Cara detectada: {nombre or 'desconocido'}")
                if nombre:
                    self.display.set_estado(Estado.IDLE, nombre=nombre)
                return nombre, id_cara
            time.sleep(0.1)
        return None, None

    # ── Saludo ────────────────────────────────────────────────────────────────

    def _saludar(self, nombre: str | None):
        log.info(f"Saludando a: {nombre or 'desconocido'}")
        self.display.set_estado(Estado.THINKING)

        if nombre:
            prompt = f"Saluda a {nombre} que acaba de aparecer. Muy breve y entusiasta."
        else:
            # Sin nombre: saludo simple + pregunta el nombre
            prompt = "Saluda a alguien nuevo y preguntale su nombre. Solo 1 oracion."

        respuesta = generar_respuesta(prompt, nombre)
        log.info(f"Saludo: '{respuesta}'")
        self.display.set_estado(Estado.SPEAKING, nombre=nombre)
        self.voz.hablar(respuesta)
        self.display.set_estado(Estado.IDLE)

    # ── Registro ──────────────────────────────────────────────────────────────

    def _registrar_persona(self, nombre: str):
        log.info(f"Registrando: '{nombre}'")
        siguiente_id = self.vision.siguiente_id()

        self.display.set_estado(Estado.SPEAKING)
        self.voz.hablar(f"Genial! Voy a recordar tu cara {nombre}. Mira hacia aqui!")
        self.display.set_estado(Estado.LISTENING)

        capturas = []
        timeout  = time.time() + 12

        while len(capturas) < CAPTURE_FRAMES and time.time() < timeout:
            ret, f = self.vision.cap.read()
            if not ret:
                break
            gray  = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
            gray  = cv2.equalizeHist(gray)
            faces = self.vision.face_cascade.detectMultiScale(gray, 1.1, 8, minSize=(60, 60))
            for (x, y, w, h) in faces:
                roi = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
                capturas.append(roi)
            time.sleep(0.05)

        if capturas:
            self.vision.aprender_rostro(siguiente_id, nombre, capturas)
            log.info(f"Registro exitoso: {nombre} (ID {siguiente_id})")
            self.display.set_estado(Estado.SPEAKING, nombre=nombre)
            self.voz.hablar(f"Listo! Ya te recuerdo, {nombre}. Hora de aventura!")
        else:
            log.warning("No se capturaron fotos")
            self.voz.hablar("Hmm, no pude verte bien. Intentalo de nuevo!")

        self.display.set_estado(Estado.IDLE)

    # ── Apagado ───────────────────────────────────────────────────────────────

    def _apagar(self):
        log.info("Apagando BMO...")
        self.vision.liberar()
        self.display.cerrar()


def main():
    agente = AgenteBMO()
    try:
        agente.run()
    except KeyboardInterrupt:
        agente._running = False
        agente._apagar()


if __name__ == "__main__":
    main()
