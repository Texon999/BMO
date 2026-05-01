# Guía de aprendizaje: Python y el proyecto BMO

Esta guía está pensada para quien ya programa en **JavaScript/Node**, **React**, **C#** o **Java** y quiere entender **Python** y este repositorio para poder **modificar y extender BMO** sin depender de asistentes de código.

---

## 1. Python frente a lo que ya conoces

| Concepto | JavaScript / Node | C# | Java | Python |
|----------|-------------------|----|------|--------|
| Tipado | Dinámico | Estático | Estático | Dinámico + **type hints** opcionales (`x: int`) |
| Bloques | `{}` | `{}` | `{}` | **Indentación obligatoria** (4 espacios) |
| Punto y coma | Opcional | Sí | Sí | **No** se usan |
| Módulos | `import` / `require` | `using` | `import` | `import` / `from módulo import algo` |
| Null | `null` / `undefined` | `null` | `null` | **`None`** |
| Booleanos | `true` / `false` | `true` / `false` | `true` / `false` | **`True` / `False`** (mayúscula) |
| Strings | `` `${x}` `` | `$"{x}"` | `"..." + x` | **`f"Hola {x}"`** |
| Listas | `[]` arrays | `List<T>` | `List<T>` | **`list`** — `[1, 2]` |
| Diccionarios | `{}` objetos | `Dictionary<K,V>` | `HashMap` | **`dict`** — `{"clave": valor}` |
| Funciones | `function f() {}` | `void F()` | `void f()` | **`def f():`** |
| Clases | `class` | `class` | `class` | **`class Nombre:`** — `self` es como `this` (explícito) |
| Ejecutar | `node archivo.js` | `dotnet run` | `java Main` | **`python -m paquete.modulo`** |

**`self` en clases:** equivale a `this` en JS/C#/Java, pero lo pasas explícitamente en la definición. Al llamar `obj.metodo()` Python inyecta `obj` como `self`.

**Type hints:** `def suma(a: int, b: int) -> int:` no fuerzan tipos en tiempo de ejecución; sirven para legibilidad y herramientas (IDE, mypy).

---

## 2. Cómo se organiza este proyecto

```
BMO/
├── src/
│   ├── main.py               # Orquestador: hilos, cámara, lógica, UI
│   ├── config/runtime.py     # Variables de entorno (cámara, mic, LLM, etc.)
│   ├── brain/
│   │   ├── brain.py          # LLM (Ollama), prompts, pipeline streaming → TTS
│   │   └── classifier.py     # Clasifica preguntas → ajusta tokens y longitud
│   ├── voice/voice.py        # Micrófono (VAD), Whisper (STT), Piper (TTS)
│   ├── vision/
│   │   ├── vision.py         # Cámara, Haar Cascade + FaceEmbedder
│   │   └── embedder.py       # ONNX: extrae embeddings faciales de 512 dims
│   ├── display/display.py    # Ventana OpenCV con estados animados
│   └── memory/register.py   # JSON de personas, embeddings, historial
├── data/
│   ├── memory.json           # Personas registradas, embeddings, historial
│   ├── face_model.onnx       # Modelo ONNX para reconocimiento facial
│   └── brain_context.txt     # Contexto extra inyectable sin tocar código
├── voices/                   # Modelos Piper TTS (.onnx)
├── assets/faces/             # PNG por estado (idle, speaking, thinking…)
├── scripts/                  # Utilidades (descargar modelo, listar mics…)
└── requirements.txt
```

**Flujo en tiempo de ejecución:**

1. `python -m src.main` → ejecuta `main()` en `src/main.py`.
2. `AgenteBMO` crea `DisplayBMO`, `VisionBMO`, `VozBMO`.
3. **Hilo cámara:** lee frames → `vision.procesar_rostro()` (Haar + ONNX) → actualiza `_nombre_actual`.
4. **Hilo lógica:** escucha (`voz.escuchar`) → `classifier.categorizar_pregunta` → `brain.responder_con_tts` (LLM streaming + cola TTS).
5. **Hilo principal:** `display.tick()` — dibuja la ventana.

---

## 3. Sintaxis mínima que verás en este repo

