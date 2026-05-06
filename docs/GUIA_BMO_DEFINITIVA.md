# 🤖 GUÍA BMO: Manual Completo - Arquitectura, Funcionamiento y Extensión

**Última actualización**: 30/04/2026  
**Versión**: 2.0  
**Estado**: Producción en Raspberry Pi 5 8GB

---

## 📑 TABLA DE CONTENIDOS

1. [Introducción Ejecutiva](#introducción-ejecutiva)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Instalación y Configuración](#instalación-y-configuración)
4. [Módulos del Proyecto](#módulos-del-proyecto)
5. [Flujo de Ejecución](#flujo-de-ejecución)
6. [Programación en Python para BMO](#programación-en-python-para-bmo)
7. [Parámetros y Optimización](#parámetros-y-optimización)
8. [Casos de Uso y Ejemplos](#casos-de-uso-y-ejemplos)
9. [Troubleshooting](#troubleshooting)
10. [Extensión y Personalización](#extensión-y-personalización)

---

## 🎯 INTRODUCCIÓN EJECUTIVA

### ¿Qué es BMO?

**BMO** es un **agente conversacional multimodal completamente autónomo** que combina:

- 🎤 **Entrada de voz** (Whisper STT - reconocimiento de voz)
- 👁️ **Visión computacional** (OpenCV + ONNX - reconocimiento facial)
- 🧠 **Procesamiento de lenguaje** (Ollama + Qwen 2.5 - inteligencia)
- 🔊 **Síntesis de voz** (Piper TTS - generación de audio)
- 🖥️ **Interfaz visual** (OpenCV - animación facial)
- 💾 **Memoria personalizada** (JSON - reconocimiento facial + contexto)

### ¿Por qué es especial?

- **100% Offline**: Funciona sin internet. Todo local en Raspberry Pi 5
- **Reconocimiento Facial**: Aprende caras de personas y recuerda contexto
- **Streaming de Voz**: Habla mientras genera la respuesta (baja latencia percibida)
- **Multimodal**: Integra audio, video, texto e interacción natural
- **Filosóficamente Autónomo**: No depende de servidores externos

### Requisitos de Hardware

| Componente | Mínimo | Recomendado |
|-----------|--------|------------|
| Raspberry Pi | 4B | 5 8GB |
| CPU Cores | 4 | 4 |
| RAM | 4GB | 8GB |
| Cámara | USB genérica | Raspberry Pi Camera |
| Micrófono | USB cualquiera | Micrófono direccional |
| Altavoz | USB o 3.5mm | Altavoz de 3W+ |

### Requisitos de Software

```bash
# Python
Python 3.10+

# Dependencias principales
- faster-whisper (STT)
- piper-tts (TTS)
- ollama (LLM)
- opencv-python (cámara)
- onnxruntime (embeddings faciales)
- sounddevice (audio)
- numpy (cálculos)
```

---

## 🏗️ ARQUITECTURA DEL SISTEMA

### Diagrama General

```
┌─────────────────────────────────────────────────────────────┐
│                     AGENTE BMO                               │
│  Orquestador Central: src/main.py (AgenteBMO)               │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
    ┌────────┐          ┌────────┐          ┌────────┐
    │ DISPLAY │          │ VISION │          │ VOICE  │
    │ (Hilo 0)│          │(Hilo 1)│          │(Hilo 2)│
    └────────┘          └────────┘          └────────┘
        │                    │                     │
        ▼                    ▼                     ▼
    ┌────────┐          ┌────────┐          ┌────────┐
    │OpenCV  │          │ Haar   │          │Whisper │
    │Animación           │Cascade │          │STT     │
    │Cara    │          │+ ONNX  │          │+       │
    │        │          │Embeddings          │Piper  │
    │        │          │        │          │TTS    │
    └────────┘          └────────┘          └────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   BRAIN (LLM)    │
                    │   src/brain/     │
                    │   - Ollama       │
                    │   - Classifier  │
                    │   - Prompt Eng. │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   MEMORY         │
                    │   src/memory/    │
                    │   - Personas     │
                    │   - Embeddings   │
                    │   - Historial    │
                    └──────────────────┘
```

### Flujo de Datos

```
ENTRADA (Sensor)
    │
    ├─ Cámara → VISION (detecta + reconoce rostro)
    └─ Micrófono → VOICE (detecta VAD + STT Whisper)
    
    │
    ▼
PROCESAMIENTO (Brain)
    │
    ├─ Clasificador: ¿Qué tipo de pregunta?
    ├─ Memory: ¿Quién es? ¿Contexto?
    └─ LLM (Ollama): Genera respuesta
    
    │
    ▼
SALIDA (Actuadores)
    │
    ├─ TTS Piper (Piper) → Altavoz
    └─ Display OpenCV → Pantalla (animación)
```

### Arquitectura de Hilos

BMO usa **3 hilos principales en paralelo**:

```python
# Hilo 0: DISPLAY (principal)
display_thread = main_thread
↓
- Renderiza animación facial
- Actualiza estados visuales
- Controla ciclo de vida

# Hilo 1: VISION (daemon)
vision_thread = Thread(target=_loop_camara)
↓
- Lee cámara continuamente (100ms)
- Detecta rostros (Haar Cascade)
- Reconoce personas (ONNX embeddings)
- Actualiza _nombre_actual thread-safe

# Hilo 2: LOGIC (daemon)
logic_thread = Thread(target=_loop_logica)
↓
- Escucha micrófono (VAD)
- Transcribo audio (Whisper STT)
- Procesa con Brain (LLM)
- Genera audio (Piper TTS)
```

### Thread Safety

**Sincronización con Lock** para evitar condiciones de carrera:

```python
# En main.py - actualización de nombre
self._lock_camara = threading.Lock()

# Escritura en hilo de cámara
with self._lock_camara:
    self._nombre_actual = nombre_nuevo

# Lectura en hilo de lógica
with self._lock_camara:
    nombre_contexto = self._nombre_actual
```

### Estados Visuales

BMO tiene 5 estados animados:

```
WARMUP (3s) → IDLE (esperando) → LISTENING (grabando)
                     ↑                    ↓
                SPEAKING ← THINKING (procesando)
```

**Transiciones**:
- WARMUP: Carga inicial
- IDLE: Esperando entrada, muestra nombre si reconoce
- LISTENING: Micrófono activo, grabando audio
- THINKING: LLM generando respuesta
- SPEAKING: TTS reproduciéndose, cara "habla"

---

## 🚀 INSTALACIÓN Y CONFIGURACIÓN

### Paso 1: Preparar Entorno

```bash
# Clonar el repositorio
cd c:\proyect\BMO

# Crear entorno virtual (recomendado)
python -m venv .venv

# Activar (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activar (Linux/Mac/RPi)
source .venv/bin/activate
```

### Paso 2: Instalar Dependencias

```bash
# Instalar desde requirements.txt
pip install -r requirements.txt

# O manualmente (para entender cada una)
pip install faster-whisper
pip install piper-tts
pip install ollama
pip install opencv-python
pip install onnxruntime
pip install sounddevice
pip install numpy
```

### Paso 3: Instalar Ollama

**En Windows**:
```bash
# Descargar de https://ollama.ai
# O usar WSL2
wsl ollama serve  # En otra terminal
```

**En RPi5**:
```bash
curl https://ollama.ai/install.sh | sh
ollama serve  # En otra terminal
```

### Paso 4: Descargar Modelos

```bash
# LLM principal (Qwen 2.5:1.5B o 3B)
ollama pull qwen2.5:1.5b
# o para mejor precisión:
ollama pull qwen2.5:3b

# Modelo ONNX de reconocimiento facial (automático)
python scripts/download_face_model.py

# Modelo Piper TTS para español (automático)
python scripts/download_voice.py
```

### Paso 5: Configuración Inicial

```bash
# Ver configuración actual
python scripts/config_tool.py --show

# Configuración interactiva
python scripts/config_tool.py --interactive

# Probar micrófono
python scripts/test_mics.py

# Probar cámara
python scripts/test_audio.py
```

### Paso 6: Lanzar BMO

```bash
# En la carpeta BMO/
python -m src.main

# O directamente
python src/main.py
```

Verás:
```
[INFO] === Iniciando BMO ===
[INFO] Config runtime | camera=0 mic=None out=None...
[INFO] Audio detectado: X dispositivos
[INFO] Ollama conectado
[INFO] === BMO listo ===
[INFO] BMO despierto
[INFO] Saludando a Desconocido
```

### Archivo de Configuración

**`config.json`** - Configuración centralizada:

```json
{
  "text_model": "qwen2.5:1.5b",
  "whisper_model": "base",
  "llm_temperature": 0.75,
  "llm_top_k": 40,
  "llm_top_p": 0.85,
  "llm_num_predict": 150,
  "llm_repeat_penalty": 1.15,
  "llm_num_thread": 4,
  "llm_keep_alive": -1,
  "chat_memory": true,
  "max_conversations": 10,
  "brain_context_hot_reload": true,
  "camera_index": 0,
  "mic_device": null,
  "output_device": null,
  "headless": false
}
```

**Todos estos valores son modificables SIN reiniciar** si `brain_context_hot_reload` es true.

---

## 🧩 MÓDULOS DEL PROYECTO

### Estructura de Carpetas

```
BMO/
├── src/                          # Código principal
│   ├── main.py                   # Orquestador y hilos
│   ├── config/
│   │   ├── runtime.py            # Variables de entorno + config.json
│   │   ├── config_manager.py     # Gestor de configuración
│   │   └── audio_manager.py      # Gestor de audio robusto
│   ├── brain/
│   │   ├── brain.py              # LLM, prompts, streaming
│   │   ├── classifier.py         # Clasificador de preguntas
│   │   ├── fact_checker.py       # Verificador de hechos (búsqueda web)
│   │   ├── fact_database.py      # Base de datos de hechos
│   │   ├── response_formatter.py # Formato de respuestas
│   │   ├── fallback_handler.py   # Respuestas por defecto
│   │   ├── hybrid_logger.py      # Sistema de logging
│   │   ├── hybrid_system.py      # Sistema híbrido
│   │   ├── question_classifier.py # Clasificador avanzado
│   │   ├── similarity.py         # Similitud coseno
│   │   ├── text_normalizer.py    # Normalización de texto
│   │   ├── models.py             # Modelos de datos
│   │   └── patterns/             # Patrones regex y lógica
│   ├── voice/
│   │   └── voice.py              # Micrófono (VAD), STT, TTS
│   ├── vision/
│   │   ├── vision.py             # Cámara, Haar, ONNX
│   │   └── embedder.py           # Extractor de embeddings ONNX
│   ├── display/
│   │   └── display.py            # Animación de cara en OpenCV
│   ├── memory/
│   │   ├── persistent_memory.py  # Memoria persistente
│   │   └── register.py           # Registro de personas (JSON)
│   └── __init__.py
├── data/
│   ├── memory.json               # Personas y embeddings
│   ├── chat_memory.json          # Historial de chats
│   ├── chat_history.json         # Histórico legado
│   ├── face_model.onnx           # Modelo de embeddings facial
│   ├── brain_context.txt         # Contexto inyectable (hot-reload)
│   ├── names.json                # Nombres registrados
│   ├── persons.json              # Metadata de personas
│   ├── trainer.yml               # Entrenamiento
│   └── facts/                    # Base de datos de hechos
│       ├── flags.json            # Banderas
│       ├── geography.json        # Geografía
│       └── science.json          # Ciencias
├── scripts/
│   ├── comprehensive_general_test.py    # Test exhaustivo
│   ├── config_tool.py                   # Herramienta de config
│   ├── download_face_model.py           # Descargar ONNX
│   ├── download_voice.py                # Descargar TTS
│   ├── test_fact_checker.py             # Test fact checker
│   └── [otros scripts de diagnóstico]
├── docs/
│   ├── GUIA_BMO_DEFINITIVA.md    # Esta guía
│   ├── ANALISIS_*.md             # Análisis especializados
│   └── SOLUCION_*.md             # Soluciones implementadas
├── requirements.txt              # Dependencias Python
├── config.json                   # Configuración central
├── README.md                     # Intro rápida
└── test_results.json             # Resultados de pruebas
```

---

### 1️⃣ MÓDULO: MAIN (`src/main.py`)

**Responsabilidad**: Orquestación central y coordinación de hilos

#### Clase Principal: `AgenteBMO`

```python
class AgenteBMO:
    def __init__(self):
        # Inicializar componentes
        self.display = DisplayBMO()        # UI
        self.vision = VisionBMO()          # Cámara
        self.voz = VozBMO()                # Audio
        
        # Estado compartido (thread-safe)
        self._nombre_actual: str | None    # Nombre pegajoso
        self._lock_camara = threading.Lock()
    
    def run(self):
        # Iniciar 3 hilos daemon
        threading.Thread(target=self._loop_camara, daemon=True).start()
        threading.Thread(target=self._loop_logica, daemon=True).start()
        
        # Hilo principal: display
        while self._running:
            if not self.display.tick():
                self._running = False
```

#### Métodos Principales

**`_loop_camara()`** - Hilo de cámara
```python
# Lee frames continuamente
# Detecta rostros (Haar Cascade)
# Reconoce personas (ONNX embeddings)
# Actualiza _nombre_actual thread-safe
# Implementa "lógica pegajosa": recuerda nombre 30 segundos

for frame in camera:
    rostros = vision.procesar_rostro(frame)  # → embeddings
    if rostros detectados:
        _nombre_actual = rostro[0].nombre
        _ultimo_visto = time.now()
    elif tiempo - _ultimo_visto > 30s:
        _nombre_actual = None
```

**`_loop_logica()`** - Hilo de lógica
```python
# Escucha micrófono continuamente
# VAD detecta cuando alguien habla
# Transcribe audio con Whisper
# Procesa con Brain (LLM)
# Genera respuesta con TTS

while True:
    texto = escuchar_con_vad()  # Bloquea hasta detectar habla
    nombre = detectar_nombre(texto)
    if nombre: registrar_persona(nombre)
    else: responder_con_tts(texto, contexto=_nombre_actual)
```

**`_registrar_persona(nombre)`** - Registro facial automático
```python
# 1. Saluda: "Voy a recordar tu cara"
# 2. Captura 25 fotos desde diferentes ángulos
# 3. Extrae embeddings ONNX (512 dimensiones)
# 4. Promedia embeddings para robustez
# 5. Guarda en memory.json
# 6. Confirma: "Listo! Te tengo en mi memoria"
```

#### Parámetros Configurables

```python
CAPTURE_FRAMES = 25        # Fotos para registrar rostro
SALUDO_COOLDOWN = 60.0     # Segundos entre saludos
VISION_PROCESS_EVERY_N = 2 # Procesar 1 cada N frames (RPi5 optimization)
NOMBRE_TIMEOUT = 30.0      # Segundos de "pegajosidad"
```

---

### 2️⃣ MÓDULO: BRAIN (`src/brain/`)

**Responsabilidad**: Procesamiento de lenguaje, generación de respuestas, pipeline LLM

#### Archivo Principal: `brain.py`

```python
def responder_con_tts(
    mensaje: str,           # "¿Cuál es la capital de Francia?"
    hablar_fn,              # Función para reproducir TTS
    on_start_speaking=None, # Callback cuando empieza a hablar
    nombre_persona=None     # Contexto de persona (opcional)
) -> str:
    """
    Pipeline completo:
    1. Verificar si es hecho factual → búsqueda web (si está habilitada)
    2. Clasificar pregunta → ajustar tokens
    3. Inyectar contexto de persona
    4. LLM genera respuesta (streaming)
    5. TTS convierte a audio
    6. Habla mientras genera
    """
    
    # 1. Fact checking (búsqueda web opcional)
    if enable_fact_checking:
        respuesta_factual = fact_checker.get_response(mensaje)
        if respuesta_factual:
            hablar_fn(respuesta_factual)
            return respuesta_factual
    
    # 2. Clasificar pregunta
    categoría = classifier.categorizar_pregunta(mensaje)
    num_tokens = classifier.num_predict_para(categoría)
    length_hint = classifier.length_hint_para(categoría)
    
    # 3. Inyectar contexto
    system_prompt = get_system_prompt(nombre_persona, contexto_brain)
    
    # 4. LLM en streaming
    respuesta_completa = ""
    for chunk in ollama.generate(
        model=TEXT_MODEL,
        prompt=mensaje,
        system=system_prompt,
        num_predict=num_tokens,
        temperature=LLM_TEMPERATURE,
        top_k=LLM_TOP_K,
        stream=True
    ):
        token = chunk.response
        respuesta_completa += token
        
        # 5. TTS streaming (habla mientras genera)
        if len(respuesta_completa) % 10 == 0:  # Cada ~10 tokens
            on_start_speaking()
            hablar_fn(respuesta_completa[-50:])  # Últimas palabras
    
    return respuesta_completa
```

#### Subcomponentes Principales

**`classifier.py`** - Clasificador de preguntas

```python
def categorizar_pregunta(texto: str) -> str:
    """Detecta tipo de pregunta para ajustar respuesta"""
    
    categorías = {
        'GREETING': ['hola', 'bye', 'gracias'],  # 40 tokens
        'OPINION': ['qué piensas', 'te gusta'],  # 80 tokens
        'FACTUAL': ['cuál es', 'cuándo'],        # 100 tokens
        'EXPLAIN': ['explícame', 'cómo'],        # 200 tokens
    }
    
    # Retorna tokens y hint de longitud
    return CATEGORIA, NUM_TOKENS, LENGTH_HINT
```

**`fact_checker.py`** - Verificador de hechos

```python
def get_factual_response(pregunta: str) -> str | None:
    """
    Detecta preguntas factuales y busca respuesta en web
    o en base de datos local si está habilitado
    """
    
    # Detectar tipo de pregunta factual
    if detectar_bandera(pregunta):
        país = extraer_país(pregunta)
        return buscar_bandera(país)
    
    if detectar_capital(pregunta):
        país = extraer_país(pregunta)
        return buscar_capital(país)
    
    return None  # No es factual, usar LLM
```

**System Prompt** - Instrucciones al LLM

```python
def get_system_prompt(nombre: str | None = None, contexto_brain: str = None) -> str:
    prompt = (
        "Eres BMO, un robot asistente amigable creado por Zambrano. "
        "Responde en español de forma natural y útil. "
        "Sé directo pero amigable, máximo 2-3 oraciones."
    )
    
    # Contexto de Hora de Aventura (si está en data/brain_context.txt)
    if contexto_brain:
        prompt += f"\n\nContexto adicional:\n{contexto_brain}"
    
    # Contexto de persona (si está registrada)
    if nombre:
        resumen_persona = memoria.get_resumen(nombre)
        if resumen_persona:
            prompt += f"\n\nContexto de {nombre}:\n{resumen_persona}"
    
    # Correcciones de hechos (si están en config)
    prompt += "\n\nCORRECCIONES IMPORTANTES:\n"
    for hecho, corrección in CORRECCIONES.items():
        prompt += f"- {hecho}: {corrección}\n"
    
    return prompt
```

---

### 3️⃣ MÓDULO: VISION (`src/vision/`)

**Responsabilidad**: Detección y reconocimiento facial

#### Archivo Principal: `vision.py`

```python
class VisionBMO:
    def __init__(self, camera_index: int = 0):
        # Inicializar cámara
        self.cap = cv2.VideoCapture(camera_index)
        
        # Haar Cascade: detector rápido de rostros
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        
        # FaceEmbedder: reconocimiento facial con ONNX
        if Path("data/face_model.onnx").exists():
            self.embedder = FaceEmbedder("data/face_model.onnx")
            self.embeddings_dict = cargar_embeddings_todos()  # De memory.json
        else:
            self.embedder = None
            print("⚠️ Modelo ONNX no encontrado. Modo degradado.")
    
    def procesar_rostro(self, frame) -> tuple[np.ndarray, list]:
        """
        Pipeline de visión:
        1. Convertir a escala de grises
        2. Detectar rostros con Haar Cascade
        3. Para cada rostro: extraer embedding ONNX
        4. Comparar con embeddings guardados
        5. Retornar detecciones
        """
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)  # Mejorar contraste
        
        # Detectar rostros (rápido, CPU)
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1,     # Piramida de escala
            minNeighbors=8,      # Filtro de falsos positivos
            minSize=(60, 60)     # Mínimo tamaño
        )
        
        resultados = []
        for (x, y, w, h) in faces:
            roi_bgr = frame[y:y+h, x:x+w]
            
            if self.embedder is None:
                # Modo degradado: solo detectar
                resultados.append({
                    "id": None,
                    "nombre": "Desconocido",
                    "similitud": -1.0
                })
            else:
                # Extraer embedding (512 dimensiones)
                embedding = self.embedder.extract(roi_bgr)
                
                # Comparar con embeddings guardados
                nombre, similitud = self.embedder.best_match(
                    embedding, 
                    self.embeddings_dict,
                    threshold=0.55  # Umbral de coseno
                )
                
                resultados.append({
                    "id": nombre,
                    "nombre": nombre or "Desconocido",
                    "similitud": similitud
                })
        
        return frame, resultados
```

#### Subcomponente: `embedder.py`

```python
class FaceEmbedder:
    def __init__(self, model_path: str):
        # Cargar modelo ONNX
        self.session = ort.InferenceSession(model_path)
    
    def extract(self, face_image_bgr) -> np.ndarray:
        """
        Extraer embedding de 512 dimensiones
        1. Preprocesar imagen
        2. Pasar por red ONNX
        3. Normalizar L2
        """
        # Preparar entrada
        face_image = cv2.cvtColor(face_image_bgr, cv2.COLOR_BGR2RGB)
        face_image = cv2.resize(face_image, (112, 112))
        face_image = (face_image / 255.0 - 0.5) / 0.5
        face_image = np.transpose(face_image, (2, 0, 1))
        face_image = np.expand_dims(face_image, 0)
        
        # Inferencia
        embedding = self.session.run(None, {"input": face_image.astype(np.float32)})
        embedding = embedding[0][0]
        
        # Normalizar L2
        norm = np.linalg.norm(embedding)
        embedding = embedding / max(norm, 1e-6)
        
        return embedding.astype(np.float32)
    
    def best_match(self, embedding, embeddings_dict, threshold=0.55) -> tuple:
        """
        Encontrar mejor coincidencia usando similitud coseno
        1. Comparar con todos los embeddings guardados
        2. Calcular similitud coseno
        3. Retornar el mejor match si supera threshold
        """
        best_name = None
        best_similarity = 0
        
        for nombre, embeddings_lista in embeddings_dict.items():
            for embedding_guardado in embeddings_lista:
                # Similitud coseno = dot product (vectors normalizados)
                similarity = np.dot(embedding, embedding_guardado)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_name = nombre
        
        if best_similarity >= threshold:
            return best_name, best_similarity
        else:
            return None, best_similarity
```

#### Aprendizaje de Rostro

```python
def aprender_rostro(self, id_nuevo: int, nombre: str, lista_caras: list):
    """
    Cuando alguien dice su nombre, capturamos su rostro
    1. Extraer embeddings de todas las fotos
    2. Promediar para robustez
    3. Guardar en memory.json
    """
    
    embeddings_validos = []
    for cara in lista_caras:
        emb = self.embedder.extract(cara)
        if emb is not None:
            embeddings_validos.append(emb)
    
    # Promediar embeddings
    embedding_promedio = np.mean(embeddings_validos, axis=0)
    
    # Normalizar L2
    norm = np.linalg.norm(embedding_promedio)
    embedding_promedio = embedding_promedio / max(norm, 1e-6)
    
    # Guardar en memory.json
    guardar_persona(id_nuevo, nombre)
    guardar_embeddings_persona(nombre, [embedding_promedio])
    
    # Actualizar caché en memoria
    self.embeddings_dict[nombre] = [embedding_promedio]
```

---

### 4️⃣ MÓDULO: VOICE (`src/voice/`)

**Responsabilidad**: Entrada/salida de audio

#### Archivo Principal: `voice.py`

```python
class VozBMO:
    def __init__(self, mic_device=None):
        # Inicializar componentes de audio
        self.whisper_model = WhisperModel("base", device="cpu")  # STT
        self.piper = PiperTTS()                                   # TTS
        self.vad = silero_vad.load_model()                       # Detectar voz
    
    def escuchar(self) -> str:
        """
        Escuchar del micrófono hasta detectar silencio
        
        Pipeline:
        1. Grabar en bucle
        2. Aplicar VAD (Voice Activity Detection)
        3. Si detecta silencio prolongado → terminar grabación
        4. Transcribo con Whisper
        """
        
        SAMPLE_RATE = 16000
        CHUNK_DURATION = 0.5  # segundos
        SILENCE_DURATION = 1.5  # segundos de silencio
        
        audio_buffer = []
        silence_count = 0
        
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            blocksize=int(SAMPLE_RATE * CHUNK_DURATION)
        ) as stream:
            while True:
                # Leer chunk de audio
                chunk, _ = stream.read(int(SAMPLE_RATE * CHUNK_DURATION))
                
                # VAD: ¿Hay voz?
                if self.vad(chunk, SAMPLE_RATE)['vad'] > 0.5:
                    audio_buffer.append(chunk)
                    silence_count = 0
                else:
                    silence_count += CHUNK_DURATION
                    if silence_count > SILENCE_DURATION:
                        break
        
        # Concatenar y transcribo
        audio_completo = np.concatenate(audio_buffer)
        resultado = self.whisper_model.transcribe(audio_completo)
        texto = resultado["text"]
        
        return texto  # "¿Cuál es la capital de Francia?"
    
    def hablar(self, texto: str):
        """
        Generar audio y reproducir
        
        Pipeline:
        1. Sintetizar texto con Piper TTS
        2. Reproducir por altavoz
        """
        
        # Piper genera audio
        audio_data = self.piper.synthesize(
            texto,
            speaker="es_ES-sharvard-medium"
        )
        
        # Reproducir
        sd.play(audio_data, samplerate=22050)
        sd.wait()  # Esperar a que termine
```

#### Voice Activity Detection (VAD)

```python
# Detectar si hay voz en un chunk de audio
# Silero VAD es modelo pequeño y rápido

def vad_function(audio_chunk, sample_rate):
    """
    Retorna confidence de voz (0-1)
    > 0.5 = hay voz
    < 0.5 = silencio/ruido
    """
    confidence = vad_model(audio_chunk, sample_rate)
    return confidence
```

---

### 5️⃣ MÓDULO: DISPLAY (`src/display/`)

**Responsabilidad**: Interfaz visual y animación de cara

#### Archivo Principal: `display.py`

```python
class DisplayBMO:
    def __init__(self):
        self.estado = Estado.WARMUP
        self.fps_anim = 30
        self.nombre_mostrar = None
    
    def tick(self) -> bool:
        """
        Renderizar un frame (llamado cada ~33ms en RPi5)
        
        Pipeline:
        1. Cargar imagen según estado
        2. Dibujar nombre si está disponible
        3. Mostrar en pantalla
        4. Retornar False si ventana cerrada
        """
        
        frame = self._get_frame_para_estado()
        
        if self.nombre_mostrar:
            cv2.putText(
                frame,
                f"Hola {self.nombre_mostrar}!",
                (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.5,
                (0, 255, 0),
                2
            )
        
        cv2.imshow("BMO", frame)
        
        # Detectar si ventana cerrada
        key = cv2.waitKey(1000 // self.fps_anim)
        if key == ord('q'):  # Q para cerrar
            return False
        
        return True  # Seguir
    
    def set_estado(self, estado: Estado, nombre: str | None = None):
        self.estado = estado
        self.nombre_mostrar = nombre
    
    def _get_frame_para_estado(self) -> np.ndarray:
        """Cargar frame según estado actual"""
        
        if self.estado == Estado.WARMUP:
            return cv2.imread("assets/faces/warmup/1.png")
        elif self.estado == Estado.IDLE:
            return cv2.imread("assets/faces/idle/1.png")
        elif self.estado == Estado.LISTENING:
            # Animar listening (cambiar frame)
            frame_idx = (time.time() * 10) % 5
            return cv2.imread(f"assets/faces/listening/{frame_idx}.png")
        elif self.estado == Estado.THINKING:
            frame_idx = (time.time() * 15) % 8
            return cv2.imread(f"assets/faces/thinking/{frame_idx}.png")
        elif self.estado == Estado.SPEAKING:
            frame_idx = (time.time() * 20) % 12
            return cv2.imread(f"assets/faces/speaking/{frame_idx}.png")
```

#### Estados

```python
class Estado(Enum):
    WARMUP = "warmup"        # Cargando
    IDLE = "idle"            # Esperando
    LISTENING = "listening"  # Grabando
    THINKING = "thinking"    # Procesando
    SPEAKING = "speaking"    # Hablando
```

---

### 6️⃣ MÓDULO: MEMORY (`src/memory/`)

**Responsabilidad**: Persistencia de personas y contexto

#### Archivo Principal: `register.py`

```python
def guardar_persona(id_nuevo: int, nombre: str):
    """Guardar registro de nueva persona en memory.json"""
    
    memoria = load_json("data/memory.json")
    
    if "personas" not in memoria:
        memoria["personas"] = {}
    
    memoria["personas"][str(id_nuevo)] = {
        "id": id_nuevo,
        "nombre": nombre,
        "registrado_en": datetime.now().isoformat(),
        "visto_por_ultima_vez": datetime.now().isoformat(),
        "contador_conversaciones": 0
    }
    
    save_json("data/memory.json", memoria)


def cargar_embeddings_todos() -> dict:
    """Cargar todos los embeddings de personas"""
    
    memoria = load_json("data/memory.json")
    embeddings_dict = {}
    
    if "embeddings" in memoria:
        for nombre, embeddings_lista in memoria["embeddings"].items():
            embeddings_dict[nombre] = [
                np.array(emb, dtype=np.float32)
                for emb in embeddings_lista
            ]
    
    return embeddings_dict  # {"Juan": [array1, array2], ...}
```

#### Estructura de `memory.json`

```json
{
  "personas": {
    "1": {
      "id": 1,
      "nombre": "Juan",
      "registrado_en": "2026-04-30T15:30:00",
      "visto_por_ultima_vez": "2026-04-30T16:45:00",
      "contador_conversaciones": 5
    }
  },
  "embeddings": {
    "Juan": [
      [0.1, 0.2, 0.3, ...],  # 512 valores
      [0.1, 0.2, 0.3, ...]
    ]
  },
  "chat_history": {
    "Juan": [
      {"role": "user", "content": "Hola BMO"},
      {"role": "assistant", "content": "¡Hola Juan!"}
    ]
  }
}
```

#### Memoria Persistente (`persistent_memory.py`)

```python
class PersistentMemory:
    def __init__(self, max_conversations=10):
        self.session_memory = []       # Memoria actual
        self.persistent_file = "data/chat_memory.json"
        self.max_conversations = max_conversations
    
    def agregar_turno(self, role: str, contenido: str):
        """Agregar turno a sesión"""
        self.session_memory.append({
            "role": role,
            "content": contenido,
            "timestamp": datetime.now().isoformat()
        })
        
        # Auto-commit cada 2 turnos
        if len(self.session_memory) % 2 == 0:
            self.guardar()
    
    def guardar(self):
        """Guardar sesión a archivo persistente"""
        memoria = load_json(self.persistent_file)
        
        # Agregar conversación actual
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
```

---

### 7️⃣ MÓDULO: CONFIG (`src/config/`)

**Responsabilidad**: Configuración centralizada y dinámica

#### Archivo Principal: `runtime.py`

```python
from src.config.config_manager import ConfigManager

# Instancia global del gestor de configuración
config_manager = ConfigManager("config.json")

# Cargar parámetros (con fallbacks)
CAMERA_INDEX = config_manager.get("camera_index", default=0)
MIC_DEVICE = config_manager.get("mic_device", default=None)
TEXT_MODEL = config_manager.get("text_model", default="qwen2.5:1.5b")

LLM_TEMPERATURE = config_manager.get("llm_temperature", default=0.75)
LLM_TOP_K = config_manager.get("llm_top_k", default=40)
LLM_TOP_P = config_manager.get("llm_top_p", default=0.85)
LLM_NUM_PREDICT = config_manager.get("llm_num_predict", default=150)
LLM_REPEAT_PENALTY = config_manager.get("llm_repeat_penalty", default=1.15)
LLM_NUM_THREAD = config_manager.get("llm_num_thread", default=4)
LLM_KEEP_ALIVE = config_manager.get("llm_keep_alive", default=-1)

BRAIN_CONTEXT_HOT_RELOAD = config_manager.get("brain_context_hot_reload", default=True)
HEADLESS = config_manager.get("headless", default=False)
```

#### Gestor de Configuración (`config_manager.py`)

```python
class ConfigManager:
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.config = self._load()
        self._start_hot_reload()
    
    def _load(self) -> dict:
        """Cargar config.json con fallbacks automáticos"""
        if Path(self.config_file).exists():
            return load_json(self.config_file)
        else:
            # Crear con valores por defecto
            default_config = {
                "text_model": "qwen2.5:1.5b",
                "llm_temperature": 0.75,
                # ... más valores
            }
            save_json(self.config_file, default_config)
            return default_config
    
    def get(self, key: str, default=None):
        """Obtener valor con fallback"""
        return self.config.get(key, default)
    
    def _start_hot_reload(self):
        """Monitorear cambios en config.json"""
        def watch_file():
            last_mtime = Path(self.config_file).stat().st_mtime
            while True:
                time.sleep(1)
                try:
                    current_mtime = Path(self.config_file).stat().st_mtime
                    if current_mtime != last_mtime:
                        self.config = self._load()
                        logger.info("Config reloaded")
                        last_mtime = current_mtime
                except:
                    pass
        
        threading.Thread(target=watch_file, daemon=True).start()
```

---

## 📊 FLUJO DE EJECUCIÓN

### Flujo Completo: De Entrada a Salida

```
┌─────────────────────────────────────────────────────────────────┐
│ USUARIO SE ACERCA Y HABLA: "¿Cuál es la capital de Francia?"    │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    │                    │
                    ▼                    ▼
            [HILO VISIÓN]          [HILO LÓGICA]
            
1️⃣ DETECCIÓN VISUAL
   Hilo cámara:
   ├─ Lee frame de cámara
   ├─ Haar Cascade detecta rostro
   ├─ ONNX extrae embedding del rostro
   ├─ Compara con embeddings guardados (similitud coseno)
   ├─ Si similitud > 0.55: RECONOCIDO
   └─ Actualiza _nombre_actual = "Juan"
   
                    │
2️⃣ ESCUCHA DE AUDIO
   Hilo lógica:
   ├─ VAD escucha micrófono
   ├─ Detecta cambio de silencio → voz activa
   ├─ Whisper transcribe: "¿Cuál es la capital de Francia?"
   └─ Termina grabación al detectar silencio
   
                    │
3️⃣ PROCESAMIENTO (BRAIN)
   ├─ Clasificador detecta: PREGUNTA FACTUAL
   ├─ Asigna tokens: 100 (respuesta corta)
   ├─ Obtiene contexto de "Juan" de memory.json
   ├─ System prompt inyecta: personalidad + contexto + correcciones
   ├─ Fact checker: ¿es pregunta sobre capital?
   │  └─ SÍ: busca en web o base de datos
   │  └─ Retorna: "París"
   └─ O LLM (Ollama Qwen) genera respuesta completa
   
                    │
4️⃣ RESPUESTA Y AUDIO
   ├─ Respuesta: "La capital de Francia es París"
   ├─ Piper TTS convierte a audio
   ├─ Reproducir por altavoz (streaming)
   └─ Mientras habla:
       ├─ Display SPEAKING: cara animada hablando
       └─ Visualización de ondas de sonido
   
                    │
5️⃣ ACTUALIZACIÓN DE MEMORIA
   ├─ Guardar turno en chat_memory.json
   ├─ Actualizar último visto para Juan
   ├─ Incrementar contador de conversaciones
   └─ Persistencia automática

                    │
6️⃣ VUELTA AL IDLE
   ├─ Display IDLE: cara esperando
   ├─ Siguiente turno cada ~0.5 segundos
   └─ Volver a escuchar...
```

### Flujo Específico: Registro de Persona Nueva

```
USUARIO: "Hola BMO, me llamo Ana"
         │
         ▼
    [HILO LÓGICA]
         │
    1. Whisper transcribe
    2. Detectar nombre: "Ana"
    3. Verificar si ya existe
         │
         NO EXISTE
         │
         ▼
    4. REGISTRAR PERSONA
       ├─ Mostrar: Estado SPEAKING
       ├─ "Hola Ana! Voy a recordar tu cara"
       ├─ Cambiar a Estado LISTENING
       ├─ Bucle 25 veces:
       │  ├─ Leer frame de cámara
       │  ├─ Haar Cascade detecta rostro
       │  ├─ Guardar en lista_caras
       │  └─ Esperar 40ms (reducir redundancia)
       ├─ Para cada cara guardada:
       │  ├─ ONNX extrae embedding (512 dims)
       │  ├─ Agregar a lista embeddings_validos
       ├─ Promediar embeddings
       ├─ Normalizar L2
       ├─ Guardar en memory.json:
       │  ├─ ID único: 1
       │  ├─ Nombre: "Ana"
       │  └─ Embeddings promediados
       ├─ Mostrar: "Listo Ana! Ya te tengo en mi memoria"
       └─ Actualizar _ultimo_saludo[Ana] = ahora
         │
         ▼
    5. Próximas veces que Ana se acerque:
       ├─ Haar detecta rostro
       ├─ ONNX extrae embedding
       ├─ best_match() compara con memoria
       └─ Encuentra a Ana (similitud > 0.55)
```

---

## 🐍 PROGRAMACIÓN EN PYTHON PARA BMO

### Para Programadores de Otros Lenguajes

Si vienes de **JavaScript, C#, Java**, aquí está el puente:

#### Tabla de Conversión

| Concepto | JS/TS | C# | Java | Python (BMO) |
|----------|-------|----|----|--------------|
| **Null** | `null`, `undefined` | `null` | `null` | `None` |
| **Verdadero/Falso** | `true`/`false` | `true`/`false` | `true`/`false` | `True`/`False` (mayúscula) |
| **String con vars** | `` `Hola ${name}` `` | `$"Hola {name}"` | `"Hola " + name` | `f"Hola {name}"` |
| **Array/Lista** | `[1, 2, 3]` | `List<int>` | `List<Integer>` | `[1, 2, 3]` |
| **Diccionario/Objeto** | `{name: "Ana"}` | `Dictionary<K,V>` | `HashMap<K,V>` | `{"name": "Ana"}` |
| **Función** | `function f() {}` | `void F()` | `void f()` | `def f():` |
| **Clase** | `class C {}` | `class C {}` | `class C {}` | `class C:` |
| **This** | `this` | `this` | `this` | `self` (explícito) |
| **Herencia** | `extends` | `:` | `extends` | `(Parent)` |
| **For loop** | `for (let i = 0; i < 5; i++)` | `for (int i = 0; i < 5; i++)` | `for (int i = 0; i < 5; i++)` | `for i in range(5):` |
| **For-Each** | `for (x of arr)` | `foreach (var x in arr)` | `for (var x : arr)` | `for x in arr:` |
| **Try-Catch** | `try {} catch (e) {}` | `try {} catch (Exception e) {}` | `try {} catch (Exception e) {}` | `try: except Exception as e:` |

#### Sintaxis Común en BMO

```python
# 1. Importar módulos
from src.brain.brain import responder_con_tts
from src.vision.vision import VisionBMO

# 2. Type hints (opcional pero recomendado)
def suma(a: int, b: int) -> int:
    return a + b

def obtener_persona(nombre: str | None = None) -> dict:
    """Docstring: qué hace la función"""
    pass

# 3. Diccionarios (como objetos JSON)
persona = {
    "id": 1,
    "nombre": "Juan",
    "datos": {
        "edad": 30
    }
}
print(persona["nombre"])  # "Juan"

# 4. Listas
rostros = [face1, face2, face3]
for rostro in rostros:
    embedding = extract(rostro)

# 5. List comprehension (genial para procesar datos)
cuadrados = [x * x for x in range(10)]
# → [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]

# 6. Clases
class VisionBMO:
    def __init__(self, camera_index: int = 0):
        self.cap = cv2.VideoCapture(camera_index)
    
    def procesar(self, frame) -> list:
        """El self siempre es explícito"""
        rostros = self.face_cascade.detectMultiScale(frame)
        return rostros

# 7. Context managers (importante para archivos y threads)
with open("data/memory.json", "r") as f:
    datos = json.load(f)  # Archivo cierra automáticamente

with threading.Lock() as lock:
    self._nombre_actual = "Juan"  # Thread-safe

# 8. Exceptions
try:
    embedding = self.embedder.extract(face)
except AttributeError as e:
    print(f"Error: {e}")
finally:
    print("Siempre se ejecuta")
```

#### Debugging en BMO

```python
# Logging (recomendado en lugar de print)
import logging
log = logging.getLogger("BMO")

log.info("BMO iniciado")           # INFO
log.warning("Recurso bajo")        # WARNING
log.error("Error crítico: %s", e)  # ERROR

# Debugging con breakpoints (si usas IDE)
import pdb
pdb.set_trace()  # Se pausa aquí

# O usar print para debugging rápido
print(f"DEBUG: nombre_actual = {self._nombre_actual}")
```

#### Threading (para entender los 3 hilos)

```python
import threading

# Crear hilo daemon (se detiene al cerrar proceso)
def mi_funcion():
    while True:
        print("Hilo ejecutando")
        time.sleep(1)

hilo = threading.Thread(target=mi_funcion, daemon=True)
hilo.start()

# Lock para evitar condiciones de carrera
lock = threading.Lock()

with lock:  # Adquirir lock
    self._nombre_actual = "Juan"
# Lock se libera automáticamente al salir

```

---

## ⚙️ PARÁMETROS Y OPTIMIZACIÓN

### Parámetros del LLM (Explicación Completa)

Todos en `src/config/runtime.py`. Se pueden cambiar en `config.json` **sin reiniciar**.

#### 1. **Temperature** (Creatividad vs Determinismo)

```json
"llm_temperature": 0.75
```

**Rango**: 0.0 → 2.0

- **0.0**: Siempre elige palabra más probable → robótico, repetitivo
- **0.3**: Muy conservador → seguro pero aburrido
- **0.5**: Equilibrio → coherente, pocas alucinaciones ← RECOMENDADO para tareas serias
- **0.75**: Más variedad natural → equilibrio bueno ← BMO usa esto
- **1.0**: Bastante creativo → puede inventar
- **1.5+**: Muy creativo → pierde coherencia

**Analogía**: Es el "nivel de confianza" al hablar. Con 0.0 BMO siempre diría lo mismo. Con 1.5 inventaría datos.

**En BMO**: Usamos 0.75 porque queremos respuestas naturales pero confiables.

#### 2. **Top-K** (Vocabulario Disponible)

```json
"llm_top_k": 40
```

**Rango**: 1 → 100

En cada paso, el modelo solo considera las K palabras más probables y descarta el resto:

- **5**: Muy limitado → solo palabras obvias
- **10**: Conservador → diccionario pequeño
- **40**: Estándar → buen balance ← BMO usa esto
- **60**: Variado → más opciones
- **100**: Muy variado → puede sonar extraño

**Ejemplo**:
```
Pregunta: "¿Cuál es la capital de..."
Top-1: "Francia" (prob 0.3)
Top-2: "España" (prob 0.25)
Top-5: "Italia" (prob 0.1)

Con top_k=5: Puede elegir entre Francia, España, Italia
Con top_k=1: SIEMPRE Francia
```

#### 3. **Top-P** (Distribución Acumulada)

```json
"llm_top_p": 0.85
```

**Rango**: 0.0 → 1.0

Complementa top_k: usa palabras hasta que las probabilidades acumuladas sumen P.

- **0.8**: Conservador → pocas opciones
- **0.85**: Equilibrio ← BMO usa esto
- **0.9**: Estándar
- **0.95**: Variado → más opciones

**Ejemplo**:
```
Top-1: "Francia" (0.3)
Top-2: "España" (0.25) → acumulado 0.55
Top-3: "Italia" (0.2) → acumulado 0.75
Top-4: "Alemania" (0.1) → acumulado 0.85
Top-5: "Belgica" (0.05) → acumulado 0.9

Con top_p=0.85: Usa Top-1 a Top-4
Con top_p=0.9: Usa Top-1 a Top-5
```

#### 4. **Num-Predict** (Longitud de Respuesta)

```json
"llm_num_predict": 150
```

**Rango**: 10 → 500

Máximo de tokens (≈ palabras o fragmentos) por respuesta.

**El clasificador sobrescribe este valor** según el tipo de pregunta:

| Tipo | Tokens | Ejemplo |
|------|--------|---------|
| GREETING | 40 | "Hola, ¿cómo estás?" |
| OPINION | 80 | "Creo que... porque..." |
| FACTUAL | 100 | "La capital de Francia es París" |
| EXPLAIN | 200 | "Explicación detallada en 3 puntos..." |

**Latencia en RPi5** (~0.15s por token):
- 40 tokens → 6s total
- 100 tokens → 15s total
- 200 tokens → 30s total

#### 5. **Repeat-Penalty** (Evitar Repetición)

```json
"llm_repeat_penalty": 1.15
```

**Rango**: 1.0 → 2.0

Penaliza que el modelo repita palabras que ya usó:

- **1.0**: Sin penalización → puede repetirse
- **1.15**: Estándar ← BMO usa esto
- **1.3**: Agresivo → evita repetición a costa de naturalidad

**Ejemplo**:
```
Sin penalty:
"Los colorados colorados de Colorado están en Colorado muy colorados"

Con penalty=1.15:
"Los colorados de Colorado están en las montañas muy rojo"
```

#### 6. **Num-Thread** (CPUs Usados)

```json
"llm_num_thread": 4
```

**RPi5**: 4 núcleos

Cuántos núcleos usa Ollama:
- **1**: Lento pero deja recursos (no recomendado)
- **2**: Medio, deja recursos para audio y visión
- **4**: Máximo rendimiento ← BMO usa esto en RPi5 8GB
- **8+**: En máquinas más potentes

#### 7. **Keep-Alive** (Mantener Modelo en RAM)

```json
"llm_keep_alive": -1
```

**Valores**:
- **-1**: Nunca descargar (siempre en RAM) ← BMO usa esto
- **0**: Descargar inmediatamente
- **300**: Descargar tras 5 minutos sin uso

**Trade-off**:
- `-1`: Inicio rápido, consume RAM siempre
- `300`: Ahorra RAM si BMO se queda sin usar
- `0`: Para pruebas, muy lento

---

### Clasificador de Preguntas

**Archivo**: `src/brain/classifier.py`

El clasificador automáticamente ajusta los parámetros según el tipo de pregunta:

```python
PATRONES_Y_CONFIGURACION = {
    "GREETING": {
        "palabras_clave": ["hola", "bye", "gracias", "dale"],
        "num_tokens": 40,
        "length_hint": "Responde en UNA sola oración corta.",
        "ejemplo": "Hola → 'Hola! ¿Cómo estás?'"
    },
    "OPINION": {
        "palabras_clave": ["qué piensas", "te gusta", "qué opinas"],
        "num_tokens": 80,
        "length_hint": "Expresa una opinión en 2 oraciones.",
        "ejemplo": "¿Te gusta la pizza? → '¡Claro! La pizza es deliciosa...'"
    },
    "FACTUAL": {
        "palabras_clave": ["cuál es", "cuándo", "dónde", "quién es"],
        "num_tokens": 100,
        "length_hint": "Responde con un dato específico en 2 oraciones.",
        "ejemplo": "¿Capital de Francia? → 'París'"
    },
    "EXPLAIN": {
        "palabras_clave": ["explícame", "cómo funciona", "por qué"],
        "num_tokens": 200,
        "length_hint": "Explica en 3-4 oraciones con detalles.",
        "ejemplo": "¿Cómo funciona...? → 'Primero... Luego... Por eso...'"
    },
}
```

**Cómo usarlo**:

```python
from src.brain.classifier import num_predict_para, length_hint_para

# Automático
categoria = classifier.categorizar_pregunta("¿Cuál es la capital de Francia?")
num_tokens = num_predict_para(categoria)  # → 100
hint = length_hint_para(categoria)        # → "Responde con un dato..."
```

---

## 📚 CASOS DE USO Y EJEMPLOS

### Caso 1: Reconocimiento Facial Automático

**Escenario**: Una persona se acerca a BMO

```
Usuario: Se acerca a la cámara

🎥 Hilo Visión:
├─ Lee 60 frames (2 segundos a 30 FPS)
├─ Haar Cascade detecta rostro en frame 15
├─ ONNX extrae embedding: [0.1, 0.2, ..., 0.5] (512 valores)
├─ Compara con embeddings guardados:
│  ├─ "Juan": similitud = 0.78 ✅ (> 0.55 threshold)
│  ├─ "Ana": similitud = 0.42 ❌
│  └─ Mejor match: "Juan"
├─ Actualiza: _nombre_actual = "Juan"
└─ Log: "[VISION] Cara reconocida: Juan (sim 0.78)"

🧠 Hilo Lógica (detecta cambio):
├─ Verifica: ¿Pasó más de 60 segundos desde último saludo a Juan?
│  ├─ SÍ → Saluda
│  └─ NO → Continúa escuchando
├─ Si saluda:
│  ├─ Display: SPEAKING
│  ├─ Hablar: "¡Hola Juan! Bienvenido"
│  ├─ _ultimo_saludo["Juan"] = ahora
│  └─ Display: IDLE
└─ Estado: Esperando input
```

### Caso 2: Registro de Persona Nueva

**Escenario**: Alguien nuevo dice su nombre

```
Usuario: "Hola, me llamo María"

📝 Transcripción:
├─ VAD detecta: VINO HABLA
├─ Whisper STT: "Hola, me llamo María"
└─ Brain classifica: PERSONA_REGISTRO

🔧 Procesamiento:
├─ detectar_nombre("Hola, me llamo María") → "María"
├─ ¿Existe "María"?
│  ├─ SÍ: Log "María ya está registrada"
│  └─ NO: Iniciar registro
└─ Registrar persona:
   ├─ Display: SPEAKING
   ├─ Hablar: "Hola María! Voy a recordar tu cara"
   ├─ Cambiar a: LISTENING
   ├─ Capturar 25 fotos:
   │  ├─ Foto 1: detecta rostro en frame
   │  ├─ Foto 2: detecta rostro en frame
   │  └─ ... (cada 40ms)
   ├─ Para cada foto:
   │  ├─ ONNX extrae embedding
   │  ├─ Guardar embedding
   ├─ Promediar embeddings
   ├─ Guardar en memory.json:
   │  {
   │    "personas": {"2": {"id": 2, "nombre": "María"}},
   │    "embeddings": {"María": [[0.1, 0.2, ..., 0.5]]}
   │  }
   ├─ Display: SPEAKING
   ├─ Hablar: "¡Listo María! Ya te tengo en mi memoria"
   └─ Display: IDLE

✅ Resultado:
   Próximas veces que María se acerque:
   ├─ ONNX reconoce: similitud = 0.76
   ├─ BMO saluda: "¡Hola María!"
   └─ Contexto inyectado si existe historial
```

### Caso 3: Pregunta Factual (Capital)

**Escenario**: Pregunta sobre una capital

```
Usuario: "¿Cuál es la capital de Italia?"

🎤 Escucha:
├─ VAD: detecta voz
├─ Whisper: "¿Cuál es la capital de Italia?"
└─ Clasificador: PREGUNTA_FACTUAL → 100 tokens

🧠 Procesamiento Brain:
├─ fact_checker.detectar_capital(mensaje)?
│  └─ SÍ → detectar_país("Italia") → buscar_capital("Italia")
│     └─ Resultado: "Roma"
│  └─ NO → Usar LLM
├─ Si fact_checker activado:
│  ├─ Retorna: "La capital de Italia es Roma"
│  └─ Sin llamar a LLM (más rápido)
└─ Si no está activado:
   ├─ LLM Qwen genera:
   │  ├─ System: "Eres BMO... contexto..."
   │  ├─ Prompt: "¿Cuál es la capital de Italia?"
   │  ├─ Streaming: "La" → "capital" → "de" → "Italia" → "es" → "Roma"
   │  └─ Respuesta: "La capital de Italia es Roma"
   ├─ Piper TTS: convierte a audio
   └─ Reproducir: "La capital de Italia es Roma"

🔊 Salida:
├─ Display: SPEAKING (cara animada hablando)
├─ Audio: Altavoz reproduce "La capital de Italia es Roma"
├─ Guardar en memory.json chat_history
└─ Display: IDLE (vuelta a esperar)

⏱️ Latencia Total:
├─ Escucha: ~1s (VAD + Whisper)
├─ Processing: ~0.5s (clasificador + búsqueda)
├─ TTS: ~2s (síntesis + reproducción)
└─ Total: ~3.5 segundos ✅
```

### Caso 4: Pregunta Conversacional

**Escenario**: Pregunta abierta

```
Usuario: "¿Cómo está el clima hoy?"

🎤 Escucha:
├─ VAD: detecta voz
├─ Whisper: "¿Cómo está el clima hoy?"
└─ Clasificador: PREGUNTA_ABIERTA → 200 tokens

🧠 Procesamiento Brain:
├─ fact_checker: ¿Es factual?
│  └─ NO (no está en patrones de hechos específicos)
├─ Usar LLM:
│  ├─ System prompt completo (si hay contexto)
│  ├─ Prompt: "¿Cómo está el clima hoy?"
│  ├─ Streaming tokens:
│  │  ├─ "No"
│  │  ├─ "tengo"
│  │  ├─ "acceso"
│  │  ├─ "al"
│  │  ├─ "clima"
│  │  ├─ "en"
│  │  ├─ "tiempo"
│  │  ├─ "real"
│  │  ├─ ","
│  │  ├─ "pero"
│  │  ├─ "puedes"
│  │  ├─ "buscar"
│  │  ├─ "en"
│  │  ├─ "internet"
│  │  └─ "."
│  └─ Respuesta completa: "No tengo acceso al clima en tiempo real, pero puedes buscar en internet."
├─ Piper TTS comienza mientras genera:
│  ├─ Al token 5: comienza síntesis de "No tengo acceso..."
│  ├─ Al token 10: comienza reproducción de primeros palabras
│  └─ Usuario escucha mientras continúa generando
└─ Guardar en memory.json

🔊 Salida:
├─ Display: THINKING (cara pensando)
├─ Display: SPEAKING (apenas comienza a hablar)
├─ Audio: Streaming (habla mientras genera)
└─ Latencia: ~6-8 segundos

⏱️ Timeline:
├─ t=0s: Usuario termina de hablar
├─ t=1s: Whisper termina transcripción
├─ t=2s: LLM comienza a generar
├─ t=3s: Primeros tokens generados, TTS comienza
├─ t=4s: Usuario escucha: "No tengo acceso..."
├─ t=8s: Respuesta completa reproducida
└─ Total: 8 segundos (pero usuario escucha desde segundo 4)
```

---

## 🐛 TROUBLESHOOTING

### Problema 1: La Cámara No se Detecta

**Síntoma**:
```
RuntimeError: No se pudo abrir la cámara 0
```

**Causas Posibles**:
1. Cámara no conectada o deshabilitada
2. Índice de cámara incorrecto
3. Permisos del sistema

**Soluciones**:

```bash
# 1. Ver dispositivos de cámara disponibles
python scripts/list_audio.py  # También lista cámaras

# 2. Cambiar índice en config.json
{
  "camera_index": 1  # Cambiar a 1, 2, etc.
}

# 3. Ver permisos (Linux)
ls -la /dev/video*

# 4. Permitir acceso a cámara
sudo usermod -a -G video $(whoami)

# 5. Ejecutar con permisos
sudo python -m src.main
```

**Fix Implementado** (ya aplicado):
```python
# En main.py - ahora BMO arranca sin cámara
try:
    self.vision = VisionBMO(camera_index=CAMERA_INDEX)
except RuntimeError as e:
    log.warning("⚠️ Cámara no disponible: %s", e)
    self.vision = None  # Modo degradado
```

### Problema 2: Micrófono No Funciona

**Síntoma**:
```
RuntimeError: No se pudo abrir dispositivo de audio
```

**Soluciones**:

```bash
# 1. Listar dispositivos de audio
python scripts/list_mics.py

# 2. Probar micrófono específico
python scripts/test_mics.py

# 3. Configurar en config.json
{
  "mic_device": 3  # Índice del micrófono
}

# 4. O dejar en auto-detección
{
  "mic_device": null  # Auto-detecta el mejor
}
```

### Problema 3: Respuestas Muy Lentas

**Síntoma**: BMO tarda >15 segundos en responder

**Causas**:
1. Modelo muy grande o LLM no optimizado
2. Número de tokens demasiado alto
3. RPi5 sobrecargada

**Soluciones**:

```bash
# 1. Ver qué modelo está usando
python scripts/config_tool.py --show

# 2. Cambiar a modelo 1.5B (más rápido)
{
  "text_model": "qwen2.5:1.5b",
  "llm_temperature": 0.75,
  "llm_num_predict": 100  # Reducir de 150
}

# 3. Monitorear recursos
python scripts/monitor_resources.py

# 4. Si sigue lento:
{
  "llm_num_thread": 2,  # Usar menos CPUs
  "llm_keep_alive": 300  # Descargar modelo si no se usa 5min
}
```

### Problema 4: Respuestas Incorrectas (Banderas, Capitales)

**Síntoma**: BMO da información falsa

```
Usuario: "¿Colores de la bandera de Colombia?"
BMO: "Azul arriba, rojo medio, amarillo abajo" ❌
```

**Soluciones**:

```bash
# 1. Verificar system prompt
python scripts/test_system_prompt.py

# 2. Habilitar fact_checker (búsqueda web)
{
  "enable_fact_checking": true
}

# 3. O agregar correcciones en config
# En data/brain_context.txt agregar:
"""
CORRECCIONES IMPORTANTES:
- Bandera Colombia: AMARILLO arriba, AZUL medio, ROJO abajo
- Bandera México: VERDE izquierda, BLANCO medio, ROJO derecha
"""

# 4. Verificar que se reloadea
{
  "brain_context_hot_reload": true
}

# 5. Upgrade de modelo (más inteligencia)
{
  "text_model": "qwen2.5:3b"
}
```

### Problema 5: BMO No Reconoce Rostros

**Síntoma**: Siempre ve "Desconocido"

**Causas**:
1. Modelo ONNX no descargado
2. Iluminación inadecuada
3. Persona muy lejos o de lado

**Soluciones**:

```bash
# 1. Descargar modelo ONNX
python scripts/download_face_model.py

# 2. Verificar que existe
ls -la data/face_model.onnx

# 3. Probar visión
python scripts/test_audio.py  # Muestra caras detectadas

# 4. Registrar de nuevo (mejor iluminación)
# El usuario debe acercarse a la cámara a ~60cm
# y mirar directamente a la cámara

# 5. Cambiar threshold de similitud
# En vision.py, aumentar threshold
# best_match(embedding, embeddings_dict, threshold=0.55)
# Cambiar a 0.50 (más sensible) o 0.60 (más estricto)
```

### Problema 6: Audio Truncado o Con Ruido

**Síntoma**: Respuestas cortadas o distorsionadas

**Soluciones**:

```bash
# 1. Configurar audio properly
python scripts/config_tool.py --test-audio

# 2. En config.json:
{
  "llm_repeat_penalty": 1.1,  # Evitar repetición
  "llm_temperature": 0.75,     # Estabilidad
  "llm_num_predict": 150       # Respuestas completas
}

# 3. Probar con Piper TTS directamente
python -c "
from src.voice.voice import VozBMO
voz = VozBMO()
voz.hablar('Prueba de audio')
"
```

---

## 🚀 EXTENSIÓN Y PERSONALIZACIÓN

### Personalización 1: Cambiar Nombre

**Archivo**: `src/brain/brain.py`

```python
def get_system_prompt(...) -> str:
    prompt = (
        "Eres BMO, un robot asistente amigable creado por Zambrano. "  # ← Cambiar aquí
        "Responde en español de forma natural y útil. "
        # ...
    )
```

Cambiar a:
```python
"Eres NOMBRE_NUEVO, un robot asistente amigable creado por AUTOR. "
```

### Personalización 2: Agregar Respuestas Predefinidas

**Archivo**: `src/brain/fallback_handler.py` o `src/brain/brain.py`

```python
RESPUESTAS_PREDEFINIDAS = {
    "¿quién eres": "Soy BMO, un robot asistente creado por Zambrano.",
    "¿qué hora es": lambda: f"Son las {datetime.now().strftime('%H:%M')}",
    "cuéntame un chiste": "¿Por qué los programadores prefieren los números pares? Porque los impares dan error.",
}

# En responder_con_tts:
for patrón, respuesta in RESPUESTAS_PREDEFINIDAS.items():
    if patrón.lower() in mensaje.lower():
        respuesta_final = respuesta() if callable(respuesta) else respuesta
        hablar_fn(respuesta_final)
        return respuesta_final
```

### Personalización 3: Agregar Contexto de Hora de Aventura

**Archivo**: `data/brain_context.txt`

Este archivo se recarga automáticamente (si `brain_context_hot_reload` es true).

```txt
# Información de Hora de Aventura

BMO es un robot de videojuegos que es personaje importante en la serie.
- BMO es amigable y curioso
- Fin y Jake son sus mejores amigos
- Viven en la Casa del Árbol
- Marceline es la Reina del Vampiro
- El Rey Helado es el villano principal
- El País de Dulces es un reino mágico
- La Guerra del Chamán pasó hace años
```

Automáticamente se inyectará en el system prompt.

### Personalización 4: Agregar Nuevas Categorías de Preguntas

**Archivo**: `src/brain/classifier.py`

```python
CATEGORIAS_PREGUNTAS = {
    # ... categorías existentes ...
    "CHISTE": {
        "palabras_clave": ["chiste", "bromea", "hazme reír"],
        "num_tokens": 60,
        "length_hint": "Cuéntame un chiste corto y divertido",
        "ejemplo": "¿Un chiste? → 'Aquí va: ...'"
    }
}

def categorizar_pregunta(texto: str) -> str:
    for categoria, config in CATEGORIAS_PREGUNTAS.items():
        for palabra in config["palabras_clave"]:
            if palabra.lower() in texto.lower():
                return categoria
    return "GENERAL"
```

### Personalización 5: Agregar Nuevo Modelo LLM

**Archivo**: `src/config/runtime.py` o `config.json`

```json
{
  "text_model": "qwen2.5:7b"  // Cambiar de modelo
}
```

**O instalar nuevo modelo**:
```bash
ollama pull llama2
ollama pull mistral
ollama pull neural-chat

# Cambiar en config.json
{"text_model": "llama2"}
```

### Personalización 6: Agregar Nuevo Idioma

**Archivo**: `src/voice/voice.py`

```python
# Cambiar modelo de Whisper
self.whisper_model = WhisperModel("base", device="cpu")  # "base" habla español

# Cambiar TTS
self.piper.synthesize(
    texto,
    speaker="es_ES-sharvard-medium"  # Español ← Cambiar aquí
)

# Disponibles:
# "es_ES-sharvard-medium" - Español España
# "es_MX-jreycar-medium" - Español México
# "en_US-kusal-medium" - Inglés
# "fr_FR-siwis-medium" - Francés
```

### Personalización 7: Agregar Dispositivos de Hardware

```python
# En src/config/runtime.py

# Cámara
CAMERA_INDEX = 0  # Cambiar a 1, 2 si hay múltiples cámaras

# Micrófono
MIC_DEVICE = None  # Auto-detecta; o 3, 4, etc.

# Altavoz
OUTPUT_DEVICE = None  # Auto-detecta; o 2, 5, etc.

# Verificar dispositivos
python scripts/list_audio.py
python scripts/list_mics.py
```

### Personalización 8: Agregar Base de Datos de Hechos

**Archivo**: `src/brain/fact_database.py`

```python
FACTS_DATABASE = {
    # Banderas
    "bandera_colombia": "amarillo arriba, azul medio, rojo abajo",
    "bandera_mexico": "verde izquierda, blanco medio, rojo derecha",
    
    # Capitales
    "capital_colombia": "Bogotá",
    "capital_mexico": "Ciudad de México",
    
    # Población
    "poblacion_colombia": "aproximadamente 52 millones de personas",
    
    # Hechos históricos
    "independencia_colombia": "1810",
    "independencia_mexico": "1810",
}

def get_fact(key: str) -> str | None:
    return FACTS_DATABASE.get(key)

# En brain.py
def responder_con_tts(...):
    fact = fact_database.get_fact(detectar_hecho(mensaje))
    if fact:
        hablar_fn(fact)
        return fact
    # ... resto del pipeline
```

### Personalización 9: Agregar Nuevo Hilo

Si necesitas un hilo adicional (ej: sensor externo):

```python
# En main.py

def __init__(self):
    # ... componentes existentes ...
    threading.Thread(target=self._loop_sensor_externo, daemon=True).start()

def _loop_sensor_externo(self):
    """Leer un sensor externo (temperatura, luminosidad, etc.)"""
    while self._running:
        valor = leer_sensor()
        if valor > threshold:
            # Hacer algo
            self.display.set_estado(Estado.SPEAKING)
            self.voz.hablar("¡Alerta! Valor alto del sensor")
        time.sleep(1.0)
```

### Personalización 10: Agregar Persistencia Extendida

**Guardar en base de datos en lugar de JSON**:

```python
# Instalar SQLite
# En src/memory/persistence.py

import sqlite3

class MemoriaSQL:
    def __init__(self):
        self.conn = sqlite3.connect("data/bmo.db")
        self.cursor = self.conn.cursor()
        self._crear_tablas()
    
    def _crear_tablas(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS personas (
                id INTEGER PRIMARY KEY,
                nombre TEXT UNIQUE,
                embedding BLOB,
                fecha_registro TIMESTAMP
            )
        """)
        self.conn.commit()
    
    def guardar_embedding(self, nombre: str, embedding: bytes):
        self.cursor.execute("""
            INSERT OR REPLACE INTO personas (nombre, embedding, fecha_registro)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (nombre, embedding))
        self.conn.commit()
```

---

## 📖 RECURSOS Y REFERENCIAS

### Documentación Oficial

| Herramienta | Documentación |
|-----------|---------------|
| Faster-Whisper | https://github.com/guillaumekln/faster-whisper |
| Piper TTS | https://github.com/rhasspy/piper |
| Ollama | https://ollama.ai |
| OpenCV | https://docs.opencv.org |
| ONNX Runtime | https://onnxruntime.ai |

### Archivos de Referencia en el Proyecto

```
docs/
├── GUIA_BMO_DEFINITIVA.md (Esta guía)
├── ANALISIS_CONOCIMIENTO_GENERAL_BMO.md (Conocimiento del modelo)
├── ANALISIS_EXHAUSTIVO_FALLOS_BMO.md (Fallos documentados)
├── ANALISIS_FORENSE_BMO.md (Análisis de problemas)
├── GUIA_APRENDIZAJE_PYTHON_Y_BMO.md (Python para BMO)
├── MEJORAS_PERSISTENCIA_BMO.md (Sistema persistente)
├── SOLUCION_BANDERA_COLOMBIA.md (Solución de hechos)
├── SOLUCION_FINAL_CONOCIMIENTO_FACTUAL.md (Sistema híbrido)
├── SOLUCION_MINIMALISTA_OFFLINE.md (Correcciones mínimas)
└── SOLUCION_OFFLINE_MODELO_MEJORADO.md (Upgrade de modelo)
```

### Scripts Útiles

```bash
# Diagnóstico completo
python scripts/comprehensive_general_test.py

# Probar modelo
python scripts/test_model_performance.py

# Configuración interactiva
python scripts/config_tool.py --interactive

# Ver estadísticas
python scripts/config_tool.py --memory-stats

# Descargar modelos
python scripts/download_face_model.py
python scripts/download_voice.py

# Listar dispositivos
python scripts/list_audio.py
python scripts/list_mics.py
python scripts/test_audio.py
python scripts/test_mics.py
```

---

## 🎯 RESUMEN Y PRÓXIMOS PASOS

### Lo que Aprendiste

✅ **Arquitectura**: BMO es un sistema multimodal con 3 hilos paralelos
✅ **Módulos**: Cada módulo tiene responsabilidad clara (VISION, VOICE, BRAIN, etc.)
✅ **Flujo**: De entrada (cámara/micrófono) → procesamiento (LLM) → salida (audio/video)
✅ **Configuración**: Totalmente dinámica y sin reinicio
✅ **Extensibilidad**: Fácil agregar características sin quebrar lo existente

### Próximos Pasos Recomendados

1. **Prueba Básica** (30 min):
   ```bash
   python -m src.main
   # Habla con BMO, registra tu cara, etc.
   ```

2. **Personalización** (1-2 horas):
   - Cambiar nombre en system prompt
   - Agregar contexto en brain_context.txt
   - Configurar dispositivos en config.json

3. **Optimización** (2-4 horas):
   - Ajustar parámetros de LLM para tu hardware
   - Probar diferentes modelos (1.5B, 3B, etc.)
   - Monitorear rendimiento

4. **Extensión** (4+ horas):
   - Agregar nuevas categorías de preguntas
   - Integrar nuevos sensores
   - Agregar base de datos de hechos
   - Crear nuevos hilos para funcionalidades

### Debugging con Logs

```python
import logging

# Ver logs en tiempo real
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("BMO")

log.info("Información: %s", variable)
log.warning("Advertencia: %s", variable)
log.error("Error crítico: %s", variable)
```

### Contacto y Ayuda

- **Reportar bugs**: Crear issue en GitHub
- **Documentación**: Ver archivos en `docs/`
- **Scripts de diagnóstico**: `python scripts/config_tool.py`
- **Tests**: `python scripts/comprehensive_general_test.py`

---

## 📄 CHANGELOG

**v2.0** (30/04/2026):
- ✅ Guía completa integrada
- ✅ Soporte para mode degradado sin cámara
- ✅ Sistema híbrido con fact_checker
- ✅ Hot-reload de configuración
- ✅ Memoria persistente mejorada

**v1.5** (25/04/2026):
- ✅ Análisis de fallos
- ✅ Optimizaciones de RPi5

**v1.0** (20/04/2026):
- ✅ Release inicial

---

**FIN DE LA GUÍA DEFINITIVA**

*Documento creado para aprender, entender y extender BMO completamente*  
*Guía adaptada a la estructura real del proyecto*  
*Enfocada en comprensión interna y modificación futura*

**¡Feliz codificación! 🚀🤖**

