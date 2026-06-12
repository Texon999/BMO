# Guía Completa del Código de BMO

## Índice
1. [Arquitectura General](#1-arquitectura-general)
2. [Estructura de Directorios](#2-estructura-de-directorios)
3. [Módulo Principal — main.py](#3-módulo-principal---mainpy)
4. [Voz — voice.py y wake_word.py](#4-voz---voicepy-y-wake_wordpy)
5. [Display — display.py](#5-display---displaypy)
6. [Visión — vision.py y embedder.py](#6-visión---visionpy-y-embedderpy)
7. [Cerebro — brain/](#7-cerebro---brain)
8. [Memoria — memory/ y storage/](#8-memoria---memory-y-storage)
9. [Configuración — config/](#9-configuración---config)
10. [Tests y Scripts](#10-tests-y-scripts)
11. [Comandos por Voz — commands.py](#11-comandos-por-voz---commandspy)
12. [Sistema de Juegos](#12-sistema-de-juegos)
13. [Cómo Agregar Juegos](#13-cómo-agregar-juegos)
14. [Cómo Agregar Comandos Genéricos](#14-cómo-agregar-comandos-genéricos)
15. [Cómo Agregar Respuestas Predefinidas](#15-cómo-agregar-respuestas-predefinidas)
16. [Cómo Extensiones via system_prompt_extra](#16-cómo-extensiones-via-system_prompt_extra)
17. [Guía Rápida de Modificaciones Comunes](#17-guía-rápida-de-modificaciones-comunes)

---

## 1. Arquitectura General

BMO es un asistente de IA **offline** y **multimodal** que corre completamente en local.
Usa **3 hilos paralelos** para máximo rendimiento:

```
┌─────────────────────────────────────────────────────────────────┐
│                        main.py (AgenteBMO)                       │
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────────────────┐  │
│  │  Hilo Cámara          │  │  Hilo Lógica                    │  │
│  │  (_loop_camara)       │  │  (_loop_logica)                 │  │
│  │                       │  │                                  │  │
│  │  Captura frames       │  │  1. Saludo automático           │  │
│  │  Haar Cascade detecta │  │  2. Wake word "BMO"             │  │
│  │  ONNX reconoce        │  │  3. STT (Whisper)               │  │
│  │  Actualiza estado     │  │  4. Clasifica pregunta          │  │
│  │  thread-safe          │  │  5. COMANDOS + JUEGOS           │  │
│  │                       │  │  6. LLM (Ollama)                │  │
│  └──────────────────────┘  │  7. TTS (Piper)                 │  │
│                             │  8. Ventana post-respuesta 10s  │  │
│                             └──────────────────────────────────┘  │
│  ┌──────────────────────┐                                         │
│  │  Hilo Principal       │                                         │
│  │  (display.tick())     │                                         │
│  │                       │                                         │
│  │  Animación facial     │                                         │
│  │  OpenCV               │                                         │
│  │  Sincronizada con     │                                         │
│  │  nivel de audio       │                                         │
│  └──────────────────────┘                                         │
└─────────────────────────────────────────────────────────────────┘
```

**Orden de procesamiento en el hilo de lógica:**
1. Detectar nombre ("me llamo X") → registrar persona
2. `ejecutar_comando()` — comandos genéricos (abrir Chrome, etc.)
3. `ejecutar_juego()` — sistema de juegos ("quiero jugar X")
4. `responder_con_tts()` — respuestas predefinidas → clasificación → LLM

**Comunicación entre hilos:**
- `_lock_camara` (threading.Lock) protege `_nombre_camara_reconocido`, `_cara_desconocida_presente`, `_nombre_activo`
- El hilo de cámara **escribe** el nombre reconocido
- El hilo de lógica **lee** el nombre para el contexto del LLM
- El display **lee** `VozBMO.audio_level` (variable de clase) para sincronizar animación

---

## 2. Estructura de Directorios

```
BMO/
├── src/                          # Código fuente
│   ├── main.py                   # Entry point, orquestador de hilos
│   ├── brain/                    # Cerebro
│   │   ├── brain.py              # Pipeline LLM → TTS, respuestas predefinidas
│   │   ├── classifier.py         # Clasificación (8 categorías), + sin_acentos público
│   │   ├── commands.py           # Comandos por voz + Sistema de Juegos
│   │   ├── fact_checker.py       # Fact-checker web (DuckDuckGo)
│   │   └── archive_hybrid/       # [ARCHIVADO] Sistema híbrido anterior (~2500 líneas)
│   │       ├── hybrid_system.py, hybrid_logger.py, ...
│   │       ├── question_classifier.py, fact_database.py
│   │       ├── fallback_handler.py, response_formatter.py
│   │       ├── similarity.py, text_normalizer.py, models.py
│   │       └── patterns/ (flag_patterns.py, science_patterns.py)
│   ├── config/
│   │   └── config_manager.py     # Config JSON centralizada con hot-reload
│   │   └── runtime.py            # Variables de entorno tipadas
│   ├── display/
│   │   └── display.py            # Animación facial OpenCV
│   ├── memory/
│   │   ├── persistent_memory.py  # Memoria MongoDB con sliding window
│   │   └── register.py           # Registro de personas y embeddings
│   ├── storage/
│   │   └── mongo_store.py        # Capa MongoDB (personas, chat_history)
│   ├── vision/
│   │   ├── embedder.py           # Extracción de embeddings ONNX 512d
│   │   └── vision.py             # Detección Haar + reconocimiento facial
│   └── voice/
│       ├── voice.py              # STT (Whisper) + TTS (Piper)
│       └── wake_word.py          # Detector de "BMO"
├── data/                         # Datos runtime
├── assets/faces/                 # Frames de animación facial
├── voices/                       # Modelos de voz Piper (.onnx)
├── scripts/                      # Scripts de utilidad y tests
│   ├── test_post_cleanup.py       # Suite de 41 tests post-limpieza
│   └── test_juegos.py            # Suite de 13+ tests del sistema de juegos
├── config.json                   # Configuración central
└── CODEGUIDE.md                  # Este archivo
```

**Archivos eliminados en limpieza:**
- `src/config/audio_manager.py` — eliminado (voice.py maneja audio directamente)
- `src/brain/hybrid_system.py` y 11 archivos relacionados → archivados en `archive_hybrid/`
- `get_info()` en `display.py` — código muerto
- `buscar_persona_por_similitud()` en `mongo_store.py` — código muerto
- ~8 métodos híbridos en `config_manager.py`
- `_truncar` duplicado en `persistent_memory.py` — ahora importa `_contexto como _truncar` de `mongo_store`
- `_sin_acentos` privado en `brain.py` — ahora `sin_acentos()` público en `classifier.py`

---

## 3. Módulo Principal — main.py

**Archivo:** `src/main.py`

### Clase `AgenteBMO`

Orquestador de TODO el sistema. Su `__init__` crea:

| Componente | Clase | Propósito |
|-----------|-------|-----------|
| `self.display` | `DisplayBMO` | Animación facial |
| `self.vision` | `VisionBMO` (opcional) | Cámara + reconocimiento facial |
| `self.voz` | `VozBMO` | STT + TTS |
| `self._wake` | `WakeWordDetector` | Detección de "BMO" |
| `self._comandos_voz` | `list[ComandoVoz]` | Comandos genéricos desde config |
| `self._juegos` | `dict[str, str]` | Juegos desde config |

### Estado thread-safe (protegido por `_lock_camara`)

| Variable | Tipo | Propósito |
|----------|------|-----------|
| `_nombre_camara_reconocido` | `str \| None` | Nombre detectado por cámara |
| `_cara_desconocida_presente` | `bool` | Hay cara no registrada |
| `_nombre_activo` | `str \| None` | Nombre para el LLM (cámara o caché) |
| `_nombre_cache_temporal` | `str \| None` | Nombre dicho pero sin foto |

### Orden en `_procesar_y_responder()`:

```python
def _procesar_y_responder(self, texto: str):
    # 1. Detectar "me llamo X" → registrar persona
    # 2. ejecutar_comando(texto, self._comandos_voz) → ¿coincide?
    #    → Sí: hablar respuesta, return
    # 3. ejecutar_juego(texto, self._juegos) → ¿coincide?
    #    → Sí: hablar respuesta, return
    # 4. responder_con_tts(mensaje=texto, ...) → flujo normal
```

---

## 4. Voz — voice.py y wake_word.py

### VozBMO (src/voice/voice.py)

**STT:** `faster-whisper` (modelo configurable, default `base` español).
**VAD:** graba solo cuando hay voz. Parámetros: `VAD_THRESHOLD=0.015`, `VAD_SILENCE_SEC=1.2s`, `VAD_MAX_SEC=10s`, `VAD_MIN_SEC=0.3s`.
**TTS:** Piper TTS con voz `es_ES-sharvard-medium.onnx`. Normaliza (π→pí, OK→okey, etc.).

Variables de clase importantes:
- `VozBMO.audio_level` — el display lo lee para sincronizar animación
- `VozBMO.ultimo_hablar_ts` — wake word lo usa para cooldown anti-eco

### WakeWordDetector (src/voice/wake_word.py)

Modo pasivo: chunks de 250ms, hasta 3s de voz, transcribe con Whisper sensible.
Detecta: "bmo", "bimo", "vimo", "bemo", "b.m.o", etc.
Anti-eco: `_COOLDOWN_POST_TTS = 1.5s`.
Ventana post-respuesta: 10s sin requerir wake word.

---

## 5. Display — display.py

**Archivo:** `src/display/display.py`

| Estado | FPS | Propósito |
|--------|-----|-----------|
| WARMUP | 2 | Cargando |
| IDLE | 2 | Esperando |
| LISTENING | 8 | Escuchando |
| THINKING | 8 | Pensando |
| SPEAKING | 4-12 | Hablando (sincronizado con audio) |
| ERROR | 2 | Error |

Modo headless: `HEADLESS=true` → no abre ventana.

---

## 6. Visión — vision.py y embedder.py

**Pipeline:** Haar Cascade → FaceEmbedder ONNX 512d → similitud coseno (umbral 0.55).
**Registro:** `aprender_rostro()` recibe imágenes BGR, extrae embeddings, promedia, normaliza L2.

---

## 7. Cerebro — brain/

### brain.py — Pipeline LLM → TTS

**Flujo de `responder_con_tts()`:**
1. `normalizar_texto_entrada(mensaje)` — corrige "número p" → "número pi", etc.
2. `buscar_respuesta_predefinida(mensaje)` — si coincide patrón → respuesta instantánea
3. `categorizar_pregunta(mensaje)` → 8 categorías
4. Asigna `num_predict`, `max_oraciones`, `length_hint` según categoría
5. Arma contextos (system prompt + historial MongoDB + sesión actual)
6. Stream con ollama.chat() → normaliza oraciones → encola TTS
7. Guarda en MongoDB

**Normalización de entrada (regex en brain.py):**
Todas las regex usan `[úu]`, `[íi]`, etc. para matchear con/sin tilde:
- `n[úu]mero p[áa]` → pi
- `n[úu]mero p[ií]` → pi
- `d[ií]jitos` → dígitos
- Y otras correcciones de pronunciación Whisper

### classifier.py — Clasificación

8 categorías: GREETING, SIMPLE, OPINION, FACTUAL, COMPARE, TECHNICAL, EXPLAIN, CREATIVE.

Orden de evaluación: GREETING → OPINION → **FACTUAL** → **COMPARE** → TECHNICAL → EXPLAIN → CREATIVE → SIMPLE.

`PATRON_PREGUNTA` y `PATRON_FACTUAL` se evalúan ANTES que `PATRON_TECNICO` para que "qué es python" retorne `factual` en vez de `technical`.

**Función pública `sin_acentos(texto)`:** normaliza vocales acentuadas para comparación robusta.

---

## 8. Memoria — memory/ y storage/

### persistent_memory.py

- Backend: MongoDB (localhost:27017)
- Solo persiste historial de personas registradas (con cara)
- Máximo 6 mensajes por persona (sliding window, ~120 chars cada uno)
- Sin cara → sesión en RAM, nunca toca MongoDB
- `_truncar(texto)` importado como alias de `mongo_store._contexto` (misma lógica, sin duplicación)

Clases: `_MongoMemory`, `_RamMemory`, `PersistentMemory`.

### mongo_store.py

Colecciones: `personas`, `chat_history`.
Búsqueda de embeddings: coseno exhaustivo con numpy (~1ms para 50 personas 512d).

### register.py

Registro con doble escritura (MongoDB + JSON): `guardar_persona()`, `guardar_embeddings_persona()`, `cargar_embeddings_todos()`, `nombres_a_ids()`.

---

## 9. Configuración — config/

### runtime.py

Variables de entorno con prefijo `BMO_`: `BMO_CAMERA_INDEX`, `BMO_MIC_DEVICE`, `BMO_WHISPER_MODEL`, `BMO_LLM_MODEL`, `BMO_VAD_THRESHOLD`, etc. Carga `.env` automáticamente.

### config_manager.py

Carga `config.json`, combina con defaults, valida rangos, migración automática.
Métodos: `get_ollama_options()`, etc. Ya sin métodos híbridos.

### config.json — Estructura

```json
{
  "comandos_voz": {
    "minecraft": { "ruta": "...", "patron": "...", "respuesta": "..." }
  },
  "juegos": {
    "hollow knight": "C:/juegos/Hollow Knight/hollow_knight.exe"
  }
}
```

Keys híbridas remanentes (`hybrid_mode_enabled`, `classification_thresholds`, etc.) aún presentes en `config.json` pero ignoradas por el código.

---

## 10. Tests y Scripts

| Script | Propósito |
|--------|-----------|
| `scripts/test_post_cleanup.py` | 41 tests de integridad post-limpieza |
| `scripts/test_juegos.py` | 13+ tests del sistema de juegos |

Ejecutar: `python scripts/test_post_cleanup.py`

---

## 11. Comandos por Voz — commands.py

**Archivo:** `src/brain/commands.py`

### Clase `ComandoVoz`

```python
class ComandoVoz:
    def __init__(self, nombre, patron, respuesta, ejecutar):
        self.patron = re.compile(patron, re.IGNORECASE)
    def coincide(self, texto) -> bool
```

### `_abrir_programa(ruta)`

Abre programas, URLs o protocolos:
- `http://` / `https://` → `webbrowser.open()`
- `steam://` / `gog://` → `subprocess.Popen(shell=True)`
- Ejecutables locales → `subprocess.Popen([ruta])`

### `construir_comandos(config)` → `list[ComandoVoz]`

Lee `config["comandos_voz"]` y registra cada comando.

### `ejecutar_comando(texto, comandos)` → `str | None`

Busca coincidencia en todos los comandos. Si hay match → ejecuta y devuelve respuesta.

---

## 12. Sistema de Juegos

Implementado en `src/brain/commands.py` como funciones modulares.

### Patrones de activación (6)

```python
_PATRONES_JUEGO = [
    r"quiero jugar (a |al )?(.+)",
    r"juguemos (a |al )?(.+)",
    r"vamos a jugar (a |al )?(.+)",
    r"pon (el )?(juego de )?(.+)",
    r"abre (el )?(juego )?(.+)",
    r"ejecuta (el )?(juego )?(.+)",
]
```
El grupo `(.+)` captura el nombre del juego.

### `_extraer_nombre_juego(texto)` → `str | None`

Extrae el nombre y limpia coletillas: "por favor", "please", "gracias", etc.

### `_mejor_coincidencia_juego(texto_juego, juegos)` → `str | None`

Busca en 3 niveles (ordenado por longitud descendente para precisión):
1. Coincidencia exacta
2. Coincidencia parcial (nombre en texto o viceversa)
3. Coincidencia por palabras (al menos una palabra coincide)

### `ejecutar_juego(texto, juegos)` → `str | None`

Flujo: extraer nombre → buscar coincidencia → abrir programa → devolver mensaje.
El nombre mostrado limpia guiones bajos: `"test_game"` → `"Test Game"`.

### `_juegos_inicializar(config)` (en main.py)

```python
self._juegos = construir_juegos(config_manager.config)
```
Valida existencia con `Path.exists()` + `shutil.which()` antes de loguear warning.

---

## 13. Cómo Agregar Juegos

Solo necesitas editar `config.json`. **Sin tocar Python.**

### Paso 1: Agregar entrada en `config.json`

```json
{
  "juegos": {
    "hollow knight":           "C:/juegos/Hollow Knight/hollow_knight.exe",
    "minecraft":               "C:/juegos/Minecraft/minecraft.exe",
    "calculadora":             "calc.exe",
    "youtube":                 "https://youtube.com",
    "hollow knight voidheart": "C:/juegos/HK Voidheart/hk.exe",
    "portal 2":                "steam://rungameid/620"
  }
}
```

- La **key** es el nombre del juego (en minúsculas, sin acentos). Se puede decir "BMO, quiero jugar Hollow Knight" o "BMO, abre el juego Hollow Knight".
- La **ruta** puede ser: ejecutable local, URL http/https, o protocolo `steam://`, `gog://`, etc.
- Juegos con nombres largos se matchean primero (más específico). "hollow knight voidheart" matchea antes que "hollow knight".

### Paso 2: Verificar con test

```bash
python scripts/test_juegos.py
```

### Reglas de matching

- "quiero jugar MINECRAFT" → exacto → abre minecraft
- "juguemos hollow knight" → parcial ("hollow knight" está en el texto) → abre hollow knight
- "vamos a jugar portal" → palabras clave ("portal" en "portal 2") → abre portal 2
- "abre el juego hollow knight voidheart edition" → coincidencia más larga primero → abre voidheart, no el vanilla

---

## 14. Cómo Agregar Comandos Genéricos

Para comandos que no son juegos (abrir programas, páginas, etc.).

### Paso 1: Agregar en `config.json`

```json
{
  "comandos_voz": {
    "chrome": {
      "ruta": "C:/Program Files/Google/Chrome/Application/chrome.exe",
      "patron": "\\babre\\s+(?:el\\s+)?chrome\\b",
      "respuesta": "Abriendo Chrome!"
    },
    "calculadora": {
      "ruta": "calc.exe",
      "patron": "\\babre\\s+(?:la\\s+)?calculadora\\b",
      "respuesta": "Abriendo la calculadora!"
    }
  }
}
```

| Campo | Obligatorio | Descripción |
|-------|------------|-------------|
| `ruta` | Sí | Ruta al ejecutable, URL, o nombre en PATH |
| `patron` | No | Regex personalizada. Default: `\babre (?:el )?nombre\b` |
| `respuesta` | No | Texto que dirá BMO al ejecutar |

### Paso 2: El patrón regex

- `\b` = límite de palabra
- `(?:el\s+)?` = "el " opcional
- El patrón default es: `r"\babre\s+(?:el\s+)?<nombre_escapado>\b"`

Ejemplos:
- "abre chrome" → match
- "abre el chrome" → match
- "abrelo chrome" → NO match (falta espacio)
- "chrome abierto" → NO match (no empieza con "abre")

---

## 15. Cómo Agregar Respuestas Predefinidas

Respuestas que BMO contesta sin consultar al LLM. Útil para datos exactos.

### Editar `src/brain/brain.py`

Busca el diccionario `RESPUESTAS_PREDEFINIDAS` y agrega:

```python
RESPUESTAS_PREDEFINIDAS: dict[re.Pattern, str] = {
    # ... existentes ...
    re.compile(r'\bcu[áa]l\ses\sla\scapital\sde\sfrancia\b', re.IGNORECASE):
        "La capital de Francia es París.",
}
```

**Reglas:**
- Usa `[áa]`, `[éé]`, etc. para tolerar acentos (Whisper a veces no los escribe)
- El patrón se compila con `re.IGNORECASE`
- La respuesta se habla textualmente
- Se evalúa ANTES del LLM, es instantánea

---

## 16. Cómo Extensiones via system_prompt_extra

Para darle contexto o habilidades sin modificar código.

### Editar `config.json`

```json
{
  "system_prompt_extra": "Eres un experto en matemáticas. Cuando te pregunten problemas, explica paso a paso.\nTambién sabes todo sobre la serie Adventure Time."
```

Esto se concatena al system prompt principal antes de enviarlo al LLM.
No requiere reiniciar BMO (solo recargar config).

---

## 17. Guía Rápida de Modificaciones Comunes

| Acción | Dónde |
|--------|-------|
| Agregar juego | `config.json` → `"juegos": {"nombre": "ruta"}` |
| Agregar comando genérico | `config.json` → `"comandos_voz": {"nombre": {ruta, patron, respuesta}}` |
| Agregar respuesta predefinida | `src/brain/brain.py` → `RESPUESTAS_PREDEFINIDAS` |
| Agregar system prompt extra | `config.json` → `"system_prompt_extra"` |
| Cambiar modelo TTS | Descargar `.onnx` a `voices/`, cambiar `voice_model` en `config.json` |
| Cambiar modelo LLM | `ollama pull modelo`, cambiar `BMO_LLM_MODEL` en `.env` |
| Deshabilitar MongoDB | `config.json` → `"chat_memory": false` |
| Modo headless | `$env:BMO_HEADLESS="true"; python src/main.py` |
| Sensibilidad micrófono | `BMO_VAD_THRESHOLD=0.01` (más) / `0.03` (menos) en `.env` |
| Forzar audio | `BMO_MIC_DEVICE=1`, `BMO_OUTPUT_DEVICE=3` en `.env` |
| Ejecutar tests | `python scripts/test_post_cleanup.py` y `python scripts/test_juegos.py` |

### Notas sobre rutas en Windows

- Usa `/` simples en JSON: `"C:/juegos/minecraft.exe"`
- Para URLs: `"https://youtube.com"` → abre navegador
- Para protocolos: `"steam://rungameid/620"` → `shell=True` automático
- Ejecutables en PATH: solo el nombre: `"calc.exe"`, `"notepad.exe"`