```python
# Comentario de una línea

"""Docstring: texto entre triple comillas al inicio de archivo o función."""

# Variables y tipos
nombre = "BMO"
activo = True
lista  = [1, 2, 3]
datos  = {"clave": "valor"}

# Condicional
if activo:
    print("encendido")
elif nombre == "BMO":
    print("soy BMO")
else:
    print("otro")

# Bucles
for i in range(5):          # 0..4
    print(i)

for clave, valor in datos.items():
    print(clave, valor)

# Listas por comprensión
cuadrados = [x * x for x in range(10) if x % 2 == 0]

# try / except
try:
    x = 1 / 0
except ZeroDivisionError as e:
    print("Error:", e)
finally:
    print("siempre se ejecuta")

# Context manager (abre y cierra automáticamente)
with open("archivo.txt", "r", encoding="utf-8") as f:
    contenido = f.read()
```

---

## 4. Archivos, carpetas y rutas (`pathlib`)

```python
from pathlib import Path

# Crear carpeta si no existe
Path("data").mkdir(parents=True, exist_ok=True)

# Leer y escribir texto
texto = Path("data/brain_context.txt").read_text(encoding="utf-8")
Path("salida.txt").write_text("hola", encoding="utf-8")

# Verificar si existe
if Path("data/face_model.onnx").exists():
    print("modelo disponible")
```

`__pycache__/` y archivos `.pyc` son bytecode generado automáticamente por Python. No los edites ni los borres manualmente.

---

## 5. Entornos virtuales y dependencias

```bash
# Crear entorno virtual
python -m venv .venv

# Activar (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activar (Linux / macOS / RPi)
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

**Dependencias principales del proyecto:**

| Paquete | Para qué |
|---------|----------|
| `faster-whisper` | STT (reconocimiento de voz) |
| `piper-tts` | TTS (síntesis de voz) |
| `sounddevice` | Captura y reproducción de audio |
| `opencv-python` | Cámara y detección de caras |
| `onnxruntime` | Inferencia del modelo facial ONNX |
| `ollama` | Cliente para el LLM local |
| `numpy` | Operaciones vectoriales (embeddings) |
| `hypothesis` | Property-based testing |

---

## 6. Concurrencia: `threading`

BMO usa tres hilos en paralelo. Cada uno ejecuta una función de forma independiente:

```python
# En main.py
threading.Thread(target=self._loop_camara, daemon=True).start()
threading.Thread(target=self._loop_logica, daemon=True).start()
# El hilo principal ejecuta display.tick()
```

- **`daemon=True`:** el hilo se detiene automáticamente cuando el proceso principal termina.
- **`threading.Lock()`:** evita que dos hilos modifiquen la misma variable al mismo tiempo.

```python
# Ejemplo de uso del lock en main.py
with self._lock_camara:
    nombre = self._nombre_actual   # lectura segura
