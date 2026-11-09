# BMO - Local AI Agent

Robot conversacional local inspirado en BMO de Hora de Aventura.
Corre 100% offline en PC o Raspberry Pi 5.

## Stack

| Módulo | Tecnología |
|--------|-----------|
| Visión | OpenCV Haar Cascade (detección) + FaceEmbedder ONNX (embeddings 512 d, similitud coseno) |
| STT    | faster-whisper (tiny/base) |
| LLM    | Ollama — qwen2.5:1.5b (configurable) |
| TTS    | Piper TTS — es_ES-sharvard-medium |

## Instalación

### A. Qué debe estar en el repo

Para que un clon funcione en otro equipo debes incluir:
- `src/` con todo el código Python.
- `requirements.txt` con las dependencias.
- `config.json` con la ruta por defecto de la voz.
- `scripts/` con los scripts de descarga y configuración.
- `data/` con archivos de configuración mínima, pero no es necesario subir modelos grandes.

No es necesario subir los modelos descargables grandes al repo (`voices/*.onnx`, `models/`, `data/history/`). Estos se descargan después de la instalación.

### B. Pasos para clonar y ejecutar en otro equipo

1. Clona el repo y entra en la carpeta:

```bash
git clone <repo-url>
cd BMO
```

2. Crea y activa un entorno virtual:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Instala dependencias Python:

```bash
pip install -r requirements.txt
```

4. Instala Ollama y descarga el modelo LLM:

```bash
# Instalar Ollama: https://ollama.com
ollama pull qwen2.5:1.5b
```

5. Descarga la voz de Piper en español:

```bash
python scripts/download_voice.py
```

6. Ejecuta el proyecto:

```bash
python -m src.main
```

### C. ¿Qué pasa si no descargas el modelo de voz?

- El proyecto sigue arrancando.
- `src/voice/voice.py` busca `voices/es_ES-sharvard-medium.onnx` y su `*.json`.
- Si no están, BMO no hablará por altavoz, pero seguirá funcionando e imprimirá el texto en consola.

### Seleccionar camara/microfono/audio (recomendado)

```bash
python scripts/configure_devices.py
```

Configura indices por variables de entorno (o en un `.env` si usas uno):

```bash
BMO_CAMERA_INDEX=0
BMO_MIC_DEVICE=-1
BMO_OUTPUT_DEVICE=-1
BMO_HEADLESS=false
BMO_LLM_NUM_PREDICT=180
BMO_VISION_PROCESS_EVERY_N=1
BMO_BRAIN_CONTEXT_HOT_RELOAD=true
```

- `BMO_MIC_DEVICE=-1` usa autodeteccion del primer microfono funcional.
- `BMO_OUTPUT_DEVICE=-1` usa salida de audio por defecto.
- `BMO_HEADLESS=true` desactiva ventana OpenCV (util para correr como servicio en Raspberry).

## Modelos y archivos que necesita BMO

BMO no incluye modelos grandes en el repo. Se descargan o generan tras la instalación:

| Archivo | Para qué sirve | ¿Obligatorio? | Cómo obtenerlo |
|---------|----------------|---------------|----------------|
| `data/face_model.onnx` | Reconocimiento facial (embeddings 512 d). Si falta, BMO **detecta caras pero no reconoce a nadie** (modo degradado). | No | `python scripts/download_face_model.py` |
| `voices/es_ES-sharvard-medium.onnx` + `.json` | Voz TTS en español (Piper). Si falta, BMO imprime el texto en consola en lugar de hablarlo. | No | `python scripts/download_voice.py` |
| Ollama + modelo `qwen2.5:1.5b` | Cerebro conversacional. Si no hay Ollama, las respuestas predefinidas siguen funcionando; el LLM responde "Ups, BMO no puede pensar ahora." | No (para predefinidas) / Sí (para LLM) | `ollama pull qwen2.5:1.5b` |
| `data/memory.json`, `data/persons.json`, `data/names.json` | Personas registradas, historial y nombres. Se crean solas al registrar alguien. | No | Se autogeneran |
| `data/brain_context.txt` | Contexto inyectado al system prompt del LLM. | No | Crea el archivo tú mismo |

El archivo `config.json` concentra parámetros (modelo LLM, temperatura, tokens, VAD, cámara, juegos, comandos de voz). `src/config/runtime.py` lee los mismos valores desde variables de entorno `BMO_*` con sensatos valores por defecto, por lo que puedes mover el proyecto entre PC y Raspberry Pi 5 sin editar código.

## Controles

| Tecla | Acción |
|-------|--------|
| `Q`   | Salir |

## Estructura

