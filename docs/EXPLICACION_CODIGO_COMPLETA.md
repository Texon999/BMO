# 🔍 EXPLICACIÓN COMPLETA DEL CÓDIGO DE BMO

**Documento**: Análisis exhaustivo del código fuente  
**Fecha**: 30/04/2026  
**Versión**: 1.0 - Producción  
**Objetivo**: Entender qué hace cada archivo, cómo interactúan y qué pasa si los modificas

---

## 📌 ÍNDICE RÁPIDO

1. [Configuración Centralizada](#1-configuración-centralizada)
2. [Módulo BRAIN (Cerebro LLM)](#2-módulo-brain)
3. [Módulo VISION (Visión)](#3-módulo-vision)
4. [Módulo VOICE (Audio)](#4-módulo-voice)
5. [Módulo DISPLAY (UI)](#5-módulo-display)
6. [Módulo MEMORY (Memoria)](#6-módulo-memory)
7. [Archivo Main (Orquestador)](#7-archivo-main)
8. [Assets y Datos](#8-assets-y-datos)
9. [Qué Pasa Si Lo Modificas](#9-qué-pasa-si-lo-modificas)
10. [Cómo Todo Se Junta](#10-cómo-todo-se-junta)

---

## 1. CONFIGURACIÓN CENTRALIZADA

### Archivos Principales

```
src/config/
├── runtime.py          # Variables de entorno como diccionario global
├── config_manager.py   # Cargador dinámico de config.json
└── audio_manager.py    # Gestor robusto de dispositivos de audio
```

### `config.json` - El Centro de Control

```json
{
  "text_model": "qwen2.5:1.5b",
  "llm_temperature": 0.75,
  "llm_top_k": 50,
  "llm_top_p": 0.90,
  "llm_num_predict": 100,
  "llm_repeat_penalty": 1.1,
  "llm_num_thread": 4,
  "llm_keep_alive": -1,
  "whisper_model": "base",
  "vad_threshold": 0.015,
  "camera_index": 0,
  "headless": false,
  "brain_context_hot_reload": true
}
```

**¿Qué es cada parámetro?**

| Parámetro | Rango | Efecto | Recomendado |
|-----------|-------|--------|-------------|
| `text_model` | qwen2.5:1.5b, 3b, 7b | Tamaño del LLM | 1.5b (RPi5) |
| `llm_temperature` | 0.0-2.0 | Creatividad (↓=robótico, ↑=creativo) | 0.75 |
| `llm_top_k` | 1-100 | Vocabulario disponible | 50 |
| `llm_top_p` | 0.0-1.0 | Masa de probabilidad acumulada | 0.90 |
| `llm_num_predict` | 10-500 | Máx. tokens por respuesta | 100 |
| `llm_repeat_penalty` | 1.0-2.0 | Penalización por repetición | 1.1 |
| `llm_num_thread` | 1-8 | CPUs usadas por Ollama | 4 (RPi5) |
| `llm_keep_alive` | -1, 0, 300+ | Modelo en RAM: -1=siempre, 0=nunca, 300=5min | -1 |
| `whisper_model` | tiny, base, small, medium, large | STT (voice-to-text) | base |
| `vad_threshold` | 0.001-0.1 | Sensibilidad de detección de voz | 0.015 |
| `camera_index` | 0+ | Índice de cámara USB | 0 |
| `brain_context_hot_reload` | true/false | Recargar brain_context.txt automáticamente | true |

### `src/config/runtime.py` - Cargador de Configuración

```python
from src.config.config_manager import config_manager

# Instancia global que carga config.json
config_manager = ConfigManager("config.json")

# Las variables de runtime leen de aquí
CAMERA_INDEX = config_manager.get("camera_index", default=0)
LLM_TEMPERATURE = config_manager.get("llm_temperature", default=0.75)
HEADLESS = config_manager.get("headless", default=False)
# ... más parámetros
```

**¿Cómo funciona?**

```python
# En runtime.py
def get(self, key: str, default=None):
    """Obtener configuración con fallback a default"""
    return self.config.get(key, default)

# En cualquier módulo
from src.config.runtime import CAMERA_INDEX
# CAMERA_INDEX es siempre el valor de config.json
```

### **Hot-Reload**: ¿Qué Significa?

Normalmente, cambiar un archivo `.env` requiere reiniciar el programa. BMO hace hot-reload:

```python
# En config_manager.py
def load_config(self):
    """Recarga automáticamente si config.json cambió"""
    current_mtime = self.config_file.stat().st_mtime
    if current_mtime != self.last_modified:  # ← El archivo cambió
        self.config = json.load(open(config_file))
        self.last_modified = current_mtime
        log.info("[CONFIG] Configuration reloaded")
```

**Casos de Uso**:

1. **Cambiar temperatura sin reiniciar**:
   - Editar `config.json`: `"llm_temperature": 0.5`
   - Guardar
   - BMO detecta cambio automáticamente
   - Próximas respuestas usan 0.5

2. **Cambiar contexto de Hora de Aventura**:
   - Editar `data/brain_context.txt`
   - Guardar
   - Si `brain_context_hot_reload` es true, se recarga automáticamente
   - Próximas respuestas inyectan el nuevo contexto

**¿Qué Pasa Si Lo Modificas?**

```json
{
  "llm_temperature": 2.0  // ← Demasiado alto
}
```

- ✅ BMO seguirá funcionando
- ⚠️ Respuestas muy creativas, puede inventar cosas
- 🔧 Para revertir: volver a 0.75 y guardar

---

## 2. MÓDULO BRAIN

### Archivo: `src/brain/brain.py`

**Responsabilidad**: Generación de respuestas usando LLM

#### Función Principal: `responder_con_tts()`

```python
def responder_con_tts(
    mensaje: str,                              # "¿Cuál es la capital de Francia?"
    hablar_fn: Callable[[str], None],          # Función para TTS
    on_start_speaking: Callable[[], None] = None,  # Callback al empezar a hablar
    nombre_persona: str = None                 # "Juan" si fue reconocido
):
    """
    Pipeline completo de generación de respuesta:
    1. Preparar memory y sistema prompt
    2. Llamar al LLM (Ollama Qwen)
    3. Stream de respuesta con TTS en paralelo
    4. Guardar en memoria persistente
    """
```

#### Paso a Paso: ¿Qué Hace Esta Función?

**Paso 1: Memoria Persistente**

```python
if config_manager.get("chat_memory", True):
    # Agregar mensaje del usuario a la memoria
    persistent_memory.add_user_message(mensaje, nombre_persona)
    
    # Obtener contexto completo para el LLM
    messages = persistent_memory.get_context_for_llm(nombre_persona)
    # messages = [
    #   {"role": "system", "content": "Eres BMO..."},
    #   {"role": "user", "content": "Hola BMO"},
    #   {"role": "assistant", "content": "¡Hola Juan!"},
    #   {"role": "user", "content": "¿Cuál es la capital de Francia?"}
    # ]
else:
    # Modo legacy para compatibilidad
    # ... construir messages manualmente
```

**¿Qué es `messages`?**

Es una lista de diccionarios con el historial de conversación:

```json
[
  {
    "role": "system",
    "content": "Eres BMO, un robot asistente... CORRECCIONES IMPORTANTES: ..."
  },
  {
    "role": "user",
    "content": "¿Cuál es la capital de Francia?"
  }
]
```

El LLM recibe esto y genera una respuesta basada en el contexto completo.

**Paso 2: Obtener Opciones de Ollama**

```python
ollama_options = config_manager.get_ollama_options()
# Devuelve un dict con parámetros del LLM:
# {
#   "temperature": 0.75,
#   "top_k": 50,
#   "top_p": 0.90,
#   "num_predict": 100,
#   "repeat_penalty": 1.1,
#   "num_thread": 4,
#   "keep_alive": -1
# }

model = config_manager.get("text_model", "qwen2.5:3b")
# Resultado: "qwen2.5:1.5b"
```

**Paso 3: Sistema de Streaming con TTS en Paralelo**

```python
# Cola de oraciones para TTS
tts_queue: list[str] = []
tts_lock = threading.Lock()    # Sincronización
tts_done = threading.Event()   # Señal de fin

def _tts_worker():
    """Hilo que consume oraciones de la cola y las convierte a audio"""
    while True:
        texto = None
        with tts_lock:  # Lectura thread-safe
            if tts_queue:
                texto = tts_queue.pop(0)
        
        if texto:
            if on_start_speaking:
                on_start_speaking()  # Callback: cambiar display a SPEAKING
            hablar_fn(texto)  # Reproducir audio
        elif tts_done.is_set():
            break  # Terminar cuando LLM termina y cola vacía
        else:
            time.sleep(0.05)  # Esperar a que haya oraciones

# Iniciar hilo de TTS
worker = threading.Thread(target=_tts_worker, daemon=True)
worker.start()
```

**¿Por Qué Dos Hilos?**

```
Hilo LLM (principal)          Hilo TTS (worker)
├─ Generar token 1            ├─ Esperando...
├─ Generar token 2            ├─ Recibe oración 1
├─ Generar token 3            ├─ Síntesis de voz
├─ ... "." → encolar          ├─ Reproducir audio
├─ Generar token N            ├─ Recibe oración 2
├─ LLM termina → tts_done.set()   ├─ Síntesis de voz
└─ Esperar a worker           └─ Reproducir audio → salida del usuario
```

**Resultado**: Usuario escucha mientras BMO sigue generando = latencia baja percibida

**Paso 4: Streaming del LLM**

```python
sentence_buffer = ""  # Buffer para acumular tokens hasta puntación

stream = ollama.chat(
    model=model,
    messages=messages,
    stream=True,  # ← Importante: devuelve chunks, no respuesta completa
    options=ollama_options,
)

for chunk in stream:  # Cada chunk es un pedazo de la respuesta
    content = chunk["message"]["content"]  # Ej: "La"
    content = re.sub(r"\*+", "", content)  # Quitar formato markdown
    full_resp.append(content)  # Guardar para usar luego
    sentence_buffer += content  # Acumular en buffer

    # Si detectamos puntación → tenemos oración completa
    if any(p in content for p in ".!?\n"):
        oracion = sentence_buffer.strip()
        sentence_buffer = ""
        if oracion and es_valida(oracion):
            with tts_lock:
                tts_queue.append(oracion)  # Encolar para TTS
```

**Ejemplo en Tiempo Real**:

```
LLM genera:     "La    capital    de    Francia    es    París    ."
Buffer acumula: "La" → "La " → "La capital" → "La capital de" → 
                "La capital de Francia" → "La capital de Francia es" → 
                "La capital de Francia es París" → [punto detectado]

→ Encolado: "La capital de Francia es París."
→ TTS reproduce mientras LLM sigue generando otras oraciones
```

**Paso 5: Guardar en Memoria Persistente**

```python
respuesta_completa = "".join(full_resp).strip()

if config_manager.get("chat_memory", True):
    # Guardar la respuesta en memoria
    persistent_memory.add_assistant_message(respuesta_completa)
    
    # Auto-commit cada 2 intercambios (usuario + asistente)
    if len(persistent_memory.session_memory) >= 4:
        persistent_memory.commit_session_to_permanent()
```

### `src/brain/classifier.py` - Clasificador de Preguntas

**¿Para Qué Sirve?**

Ajusta automáticamente los parámetros del LLM según el tipo de pregunta:

```python
categorizar_pregunta("hola") → "greeting" → 40 tokens
categorizar_pregunta("¿Quién es Finn?") → "factual" → 100 tokens
categorizar_pregunta("Explícame cómo funciona X") → "explain" → 200 tokens
```

**Patrones Detectados**:

```python
PATRONES_GREETING = ["hola", "bye", "gracias", "dale", "¿cómo estás?"]
PATRONES_OPINION = ["qué piensas", "te gusta", "cuál prefieres"]
PATRONES_COMPARE = ["diferencia entre", "cuál es mejor", "vs"]
PATRONES_FACTUAL = ["qué es", "quién es", "cuándo", "dónde"]
PATRONES_EXPLAIN = ["explícame", "cómo funciona", "por qué"]
```

**Implementación**:

```python
def categorizar_pregunta(texto: str) -> str:
    texto_lower = texto.lower()
    
    # Orden de evaluación (importante)
    if any(p in texto_lower for p in PATRONES_GREETING):
        return QueryCategory.GREETING  # 40 tokens
    elif any(p in texto_lower for p in PATRONES_OPINION):
        return QueryCategory.OPINION   # 80 tokens
    elif any(p in texto_lower for p in PATRONES_COMPARE):
        return QueryCategory.COMPARE   # 120 tokens
    # ... más categorías
    else:
        return QueryCategory.SIMPLE    # 100 tokens por defecto

# Números de tokens por categoría
NUM_PREDICT_MAP = {
    "greeting": 40,
    "opinion": 80,
    "compare": 120,
    "factual": 100,
    "explain": 200,
    "creative": 280,
}
```

**¿Qué Pasa Si Lo Modificas?**

```python
# ANTES
PATRONES_GREETING = ["hola", "bye"]

# DESPUÉS - Agregar más saludos
PATRONES_GREETING = ["hola", "bye", "buenos días", "buenas noches", "hey"]
```

Resultado:
- ✅ BMO reconoce más saludos
- ✅ Responde más rápido (40 tokens)
- ⚠️ Algo que no sea saludo podría clasificarse como saludo

---

## 3. MÓDULO VISION

### Archivos: `src/vision/vision.py` y `src/vision/embedder.py`

### `vision.py` - Cámara y Haar Cascade

```python
class VisionBMO:
    def __init__(self, camera_index: int = 0):
        # Abrir cámara
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"No se pudo abrir cámara {camera_index}")
        
        # Cargar Haar Cascade (detector rápido de rostros)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        
        # Cargar modelo ONNX si existe
        if Path("data/face_model.onnx").exists():
            self.embedder = FaceEmbedder("data/face_model.onnx")
            self.embeddings_dict = cargar_embeddings_todos()
            print("✓ Visión BMO lista (reconocimiento facial activo)")
        else:
            self.embedder = None
            self.embeddings_dict = {}
            print("⚠ Visión BMO lista (modo degradado)")
```

**¿Qué es Haar Cascade?**

Es un clasificador de imágenes que detecta rostros rápidamente (CPU):

```python
def procesar_rostro(self, frame: np.ndarray) -> tuple[np.ndarray, list]:
    """
    Pipeline de visión:
    1. Convertir a escala de grises
    2. Detectar rostros con Haar Cascade
    3. Para cada rostro: extraer embedding ONNX
    4. Comparar con embeddings guardados
    """
    
    # Paso 1: Escala de grises y ecualización (mejor contraste)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    
    # Paso 2: Detectar rostros
    # scaleFactor=1.1 → pirámide de escalas
    # minNeighbors=8 → filtro de falsos positivos
    # minSize=(60, 60) → rostro mínimo
    faces = self.face_cascade.detectMultiScale(
        gray, 
        scaleFactor=1.1,
        minNeighbors=8,
        minSize=(60, 60)
    )
    # faces = [(x1, y1, w1, h1), (x2, y2, w2, h2), ...]
    
    resultados = []
    for (x, y, w, h) in faces:
        roi_bgr = frame[y:y+h, x:x+w]  # Región de interés
        
        if self.embedder is None:
            # Modo degradado: solo detectar
            resultados.append({
                "id": None,
                "nombre": "Desconocido",
                "similitud": -1.0
            })
        else:
            # Paso 3: Extraer embedding ONNX
            embedding = self.embedder.extract(roi_bgr)
            
            # Paso 4: Comparar con memory
            nombre, similitud = self.embedder.best_match(
                embedding,
                self.embeddings_dict,
                threshold=0.55  # ← Umbral de similitud coseno
            )
            
            resultados.append({
                "id": nombre,
                "nombre": nombre or "Desconocido",
                "similitud": similitud
            })
    
    return frame, resultados
```

### `embedder.py` - Extracción de Embeddings ONNX

```python
class FaceEmbedder:
    def extract(self, face_bgr: np.ndarray) -> np.ndarray:
        """
        Recibe: ROI BGR (cualquier tamaño)
        Devuelve: embedding de 512 dimensiones normalizado L2
        
        Proceso:
        1. BGR → RGB
        2. Resize a 112×112
        3. Normalizar a [-1, 1]
        4. HWC → CHW → batch dim
        5. Pasar por ONNX
        6. Normalizar L2
        """
        
        # Paso 1: Color conversion
        img = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
        
        # Paso 2: Resize
        img = cv2.resize(img, (112, 112))
        
        # Paso 3: Normalización
        img = img.astype(np.float32) / 255.0
        img = (img - 0.5) / 0.5  # → [-1, 1]
        
        # Paso 4: Formato para ONNX
        blob = img.transpose(2, 0, 1)  # HWC → CHW
        blob = blob[np.newaxis, :]      # → (1, 3, 112, 112)
        
        # Paso 5: Inferencia ONNX
        raw = self._session.run(None, {self._input_name: blob})[0][0]
        # raw shape: (512,) - vector de características faciales
        
        # Paso 6: Normalizar L2
        norm = np.linalg.norm(raw)
        embedding = raw / max(norm, 1e-6)
        
        return embedding.astype(np.float32)
    
    def best_match(self, query, candidates, threshold=0.55):
        """
        Encuentra mejor coincidencia usando similitud coseno
        
        Similitud coseno = dot(a, b) para vectores normalizados
        Rango: [-1, 1]
        - 1.0 = idéntico
        - 0.5 = parecido
        - 0.0 = sin relación
        - -1.0 = opuesto
        """
        best_name = None
        best_sim = -1.0
        
        for nombre, embeddings in candidates.items():
            for emb in embeddings:
                # Similitud coseno
                sim = np.dot(query, emb)
                
                if sim > best_sim:
                    best_sim = sim
                    best_name = nombre
        
        if best_sim >= threshold:
            return (best_name, best_sim)
        else:
            return (None, best_sim)
```

**¿Qué Pasa Si Lo Modificas?**

```python
# ORIGINAL
threshold = 0.55

# MÁS SENSIBLE (reconoce más caras, pero puede fallar)
threshold = 0.50
# Resultado: más falsos positivos, reconoce caras lejanas

# MÁS ESTRICTO (solo caras muy similares)
threshold = 0.65
# Resultado: menos falsos positivos, pero puede no reconocer a personas
```

---

## 4. MÓDULO VOICE

### Archivo: `src/voice/voice.py`

**Responsabilidad**: STT (speech-to-text) + TTS (text-to-speech)

### STT con VAD (Voice Activity Detection)

```python
def escuchar(self) -> str:
    """
    Escucha hasta detectar voz, graba hasta silencio, transcribe
    Usa VAD para detectar actividad de voz automáticamente
    """
    
    chunk_size = int(CHUNK_SEC * SAMPLE_RATE)  # 0.05s de audio
    buffer = []
    grabando = False
    silencio_acc = 0.0
    total_acc = 0.0
    
    print("[STT] Esperando voz...")
    
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=self._mic,
        blocksize=chunk_size
    ) as stream:
        while True:
            # Leer chunk de micrófono
            chunk, _ = stream.read(chunk_size)
            chunk_np = chunk.flatten()
            nivel = np.abs(chunk_np).max()  # Amplitud máxima del chunk
            
            if not grabando:
                # En silencio esperando voz
                if nivel > VAD_THRESHOLD:  # VAD detects voice
                    print("[STT] Voz detectada, grabando...")
                    grabando = True
                    buffer = [chunk_np]
                    total_acc = CHUNK_SEC
                    silencio_acc = 0.0
            else:
                # Grabando
                buffer.append(chunk_np)
                total_acc += CHUNK_SEC
                
                if nivel < VAD_THRESHOLD:
                    # Silencio
                    silencio_acc += CHUNK_SEC
                else:
                    # Todavía hay voz
                    silencio_acc = 0.0
                
                # Terminar si:
                if silencio_acc >= VAD_SILENCE_SEC or total_acc >= VAD_MAX_SEC:
                    print(f"[STT] Fin de voz ({total_acc:.1f}s grabados)")
                    break
    
    # Concatenar buffer en un audio continuo
    audio_np = np.concatenate(buffer)
    
    # Transcribir con Whisper
    segments, _ = self.stt.transcribe(
        audio_np,
        language=WHISPER_LANG,  # "es"
        beam_size=STT_BEAM_SIZE,  # 2
        best_of=STT_BEST_OF,  # 2
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
        condition_on_previous_text=False,
        no_speech_threshold=0.6,
        log_prob_threshold=-0.8,
    )
    
    # Filtrar segmentos con baja confianza
    texto = " ".join(
        s.text for s in segments if s.no_speech_prob < 0.6
    ).strip()
    
    if texto:
        print(f"[STT] '{texto}'")
    else:
        print("[STT] Sin habla reconocida")
    
    return texto
```

**¿Qué es VAD?**

Voice Activity Detection detecta automáticamente si hay voz:

```python
nivel = np.abs(chunk_np).max()

if nivel > VAD_THRESHOLD (0.015):
    → "Hay voz, grabar"
else:
    → "Silencio"
```

**Timeline de Grabación**:

```
t=0s: Usuario empieza a hablar
     nivel=0.001 (< threshold 0.015) → ignorar
t=0.2s: Usuario habla claramente
     nivel=0.08 (> threshold) → INICIAR GRABACIÓN
t=0.5s: Usuario sigue hablando
     nivel=0.07 → continuar
t=2s: Usuario termina de hablar
     nivel=0.001 → CONTAR SILENCIO
t=3.2s: 1.2s de silencio acumulado (VAD_SILENCE_SEC)
     → TERMINAR GRABACIÓN
     → Whisper transcribe los ~3 segundos
```

### TTS (Text-to-Speech)

```python
def hablar(self, texto: str):
    """Convierte texto a audio con Piper TTS y lo reproduce"""
    
    if not self._tts:
        print(f"[BMO]: {texto}")  # Sin audio
        return
    
    print(f"[TTS] '{texto[:70]}'")  # Log del texto
    
    try:
        # Piper sintetiza el texto
        chunks = list(self._tts.synthesize(texto))
        
        if not chunks:
            return
        
        # Concatenar chunks de audio
        audio_np = np.concatenate([c.audio_float_array for c in chunks])
        sr = chunks[0].sample_rate
        
        # Agregar silencio pre y post (evitar cortes de palabras)
        silence_pre = np.zeros(int(0.05 * sr))    # 50ms silencio antes
        silence_post = np.zeros(int(0.5 * sr))   # 500ms silencio después
        
        audio_final = np.concatenate([silence_pre, audio_np, silence_post])
        
        # Reproducir
        sd.play(audio_final, samplerate=sr, device=OUTPUT_DEVICE)
        sd.wait()  # Bloquear hasta que termine
        
    except Exception as e:
        print(f"[TTS] Error: {e}")
```

**¿Qué Pasa Si Lo Modificas?**

```python
# Agregar más silencio al final
silence_post = np.zeros(int(1.0 * sr))  # 1 segundo en lugar de 500ms
# Resultado: pausa más larga entre oraciones

# Quitar silencio
silence_pre = np.zeros(0)
silence_post = np.zeros(0)
# Resultado: oraciones pueden cortarse o solaparse
```

---

## 5. MÓDULO DISPLAY

### Archivo: `src/display/display.py`

```python
class DisplayBMO:
    def __init__(self):
        self._frames: dict[str, list[np.ndarray]] = {}
        self._load_faces()  # Cargar PNGs de assets/faces/
        
        self.estado = Estado.WARMUP
        self._idx = 0  # Índice de frame actual para animación
        self._last_t = time.time()
        self._nombre = None  # Nombre de persona reconocida
        
        self._headless = HEADLESS
        if not self._headless:
            cv2.namedWindow("BMO", cv2.WINDOW_NORMAL)
    
    def _load_faces(self):
        """Cargar imágenes PNG para cada estado"""
        for estado in Estado:
            folder = Path("assets/faces") / estado.value
            pngs = sorted(folder.glob("*.png")) if folder.exists() else []
            
            if pngs:
                # Cargar imágenes PNG (con canal alpha si existe)
                self._frames[estado.value] = [
                    cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
                    for p in pngs
                ]
            else:
                # Fallback: rectángulo de color sólido
                color = {
                    "warmup": (40, 40, 40),       # Gris oscuro
                    "idle": (60, 120, 60),        # Verde
                    "listening": (60, 120, 180),  # Azul
                    "thinking": (120, 80, 40),    # Marrón
                    "speaking": (40, 160, 80),    # Verde brillante
                }.get(estado.value, (80, 80, 80))
                
                fb = np.full((480, 480, 3), color, dtype=np.uint8)
                self._frames[estado.value] = [fb]
    
    def set_estado(self, estado: Estado, nombre: str | None = None):
        """Cambiar estado y mostrar nombre"""
        if estado != self.estado:
            self.estado = estado
            self._idx = 0  # Reset animación
        if nombre is not None:
            self._nombre = nombre
    
    def tick(self) -> bool:
        """Renderizar un frame (llamado continuamente)"""
        if self._headless:
            time.sleep(0.03)
            return True
        
        now = time.time()
        if now - self._last_t >= 1.0 / FPS_ANIM:  # FPS_ANIM = 4
            frames = self._frames[self.estado.value]
            self._idx = (self._idx + 1) % len(frames)
            self._last_t = now
        
        # Obtener frame actual
        frame = self._frames[self.estado.value][self._idx].copy()
        
        # RGBA → BGR (componer sobre fondo oscuro)
        if frame.shape[2] == 4:
            bgr = frame[:, :, :3]
            alpha = frame[:, :, 3:4] / 255.0
            bg = np.full_like(bgr, 30)
            frame = (bgr * alpha + bg * (1 - alpha)).astype(np.uint8)
        
        # Dibujar nombre si está disponible
        if self._nombre and self.estado in (Estado.IDLE, Estado.SPEAKING):
            cv2.putText(
                frame,
                f"Hola, {self._nombre}!",
                (15, 460),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (100, 255, 100),  # Verde
                2
            )
        
        # Dibujar etiqueta de estado
        label = self.estado.value.upper()
        cv2.putText(
            frame,
            label,
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (200, 200, 200),
            1
        )
        
        # Mostrar en ventana
        cv2.imshow("BMO", frame)
        key = cv2.waitKey(1) & 0xFF
        return key != ord("q")  # Q para cerrar
    
    def cerrar(self):
        if not self._headless:
            cv2.destroyAllWindows()
```

**Estructura de Assets**:

```
assets/faces/
├── warmup/
│   ├── 1.png  ← Imagen de inicio (cargando)
│   └── 2.png
├── idle/
│   ├── 1.png  ← Cara en reposo (esperando)
│   └── 2.png
├── listening/
│   ├── 1.png  ← Micrófono activo
│   ├── 2.png
│   └── 3.png
├── thinking/
│   ├── 1.png  ← LLM procesando
│   ├── 2.png
│   └── 3.png
└── speaking/
    ├── 1.png  ← Hablando (TTS)
    ├── 2.png
    └── 3.png
```

**¿Qué Pasa Si Lo Modificas?**

```python
# Cambiar tamaño de fuente del nombre
cv2.putText(frame, f"Hola, {self._nombre}!", ..., fontScale=2.0)
# Resultado: nombre más grande

# Cambiar color del nombre
cv2.putText(frame, ..., color=(0, 0, 255))  # Rojo en lugar de verde
# Resultado: nombre en rojo

# Cambiar velocidad de animación
FPS_ANIM = 2  # Más lento (1 frame cada 0.5s)
# Resultado: animación más lenta
```

---

## 6. MÓDULO MEMORY

### Archivos: `src/memory/register.py` y `src/memory/persistent_memory.py`

### `register.py` - Persistencia en JSON

```python
MEMORY_FILE = Path("data/memory.json")

def _load() -> dict:
    """Cargar memory.json con caché en memoria"""
    global _memoria_cache
    if _memoria_cache is not None:
        return _memoria_cache
    
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            _memoria_cache = json.load(f)
            return _memoria_cache
    
    _memoria_cache = {}
    return {}

def _save(data: dict):
    """Guardar memory.json (invalida caché)"""
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    _memoria_cache = None  # Invalidar caché
```

**Estructura de `data/memory.json`**:

```json
{
  "1": {
    "nombre": "Juan",
    "visitas": 3,
    "ultima_vez": "2026-04-19 13:00:00",
    "resumen": "Usuario: hola | BMO: hola Juan! / Usuario: ¿Cómo estás? | BMO: Muy bien!",
    "turnos_recientes": [
      {"user": "hola", "assistant": "hola Juan!"},
      {"user": "¿cómo estás?", "assistant": "muy bien, gracias"}
    ],
    "embeddings": [
      [0.1, 0.2, ..., 0.5]  // 512 dimensiones
    ]
  },
  "_anonimo": {
    "turnos_recientes": []  // Para usuarios no reconocidos
  }
}
```

### Funciones Principales

```python
def guardar_persona(id_persona: int, nombre: str):
    """Guardar registro de nueva persona"""
    memoria = _load()
    key = str(id_persona)
    
    visitas = memoria.get(key, {}).get("visitas", 0) + 1
    entrada = memoria.get(key, {})
    
    entrada.update({
        "nombre": nombre,
        "visitas": visitas,
        "ultima_vez": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    
    if "resumen" not in entrada:
        entrada["resumen"] = ""
    if "turnos_recientes" not in entrada:
        entrada["turnos_recientes"] = []
    
    memoria[key] = entrada
    _save(memoria)


def obtener_contexto_persona(nombre: str) -> str:
    """Obtener resumen de conversaciones previas"""
    memoria = _load()
    
    for key, entrada in memoria.items():
        if key != "_anonimo" and entrada.get("nombre", "").lower() == nombre.lower():
            return entrada.get("resumen", "")
    
    return ""


def agregar_turno_persona(nombre: str, mensaje: str, respuesta: str):
    """Guardar turno en conversación de persona"""
    memoria = _load()
    
    # Encontrar ID de la persona
    id_persona = None
    for key, entrada in memoria.items():
        if key != "_anonimo" and entrada.get("nombre", "").lower() == nombre.lower():
            id_persona = key
            break
    
    if id_persona is None:
        return  # No existe
    
    # Agregar turno a buffer circular
    entrada = memoria[id_persona]
    entrada["turnos_recientes"].append({
        "user": mensaje,
        "assistant": respuesta
    })
    
    # Mantener solo últimos MAX_TURNS
    entrada["turnos_recientes"] = entrada["turnos_recientes"][-MAX_TURNS:]
    
    # Regenerar resumen
    entrada["resumen"] = " / ".join([
        f"Usuario: {t['user']} | BMO: {t['assistant']}"
        for t in entrada["turnos_recientes"]
    ])
    
    entrada["ultima_vez"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    memoria[id_persona] = entrada
    _save(memoria)
```

### `persistent_memory.py` - Memoria Persistente Mejorada

```python
class PersistentMemory:
    def __init__(self, max_conversations=10):
        self.session_memory = []  # Temporal (esta sesión)
        self.persistent_file = "data/chat_memory.json"
        self.max_conversations = max_conversations
    
    def add_user_message(self, contenido: str, nombre_persona: str | None = None):
        """Agregar mensaje del usuario a sesión"""
        self.session_memory.append({
            "role": "user",
            "content": contenido,
            "timestamp": datetime.now().isoformat(),
            "person": nombre_persona
        })
    
    def add_assistant_message(self, contenido: str):
        """Agregar respuesta de BMO a sesión"""
        self.session_memory.append({
            "role": "assistant",
            "content": contenido,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_context_for_llm(self, nombre_persona: str | None = None) -> list:
        """Construir messages para el LLM"""
        messages = [
            {"role": "system", "content": get_system_prompt()}
        ]
        
        # Agregar últimos turnos de sesión
        for msg in self.session_memory[-10:]:  # Últimos 10 mensajes
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return messages
    
    def commit_session_to_permanent(self):
        """Guardar sesión actual a archivo persistente"""
        memoria = load_json(self.persistent_file) if Path(self.persistent_file).exists() else {}
        
        conversacion = {
            "id": len(memoria.get("conversations", [])),
            "turnos": self.session_memory,
            "fecha": datetime.now().isoformat()
        }
        
        if "conversations" not in memoria:
            memoria["conversations"] = []
        
        memoria["conversations"].append(conversacion)
        
        # Mantener solo últimas N conversaciones
        memoria["conversations"] = memoria["conversations"][-self.max_conversations:]
        
        save_json(self.persistent_file, memoria)
        self.session_memory = []  # Limpiar sesión
    
    def save_memory(self):
        """Guardar todo al salir"""
        if self.session_memory:
            self.commit_session_to_permanent()

# Instancia global
persistent_memory = PersistentMemory()
register_shutdown_handler(persistent_memory.save_memory)
```

---

## 7. ARCHIVO MAIN

### `src/main.py` - Orquestador Central

**Clase Principal**: `AgenteBMO`

```python
class AgenteBMO:
    def __init__(self):
        log.info("=== Iniciando BMO ===")
        
        # Inicializar componentes
        self.display = DisplayBMO()
        
        # Visión (con fallback si no hay cámara)
        self.vision = None
        try:
            self.vision = VisionBMO(camera_index=CAMERA_INDEX)
        except RuntimeError as e:
            log.warning("⚠️ Cámara no disponible: %s", e)
            log.warning("⚠️ BMO funcionará sin reconocimiento facial")
        
        self.voz = VozBMO(mic_device=MIC_DEVICE)
        
        # Estado compartido (thread-safe con locks)
        self._nombre_actual: str | None = None   # Nombre pegajoso
        self._nombre_camara: str | None = None    # Nombre raw de cámara
        self._lock_camara = threading.Lock()
        self._ultimo_visto: float = 0.0
        self._NOMBRE_TIMEOUT = 30.0  # Segundos de "pegajosidad"
        
        self._running = True
        self._ultimo_saludo: dict[str, float] = {}
    
    def run(self):
        """Iniciar los 3 hilos principales"""
        # Hilo 1: Cámara
        threading.Thread(target=self._loop_camara, daemon=True).start()
        
        # Hilo 2: Lógica
        threading.Thread(target=self._loop_logica, daemon=True).start()
        
        # Hilo 0: Display (principal)
        while self._running:
            if not self.display.tick():
                self._running = False
        
        self._apagar()
    
    def _loop_camara(self):
        """Hilo 1: Detección y reconocimiento facial"""
        if self.vision is None:
            log.info("Hilo de cámara desactivado")
            return
        
        while self._running:
            ret, frame = self.vision.cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            # Procesar frame (Haar + ONNX)
            _, detecciones = self.vision.procesar_rostro(frame)
            
            reconocidos = [d for d in detecciones if d["id"] is not None]
            desconocidos = [d for d in detecciones if d["id"] is None]
            
            with self._lock_camara:
                if reconocidos:
                    nombre = str(reconocidos[0]["nombre"])
                    self._nombre_actual = nombre
                    self._ultimo_visto = time.time()
                else:
                    # Lógica "pegajosa": mantener nombre si no pasó timeout
                    if time.time() - self._ultimo_visto > self._NOMBRE_TIMEOUT:
                        self._nombre_actual = None
            
            time.sleep(0.1)
    
    def _loop_logica(self):
        """Hilo 2: Escucha, procesa y responde"""
        self.display.set_estado(Estado.WARMUP)
        time.sleep(3.0)  # Cargar recursos
        
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
        """Un ciclo: saludar → escuchar → procesar → responder"""
        
        # Saludo si hay cara conocida
        with self._lock_camara:
            nombre_camara = self._nombre_actual
        
        if nombre_camara:
            ahora = time.time()
            if ahora - self._ultimo_saludo.get(nombre_camara, 0) > SALUDO_COOLDOWN:
                self._ultimo_saludo[nombre_camara] = ahora
                saludo = saludo_fijo(nombre_camara)
                log.info(f"Saludando a {nombre_camara}")
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
        
        # Contexto actual
        with self._lock_camara:
            nombre_contexto = self._nombre_actual
        
        # Detectar nombre nuevo
        nombre_nuevo = detectar_nombre(texto)
        if nombre_nuevo:
            conocidos = list(nombres_a_ids().values())
            if nombre_nuevo.lower() not in [n.lower() for n in conocidos]:
                self._registrar_persona(nombre_nuevo)
                return
        
        # Responder
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
    
    def _registrar_persona(self, nombre: str):
        """Capturar rostro y guardar embeddings"""
        log.info(f"Registrando: {nombre}")
        
        siguiente_id = self.vision.siguiente_id()
        
        self.display.set_estado(Estado.SPEAKING)
        self.voz.hablar(f"Hola {nombre}! Voy a recordar tu cara")
        
        time.sleep(0.5)
        self.voz.hablar("Capturando en 3, 2, 1!")
        self.display.set_estado(Estado.LISTENING)
        
        # Capturar 25 fotos
        capturas = []
        timeout = time.time() + 15
        
        while len(capturas) < 25 and time.time() < timeout:
            ret, frame = self.vision.cap.read()
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            faces = self.vision.face_cascade.detectMultiScale(
                gray, 1.1, 8, minSize=(60, 60)
            )
            
            for (x, y, w, h) in faces:
                roi_bgr = frame[y:y+h, x:x+w]
                capturas.append(roi_bgr)
                if len(capturas) % 5 == 0:
                    log.info(f"  {len(capturas)}/25 fotos")
            
            time.sleep(0.04)
        
        # Guardar si tenemos suficientes fotos
        if len(capturas) >= 10:
            self.vision.aprender_rostro(siguiente_id, nombre, capturas)
            log.info(f"Registro exitoso: {nombre}")
            self._ultimo_saludo[nombre] = time.time()
            self.display.set_estado(Estado.SPEAKING, nombre=nombre)
            self.voz.hablar(f"¡Listo {nombre}! Ya te tengo en mi memoria")
        else:
            log.warning(f"Pocas fotos: {len(capturas)}")
            self.display.set_estado(Estado.SPEAKING)
            self.voz.hablar("No pude verte bien, intentalo de nuevo!")
        
        self.display.set_estado(Estado.IDLE)
    
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
```

---

## 8. ASSETS Y DATOS

### Carpeta `assets/faces/`

Contiene imágenes PNG animadas para cada estado:

```
assets/faces/
├── warmup/     # Cargando (1-2 frames)
├── idle/       # Esperando (1-2 frames)
├── listening/  # Escuchando (3-5 frames animados)
├── thinking/   # Pensando (5-8 frames animados)
└── speaking/   # Hablando (8-10 frames animados)
```

**Formato de Imágenes**:
- Resolución: 480×480 píxeles
- Formato: PNG con canal alpha (RGBA)
- Fondo: Transparente o color sólido

### Carpeta `data/`

```
data/
├── memory.json             # Persistencia de personas y embeddings
├── chat_memory.json        # Historial de conversaciones
├── face_model.onnx         # Modelo ONNX de embeddings faciales
├── brain_context.txt       # Contexto inyectable (Hora de Aventura)
├── names.json              # Índice de nombres
├── persons.json            # Metadatos de personas
└── facts/                  # Base de datos de hechos (opcional)
    ├── flags.json
    ├── geography.json
    └── science.json
```

### `data/brain_context.txt` - Contexto Inyectable

```txt
# Información de Hora de Aventura

BMO es un robot de videojuegos que es personaje importante en la serie.
Vive en la Casa del Árbol con Finn y Jake.

Personajes principales:
- Finn: humano aventurero de 14 años
- Jake: perro mágico que puede cambiar de forma
- Marceline: Reina del Vampiro, amiga de los protagonistas
- Rey Helado: villano principal
- Princess Bubblegum: Princesa del País de Dulces

Lugares:
- Casa del Árbol: hogar de Finn y Jake
- País de Dulces: reino mágico
- Dungeon: mazmorra peligrosa
- Tierra de Fuego: reino de fuego
```

Si `brain_context_hot_reload` es true, este archivo se recarga automáticamente cada vez que cambia.

---

## 9. QUÉ PASA SI LO MODIFICAS

### Cambios Comunes y Sus Efectos

#### 1. Modificar `config.json`

```json
{
  "llm_temperature": 2.0
}
```

**Efecto**:
- ✅ Respuestas más creativas
- ❌ Puede inventar datos falsos
- ❌ Puede perder coherencia

**Solución**: Volver a 0.75 y guardar

---

#### 2. Agregar Nuevo Patrón al Clasificador

```python
# En classifier.py
PATRONES_DESPEDIDA = ["adios", "hasta luego", "nos vemos"]

# En categorizar_pregunta()
if any(p in texto_lower for p in PATRONES_DESPEDIDA):
    return QueryCategory.GREETING
```

**Efecto**:
- ✅ BMO reconoce más despedidas
- ✅ Responde rápido (40 tokens)
- ⚠️ Podría clasificar mal palabras similares

---

#### 3. Cambiar Umbral de Similitud de Rostro

```python
# En vision.py
threshold = 0.50  # Más sensible
# threshold = 0.65  # Más estricto
```

**Efecto**:
- `0.50`: Reconoce más caras (falsos positivos)
- `0.65`: Solo caras muy similares (falsos negativos)
- `0.55`: Balance actual

---

#### 4. Cambiar Modelo de Whisper

```json
{
  "whisper_model": "tiny",
  "whisper_model": "base",
  "whisper_model": "small",
  "whisper_model": "medium"
}
```

**Efecto**:
| Modelo | Velocidad | Precisión | RAM |
|--------|-----------|-----------|-----|
| tiny | muy rápido | baja | <500MB |
| base | rápido | media | ~1GB |
| small | medio | buena | ~2GB |
| medium | lento | muy buena | ~5GB |

---

#### 5. Cambiar Modelo LLM

```json
{
  "text_model": "qwen2.5:1.5b",    // Actual
  "text_model": "qwen2.5:3b",      // Mejor precisión (+3s latencia)
  "text_model": "llama2",          // Alternativa
  "text_model": "mistral"          // Alternativa rápida
}
```

**Efecto**:
| Modelo | Velocidad | Precisión | RAM |
|--------|-----------|-----------|-----|
| qwen2.5:1.5b | 6-8s | media | ~2GB |
| qwen2.5:3b | 8-10s | buena | ~4GB |
| llama2:7b | 10-15s | excelente | ~6GB |
| mistral | 5-7s | buena | ~3GB |

---

#### 6. Agregar Nuevo Sistema Prompt

```python
# En brain.py
def get_system_prompt() -> str:
    base = "Eres BMO..."
    # Agregar instrucciones personalizadas
    extras = """
    IMPORTANTE:
    - Siempre saluda con entusiasmo
    - Usa emojis en las respuestas
    - Habla como un niño pequeño
    """
    return base + extras
```

**Efecto**:
- ✅ BMO tiene personalidad diferente
- ⚠️ Puede conflictuar con instrucciones originales
- 🔧 Para revertir: quitar el bloque extras

---

#### 7. Cambiar Tokens Máximos por Categoría

```python
# En classifier.py
NUM_PREDICT_MAP = {
    "greeting": 40,
    "factual": 200,  # Aumentado de 100
    "explain": 500,  # Aumentado de 200
}
```

**Efecto**:
- ✅ Respuestas más largas en esas categorías
- ❌ Latencia aumenta
- 🔧 En RPi5 puede ser muy lento

---

#### 8. Deshabilitar Reconocimiento Facial

```python
# En main.py
# self.vision = VisionBMO(...)  # ← Comentar esta línea
self.vision = None
```

**Efecto**:
- ✅ Ahorra CPU
- ❌ BMO no reconoce a nadie
- ⚠️ No puede registrar personas nuevas

---

#### 9. Agregar Tipo de Pregunta Nuevo

```python
# En brain.py
PATRONES_BROMA = ["chiste", "bromea", "hazme reír"]

# En main.py _ciclo_escucha()
if "chiste" in texto.lower():
    self.voz.hablar("Aquí va: ...")
    return
```

**Efecto**:
- ✅ BMO responde especialmente a bromas
- ✅ Respuesta instantánea (sin LLM)
- 🔧 Agrega lógica especial

---

#### 10. Cambiar Dispositivo de Salida de Audio

```json
{
  "output_device": 2
}
```

**Cómo encontrar el índice**:
```bash
python scripts/list_audio.py
```

**Efecto**:
- ✅ Audio sale por altavoz diferente
- ❌ Si índice inválido, error
- 🔧 Volver a `null` para auto

---

## 10. CÓMO TODO SE JUNTA

### Flujo Completo: Usuario Hace Una Pregunta

```
USUARIO: "Hola BMO, ¿cuál es la capital de Francia?"
         │
         ├─→ [HILO VISIÓN] procesar_rostro()
         │   ├─ Haar Cascade detecta rostro
         │   ├─ FaceEmbedder.extract() → embedding
         │   ├─ best_match() compara con memory.json
         │   └─ Resultado: "Juan" (similitud 0.78)
         │   
         └─→ [HILO LÓGICA] _ciclo_escucha()
             ├─ [DISPLAY] set_estado(LISTENING)
             │
             ├─ [VOICE] escuchar()
             │  ├─ VAD detecta voz
             │  ├─ Grabar 2.5 segundos
             │  ├─ Whisper transcribe
             │  └─ Retorna: "¿Cuál es la capital de Francia?"
             │
             ├─ [CLASSIFIER] categorizar_pregunta()
             │  └─ Detecta "cuál es" → FACTUAL (100 tokens)
             │
             ├─ [MEMORY] obtener_contexto_persona("Juan")
             │  └─ Contexto: "Usuario: hola | BMO: Hola Juan!"
             │
             ├─ [BRAIN] responder_con_tts()
             │  ├─ [DISPLAY] set_estado(THINKING)
             │  │
             │  ├─ build_messages()
             │  │  └─ [
             │  │      {"role": "system", "content": "Eres BMO..."},
             │  │      {"role": "user", "content": "Hola"},
             │  │      {"role": "assistant", "content": "Hola Juan!"},
             │  │      {"role": "user", "content": "¿Cuál es...?"}
             │  │    ]
             │  │
             │  ├─ [OLLAMA] chat() → streaming
             │  │  ├─ Token: "La"
             │  │  ├─ Token: " "
             │  │  ├─ Token: "capital"
             │  │  ├─ ... 
             │  │  ├─ Token: "es"
             │  │  ├─ Token: " "
             │  │  ├─ Token: "París"
             │  │  └─ Token: "." ← Encolar para TTS
             │  │
             │  ├─ [VOICE] hablar() en paralelo (worker thread)
             │  │  ├─ TTS sintetiza: "La capital de Francia es París"
             │  │  ├─ Reproducir audio
             │  │  └─ Usuario escucha
             │  │
             │  ├─ [DISPLAY] set_estado(SPEAKING, nombre="Juan")
             │  │
             │  └─ Respuesta completa: "La capital de Francia es París."
             │
             ├─ [MEMORY] guardar_turno_persona()
             │  └─ Guardar: Usuario: "¿Cuál..." | BMO: "La capital..."
             │
             └─ [DISPLAY] set_estado(IDLE)
                
USUARIO ESCUCHA: "La capital de Francia es París" (desde ~segundo 1)
LATENCIA TOTAL: ~4-5 segundos

Timeline:
t=0s: Usuario termina de hablar
t=0.5s: Whisper termina transcripción
t=1s: LLM comienza, primeros tokens
t=1.2s: TTS comienza síntesis
t=1.5s: Audio comienza a reproducir
t=4s: Respuesta completa reproducida
```

### Interacción de Componentes

```
┌──────────────┐
│   CONFIG     │ ← Parámetros globales
└──────┬───────┘
       │
       ├──→ [VOICE]
       │     └─ WHISPER_MODEL, VAD_THRESHOLD, etc.
       │
       ├──→ [BRAIN]
       │     ├─ LLM_TEMPERATURE, LLM_NUM_PREDICT
       │     └─ brain_context_hot_reload
       │
       ├──→ [VISION]
       │     └─ CAMERA_INDEX
       │
       └──→ [DISPLAY]
             └─ HEADLESS

┌──────────────┐
│   MEMORY     │ ← Estado persistente
└──────┬───────┘
       │
       ├─ memory.json
       │  ├─ Personas registradas
       │  ├─ Embeddings faciales
       │  └─ Contextos de conversación
       │
       └─ chat_memory.json
          └─ Historial de chat

┌──────────────┐
│   MAIN       │ ← Orquestación
└──────┬───────┘
       │
       ├─ [DISPLAY] Renderizar UI
       │
       ├─ [VISION] Detectar/reconocer rostros
       │
       ├─ [VOICE] Escuchar y hablar
       │
       └─ [BRAIN] Procesar y responder
          ├─ Classifier → tokens ajustados
          ├─ Memory → contexto personalizado
          ├─ LLM → generación de respuesta
          └─ TTS → audio streaming
```

### Mejora de Latencia Percibida

```
OPCIÓN A: Streaming Deshabilitado
LLM genera todo → TTS convierte → Reproducir
t=0s: LLM comienza
t=8s: LLM termina
t=10s: TTS termina síntesis
t=12s: Audio comienza a reproducir
→ Usuario espera 12 segundos

OPCIÓN B: Streaming Habilitado (BMO actual)
LLM genera oraciones → TTS en paralelo → Reproducir mientras genera
t=0s: LLM comienza, primeros tokens
t=1s: Oración 1 lista → encolada
t=1.2s: TTS comienza síntesis
t=1.5s: Audio comienza → Usuario escucha
t=8s: LLM termina
t=10s: TTS termina última oración
→ Usuario escucha desde segundo 1.5 (mejora 10x)
```

---

## 📝 RESUMEN

**Componentes Clave**:
1. ✅ **CONFIG**: Parámetros dinámicos sin reinicio
2. ✅ **BRAIN**: LLM con streaming y memoria
3. ✅ **VISION**: Reconocimiento facial ONNX
4. ✅ **VOICE**: Audio con VAD
5. ✅ **DISPLAY**: UI animada
6. ✅ **MEMORY**: Persistencia JSON
7. ✅ **MAIN**: Orquestación de 3 hilos

**Modificaciones Seguras**:
- ✅ Cambiar parámetros en config.json
- ✅ Agregar patrones de clasificación
- ✅ Ajustar umbrales
- ✅ Cambiar modelos (con disponibilidad de RAM)
- ✅ Editar brain_context.txt

**Modificaciones Riesgosas**:
- ❌ Cambiar sincronización de hilos sin entender
- ❌ Quitar validaciones de entrada
- ❌ Cambiar estructura de memory.json manualmente
- ❌ Modificar pipes de streaming sin probar

**Filosofía de Diseño**:
- 100% Local y offline
- Reconocimiento facial persistente
- Memoria personalizada por persona
- Streaming para baja latencia percibida
- Robustez ante falta de cámara/micrófono