```

Sin el lock, un hilo podría leer `_nombre_actual` mientras otro lo está escribiendo, causando datos inconsistentes.

---

## 7. Módulos clave — qué tocar para qué

| Objetivo | Archivo | Qué cambiar |
|----------|---------|-------------|
| Personalidad y prompts de BMO | `src/brain/brain.py` | `SYSTEM_PROMPT`, `RESPUESTAS_PREDEFINIDAS`, `SALUDOS_*` |
| Longitud de respuestas por tipo | `src/brain/classifier.py` | `NUM_PREDICT_MAP`, `LENGTH_HINT_MAP`, patrones regex |
| Parámetros del LLM (temperatura, tokens) | `src/config/runtime.py` | Variables `LLM_*` o env vars `BMO_LLM_*` |
| Contexto extra sin tocar código | `data/brain_context.txt` | Editar el archivo (se recarga automáticamente) |
| Reconocimiento facial | `src/vision/vision.py` | Umbral coseno (`threshold` en `best_match`) |
| Modelo ONNX de embeddings | `src/vision/embedder.py` | Preprocesamiento, normalización |
| Micrófono / Whisper / TTS | `src/voice/voice.py` | Umbrales VAD, modelo Whisper, silencio TTS |
| Animación de la pantalla | `src/display/display.py` | `FPS_ANIM`, estados, colores fallback |
| Flujo principal / nuevos hilos | `src/main.py` | `AgenteBMO`, `_ciclo_escucha`, `_registrar_persona` |
| Memoria y persistencia | `src/memory/register.py` | Formato JSON, `MAX_TURNS`, `ANON_MAX_TURNS` |

---

## 8. Parámetros del LLM — qué hace cada uno

Todos viven en `src/config/runtime.py` y se pueden sobreescribir con variables de entorno `BMO_LLM_*` sin tocar código.

### 8.1 Temperatura (`BMO_LLM_TEMPERATURE`) — valor actual: `0.5`

Controla qué tan predecible o creativa es la respuesta. El modelo calcula una probabilidad para cada posible siguiente palabra; la temperatura escala esas probabilidades:

```
0.0  → siempre elige la palabra más probable (robótico, repetitivo)
0.3  → muy conservador, respuestas seguras y predecibles
0.5  → equilibrio: coherente, pocas alucinaciones  ← BMO usa esto
0.7  → más variedad natural, algo más creativo
1.0  → mucha variedad, puede inventar cosas
1.5+ → muy creativo, pierde coherencia fácilmente
```

**Analogía:** es el "nivel de confianza" al hablar. Con 0.0 BMO siempre diría exactamente lo mismo ante la misma pregunta. Con 1.5 inventaría datos con total seguridad.

### 8.2 Top-K (`BMO_LLM_TOP_K`) — valor actual: `40`

En cada paso, el modelo solo considera las K palabras más probables y descarta el resto antes de aplicar temperatura:

```
10  → muy conservador, vocabulario limitado
40  → estándar, buen balance  ← BMO usa esto
60  → más variedad de vocabulario
100 → mucha variedad, puede sonar raro
```

**Analogía:** limitar el diccionario disponible. Con top_k=10 solo usa las palabras más obvias.

### 8.3 Top-P (`BMO_LLM_TOP_P`) — valor actual: `0.85`

Complementa top_k: elige las palabras cuyas probabilidades acumuladas suman hasta P. Si las primeras 5 palabras ya suman 0.85 de probabilidad, solo usa esas 5 aunque top_k sea 40:

```
0.8  → más conservador  ← BMO usa 0.85
0.9  → estándar
0.95 → más variedad
```

### 8.4 Num-Predict (`BMO_LLM_NUM_PREDICT`) — fallback: `150`

Máximo de tokens (≈ palabras o fragmentos) por respuesta. **El clasificador sobreescribe este valor** según el tipo de pregunta. El fallback solo se usa si el clasificador falla.

En RPi5 con Qwen 2.5:1.5b, cada token tarda ~0.15s:
- 40 tokens (saludo) → ~6s
- 100 tokens (factual) → ~15s
- 200 tokens (explicación) → ~30s

### 8.5 Repeat-Penalty (`BMO_LLM_REPEAT_PENALTY`) — valor actual: `1.15`

Penaliza que el modelo repita palabras que ya usó en la misma respuesta:

```
1.0  → sin penalización (puede repetirse mucho)
1.15 → estándar para conversación  ← BMO usa esto
1.3+ → muy agresivo, puede sonar forzado
```

### 8.6 Num-Thread (`BMO_LLM_NUM_THREAD`) — valor actual: `4`

Cuántos núcleos del procesador usa Ollama. RPi5 tiene 4 núcleos físicos. Usar 4 deja margen para los otros hilos (cámara, audio, display).

### 8.7 Keep-Alive (`BMO_LLM_KEEP_ALIVE`) — valor actual: `-1`

```
-1  → el modelo nunca se descarga de RAM  ← recomendado para feria
 0  → se descarga inmediatamente tras cada respuesta
300 → se descarga tras 5 minutos sin uso
```

---

## 9. El clasificador de preguntas (`src/brain/classifier.py`)

Antes de llamar al LLM, el clasificador analiza el texto y decide cuántos tokens usar y qué instrucción de longitud darle al modelo. Esto evita que BMO genere respuestas largas para preguntas simples.

```python
from src.brain.classifier import num_predict_para, length_hint_para

num_predict_para("hola BMO")         # → 40
length_hint_para("hola BMO")         # → "Responde en UNA sola oración corta."

