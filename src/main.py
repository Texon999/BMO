"""
Módulo principal de BMO — Agente conversacional autónomo con IA multimodal.

ARQUITECTURA DEL SISTEMA:
BMO es un agente de IA completo que integra múltiples modalidades:
- 🎤 Entrada de voz (Whisper STT)
- 👁️ Visión computacional (OpenCV + ONNX)
- 🧠 Procesamiento de lenguaje (Ollama + Qwen 2.5:1.5B)
- 🔊 Síntesis de voz (Piper TTS)
- 🖥️ Interfaz visual (animaciones de cara)
- 💾 Memoria personalizada (reconocimiento facial + contexto)

ARQUITECTURA DE HILOS:
El sistema opera con tres hilos paralelos para máximo rendimiento:

  🎨 Hilo Principal (display):
    - Renderiza la animación de la cara de BMO en tiempo real
    - Controla el ciclo de vida del proceso
    - Estados visuales: warmup, idle, listening, thinking, speaking
    - Si se cierra la ventana → BMO se apaga completamente

  📷 Hilo de Cámara (_loop_camara):
    - Captura frames continuamente de la cámara
    - Procesa 1 de cada VISION_PROCESS_EVERY_N frames (optimización RPi5)
    - Detecta rostros con Haar Cascade (rápido, CPU)
    - Reconoce personas con embeddings ONNX (512 dimensiones)
    - Implementa lógica "pegajosa": recuerda nombres durante NOMBRE_TIMEOUT segundos
    - Actualiza _nombre_actual thread-safe con locks

  🎧 Hilo de Lógica (_loop_logica):
    - Escucha micrófono con VAD (detección de actividad de voz)
    - Transcribe audio con Whisper cuando detecta habla
    - Procesa texto: detección de nombres, respuestas predefinidas, LLM
    - Maneja registro facial automático para nuevas personas
    - Genera respuestas contextuales basadas en reconocimiento facial

FLUJO COMPLETO DE CONVERSACIÓN:
1. **Detección de Presencia**: Cámara detecta y reconoce rostros continuamente
2. **Saludo Automático**: Si reconoce a alguien nuevo, saluda por nombre
3. **Escucha Activa**: VAD detecta cuando alguien empieza a hablar
4. **Grabación Inteligente**: Graba hasta detectar silencio o timeout
5. **Transcripción**: Whisper convierte audio a texto en español
6. **Análisis de Intención**: 
   - ¿Es un nombre nuevo? → Inicia registro facial
   - ¿Hay respuesta predefinida? → Respuesta instantánea
   - ¿Necesita LLM? → Clasificación + generación contextual
7. **Respuesta Multimodal**: 
   - Generación de texto con contexto personalizado
   - Síntesis de voz en streaming (habla mientras piensa)
   - Animación facial sincronizada con el estado
8. **Actualización de Memoria**: Guarda el turno en el contexto de la persona

REGISTRO FACIAL AUTOMÁTICO:
Cuando alguien dice "me llamo X" o "soy X":
1. **Validación**: Verifica que el nombre no esté ya registrado
2. **Instrucciones**: Explica el proceso al usuario
3. **Captura Múltiple**: Toma 25 fotos del rostro desde diferentes ángulos
4. **Extracción de Features**: Genera embeddings ONNX de 512 dimensiones
5. **Promediado**: Combina embeddings para mayor robustez
6. **Persistencia**: Guarda en memory.json con ID único
7. **Confirmación**: Notifica éxito y saluda por nombre

LÓGICA DE RECONOCIMIENTO "PEGAJOSA":
- Cuando se reconoce una cara → _nombre_actual = nombre
- Si la cara desaparece → mantiene el nombre durante NOMBRE_TIMEOUT segundos
- Esto evita pérdida de contexto por movimientos temporales
- Permite conversaciones naturales sin re-reconocimiento constante

OPTIMIZACIONES PARA RASPBERRY PI 5:
- **Visión**: Procesa 1 de cada 2 frames (VISION_PROCESS_EVERY_N=2)
- **Audio**: VAD evita procesamiento continuo de silencio
- **LLM**: Clasificador reduce tokens según tipo de pregunta
- **TTS**: Streaming permite hablar mientras genera
- **Memoria**: Caché en RAM evita I/O repetitivo de JSON
- **Hilos**: Paralelización maximiza uso de 4 núcleos

CONFIGURACIÓN DINÁMICA:
Todos los parámetros se leen desde src/config/runtime.py:
- Índices de cámara y micrófono
- Modelos de Whisper y configuración STT
- Parámetros del LLM (temperatura, tokens, etc.)
- Umbrales de VAD y timeouts
- Modo headless para ejecución sin pantalla

MANEJO DE ERRORES Y ROBUSTEZ:
- Autodetección de micrófono si no se especifica
- Modo degradado si falta el modelo facial ONNX
- Fallbacks para dispositivos de audio no disponibles
- Recuperación automática de errores de transcripción
- Validación de recursos en _preflight()

ESTADOS VISUALES Y FEEDBACK:
- **WARMUP**: Cargando componentes (3 segundos)
- **IDLE**: Esperando interacción, muestra nombre si reconoce a alguien
- **LISTENING**: Micrófono activo, grabando audio
- **THINKING**: LLM procesando, generando respuesta
- **SPEAKING**: TTS reproduciendo, cara animada hablando

INTEGRACIÓN CON MEMORIA PERSONALIZADA:
- Cada persona reconocida tiene su propio contexto de conversación
- El resumen se inyecta en el system prompt del LLM
- Continuidad entre sesiones sin contaminar contextos
- Cooldown de saludos evita repetición excesiva (60 segundos)

EJEMPLO DE SESIÓN TÍPICA:
1. Usuario se acerca → cámara detecta cara desconocida
2. Usuario: "Hola, me llamo Ana" → BMO inicia registro facial
3. BMO: "Hola Ana! Voy a recordar tu cara..." → captura 25 fotos
4. BMO: "Listo Ana! Ya te tengo en mi memoria" → registro completo
5. Usuario: "¿Qué tiempo hace?" → BMO clasifica como FACTUAL
6. BMO: "No tengo datos del clima actual, búscalo en internet" → respuesta en 2 oraciones
7. Próxima sesión: BMO reconoce a Ana y saluda automáticamente con contexto previo
"""
import threading
import time
import logging
import cv2
import sounddevice as sd
import ollama

