# 🏗️ ARQUITECTURA DE BMO - Diagramas y Conexiones

**Documento**: Guía de arquitectura, flujos de datos, y diagramas  
**Fecha**: 30/04/2026  
**Versión**: 1.0

---

## 📌 ÍNDICE

1. [Arquitectura General](#arquitectura-general)
2. [Flujos de Datos](#flujos-de-datos)
3. [Threading y Sincronización](#threading-y-sincronización)
4. [Módulos y Dependencias](#módulos-y-dependencias)
5. [Secuencias Temporales](#secuencias-temporales)
6. [Estados y Transiciones](#estados-y-transiciones)
7. [Estructuras de Datos](#estructuras-de-datos)

---

## 🏛️ ARQUITECTURA GENERAL

### Vista de 30,000 pies

```
┌─────────────────────────────────────────────────────────┐
│                      BMO SYSTEM                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐   │
│  │   DISPLAY   │  │   CONFIG    │  │   MEMORY     │   │
│  │ (UI/Video)  │  │ (Hot-reload)│  │ (JSON Persist)   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘   │
│         │                │               │            │
│         └────────────────┼───────────────┘            │
│                          │                            │
│                   ┌──────▼─────────┐                  │
│                   │    MAIN.PY     │                  │
│                   │  (Orquestador) │                  │
│                   └──────┬─────────┘                  │
│                          │                            │
│      ┌───────────────────┼───────────────────┐       │
│      │                   │                   │       │
│  ┌───▼────┐          ┌──▼───┐          ┌───▼──┐    │
│  │ VISION │          │BRAIN │          │VOICE │    │
│  │(Faces) │          │(LLM) │          │(Audio)    │
│  └────────┘          └──────┘          └───────┘   │
│      │                   │                   │       │
│  Ollama: 11434 ◄─────────┘                   │       │
│  OpenCV: local              Piper TTS        │       │
│  ONNX: local          Faster Whisper         │       │
│                           SoundDevice       │       │
│                                             │       │
└─────────────────────────────────────────────────────┘
```

---

### Stack de Tecnologías

```
Capa de Aplicación:
├─ main.py (orquestación)
├─ brain/ (LLM)
├─ voice/ (audio)
├─ vision/ (visión)
├─ display/ (UI)
└─ memory/ (persistencia)

Capa de Modelos:
├─ Qwen2.5:1.5b (LLM)
├─ Faster-Whisper (STT)
├─ Piper TTS (síntesis)
└─ MobileFaceNet ONNX (embeddings)

Capa de Infraestructura:
├─ Ollama (LLM server)
├─ OpenCV (visión)
├─ NumPy (álgebra lineal)
├─ SoundDevice (audio I/O)
└─ JSON (persistencia)

Hardware:
├─ CPU (RPi5 8GB)
├─ Cámara USB (opcional)
├─ Micrófono USB (requerido)
└─ Altavoz USB (requerido)
```

---

## 🔄 FLUJOS DE DATOS

### 1. Flujo Principal: Usuario Pregunta → BMO Responde

```
┌──────────────┐
│ Usuario      │
│ "Hola BMO,   │
│ ¿Cómo        │
│ estás?"      │
└────────┬─────┘
         │
         │ Audio capturado por micrófono
         ▼
    ┌────────────────┐
    │ VOICE.escuchar()
    │ [STT Pipeline] │
    │                │
    │ 1. VAD detecta │
    │    voz         │
    │ 2. Grabar audio│
    │ 3. Whisper     │
    │    transcribe  │
    └────────┬───────┘
             │
             │ Texto: "Hola BMO, ¿Cómo estás?"
             ▼
        ┌──────────────────────┐
        │ BRAIN.responder()    │
        │ [LLM Pipeline]       │
        │                      │
        │ 1. Memoria:          │
        │    buscar contexto   │
        │ 2. Clasificador:     │
        │    tipo de pregunta  │
        │ 3. LLM (Ollama):     │
        │    generar respuesta │
        │ 4. TTS queue:        │
        │    encolar oraciones │
        └────────┬─────────────┘
                 │
                 │ Respuesta: "¡Hola! Estoy bien, gracias"
                 ▼
        ┌──────────────────┐
        │ VOICE.hablar()   │
        │ [TTS Pipeline]   │
        │                  │
        │ 1. Piper síntesis│
        │ 2. Reproducir    │
        │ 3. SoundDevice   │
        └────────┬─────────┘
                 │
                 │ Audio sale del altavoz
                 ▼
            ┌─────────────┐
            │ Usuario     │
            │ escucha:    │
            │ "¡Hola!     │
            │ Estoy bien, │
            │ gracias"    │
            └─────────────┘
```

---

### 2. Flujo de Visión: Detectar Rostro → Reconocer

```
┌──────────────────┐
│ Cámara           │
│ 30 FPS           │
│ 640x480          │
└────────┬─────────┘
         │
         │ Frame BGR
         ▼
    ┌──────────────────────────┐
    │ Vision.procesar_rostro() │
    │                          │
    │ 1. BGR → Grayscale       │
    │ 2. Ecualizar histograma  │
    │ 3. Haar Cascade detecta  │
    │    faces                 │
    └────────┬─────────────────┘
             │
             │ Si no hay caras → Return []
             │
             │ Si hay caras → Lista de (x,y,w,h)
             ▼
        ┌────────────────────────────┐
        │ Para cada rostro:          │
        │                            │
        │ 1. Extraer ROI (región)    │
        │ 2. Si ONNX disponible:     │
        │    - FaceEmbedder.extract()│
        │    - Embedding 512-dim     │
        │ 3. Comparar con memory     │
        │    - best_match()          │
        │    - Similitud coseno      │
        └────────┬───────────────────┘
                 │
                 │ Resultado: (nombre, similitud)
                 │ Ejemplo: ("Juan", 0.78)
                 ▼
            ┌─────────────────────┐
            │ main._nombre_actual │
            │ = "Juan"            │
            │                     │
            │ → Display renderiza │
            │   "Hola, Juan!"     │
            └─────────────────────┘
```

---

### 3. Flujo de Memoria: Guardar Conversación

```
┌─────────────────────────────────┐
│ Usuario: "Hola, me llamo Pedro" │
│ BMO: "¡Hola Pedro!"             │
└────────┬────────────────────────┘
         │
         │
         ▼
┌──────────────────────────────┐
│ persistent_memory.           │
│ add_user_message()           │
│                              │
│ session_memory append:       │
│ {                            │
│   "role": "user",            │
│   "content": "Hola, me...",  │
│   "timestamp": "2026-04-30..."
│ }                            │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ persistent_memory.           │
│ add_assistant_message()      │
│                              │
│ session_memory append:       │
│ {                            │
│   "role": "assistant",       │
│   "content": "¡Hola Pedro!", │
│   "timestamp": "2026-04-30..."
│ }                            │
└──────────────┬───────────────┘
               │
               ▼ Si 2+ turnos en sesión
┌──────────────────────────────────┐
│ persistent_memory.               │
│ commit_session_to_permanent()    │
│                                  │
│ Lee chat_memory.json             │
│ Agrega conversación nueva        │
│ Guarda archivo                   │
└──────────────┬───────────────────┘
               │
               ▼
        ┌─────────────────┐
        │ data/           │
        │ chat_memory.json│
        │                 │
        │ Conversación    │
        │ persistida      │
        │ (PERMANENTE)    │
        └─────────────────┘
```

---

## 🧵 THREADING Y SINCRONIZACIÓN

### Arquitectura de Threads

```
Main Process
│
├─ Thread 1: _loop_camara()
│  │ while self._running:
│  ├─ cap.read() → frame
│  ├─ procesar_rostro(frame)
│  ├─ with self._lock_camara:
│  │  └─ self._nombre_actual = nombre
│  └─ sleep(0.1)
│
├─ Thread 2: _loop_logica()
│  │ while self._running:
│  ├─ voz.escuchar() → texto
│  ├─ with self._lock_camara:
│  │  └─ nombre_contexto = self._nombre_actual
│  ├─ brain.responder_con_tts(
│  │    texto, 
│  │    hablar_fn,
│  │    nombre_persona=nombre_contexto
│  │  )
│  │ Internamente en responder_con_tts():
│  │ └─ Hilo TTS worker (daemon)
│  │    ├─ while tts_queue no vacía:
│  │    ├─ with tts_lock:
│  │    │  └─ texto = tts_queue.pop(0)
│  │    ├─ hablar_fn(texto) [BLOQUEANTE]
│  │    └─ sleep(0.05)
│  └─ sleep(0.5)
│
└─ Main (UI Loop):
   while self._running:
   ├─ display.tick()
   ├─ cv2.imshow() [BLOQUEANTE]
   └─ sleep(1/FPS_DISPLAY)
```

---

### Sincronización de Locks

```
Recurso Compartido: self._nombre_actual

┌─────────────────────────────────────────┐
│ Thread 1 (Cámara)                       │
├─────────────────────────────────────────┤
│ t=0s:                                   │
│ with self._lock_camara:      ← ADQUIRIR │
│   self._nombre_actual = "Juan"          │
│                         ← LIBERAR       │
│                                         │
│ t=10s:                                  │
│ with self._lock_camara:      ← ADQUIRIR │
│   self._nombre_actual = "María"         │
│                         ← LIBERAR       │
└────────────┬──────────────────────────┬─┘
             │                          │
             │ Esperando Lock           │
             │                          │
┌────────────▼──────────────────────────▼─┐
│ Thread 2 (Lógica)                       │
├─────────────────────────────────────────┤
│ t=0.5s:                                 │
│ with self._lock_camara: ← ESPERAR...    │
│   nombre = self._nombre_actual          │
│           ← Obtiene "Juan"              │
│ LIBERAR (Thread 1 puede entrar)         │
│                                         │
│ t=10.5s:                                │
│ with self._lock_camara: ← ESPERAR...    │
│   nombre = self._nombre_actual          │
│           ← Obtiene "María"             │
│ LIBERAR                                 │
└─────────────────────────────────────────┘
```

**Importancia**: Sin locks:
```
Timeline sin sincronización (❌ RIESGOSO):
t=0: Thread 1 lee self._nombre_actual = "Juan"
t=0: Thread 2 escribe self._nombre_actual = "María"
t=0: Thread 1 continúa con datos corruptos

→ Race condition → crash o comportamiento impredecible
```

---

## 🔗 MÓDULOS Y DEPENDENCIAS

### Árbol de Importaciones

```
main.py (punto de entrada)
├─ src.brain.brain
│  ├─ src.config.runtime
│  ├─ src.memory.register
│  ├─ src.brain.classifier
│  ├─ ollama (API LLM)
│  └─ numpy (operaciones)
│
├─ src.voice.voice
│  ├─ faster_whisper (STT)
│  ├─ piper.tts (TTS)
│  ├─ sounddevice (audio I/O)
│  └─ numpy
│
├─ src.vision.vision
│  ├─ opencv (cv2)
│  ├─ src.vision.embedder
│  │  ├─ onnxruntime (inferencia)
│  │  ├─ numpy
│  │  └─ opencv
│  └─ src.memory.register
│
├─ src.display.display
│  ├─ opencv (cv2)
│  ├─ numpy
│  └─ src.config.runtime
│
├─ src.memory.register
│  ├─ pathlib
│  ├─ json
│  └─ datetime
│
└─ src.config.runtime
   └─ src.config.config_manager
      ├─ json
      ├─ pathlib
      └─ datetime
```

---

### Dependencia de Configuración

```
config.json (fuente única de verdad)
│
├─ voice.py
│  ├─ whisper_model: "base"
│  ├─ vad_threshold: 0.015
│  └─ output_device: 0
│
├─ brain.py
│  ├─ llm_temperature: 0.75
│  ├─ llm_num_predict: 100
│  └─ llm_num_thread: 4
│
├─ vision.py
│  └─ camera_index: 0
│
└─ display.py
   └─ headless: false
```

---

## ⏱️ SECUENCIAS TEMPORALES

### Secuencia Típica: 10 Segundos de Interacción

```
TIEMPO    EVENTO                              THREAD           ESTADO
────────────────────────────────────────────────────────────────────────
t=0.0s    Usuario comienza a hablar          Main (Display)   IDLE
          - Micrófono capta audio            Voice (Lógica)   

t=0.2s    VAD detecta nivel > 0.015          Voice (Lógica)   LISTENING
          - Display → LISTENING              Display (Main)

t=2.0s    Usuario termina de hablar          Voice (Lógica)   LISTENING
          - VAD mide 1.2s de silencio
          - Termina grabación

t=2.5s    Whisper transcribe                 Voice (Lógica)   THINKING
          - "¿Cuál es la capital..."         Display (Main)

t=3.0s    Respuesta texto lista              Voice (Lógica)   THINKING
          - Enviada a brain                  Display (Main)

t=3.5s    Clasificador categoriza            Brain (Lógica)   THINKING
          - Tipo: FACTUAL (100 tokens)

t=4.0s    LLM comienza streaming             Brain (Lógica)   THINKING
          - Ollama genera primer token       Display (Main)

t=5.0s    Oración 1 lista en buffer          Brain (Lógica)   SPEAKING
          - Encolada para TTS                Display (Main)
          - Display → SPEAKING

t=5.1s    TTS comienza síntesis              Brain+Voice      SPEAKING
          - Workers paralelos                (2 threads)

t=5.5s    Audio comienza a reproducir        Voice (Lógica)   SPEAKING
          - Usuario escucha: "La capital..." Display (Main)

t=8.0s    LLM termina generación             Brain (Lógica)   SPEAKING
          - tts_done.set()

t=8.5s    TTS finaliza última oración        Voice (Lógica)   SPEAKING
          - Worker exit

t=9.0s    Audio finaliza                     Voice (Lógica)   SPEAKING
          - Display → IDLE

t=10.0s   Estado vuelto a IDLE               Display (Main)   IDLE
          - Esperando siguiente entrada

LATENCIA PERCIBIDA: 5.5s - 0.5s = 5 segundos (desde fin del habla usuario)
```

---

### Secuencia de Registro de Persona Nueva

```
TIEMPO    EVENTO                                     MÓDULO
────────────────────────────────────────────────────────────────
t=0s      Usuario: "Me llamo Carlos"                 Voice/Brain
t=0.1s    Detectar nombre con regex                  Brain
t=0.2s    Nombre NO en memory.json → Iniciar registro Main

t=0.5s    Display: LISTENING                         Display
t=0.6s    Pedir confirmación: "¿Te llamas Carlos?"   Voice
t=0.7s    Capturar rostro (15 segundos)              Vision

t=0.7s    Cámara: detectar rostro                    Vision (thread)
t=1.0s    Foto #1 capturada                          Vision
t=1.3s    Foto #2 capturada                          Vision
...
t=15.7s   Foto #25 capturada                         Vision

t=16s     Generar embeddings ONNX                    Vision
          - 25 caras × embedding 512-dim             Embedder
          - Promediar: embedding único por persona

t=17s     Guardar en memory.json                     Memory
          - ID: 2
          - Nombre: Carlos
          - Embeddings: [promedio]

t=17.5s   Confirmación: "¡Listo Carlos!"            Voice
t=18s     Display: IDLE, esperando siguiente         Display

LATENCIA TOTAL: 18 segundos (tiempo de registro)
```

---

## 🔀 ESTADOS Y TRANSICIONES

### Estado de Display

```
                    ┌─────────────┐
                    │   WARMUP    │ (cargando recursos)
                    └──────┬──────┘
                           │ (3 segundos)
                           ▼
                    ┌─────────────┐
                    │    IDLE     │◄────────┐
                    └──────┬──────┘         │
                           │               │
                    (usuario habla)   (termina respuesta)
                           │               │
                           ▼               │
                    ┌─────────────┐      │
                    │ LISTENING   │      │
                    └──────┬──────┘      │
                           │             │
              (Whisper termina transcripción)
                           │             │
                           ▼             │
                    ┌─────────────┐      │
                    │  THINKING   │      │
                    └──────┬──────┘      │
                           │             │
              (LLM genera primera oración)
                           │             │
                           ▼             │
                    ┌─────────────┐      │
                    │  SPEAKING   │      │
                    └──────┬──────┘      │
                           │             │
                    (audio termina)      │
                           └─────────────┘
```

---

### Estado de Memoria

```
┌─────────────────────────────────────────────────┐
│ MEMORY STATE MACHINE                            │
├─────────────────────────────────────────────────┤
│                                                 │
│ ┌──────────────────────────────────────────┐  │
│ │ SESSION (en RAM, temporal)               │  │
│ │ ┌────────────────────────────────────┐  │  │
│ │ │ User: "Hola"                       │  │  │
│ │ │ Assistant: "¡Hola!"               │  │  │
│ │ │ User: "¿Cómo estás?"              │  │  │
│ │ │ Assistant: "Muy bien, gracias"    │  │  │
│ │ └────────────────────────────────────┘  │  │
│ │ (MAX 10 últimos mensajes)                │  │
│ └──────────────────────────────────────────┘  │
│                                                 │
│ Cuando: len(session) >= 4 (2 turnos)           │
│         OR usuario termina sesión              │
│                                                 │
│ COMMIT ↓↓↓                                      │
│                                                 │
│ ┌──────────────────────────────────────────┐  │
│ │ PERMANENT (archivo JSON)                 │  │
│ │ ┌────────────────────────────────────┐  │  │
│ │ │ data/chat_memory.json             │  │  │
│ │ │ {                                  │  │  │
│ │ │   "conversations": [              │  │  │
│ │ │     {                              │  │  │
│ │ │       "id": 0,                     │  │  │
│ │ │       "turnos": [...],             │  │  │
│ │ │       "fecha": "2026-04-30..."     │  │  │
│ │ │     }                              │  │  │
│ │ │   ]                                │  │  │
│ │ │ }                                  │  │  │
│ │ └────────────────────────────────────┘  │  │
│ │ (Historial completo)                     │  │
│ └──────────────────────────────────────────┘  │
│                                                 │
│ TAMBIÉN:                                       │
│ ├─ data/memory.json                            │
│ │  └─ Personas registradas + embeddings       │
│ └─ data/brain_context.txt                      │
│    └─ Contexto inyectable                      │
└─────────────────────────────────────────────────┘
```

---

## 📊 ESTRUCTURAS DE DATOS

### Estructura: memory.json

```json
{
  "1": {
    "nombre": "Juan",
    "visitas": 3,
    "ultima_vez": "2026-04-19 13:00:00",
    "resumen": "Usuario: hola | BMO: hola Juan! / Usuario: ¿cómo estás? | BMO: muy bien",
    "turnos_recientes": [
      {
        "user": "hola",
        "assistant": "¡Hola Juan!"
      },
      {
        "user": "¿cómo estás?",
        "assistant": "Muy bien, gracias por preguntar"
      }
    ],
    "embeddings": [
      [0.125, 0.234, ..., 0.567],  // 512 dimensiones
      [0.132, 0.241, ..., 0.571]
    ]
  },
  "2": {
    "nombre": "María",
    "visitas": 1,
    ...
  },
  "_anonimo": {
    "turnos_recientes": []
  }
}
```

---

### Estructura: chat_memory.json

```json
{
  "conversations": [
    {
      "id": 0,
      "fecha": "2026-04-19T13:00:00",
      "turnos": [
        {
          "role": "system",
          "content": "Eres BMO, un robot asistente..."
        },
        {
          "role": "user",
          "content": "Hola BMO",
          "timestamp": "2026-04-19T13:00:00",
          "person": "Juan"
        },
        {
          "role": "assistant",
          "content": "¡Hola Juan! Me alegra verte",
          "timestamp": "2026-04-19T13:00:05"
        }
      ]
    }
  ]
}
```

---

### Estructura: Embedding (512-dim)

```
Array de 512 floats:
[
  0.125,   // dim 0
  0.234,   // dim 1
  0.567,   // dim 2
  -0.123,  // dim 3
  ...
  0.891    // dim 511
]

Representación facial comprimida:
- Cada persona tiene ~3-5 embeddings (del registro)
- Se promedian en uno solo por persona
- Similitud coseno compara contra memory
- Resultado: (nombre, similitud) si similitud >= 0.55
```

---

### Estructura: Mensaje LLM

```json
{
  "role": "user",      // o "assistant"
  "content": "¿Cuál es la capital de Francia?",
  "timestamp": "2026-04-30T14:35:42.123456",  // opcional
  "person": "Juan"     // opcional
}

Secuencia completa para LLM:
[
  {"role": "system", "content": "[sistema prompt]"},
  {"role": "user", "content": "Hola"},
  {"role": "assistant", "content": "¡Hola!"},
  {"role": "user", "content": "¿Cuál es la capital de Francia?"}
]

Enviado a Ollama:
POST http://localhost:11434/api/chat
{
  "model": "qwen2.5:1.5b",
  "messages": [...],
  "stream": true,
  "options": {
    "temperature": 0.75,
    "top_k": 50,
    ...
  }
}

Respuesta stream (chunks):
{"message": {"content": "La"}}
{"message": {"content": " capital"}}
{"message": {"content": " de"}}
...
```

---

### Estructura: Audio Processing

```
Micrófono
  ↓ 16kHz, 16-bit mono
  ├─ SoundDevice captura chunks
  │
  ▼ Chunks: 1024 samples @ 16kHz = ~64ms cada uno
  
VAD (Voice Activity Detection):
  ├─ Calcula nivel: max(|samples|) ∈ [0.0, 1.0]
  ├─ Compara con threshold (0.015)
  ├─ Si nivel > 0.015 → grabando
  └─ Si nivel < 0.015 por 1.2s → parar
  
  ▼ Audio grabado: 3-10 segundos
  
Whisper
  ├─ Input: PCM audio 16kHz
  ├─ Processing: VAD → features → Whisper
  └─ Output: Transcripción en texto
  
TTS (Text-to-Speech)
  ├─ Input: "La capital de Francia es París"
  ├─ Piper ONNX sintetiza
  ├─ Output: Audio PCM 22050Hz
  ├─ Agregar silencio: pre=50ms, post=500ms
  └─ SoundDevice reproduce
  
  ▼ Altavoz
```

---

## 📈 COMPLEJIDAD COMPUTACIONAL

### Latencia por Módulo (RPi5 8GB con qwen2.5:1.5b)

```
┌──────────────┬──────────┬────────┬──────────┐
│ Módulo       │ Min (ms) │ Típico │ Max (ms) │
├──────────────┼──────────┼────────┼──────────┤
│ Whisper STT  │ 500      │ 1500   │ 3000     │
│ Classifier   │ 10       │ 50     │ 100      │
│ LLM Stream   │ 2000     │ 8000   │ 15000    │
│ TTS          │ 500      │ 1500   │ 3000     │
│ TOTAL (seq)  │ 3010     │ 11050  │ 21100    │
│ TOTAL (par)  │ 3010     │ 8500   │ 15000    │
└──────────────┴──────────┴────────┴──────────┘

Paralelismo reduce latencia:
- LLM genera mientras TTS sintetiza
- Cámara detecta mientras LLM procesa
- Resultado: mejora 20-30%
```

---

### Consumo de Recursos

```
┌──────────────┬──────┬────────┬──────────┐
│ Componente   │ CPU  │ RAM    │ Almacen  │
├──────────────┼──────┼────────┼──────────┤
│ Qwen2.5:1.5b │ 80%  │ 2.0GB  │ 1.0GB    │
│ Whisper base │ 30%  │ 1.0GB  │ 1.4GB    │
│ Piper TTS    │ 10%  │ 0.5GB  │ 0.5GB    │
│ ONNX face    │ 15%  │ 0.3GB  │ 0.6GB    │
│ BMO app      │ 5%   │ 0.2GB  │ 0.1MB    │
├──────────────┼──────┼────────┼──────────┤
│ TOTAL        │ 100% │ 4.0GB  │ 3.6GB    │
└──────────────┴──────┴────────┴──────────┘

RPi5 8GB → 4GB para BMO + 2GB buffer + 2GB OS = OK ✓
RPi5 4GB → Insuficiente ✗

Optimizaciones:
- keep_alive: 300 → libera LLM después 5min
- Whisper tiny → 0.5GB (pero menos preciso)
- Sin visión → -0.3GB
```

---

## 🔐 Seguridad de Datos

```
Datos Persistentes:
├─ memory.json
│  ├─ Contiene: Nombres, conversaciones, embeddings faciales
│  ├─ Ubicación: data/memory.json (local)
│  ├─ Privacidad: NO se envía a internet
│  └─ Respaldo: Manual (copiar archivo)
│
├─ chat_memory.json
│  ├─ Contiene: Historial de conversaciones
│  ├─ Ubicación: data/chat_memory.json (local)
│  ├─ Privacidad: NO se envía a internet
│  └─ Acceso: Solo lectura por BMO
│
└─ config.json
   ├─ Contiene: Parámetros de ejecución
   ├─ Ubicación: config.json (raíz)
   ├─ Privacidad: No sensible
   └─ Modificable: Editar directamente

Datos NO Persistentes (volátiles):
├─ Embeddings en RAM (se descartan al apagar)
├─ LLM cache en RAM (se descartan)
└─ Audio buffer en RAM (se descargan)

Acceso a Internet:
├─ Ollama API: http://localhost:11434 (local, no internet)
├─ Whisper: offline (modelos locales)
├─ Piper: offline (modelos locales)
├─ ONNX: offline (modelos locales)
└─ Internet: CERO acceso por defecto ✓
   (Solo si agregan duckduckgo para búsqueda web)
```

---

**Documento Completado**: Arquitectura detallada de BMO con flujos, threads, estados y estructuras de datos.