num_predict_para("explícame la IA")  # → 200
length_hint_para("explícame la IA")  # → "Explica en 3 oraciones: idea principal..."
```

**Categorías y tokens actuales:**

| Categoría | Patrón detectado | Tokens | Instrucción al modelo |
|-----------|-----------------|--------|-----------------------|
| `GREETING` | "hola", "bye", "gracias", "dale" | 40 | 1 oración corta |
| `OPINION` | "qué piensas", "te gusta", "qué opinas" | 80 | 2 oraciones directas |
| `COMPARE` | "diferencia entre", "vs", "cuál es mejor" | 120 | 2-3 oraciones |
| `FACTUAL` | "qué es", "quién es", "cuándo", "dónde" | 100 | 2 oraciones, sin inventar |
| `TECHNICAL` | "código", "python", "api", "bug", "función" | 180 | 3 oraciones claras |
| `EXPLAIN` | "explícame", "cómo funciona", "por qué" | 200 | 3 oraciones estructuradas |
| `CREATIVE` | "cuento", "poema", "lista", "inventa" | 280 | 4-5 oraciones |
| `SIMPLE` | (default, sin patrón claro) | 100 | 2 oraciones directas |

**Para agregar una categoría nueva:**
1. Agrega la constante en `QueryCategory`
2. Agrega el valor en `NUM_PREDICT_MAP`
3. Agrega la instrucción en `LENGTH_HINT_MAP`
4. Agrega el patrón regex y el `if re.search(...)` en `categorizar_pregunta`

**Cómo llega la instrucción al modelo:** el `length_hint` se inyecta en el mensaje del usuario (no en el system prompt), así el system prompt permanece fijo entre llamadas y Ollama puede cachear su procesamiento:

```python
# En brain.py — el contexto dinámico va en el mensaje, no en el system
partes_contexto.append(f"[Instrucción: {length_hint}]")
mensaje_con_contexto = "\n".join(partes_contexto) + "\n" + mensaje
```

---

## 10. Reconocimiento facial ONNX (`src/vision/`)

### Por qué se migró de LBPH a ONNX

**LBPH (antes):** comparaba histogramas de píxeles. Frágil con cambios de iluminación, ángulo o distancia.

**ONNX embeddings (ahora):** una red neuronal (MobileFaceNet) convierte cada cara en un vector de 512 números. Dos fotos de la misma persona producen vectores similares aunque la iluminación cambie.

### Cómo funciona

```python
# embedder.py — extracción
embedding = embedder.extract(roi_bgr)   # → array float32 de shape (512,)

# embedder.py — comparación
similitud = np.dot(embedding_nuevo, embedding_guardado)  # cosine similarity
# Si similitud >= 0.55 → misma persona
```

### Modo degradado

Si `data/face_model.onnx` no existe, BMO arranca igual pero sin reconocimiento facial. Detecta caras (Haar Cascade) pero no identifica a nadie. Para activar el reconocimiento:

```bash
python scripts/download_face_model.py
```

### Registro de una persona nueva

Cuando alguien dice "me llamo X":
1. BMO captura 25 fotos del rostro en BGR (del frame original, no en escala de grises)
2. Extrae el embedding de cada foto con ONNX
3. Promedia los embeddings válidos y normaliza L2
4. Guarda el embedding promedio en `data/memory.json`
5. A partir de ese momento, al ver esa cara calcula similitud coseno y la reconoce

---

## 11. Memoria y contexto (`src/memory/register.py`)

### Caché en memoria

El módulo mantiene un caché en RAM para evitar leer el JSON del disco en cada llamada (importante en RPi5 con SD card):

```python
_memoria_cache: dict | None = None

def _load() -> dict:
    global _memoria_cache
    if _memoria_cache is not None:
        return _memoria_cache   # lectura desde RAM, instantánea
    # ... leer del disco solo si el caché está vacío

def _save(data: dict):
    # ... escribir al disco
    _memoria_cache = None   # invalidar caché tras escritura