from src.display.display import DisplayBMO, Estado
from src.vision.vision   import VisionBMO
from src.voice.voice     import VozBMO
from src.voice.wake_word import WakeWordDetector
from src.brain.brain     import responder_con_tts, detectar_nombre, saludo_fijo, precargar_modelo
from src.memory.register import nombres_a_ids
from src.config.runtime import (
    CAMERA_INDEX,
    MIC_DEVICE,
    OUTPUT_DEVICE,
    HEADLESS,
    VISION_PROCESS_EVERY_N,
    BRAIN_CONTEXT_HOT_RELOAD,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("BMO")

CAPTURE_FRAMES = 25     # fotos para registrar un rostro
SALUDO_COOLDOWN = 60.0  # segundos entre saludos a la misma persona


def _preflight():
    """Valida recursos base antes de iniciar el loop."""
    log.info(
        "Config runtime | camera=%s mic=%s out=%s headless=%s vision_every_n=%s brain_hot_reload=%s",
        CAMERA_INDEX,
        MIC_DEVICE,
        OUTPUT_DEVICE,
        HEADLESS,
        VISION_PROCESS_EVERY_N,
        BRAIN_CONTEXT_HOT_RELOAD,
    )
    try:
        devices = sd.query_devices()
        log.info("Audio detectado: %s dispositivos", len(devices))
    except Exception as e:
        log.warning("No se pudo consultar audio: %s", e)

    try:
        ollama.list()
        log.info("Ollama conectado")
    except Exception as e:
        log.warning("Ollama no responde: %s", e)


class AgenteBMO:
    def __init__(self):
        log.info("=== Iniciando BMO ===")
        self.display = DisplayBMO()
        
        # Intentar inicializar visión, pero permitir degradación sin cámara
        self.vision = None
        try:
            self.vision = VisionBMO(camera_index=CAMERA_INDEX)
        except RuntimeError as e:
            log.warning("  Cámara no disponible: %s", e)
            log.warning("  BMO funcionará sin reconocimiento facial (solo audio)")
        
        self.voz = VozBMO(mic_device=MIC_DEVICE)

        # Wake word detector — usa el mismo modelo STT de VozBMO
        self._wake = WakeWordDetector(
            stt=self.voz.stt,
            mic_device=self.voz._mic,
            sample_rate=16000,
            tts_rate=self.voz._tts_rate,
        )

        self._running = True

        # ── Estado de visión (thread-safe) ────────────────────────────────────
        # Nombre reconocido por la cámara (cara registrada en memory.json)
        self._nombre_camara_reconocido: str | None = None
        # True si hay una cara en cámara pero NO está registrada
        self._cara_desconocida_presente: bool = False
        self._ultimo_visto: float = 0.0
        self._NOMBRE_TIMEOUT = 30.0   # segundos antes de olvidar el nombre pegajoso
        self._lock_camara = threading.Lock()
        self._vision_frame_idx = 0
        self._last_detecciones: list = []
        self._vision_estado_log = "sin_caras"
        self._vision_ultimo_nombre: str | None = None

        # ── Nombre en uso para el LLM (puede venir de cámara o de caché) ─────
        # Si la cámara reconoce → _nombre_activo = nombre reconocido (persistente)
        # Si no hay cámara y el usuario dijo su nombre → _nombre_activo = caché temporal
        # En cualquier otro caso → None
        self._nombre_activo: str | None = None
        self._nombre_cache_temporal: str | None = None  # solo RAM, sin foto

        self._ultimo_saludo: dict[str, float] = {}

        log.info("=== BMO listo ===")

    def run(self):
        threading.Thread(target=self._loop_camara, daemon=True).start()
        threading.Thread(target=self._loop_logica, daemon=True).start()
        while self._running:
            if not self.display.tick():
                self._running = False
        self._apagar()

    # ── Hilo de cámara ────────────────────────────────────────────────────────

    def _loop_camara(self):
        """Lee la cámara, actualiza el nombre reconocido y el flag de cara desconocida."""
        if self.vision is None:
            log.info("Hilo de cámara desactivado (sin cámara disponible)")
            return

        while self._running:
            ret, frame = self.vision.cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            if self._vision_frame_idx % VISION_PROCESS_EVERY_N == 0:
                _, self._last_detecciones = self.vision.procesar_rostro(frame)
            self._vision_frame_idx += 1

            detecciones = self._last_detecciones
            reconocidos  = [d for d in detecciones if d["id"] is not None]
            desconocidos = [d for d in detecciones if d["id"] is None]

            self._log_eventos_vision(reconocidos, desconocidos)

            with self._lock_camara:
                if reconocidos:
                    nombre = str(reconocidos[0]["nombre"])
                    self._nombre_camara_reconocido = nombre
                    self._cara_desconocida_presente = False
                    self._ultimo_visto = time.time()
                    # Si la cámara reconoce a alguien, ese es el nombre activo
                    # y descartamos cualquier caché temporal
                    self._nombre_activo = nombre
                    self._nombre_cache_temporal = None
                elif desconocidos:
                    self._cara_desconocida_presente = True
                    # Lógica pegajosa: mantener nombre reconocido durante el timeout
                    if time.time() - self._ultimo_visto > self._NOMBRE_TIMEOUT:
                        self._nombre_camara_reconocido = None
                        self._nombre_activo = self._nombre_cache_temporal  # volver al caché si existe
                else:
                    self._cara_desconocida_presente = False
                    if time.time() - self._ultimo_visto > self._NOMBRE_TIMEOUT:
                        self._nombre_camara_reconocido = None
                        self._nombre_activo = self._nombre_cache_temporal

            time.sleep(0.1)

    def _log_eventos_vision(self, reconocidos: list[dict], desconocidos: list[dict]):
        if not reconocidos and not desconocidos:
            if self._vision_estado_log != "sin_caras":
                log.info("[VISION] Sin caras en cámara")
                self._vision_estado_log = "sin_caras"
                self._vision_ultimo_nombre = None
            return
        if reconocidos:
            nombre = str(reconocidos[0]["nombre"])
            similitud = float(reconocidos[0]["similitud"])
            if self._vision_estado_log != "reconocido" or self._vision_ultimo_nombre != nombre:
                log.info("[VISION] Cara reconocida: %s (sim %.1f)", nombre, similitud)
                self._vision_estado_log = "reconocido"
                self._vision_ultimo_nombre = nombre
            return
        if self._vision_estado_log != "desconocido":
            log.info("[VISION] Cara detectada pero no reconocida (%s rostro/s)", len(desconocidos))
            self._vision_estado_log = "desconocido"
            self._vision_ultimo_nombre = None

    # ── Hilo de lógica ────────────────────────────────────────────────────────

    def _loop_logica(self):
        self.display.set_estado(Estado.WARMUP)
        log.info("Precargando modelo LLM durante warmup...")
        precargar_modelo()
        time.sleep(1.0)
        log.info("BMO despierto")

        self.display.set_estado(Estado.SPEAKING)
        self.voz.hablar("Hola! Soy BMO. Estoy listo para hablar contigo!")
        self.display.set_estado(Estado.IDLE)

        while self._running:
            try:
                self._ciclo_escucha()
            except Exception as e:
                log.error(f"Error en ciclo: {e}")
                time.sleep(1.0)

    def _ciclo_escucha(self):
        """
        Un ciclo completo:
          1. Saludo automático si la cámara reconoce a alguien nuevo
          2. Escucha pasiva esperando el wake word "BMO"
          3. Al detectar wake word → tín → escucha el prompt completo
          4. Procesa y responde
        """
        # Saludo automático si la cámara reconoce a alguien nuevo
        with self._lock_camara:
            nombre_reconocido = self._nombre_camara_reconocido

        if nombre_reconocido:
            ahora = time.time()
            if ahora - self._ultimo_saludo.get(nombre_reconocido, 0) > SALUDO_COOLDOWN:
                self._ultimo_saludo[nombre_reconocido] = ahora
                saludo = saludo_fijo(nombre_reconocido)
                log.info(f"Saludando a {nombre_reconocido}: '{saludo}'")
                self.display.set_estado(Estado.SPEAKING, nombre=nombre_reconocido)
                self.voz.hablar(saludo)
                self.display.set_estado(Estado.IDLE)

        # ── Escucha pasiva: esperar wake word ─────────────────────────────────
        self.display.set_estado(Estado.IDLE)
        wake_detectado, prompt_inline = self._wake.escuchar_pasivo()

        if not wake_detectado:
            return   # nadie dijo "BMO", seguir esperando

        # ── Wake word detectado: escuchar el prompt completo ──────────────────
        # Si el prompt ya venía inline ("BMO qué hora es"), usarlo directamente.
        # Si no, escuchar el siguiente enunciado completo.
        if prompt_inline:
            texto = prompt_inline
            log.info(f"[WAKE] Prompt inline: '{texto}'")
        else:
            self.display.set_estado(Estado.LISTENING)
            texto = self.voz.escuchar()

        if not texto:
            self.display.set_estado(Estado.IDLE)
            return

        log.info(f"Escuché: '{texto}'")

        # Leer estado de cámara
        with self._lock_camara:
            nombre_reconocido = self._nombre_camara_reconocido
            cara_desconocida  = self._cara_desconocida_presente
            camara_disponible = self.vision is not None

        # ── Lógica de nombre ──────────────────────────────────────────────────
        nombre_nuevo = detectar_nombre(texto)

        if nombre_nuevo:
            conocidos     = list(nombres_a_ids().values())
            ya_registrado = nombre_nuevo.lower() in [n.lower() for n in conocidos]

            if camara_disponible and cara_desconocida and not ya_registrado:
                log.info(f"[NOMBRE] Cara desconocida dijo '{nombre_nuevo}' → registrando foto")
                self._registrar_persona(nombre_nuevo)
                return
            elif camara_disponible and nombre_reconocido:
                log.info(f"[NOMBRE] Cámara ya reconoció a '{nombre_reconocido}', ignorando '{nombre_nuevo}'")
            elif not camara_disponible and not ya_registrado:
                self._nombre_cache_temporal = nombre_nuevo
                self._nombre_activo = nombre_nuevo
                log.info(f"[NOMBRE] Sin cámara → nombre en caché temporal: '{nombre_nuevo}'")
                self.display.set_estado(Estado.SPEAKING)
                self.voz.hablar(f"Hola {nombre_nuevo}! Te recuerdo mientras hablamos, pero sin cámara no puedo guardar tu cara.")
                self.display.set_estado(Estado.IDLE)
                return
            elif ya_registrado:
                log.info(f"[NOMBRE] '{nombre_nuevo}' ya está registrado")
                if not camara_disponible:
                    self._nombre_cache_temporal = nombre_nuevo
                    self._nombre_activo = nombre_nuevo

        # Nombre activo para el LLM
        with self._lock_camara:
            nombre_contexto = self._nombre_activo

        log.info("Pensando... (contexto: %s)", nombre_contexto or "ninguno")
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
        """
        Registra la cara de la persona frente a la cámara.
        Solo se llama cuando hay cámara activa y cara desconocida.
        Al terminar, el nombre queda persistente en memory.json.
        """
        log.info(f"Iniciando registro: '{nombre}'")
        siguiente_id = self.vision.siguiente_id()

        self.display.set_estado(Estado.SPEAKING)
        self.voz.hablar(f"Hola {nombre}! Voy a recordar tu cara. Quedate quieto y mirame!")
        time.sleep(0.5)
        self.voz.hablar("Capturando en tres, dos, uno!")
        self.display.set_estado(Estado.LISTENING)

        capturas = []
        timeout = time.time() + 15
        log.info(f"Capturando {CAPTURE_FRAMES} fotos...")

        while len(capturas) < CAPTURE_FRAMES and time.time() < timeout:
            ret, f = self.vision.cap.read()
            if not ret:
                break
            gray  = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
            gray  = cv2.equalizeHist(gray)
            faces = self.vision.face_cascade.detectMultiScale(gray, 1.1, 8, minSize=(60, 60))
            for (x, y, w, h) in faces:
                roi_bgr = f[y:y+h, x:x+w]
                capturas.append(roi_bgr)
                if len(capturas) % 5 == 0:
                    log.info(f"  {len(capturas)}/{CAPTURE_FRAMES} fotos")
            time.sleep(0.04)

        if len(capturas) >= 10:
            self.vision.aprender_rostro(siguiente_id, nombre, capturas)
            log.info(f"Registro exitoso: {nombre} (ID {siguiente_id}, {len(capturas)} fotos)")
            # El nombre ahora es persistente — actualizar estado y limpiar caché temporal
            with self._lock_camara:
                self._nombre_activo = nombre
                self._nombre_cache_temporal = None
            self._ultimo_saludo[nombre] = time.time()
            self.display.set_estado(Estado.SPEAKING, nombre=nombre)
            self.voz.hablar(f"Listo {nombre}! Ya te tengo en mi memoria.")
        else:
            log.warning(f"Pocas fotos capturadas: {len(capturas)}")
            self.display.set_estado(Estado.SPEAKING)
            self.voz.hablar("Hmm, no pude verte bien. Intentalo de nuevo!")

        self.display.set_estado(Estado.IDLE)

    # ── Apagado ───────────────────────────────────────────────────────────────

    def _apagar(self):
        log.info("Apagando BMO...")
        if self.vision:
            self.vision.liberar()
        self.display.cerrar()


def main():
    _preflight()
    agente = AgenteBMO()
    try:
        agente.run()
    except KeyboardInterrupt:
        agente._running = False
        agente._apagar()


if __name__ == "__main__":
    main()
