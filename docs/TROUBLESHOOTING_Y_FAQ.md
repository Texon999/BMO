# ❓ TROUBLESHOOTING Y FAQ - BMO

**Documento**: Solución de problemas y preguntas frecuentes  
**Fecha**: 30/04/2026  
**Versión**: 1.0

---

## 📋 TABLA DE CONTENIDOS

1. [Problemas de Inicio](#problemas-de-inicio)
2. [Problemas de Audio](#problemas-de-audio)
3. [Problemas de Cámara](#problemas-de-cámara)
4. [Problemas de Respuestas](#problemas-de-respuestas)
5. [Problemas de Performance](#problemas-de-performance)
6. [Problemas de Memoria](#problemas-de-memoria)
7. [Preguntas Frecuentes](#preguntas-frecuentes)

---

## 🔴 PROBLEMAS DE INICIO

### P1: "ModuleNotFoundError: No module named 'ollama'"

**Síntoma**:
```
Traceback (most recent call last):
  File "src/main.py", line X, in <module>
    import ollama
ModuleNotFoundError: No module named 'ollama'
```

**Causa**: No instalaron las dependencias

**Solución**:
```bash
# 1. Verificar que Ollama está corriendo
ollama serve  # Debe estar en otra terminal

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Si sigue fallando:
pip install ollama --upgrade

# 4. Verificar Ollama en otra terminal
curl http://localhost:11434/api/tags
```

---

### P2: "Connection refused: ('127.0.0.1', 11434)"

**Síntoma**:
```
ollama.ResponseError: ('Connection refused',
```

**Causa**: Ollama no está ejecutándose

**Solución**:
```bash
# Terminal 1: Iniciar Ollama
ollama serve

# Terminal 2 (después de que Terminal 1 diga "Listening on"):
python src/main.py
```

**Verificar que funciona**:
```bash
# En Terminal 3
curl http://localhost:11434/api/tags
# Debe mostrar lista de modelos
```

---

### P3: "RuntimeError: No cameras detected"

**Síntoma**:
```
RuntimeError: No cameras detected
```

**Causa**: Cámara USB no conectada, driver no instalado, o índice incorrecto

**Solución A** (Verificar dispositivos):
```bash
python scripts/list_audio.py  # También lista cámaras
```

**Solución B** (Probar diferentes índices):
```json
{
  "camera_index": 0,  // Probar 0, 1, 2...
}
```

**Solución C** (Funcionamiento sin cámara):
```bash
# BMO funciona sin cámara (degraded mode)
# Simplemente no reconoce rostros
# No hacer nada, BMO inicia igual
```

---

### P4: "FileNotFoundError: data/face_model.onnx"

**Síntoma**:
```
FileNotFoundError: [Errno 2] No such file or directory: 'data/face_model.onnx'
```

**Causa**: Modelo ONNX no descargado

**Solución**:
```bash
# 1. Opción: Descargar modelo
python scripts/download_face_model.py

# 2. Opción: Ejecutar sin reconocimiento facial
# Si no lo descarga, BMO igual funciona sin ONNX
# Solo detecta caras pero no las reconoce
```

---

### P5: "JSONDecodeError in config.json"

**Síntoma**:
```
json.JSONDecodeError: Expecting value: line X column Y
```

**Causa**: `config.json` tiene error de sintaxis JSON

**Solución**:
```bash
# 1. Abrir config.json en editor
# 2. Buscar errores comunes:
# - Comas faltantes en el final
# - Comillas sin cerrar
# - Punto y coma en lugar de coma

# Estructura correcta:
{
  "key1": "value1",      // ← Coma
  "key2": "value2"       // ← SIN coma (es la última)
}

# 3. Validar online: https://jsonlint.com/
```

---

## 🔊 PROBLEMAS DE AUDIO

### P6: "No microphones found"

**Síntoma**:
```
[VOICE] No microphones found
```

**Causa**: Micrófono no conectado o driver no instalado

**Solución A** (Verificar micrófonos):
```bash
# Windows
python scripts/list_audio.py

# Linux
arecord -l

# macOS
system_profiler SPAudioDataType
```

**Solución B** (Especificar micrófono):
```json
{
  "mic_device": 1  // Cambiar número
}
```

**Solución C** (Fallback a micrófono por defecto):
```json
{
  "mic_device": null  // null = auto-detect
}
```

---

### P7: "No audio output / No sound"

**Síntoma**:
- BMO responde en log pero no se escucha
- `print("BMO: hola")` aparece pero nada de audio

**Causa**: Altavoz desconectado, índice incorrecto, o Piper no funciona

**Solución A** (Verificar altavoces):
```bash
python scripts/list_audio.py
```

**Solución B** (Cambiar dispositivo de salida):
```json
{
  "output_device": 0  // Probar índices diferentes
}
```

**Solución C** (Probar Piper directamente):
```bash
python scripts/test_audio.py
```

**Solución D** (Sin TTS - solo texto):
```bash
# BMO funcionará sin audio (degradado)
# Salida solo por consola
# Esto es fallback automático
```

---

### P8: "Whisper transcription failing"

**Síntoma**:
```
[STT] Sin habla reconocida
```

**Causa**: 
- Micrófono con ruido de fondo muy alto
- Umbral VAD demasiado alto
- Audio muy bajo o muy alto

**Solución A** (Reducir ruido):
```bash
# Grabar en lugar silencioso
# Reducir música, fans de PC, etc.
```

**Solución B** (Ajustar VAD**):
```json
{
  "vad_threshold": 0.015  // Actual
  // Probar: 0.01 (más sensible) o 0.02 (menos sensible)
}
```

**Solución C** (Cambiar modelo Whisper):
```json
{
  "whisper_model": "base"   // Actual
  // Probar: "small" si tenés RAM
}
```

---

### P9: "Audio clipping / Distortion"

**Síntoma**:
- Audio suena cortado, distorsionado, o duplicado

**Causa**: 
- Volumen muy alto
- Buffer de audio incorrecto
- Tasa de muestreo incompatible

**Solución A** (Reducir volumen):
```bash
# Sistema operativo → bajar volumen del altavoz al 70%
```

**Solución B** (Aumentar silencio):
```python
# En voice.py
silence_pre = np.zeros(int(0.1 * sr))    # ← Aumentar de 0.05
silence_post = np.zeros(int(1.0 * sr))   # ← Aumentar de 0.5
```

---

## 📷 PROBLEMAS DE CÁMARA

### P10: "Haar Cascade no detecta rostros"

**Síntoma**:
```
[VISION] Detectadas 0 caras
```

**Causa**: 
- Iluminación insuficiente
- Rostro muy lejano
- Parámetros de Haar incorrectos

**Solución A** (Iluminación):
```bash
# Mejor iluminación
# Cara frente a la cámara
# Luz frontal
```

**Solución B** (Ajustar Haar Cascade):
```python
# En vision.py, función procesar_rostro()
faces = self.face_cascade.detectMultiScale(
    gray,
    scaleFactor=1.1,      # ← Probar 1.05-1.15
    minNeighbors=8,       # ← Probar 5-12
    minSize=(60, 60)      # ← Probar (30, 30) o (80, 80)
)
```

| Parámetro | Bajo | Alto | Efecto |
|-----------|------|------|--------|
| scaleFactor | 1.01 | 1.3 | Lento ↔ Rápido |
| minNeighbors | 3 | 15 | Muchos detectos ↔ Pocos detectos |
| minSize | (10,10) | (100,100) | Caras lejanas ↔ Solo caras grandes |

---

### P11: "Reconocimiento facial falla"

**Síntoma**:
```
[VISION] Similitud: 0.42 (< 0.55 threshold)
# O todo se reconoce como la misma persona
```

**Causa**: 
- Umbral de similitud incorrecto
- Iluminación diferente al registrarse
- Ángulo de rostro muy diferente

**Solución A** (Ajustar umbral):
```python
# En embedder.py, función best_match()
if best_sim >= 0.55:  # ← Cambiar threshold
    return (best_name, best_sim)

# Probar:
# 0.50: Más reconocimientos (falsos positivos)
# 0.55: Actual (balanceado)
# 0.60: Menos reconocimientos (falsos negativos)
```

**Solución B** (Re-registrar rostro)**:
```bash
# Registrar persona de nuevo
# Con mejor iluminación y múltiples ángulos
```

**Solución C** (Logs detallados)**:
```python
# En vision.py
log.info(f"[VISION] Mejor coincidencia: {nombre} ({similitud:.3f})")
log.info(f"[VISION] Threshold: 0.55, aceptado: {similitud >= 0.55}")
```

---

## 💬 PROBLEMAS DE RESPUESTAS

### P12: "BMO da respuestas incorrectas"

**Síntoma**:
```
Usuario: "¿Cuál es la capital de Francia?"
BMO: "Es París... no espera, es Lyon"
```

**Causa**: 
- LLM tiene datos incorrectos en su entrenamiento
- Sistema prompt no tiene correcciones
- Temperatura muy alta

**Solución A** (Agregar corrección a brain_context.txt):
```txt
# data/brain_context.txt
CORRECCIONES DE HECHOS:
- La capital de Francia es París
- No es Lyon, Marsella, o Estrasburgo
```

**Solución B** (Reducir temperatura):
```json
{
  "llm_temperature": 0.5  // De 0.75 a 0.5 (menos creativo)
}
```

**Solución C** (Aumentar tokens para más elaboración)**:
```json
{
  "llm_num_predict": 150  // De 100 a 150
}
```

---

### P13: "BMO responde cosas no solicitadas"

**Síntoma**:
```
Usuario: "Hola"
BMO: "Hola! Te diré que la capital de Francia es París..."
# (información no pedida)
```

**Causa**: 
- Temperatura muy alta
- System prompt muy verboso

**Solución A** (Reducir temperatura):
```json
{
  "llm_temperature": 0.3  // Más conservador
}
```

**Solución B** (Simplificar sistema prompt)**:
```python
# En brain.py, get_system_prompt()
# Reducir INFORMACIÓN_EXTRA
# Mantener solo esencial
```

---

### P14: "Respuestas se cortan abruptamente"

**Síntoma**:
```
Usuario: "¿Qué es un algoritmo?"
BMO: "Un algoritmo es una secuencia de pasos para..."
# Se corta aquí
```

**Causa**: 
- `num_predict` demasiado bajo
- Clasificación incorrecta de pregunta

**Solución A** (Aumentar tokens):
```json
{
  "llm_num_predict": 150  // De 100
}
```

**Solución B** (Revisar clasificación)**:
```python
# En classifier.py
# Verificar que "¿Qué es?" se clasifica como EXPLAIN
# EXPLAIN tiene 200 tokens, suficiente
```

---

### P15: "BMO responde lentamente"

**Síntoma**:
```
Usuario habla a las 12:00:00
BMO comienza respuesta a las 12:00:20 (20 segundos)
```

**Causa**: 
- LLM modelo muy grande o lento
- Hardware bajo rendimiento
- Muchos tokens configurados

**Solución A** (Reducir tokens):
```json
{
  "llm_num_predict": 50  // De 100 (respuestas muy cortas)
}
```

**Solución B** (Usar modelo más rápido):
```json
{
  "text_model": "qwen2.5:1.5b"  // Más pequeño y rápido
}
```

**Solución C** (Menos threads):
```json
{
  "llm_num_thread": 2  // De 4 (menos parallelismo pero menos CPU)
}
```

---

## ⚡ PROBLEMAS DE PERFORMANCE

### P16: "CPU usage 100%, RPi5 se calienta"

**Síntoma**:
```
htop muestra proceso Python usando 90%+ CPU
Temperatura: 70°C+
```

**Causa**: 
- `num_thread` demasiado alto
- Modelos muy grandes
- Todas las características activadas

**Solución A** (Reducir threads):
```json
{
  "llm_num_thread": 1  // De 4 (una a la vez)
}
```

**Solución B** (Usar modelo pequeño):
```json
{
  "text_model": "qwen2.5:1.5b"
  "whisper_model": "tiny"
}
```

**Solución C** (Deshabilitar visión):
```python
# En main.py
self.vision = None  # Sin reconocimiento facial
```

**Solución D** (Aumentar keep_alive timeout)**:
```json
{
  "llm_keep_alive": 300  // Libera RAM después de 5min inactividad
}
```

---

### P17: "RAM llena, crash por memoria"

**Síntoma**:
```
MemoryError: Unable to allocate X.XX GiB for array
```

**Causa**: 
- Modelo LLM muy grande
- Modelo Whisper muy grande
- Acumulación de historial de chat

**Solución A** (Reducir modelos):
```json
{
  "text_model": "qwen2.5:1.5b",
  "whisper_model": "base",
  "llm_keep_alive": 0  // Libera LLM inmediatamente después de usar
}
```

**Solución B** (Limpiar cache)**:
```bash
# Ollama libera memoria
ollama pull qwen2.5:1.5b

# O reiniciar Ollama
# Control+C en terminal donde corre ollama serve
```

**Solución C** (Ver RAM usado)**:
```bash
free -h  # Linux
wmic OS get TotalVisibleMemorySize,FreePhysicalMemory  # Windows
```

---

### P18: "GPU no se usa (solo CPU)"

**Síntoma**:
```
nvidia-smi muestra GPU ociosa
BMO usa 100% CPU en lugar de GPU
```

**Causa**: 
- Ollama no detecta GPU
- Driver NVIDIA/AMD no instalado

**Solución A** (Verificar GPU):
```bash
# NVIDIA
nvidia-smi

# AMD
rocm-smi
```

**Solución B** (Reinstalar Ollama con GPU)**:
```bash
# En Windows/Linux con NVIDIA
# Descargar versión GPU desde ollama.com
# O instalar NVIDIA CUDA Toolkit
```

---

## 🧠 PROBLEMAS DE MEMORIA

### P19: "BMO no recuerda conversaciones anteriores"

**Síntoma**:
```
Usuario: "Me llamo Juan"
BMO: "Hola Juan!"

Usuario (después): "¿Cómo me llamo?"
BMO: "No te he dicho que me llames de ninguna forma"
```

**Causa**: 
- Chat memory deshabilitado
- memory.json corrupto
- Sesión no guardada

**Solución A** (Verificar memory.json):
```bash
cat data/memory.json
# Debe contener entrada con "Juan"
```

**Solución B** (Habilitar chat memory)**:
```json
{
  "chat_memory": true  // Asegurar que está true
}
```

**Solución C** (Restaurar desde backup)**:
```bash
# Si memory.json está corrupto
cp data/memory.json.backup data/memory.json

# O, recrear vacío
echo '{}' > data/memory.json
```

---

### P20: "memory.json crece demasiado"

**Síntoma**:
```
data/memory.json > 50MB
BMO tarda cada vez más en guardar
```

**Causa**: 
- Demasiadas conversaciones guardadas
- MAX_TURNS configurado alto

**Solución A** (Reducir historiales):
```python
# En register.py
MAX_TURNS = 3  // De 6 (guardar menos turnos)
```

**Solución B** (Limpiar archivo)**:
```bash
# Respaldar primero
cp data/memory.json data/memory.json.old

# Recrear vacío
echo '{}' > data/memory.json

# Perderá historial pero se libera espacio
```

**Solución C** (Archivar memoria vieja)**:
```python
# En main.py, al apagar
def _apagar(self):
    import shutil
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy("data/memory.json", f"data/memory.{timestamp}.json")
    # Luego limpiar memory.json
```

---

## ❓ PREGUNTAS FRECUENTES

### P: ¿Puedo usar BMO sin cámara?

**R**: Sí, funcionará perfecto. Solo no reconocerá rostros. Todo lo demás (escuchar, responder, hablar) funciona igual.

---

### P: ¿Puedo usar BMO sin micrófono?

**R**: No. Necesita micrófono para escuchar. Sin micrófono, se queda esperando.

Workaround: Automatizar input con un script que inyecte texto sin necesidad de STT.

---

### P: ¿Cuál es la latencia mínima?

**R**: Con RPi5 8GB y qwen2.5:1.5b:
- Whisper: 0.5-2 segundos
- LLM: 5-10 segundos
- TTS: 1-2 segundos
- **Total: 7-14 segundos** desde que el usuario termina de hablar hasta que escucha respuesta

---

### P: ¿Puedo cambiar el modelo LLM a uno más grande?

**R**: Sí, pero:
- RPi5 8GB: máximo qwen2.5:3b
- PC 16GB: qwen2.5:7b
- Requerimientos de RAM aproximados:
  - 1.5b: 2GB
  - 3b: 4GB
  - 7b: 7GB

---

### P: ¿Cómo agrego múltiples idiomas?

**R**: 
1. Cambiar `WHISPER_LANG` en `config/runtime.py`
2. Whisper soporta 99 idiomas automáticamente
3. LLM entiende múltiples idiomas sin cambios

---

### P: ¿Puedo grabar las conversaciones?

**R**: Sí, modificar `_ciclo_escucha()`:
```python
with open("conversaciones.txt", "a") as f:
    f.write(f"Usuario: {texto}\n")
    f.write(f"BMO: {respuesta}\n\n")
```

---

### P: ¿Qué pasa si cierto el programa mientras procesa?

**R**: No pasa nada malo. BMO gracefully shutdown:
1. Guarda memoria actual
2. Cierra streams de audio/video
3. Libera recursos
4. Termina

---

### P: ¿Puedo ejecutar dos instancias de BMO?

**R**: No recomendado. Competirán por:
- Puerto 11434 de Ollama
- Micrófono
- Cámara
- GPU

Mejor: Una instancia principal + scripts que inyecten texto.

---

### P: ¿Ollama necesita internet?

**R**: 
- Primera descarga del modelo: SÍ (necesita internet)
- Ejecución posterior: NO (totalmente offline)
- Actualizaciones: NO necesarias (offline funciona indefinidamente)

---

### P: ¿Cómo borro a una persona registrada?

**R**: Editar `data/memory.json`:
```json
{
  "1": { "nombre": "Juan", ... },   // ← Borrar todo este bloque
  "2": { "nombre": "María", ... }   // ← Mantener
}
```

O usar script:
```python
import json
with open("data/memory.json", "r") as f:
    memoria = json.load(f)
del memoria["1"]  # Borrar persona con ID 1
with open("data/memory.json", "w") as f:
    json.dump(memoria, f)
```

---

### P: ¿Qué es un "hallucination" del LLM?

**R**: Cuando BMO inventa cosas:
```
Usuario: "¿Cuál es la capital de Marte?"
BMO: "Es New Olympus" ← INVENTADO (Marte no tiene capital)
```

**Cómo evitar**:
1. Reducir temperatura (0.3 en lugar de 0.75)
2. Agregar correcciones a `brain_context.txt`
3. Usar modelo más preciso (qwen2.5:3b en lugar de 1.5b)

---

### P: ¿Cómo hago que BMO olvide algo?

**R**: Borrar de `data/brain_context.txt`:

```txt
// ANTES
CORRECCIONES DE HECHOS:
- La capital de Francia es París
- Python fue inventado en 1991

// DESPUÉS (borrar la línea)
CORRECCIONES DE HECHOS:
- Python fue inventado en 1991
```

---

### P: ¿Es seguro que BMO acceda a internet?

**R**: BMO NO accede a internet por defecto (todo local). Si quieres agregar búsqueda web:

```python
# En brain.py
from duckduckgo_search import DDGS

# Búsqueda web (opcional)
if categoria == "factual":
    resultados = DDGS().text(texto, max_results=3)
    # Agregar a contexto
```

Pero sin esto, 100% offline.

---

## 🎯 TABLA DE DIAGNÓSTICO RÁPIDO

| Síntoma | Causa Probable | Solución |
|---------|---|---|
| BMO no inicia | Ollama no corre | `ollama serve` en otra terminal |
| Sin audio | Altavoz desconectado | Conectar altavoz |
| No reconoce voz | Micrófono ruidoso | Lugar silencioso |
| CPU 100% | Demasiados threads | Reducir `llm_num_thread` |
| RAM llena | Modelo muy grande | Usar modelo pequeño |
| Respuestas falsas | Temperatura alta | Reducir a 0.5 |
| No reconoce rostros | Luz insuficiente | Mejor iluminación |
| Olvida conversaciones | Memory disabled | Activar `chat_memory` |
| Muy lento | Modelo grande | Usar qwen2.5:1.5b |
| Muy creativo | Temperature alto | Reducir a 0.75 |

---

**Última actualización**: 30/04/2026  
**Problemas documentados**: 20+  
**Casos de uso cubiertos**: Todos  

Si el problema persiste: Agregar logs (`logging.DEBUG`) y compartir output.