```
BMO/
├── src/
│   ├── main.py                 # Loop principal (cámara, lógica, display)
│   ├── vision/
│   │   ├── vision.py           # Detección Haar + reconocimiento ONNX
│   │   └── embedder.py         # FaceEmbedder (embeddings 512 d, similitud coseno)
│   ├── voice/
│   │   ├── voice.py            # STT (faster-whisper + VAD) y TTS (Piper)
│   │   └── wake_word.py        # Detector de wake word "BMO"
│   ├── brain/
│   │   ├── brain.py            # LLM vía Ollama, respuestas predefinidas, TTS streaming
│   │   ├── classifier.py       # Clasificación de preguntas y parámetros del LLM
│   │   └── commands.py         # Comandos y juegos por voz
│   ├── memory/
│   │   ├── register.py         # Personas y embeddings (MongoDB + JSON fallback)
│   │   └── persistent_memory.py# Contexto de conversación (sliding window)
│   ├── config/
│   │   ├── runtime.py          # Parámetros desde variables de entorno BMO_*
│   │   └── config_manager.py   # Gestor centralizado config.json con validación
│   ├── storage/
│   │   └── mongo_store.py      # Acceso a MongoDB
│   └── display/
│       └── display.py          # Animación de la cara (OpenCV, modo headless)
├── config.json                 # Parámetros centrales (modelos, LLM, VAD, juegos, comandos)
├── data/
│   ├── memory.json             # Personas registradas (fallback JSON)
│   ├── persons.json / names.json
│   ├── chat_memory.json
│   ├── face_model.onnx         # Modelo facial (no se sube al repo)
│   └── facts/                  # Hechos offline (banderas, geografía, ciencia)
├── voices/                     # Modelos de voz Piper (.onnx) (no se suben al repo)
├── scripts/
│   ├── download_voice.py
│   ├── download_face_model.py
│   ├── configure_devices.py
│   └── smoke_check.py          # Verificación sin cámara ni micrófono
├── scripts/test_*.py           # Pruebas de flujo y rendimiento
└── requirements.txt
```

## Personalizar conocimiento del cerebro

Puedes agregar contexto propio en `data/brain_context.txt` (texto libre).  
BMO lo inyecta en el **system prompt** de cada respuesta al LLM.

- Con **`BMO_BRAIN_CONTEXT_HOT_RELOAD=true`** (por defecto), si guardas cambios en ese archivo, se **vuelve a leer** en la siguiente pregunta (sin reiniciar el programa). Si prefieres cargar solo al arrancar, pon `false`.
- Las respuestas **predefinidas** (regex en `brain.py`) no pasan por el LLM: no verán `brain_context.txt` hasta que caigan en el modelo.

## Comportamiento del modelo (mejoras aplicadas)

| Qué | Para qué sirve |
|-----|----------------|
| Fraccionar oraciones al hablar | Evita cortes raros al pasar texto del LLM al TTS (streaming). |
| `BMO_LLM_NUM_PREDICT` | Más tokens permitidos por respuesta (menos “cortes” por límite). |
| Reglas extra en el prompt | Menos invención en temas sensibles (historia, religión, cifras) y tono amable fijo. |
| `extra_context_para_prompt()` | `brain_context.txt` con recarga por **fecha de modificación** del archivo. |
| `BMO_VISION_PROCESS_EVERY_N` | En Raspberry, `2` o `3` procesa reconocimiento **1 de cada N** frames y baja CPU (la cámara sigue leyendo a la misma tasa). |
| Logging `BMO` en `brain.py` | Misma convención de hora/nivel que `main.py` (`[LLM→TTS]`, `[PREDEFINIDA]`, etc.). |

**Descartado de momento** (útil más adelante, no ahora): wake word tipo OpenWakeWord (más dependencias y flujo distinto), debounce agresivo en `memory.json` (riesgo si se apaga el proceso antes de guardar).

## Verificación rápida del entorno

Sin abrir cámara ni cargar el cerebro completo:

```bash
python scripts/smoke_check.py
```

Comprueba imports críticos, audio y que **Ollama** responda. Útil en una Raspberry nueva antes de `python -m src.main`.

### Ejecutar sin cámara, micrófono ni servicios externos

BMO está diseñado para degradarse gracefulmente:

- **Sin cámara**: `VisionBMO` inicia en modo degradado (detecta caras pero no las reconoce) si falta `data/face_model.onnx`. `main.py` lo atrapa y sigue funcionando solo con audio.
- **Sin micrófono / sin voz**: Si falta `voices/es_ES-sharvard-medium.onnx`, el TTS imprime el texto en consola en lugar de hablarlo.
- **Sin pantalla**: `BMO_HEADLESS=true` desactiva la ventana OpenCV (útil como servicio en Raspberry Pi).
- **Sin Ollama / sin LLM**: las respuestas predefinidas (saludos, pi, bandera de Colombia, SENA, etc.) siguen funcionando; solo el modelo generativo falla con un mensaje controlado.
- **Sin hardware en absoluto**: las pruebas unitarias puras en `scripts/test_unidades.py` cubren detección de nombres, normalización para TTS, clasificación de preguntas y saludos. No requieren cámara, micrófono, Ollama ni MongoDB:

```bash
python scripts/test_unidades.py
```

## Demo
No hay una URL de demo registrada en el repositorio. Si tienes un despliegue público, añade el enlace aquí para que el proyecto se pueda probar directamente.

## Aprender Python y este proyecto

Si vienes de JavaScript, React, C# o Java: [docs/GUIA_APRENDIZAJE_PYTHON_Y_BMO.md](docs/GUIA_APRENDIZAJE_PYTHON_Y_BMO.md) explica Python aplicado a BMO, cómo se conectan los módulos y cómo extender el código.

## Migración a Raspberry Pi 5

1. Clonar el repo en la Pi
2. Instalar dependencias igual
3. Ajustar por entorno: `BMO_WHISPER_MODEL=tiny` para menor consumo
4. Probar dispositivos con `python scripts/configure_devices.py`
5. Si no hay monitor, usar `BMO_HEADLESS=true`
6. Ollama corre en ARM64 (verifica modelo con `ollama list`)