```

### Estructura de `data/memory.json`

```json
{
  "_anonimo": {
    "turnos_recientes": [
      {"user": "qué es un animal", "assistant": "Un animal es..."},
      {"user": "qué es un perro",  "assistant": "Un perro es..."}
    ]
  },
  "0": {
    "nombre": "Sambrano",
    "visitas": 3,
    "ultima_vez": "2026-04-19 00:32:54",
    "resumen": "Usuario: hola | BMO: hola Sambrano! / ...",
    "turnos_recientes": [
      {"user": "hola", "assistant": "hola Sambrano!"}
    ],
    "embeddings": [[0.021, -0.134, 0.887, "..."]]
  }
}
```

### Sesión con nombre (persona registrada)

BMO ve la cara → calcula similitud coseno → reconoce a Sambrano → inyecta el resumen en el mensaje → responde con contexto de conversaciones anteriores.

### Sesión anónima (sin nombre)

Los últimos 6 turnos se guardan en `_anonimo` con buffer circular. Cuando llega el turno 7, el más antiguo se descarta. Esto permite que BMO lleve el hilo aunque no sepa quién habla.

```python
# Constantes en register.py
MAX_TURNS      = 6   # turnos por persona registrada
ANON_MAX_TURNS = 6   # turnos en sesión anónima
```

---

## 12. Pipeline LLM → TTS (`src/brain/brain.py`)

El pipeline permite que BMO empiece a hablar antes de terminar de pensar:

```
LLM genera tokens → buffer acumula → detecta puntuación → encola oración
                                                              ↓
                                              Worker TTS reproduce oración
                                              (en paralelo con el LLM)
```

```python
# Simplificado de brain.py
def _tts_worker():
    while True:
        with tts_lock:
            texto = tts_queue.pop(0) if tts_queue else None
        if texto:
            hablar_fn(texto)          # reproduce la oración
        elif tts_done.is_set():
            break
        else:
            time.sleep(0.05)          # espera sin bloquear

# El stream del LLM encola oraciones completas
for chunk in ollama.chat(..., stream=True):
    sentence_buffer += chunk["message"]["content"]
    completas, resto = _extraer_oraciones(sentence_buffer)
    for oracion in completas:
        tts_queue.append(oracion)     # el worker la reproduce en paralelo
```

**System prompt fijo:** el `SYSTEM_PROMPT` no cambia entre llamadas. El contexto dinámico (nombre de persona, historial, instrucción de longitud) va en el mensaje del usuario. Esto permite que Ollama cachee el procesamiento del system prompt y reduzca la latencia del primer token.

---

## 13. Viabilidad en Raspberry Pi 5 8GB

BMO es viable en RPi5. Consumo estimado:

| Componente | RAM |
|-----------|-----|
| Sistema operativo | ~0.5 GB |
| Python + librerías | ~0.3 GB |
| Whisper base (STT) | ~1.0 GB |
| Piper TTS | ~0.4 GB |
| OpenCV + ONNX | ~0.3 GB |
| Qwen 2.5:1.5b (LLM) | ~3.7 GB |
| **Total** | **~6.2 GB** |
| **Buffer disponible** | **~1.8 GB** |

**Latencia esperada:**
- STT (Whisper base, 10s de audio): 6-10s
- LLM saludo (40 tokens): ~6s
- LLM factual (100 tokens): ~15s
- LLM explicación (200 tokens): ~30s
- TTS por oración: ~2-3s

**Optimizaciones ya activas para RPi5:**
- `VISION_PROCESS_EVERY_N = 2` — procesa 1 de cada 2 frames (~15 FPS efectivos, menos CPU)
- `LLM_TEMPERATURE = 0.5` — conservador, menos alucinaciones
- `LLM_TOP_P = 0.85` — más conservador que el estándar 0.9
- Caché en memoria en `register.py` — evita lecturas repetidas de SD card
- System prompt fijo — Ollama cachea el prefill entre llamadas

**Instalación en RPi5:**
```bash
# Instalar Ollama
curl https://ollama.ai/install.sh | sh

# Descargar modelo LLM
ollama pull qwen2.5:1.5b

# Descargar modelo facial ONNX
python scripts/download_face_model.py

# Instalar dependencias Python
pip install -r requirements.txt

# Ejecutar
python -m src.main
```

---

## 14. Cómo agregar una función nueva

1. **Define el objetivo** — ej.: "BMO responde diferente si detecta más de una cara".
2. **Elige el lugar** — ¿ocurre en la cámara? → `_loop_camara` en `main.py`. ¿Al procesar texto? → `_ciclo_escucha` o `brain.py`.
3. **Implementa una función pequeña** y llámala desde el flujo existente.
4. **Prueba** desde la raíz del proyecto: `python -m src.main`.
5. Si falla, lee el **traceback de abajo hacia arriba** — la última línea es el error, las de arriba son la cadena de llamadas.

**Ejemplo — detectar palabra clave en `_ciclo_escucha`:**

```python
# En main.py, dentro de _ciclo_escucha, después de obtener `texto`
if "apagado" in texto.lower():
    self.voz.hablar("Hasta luego!")
    self._running = False
    return
