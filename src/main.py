"""
BMO — Agente local autónomo

Flujo:
  1. Warmup
  2. BMO escucha SIEMPRE (no requiere cara)
  3. Si detecta cara conocida → usa su nombre como contexto
  4. Si alguien dice su nombre → inicia registro de cara
  5. Responde con LLM en loop continuo
"""
import threading
import time
import logging
import random
import cv2

from src.display.display import DisplayBMO, Estado
from src.vision.vision   import VisionBMO
from src.voice.voice     import VozBMO
from src.brain.brain     import responder_con_tts, detectar_nombre, saludo_fijo
from src.memory.register import nombres_a_ids

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("BMO")

CAPTURE_FRAMES = 25     # fotos para registrar un rostro
SALUDO_COOLDOWN = 60.0  # segundos entre saludos a la misma persona


class AgenteBMO:
    def __init__(self):
        log.info("=== Iniciando BMO ===")
        self.display = DisplayBMO()
        self.vision  = VisionBMO(camera_index=0)
        self.voz     = VozBMO()

        self._running         = True
        self._nombre_actual: str | None = None   # nombre detectado por cámara (pegajoso)
        self._nombre_camara:  str | None = None   # nombre raw del hilo de cámara
        self._ultimo_saludo: dict[str, float] = {}
        self._lock_camara     = threading.Lock()
        self._ultimo_visto:   float = 0.0         # timestamp última vez que se vio cara
        self._NOMBRE_TIMEOUT  = 30.0              # segundos antes de olvidar el nombre

        log.info("=== BMO listo ===")

    def run(self):
        # Hilo de cámara — actualiza _nombre_actual en segundo plano
        threading.Thread(target=self._loop_camara, daemon=True).start()
        # Hilo de lógica — escucha y responde
        threading.Thread(target=self._loop_logica, daemon=True).start()
        # Hilo principal — solo animación
        while self._running:
            if not self.display.tick():
                self._running = False
        self._apagar()

    # ── Hilo de cámara ────────────────────────────────────────────────────────

    def _loop_camara(self):
        """Lee la cámara y actualiza el nombre detectado con lógica pegajosa."""
        while self._running:
            ret, frame = self.vision.cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            _, detecciones = self.vision.procesar_rostro(frame)
            reconocidos = [d["nombre"] for d in detecciones if d["id"] is not None]

            with self._lock_camara:
                if reconocidos:
                    self._nombre_camara = reconocidos[0]
                    self._nombre_actual = reconocidos[0]   # actualizar nombre pegajoso
                    self._ultimo_visto  = time.time()
                else:
                    self._nombre_camara = None
                    # Olvidar nombre solo si pasó el timeout
                    if time.time() - self._ultimo_visto > self._NOMBRE_TIMEOUT:
                        self._nombre_actual = None

            time.sleep(0.1)

    # ── Hilo de lógica ────────────────────────────────────────────────────────

    def _loop_logica(self):
        self.display.set_estado(Estado.WARMUP)
        time.sleep(3.0)
        log.info("BMO despierto")

        # Saludo inicial
        self.display.set_estado(Estado.SPEAKING)
        self.voz.hablar("Hola! Soy BMO. Estoy listo para hablar contigo!")
        self.display.set_estado(Estado.IDLE)

        while self._running:
            try:
                self._ciclo_escucha()
            except Exception as e:
                log.error(f"Error: {e}")
                time.sleep(1.0)

    def _ciclo_escucha(self):
        """Un ciclo: escuchar → procesar → responder."""
        # Saludo si hay cara conocida nueva
        with self._lock_camara:
            nombre_camara = self._nombre_actual

        if nombre_camara:
            ahora = time.time()
            if ahora - self._ultimo_saludo.get(nombre_camara, 0) > SALUDO_COOLDOWN:
                self._ultimo_saludo[nombre_camara] = ahora
                saludo = saludo_fijo(nombre_camara)
                log.info(f"Saludando a {nombre_camara}: '{saludo}'")
                self.display.set_estado(Estado.SPEAKING, nombre=nombre_camara)
                self.voz.hablar(saludo)
                self.display.set_estado(Estado.IDLE)

        # Escuchar
        self.display.set_estado(Estado.LISTENING)
        texto = self.voz.escuchar()

        if not texto:
            self.display.set_estado(Estado.IDLE)
            time.sleep(0.5)
            return

        log.info(f"Escuché: '{texto}'")

        # Obtener nombre actual de cámara para contexto (pegajoso)
        with self._lock_camara:
            nombre_contexto = self._nombre_actual
        if nombre_contexto:
            log.info(f"Pensando... (contexto: {nombre_contexto})")
        else:
            log.info("Pensando... (contexto: ninguno)")

        # Detectar si dice su nombre → registrar
        nombre_nuevo = detectar_nombre(texto)
        if nombre_nuevo:
            # No registrar si ya lo conocemos con ese nombre
            conocidos = list(nombres_a_ids().values())
            if nombre_nuevo.lower() not in [n.lower() for n in conocidos]:
                self._registrar_persona(nombre_nuevo)
                return
            else:
                log.info(f"'{nombre_nuevo}' ya está registrado")

        # Responder — LLM y TTS en paralelo (igual que be-more-agent)
        self.display.set_estado(Estado.THINKING)

        def _on_speaking():
            self.display.set_estado(Estado.SPEAKING, nombre=nombre_contexto)

        responder_con_tts(
            mensaje=texto,
            hablar_fn=self.voz.hablar,
            on_start_speaking=_on_speaking,
            nombre_persona=nombre_contexto,
        )
        self.display.set_estado(Estado.IDLE)

    # ── Registro de persona ───────────────────────────────────────────────────

    def _registrar_persona(self, nombre: str):
        log.info(f"Iniciando registro: '{nombre}'")
        siguiente_id = self.vision.siguiente_id()

        # Instrucciones claras
        self.display.set_estado(Estado.SPEAKING)
        self.voz.hablar(f"Hola {nombre}! Voy a recordar tu cara. Quedate quieto y mirame!")
        time.sleep(0.5)
        self.voz.hablar("Capturando en tres, dos, uno!")
        self.display.set_estado(Estado.LISTENING)

        capturas = []
        timeout  = time.time() + 15
        log.info(f"Capturando {CAPTURE_FRAMES} fotos...")

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
                if len(capturas) % 5 == 0:
                    log.info(f"  {len(capturas)}/{CAPTURE_FRAMES} fotos")
            time.sleep(0.04)

        if len(capturas) >= 10:
            self.vision.aprender_rostro(siguiente_id, nombre, capturas)
            log.info(f"Registro exitoso: {nombre} (ID {siguiente_id}, {len(capturas)} fotos)")
            self._ultimo_saludo[nombre] = time.time()
            self.display.set_estado(Estado.SPEAKING, nombre=nombre)
            self.voz.hablar(f"Listo {nombre}! Ya te tengo en mi memoria. Hora de aventura!")
        else:
            log.warning(f"Pocas fotos capturadas: {len(capturas)}")
            self.display.set_estado(Estado.SPEAKING)
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