```

**Ejemplo — agregar una respuesta predefinida en `brain.py`:**

```python
# En RESPUESTAS_PREDEFINIDAS
r"(?:cuántos|cuantos)\s+años\s+tienes":
    "¡Tengo la edad que Zambrano me dio! Soy un robot, así que no envejezco.",
```

---

## 15. Herramientas útiles

```bash
# Verificar imports, audio y Ollama sin iniciar BMO completo
python scripts/smoke_check.py

# Descargar el modelo ONNX para reconocimiento facial
python scripts/download_face_model.py

# Listar micrófonos disponibles
python scripts/list_mics.py

# Listar dispositivos de audio
python scripts/list_audio.py
```

**`data/brain_context.txt`** — con `BMO_BRAIN_CONTEXT_HOT_RELOAD=true` (activo por defecto), editar este archivo actualiza el contexto de BMO sin reiniciar. Útil para agregar información sobre el evento o la feria.

---

## 16. Depuración rápida

```python
# Agregar trazas temporales
import logging
log = logging.getLogger("BMO")
log.info("valor de x: %s", x)

# O simplemente
print(f"[DEBUG] nombre_actual={self._nombre_actual}")
```

- **Traceback:** lee de abajo hacia arriba. La última línea es el error; las de arriba son la cadena de llamadas.
- **ImportError:** casi siempre es ejecutar el script desde la carpeta incorrecta. Siempre ejecuta desde `BMO/` con `python -m src.main`.
- **`ModuleNotFoundError: onnxruntime`:** falta instalar dependencias. Ejecuta `pip install -r requirements.txt`.
- **`FileNotFoundError: data/face_model.onnx`:** ejecuta `python scripts/download_face_model.py`.

---

## 17. Recursos oficiales

- Python tutorial: [https://docs.python.org/3/tutorial/](https://docs.python.org/3/tutorial/)
- `pathlib`: [https://docs.python.org/3/library/pathlib.html](https://docs.python.org/3/library/pathlib.html)
- `threading`: [https://docs.python.org/3/library/threading.html](https://docs.python.org/3/library/threading.html)
- ONNX Runtime: [https://onnxruntime.ai/docs/](https://onnxruntime.ai/docs/)
- Ollama API: [https://github.com/ollama/ollama/blob/main/docs/api.md](https://github.com/ollama/ollama/blob/main/docs/api.md)

## 18. Lecciones aprendidas: Debugging de BMO en producción

### 18.1 Caso real: BMO dejó de funcionar bien

**Síntomas reportados:**
- Respuestas incorrectas (ej: "colores de Colombia: rojo, verde y blanco" en lugar de "amarillo, azul y rojo")
- Latencia muy alta (35+ segundos)
- Pérdida de streaming (generaba completo, luego hablaba completo)

**Investigación realizada:**
1. **Análisis de parámetros**: Comparamos configuración actual vs documentación de análisis previos
2. **Identificación de cambios**: Encontramos que se habían modificado parámetros que funcionaban perfectamente
3. **Restauración sistemática**: Volvimos a la configuración original exitosa

### 18.2 Parámetros que se habían modificado incorrectamente

| Parámetro | Valor original (exitoso) | Valor problemático | Efecto del cambio |
|-----------|-------------------------|-------------------|-------------------|
| `temperature` | 0.75 | 0.2 | Respuestas robóticas, pérdida de naturalidad |
| `top_k` | 50 | 10 | Vocabulario muy limitado, respuestas pobres |
| `top_p` | 0.90 | 0.7 | Demasiado conservador |
| `num_predict` | 100 | 30 | Respuestas cortadas, información incompleta |
| `repeat_penalty` | 1.1 | 1.2 | Demasiado agresivo contra repeticiones |

### 18.3 Configuración final que funciona perfectamente

```bash
# .env - Configuración ORIGINAL que funcionaba
BMO_LLM_NUM_PREDICT=100
BMO_LLM_TEMPERATURE=0.75
BMO_LLM_TOP_K=50
BMO_LLM_TOP_P=0.90
BMO_LLM_REPEAT_PENALTY=1.1
```

**Resultados tras la corrección:**
- ✅ Latencia: 4-6 segundos (vs 35+ segundos antes)
- ✅ Streaming restaurado: habla mientras genera
- ✅ Respuestas más precisas (aunque aún necesita mejoras en datos factuales)

### 18.4 System prompt optimizado

```python
SYSTEM_PROMPT = (
    "Eres BMO, un robot asistente amigable creado por Zambrano. "
    "Responde en español de forma natural y útil. "
    "Si te preguntan sobre Hora de Aventura, usa tu conocimiento de la serie. "
    "Para datos factuales (banderas, geografía, historia), sé muy preciso. "
    "Si no estás 100% seguro de un dato, di 'No estoy seguro de esa información'. "
    "Sé directo pero amigable, máximo 2-3 oraciones."
)
```

### 18.5 Contexto factual para evitar alucinaciones

En `data/brain_context.txt` se agregó información factual básica:

```
Datos factuales importantes (para evitar errores):
- Bandera de Colombia: amarillo, azul y rojo (franjas horizontales)
- Bandera de México: verde, blanco y rojo (franjas verticales)
- Bandera de España: rojo, amarillo y rojo (franjas horizontales)
```

### 18.6 Streaming vs No-streaming: Impacto en experiencia

**Sin streaming (problemático):**
```
Usuario pregunta → [8s pensando] → [4s hablando] = 12s total
Experiencia: "BMO se quedó colgado, luego habló de golpe"
```

**Con streaming (correcto):**
```
Usuario pregunta → [2s] primera oración → [2s] segunda oración = 4s total
Experiencia: "BMO empezó a responder inmediatamente"
```

### 18.7 Metodología de debugging aplicada

1. **Comparación histórica**: Revisar documentación de configuraciones que funcionaban
2. **Análisis de cambios**: Identificar qué se modificó entre versión buena y mala
3. **Restauración incremental**: Volver paso a paso a la configuración exitosa
4. **Validación**: Probar que los cambios efectivamente resuelven el problema

### 18.8 Reglas para futuras modificaciones

**❌ NO hacer:**
- Cambiar parámetros del LLM sin documentar los valores originales
- Optimizar "a ciegas" sin medir el impacto real
- Asumir que "más rápido = mejor" sin considerar calidad

**✅ SÍ hacer:**
- Documentar configuración actual antes de cambios
- Hacer cambios incrementales y medir impacto
- Mantener respaldo de configuraciones que funcionan bien
- Probar con casos de uso reales (preguntas sobre banderas, etc.)

### 18.9 Configuración de producción recomendada

Para un BMO estable en feria tecnológica:

```bash
# Parámetros probados y estables
BMO_LLM_MODEL=qwen2.5:1.5b
BMO_LLM_NUM_PREDICT=100
BMO_LLM_TEMPERATURE=0.75
BMO_LLM_TOP_K=50
BMO_LLM_TOP_P=0.90
BMO_LLM_REPEAT_PENALTY=1.1
BMO_LLM_KEEP_ALIVE=-1

# Optimizaciones para RPi5
BMO_VISION_PROCESS_EVERY_N=2
BMO_LLM_NUM_THREAD=4
```

**Rendimiento esperado:**
- Saludos: ~4-6 segundos
- Preguntas factuales: ~6-10 segundos  
- Explicaciones: ~15-20 segundos
- Streaming activo: empieza a hablar en ~2 segundos

### 18.10 Monitoreo en tiempo real

**Logs importantes a observar:**
```
[LLM→TTS] 'respuesta'  # Confirma que streaming funciona
[TTS] 4.0s            # Tiempo de síntesis por oración
HTTP Request: POST    # Latencia de llamada a Ollama
```

**Señales de problemas:**
- Latencia > 10s para preguntas simples
- Ausencia de logs `[LLM→TTS]` (streaming roto)
- Respuestas obviamente incorrectas (alucinaciones)

---

BMO tiene tres hilos: **cámara** (Haar + ONNX embeddings), **lógica** (VAD → Whisper → clasificador → LLM → TTS) y **display** (animación). La memoria persiste en `data/memory.json` con caché en RAM. El clasificador de preguntas ajusta tokens e instrucciones de longitud antes de cada llamada al LLM. El system prompt es fijo para aprovechar el caché de Ollama.

Los archivos más importantes para modificar el comportamiento de BMO son `brain.py` (personalidad y prompts), `classifier.py` (longitud de respuestas) y `runtime.py` (parámetros del LLM via variables de entorno `BMO_*`).
