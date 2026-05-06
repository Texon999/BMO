# 🛠️ GUÍA PRÁCTICA DE MODIFICACIONES - BMO

**Documento**: Ejemplos prácticos de cómo modificar BMO sin romperlo  
**Fecha**: 30/04/2026  
**Versión**: 1.0

---

## 📋 ÍNDICE

1. [Modificaciones Simples (Config)](#1-modificaciones-simples)
2. [Modificaciones de Personalidad](#2-modificaciones-de-personalidad)
3. [Agregar Funcionalidades](#3-agregar-funcionalidades)
4. [Optimizaciones de Rendimiento](#4-optimizaciones)
5. [Debugging y Logs](#5-debugging)
6. [Qué NO Hacer](#6-qué-no-hacer)

---

## 1. MODIFICACIONES SIMPLES

### A. Cambiar la Personalidad de BMO

**Archivo**: `config.json`

```json
{
  "llm_temperature": 0.75,    // Cambiar a:
  "llm_temperature": 1.2      // Más creativo
}
```

**Efecto**:
- 0.3 = Muy conservador (respuestas predecibles)
- 0.75 = Balanceado (actual)
- 1.2 = Creativo (inventa más)
- 2.0 = Demasiado creativo (puede fallar)

**Prueba**:
```bash
# 1. Editar config.json
# 2. Sin reiniciar, decir: "cuéntame un chiste"
# 3. Compara con temperatura anterior
```

---

### B. Hacer Más Rápido o Más Lento

**Archivo**: `config.json`

```json
{
  "llm_num_predict": 100    // Máximo tokens por respuesta
}
```

**Valores**:
- `50`: Muy corto (~3-5 segundos) - bueno para saludos
- `100`: Normal (~8-10 segundos) - equilibrio
- `200`: Largo (~15-20 segundos) - explicaciones
- `500`: Muy largo (~40-50 segundos) - no recomendado

**Prueba**:
```bash
# 1. Poner 50
# 2. Preguntar: "¿Quién es Finn?"
# Resultado: Respuesta corta, muy rápido
```

---

### C. Cambiar el Micrófono o Altavoz

**Archivo**: `scripts/list_audio.py` (primero busca índices disponibles)

```bash
python scripts/list_audio.py
```

**Output**:
```
Microphones:
[0] USB Audio Device - NOVASTAR
[1] Realtek High Definition Audio
[2] Built-in Microphone

Speakers:
[0] Speakers (High Definition Audio Device)
[1] HDMI Output
```

**Cambiar en `config.json`**:

```json
{
  "camera_index": 0,
  "mic_device": 1,           // Cambiar de 0 a 1
  "output_device": 1         // Cambiar de 0 a 1
}
```

---

### D. Cambiar Modelo de STT (Reconocimiento de Voz)

**Archivo**: `config.json`

```json
{
  "whisper_model": "base"    // Opciones: tiny, base, small, medium
}
```

| Modelo | Velocidad | Precisión | RAM | Recomendado |
|--------|-----------|-----------|-----|-------------|
| `tiny` | ⚡⚡⚡ Muy rápido | ⭐ Pobre | 300MB | No |
| `base` | ⚡⚡ Rápido | ⭐⭐⭐ Buena | 1GB | ✅ SÍ |
| `small` | ⚡ Medio | ⭐⭐⭐⭐ Muy buena | 2GB | SÍ (si RAM) |
| `medium` | 🐢 Lento | ⭐⭐⭐⭐⭐ Excelente | 5GB | No (lento) |

**Prueba**:
```bash
# 1. Cambiar a "tiny"
# 2. Decir: "Barcelona es la capital de España"
# Resultado: Whisper dirá "Barcalona es la capital..." (error)

# 1. Cambiar a "base"
# 2. Mismo texto
# Resultado: Transcripción perfecta
```

---

## 2. MODIFICACIONES DE PERSONALIDAD

### A. Inyectar Contexto Personalizado

**Archivo**: `data/brain_context.txt`

Agregar información que BMO debe saber:

```txt
# Información que BMO siempre debe recordar

SOBRE TI:
- Naciste en 2015
- Tu hobby favorito es jugar videojuegos
- Tu color favorito es azul

SOBRE EL USUARIO:
- Es ingeniero de software
- Vive en Madrid
- Le encanta la tecnología

CORRECCIONES DE HECHOS:
- La capital de España es Madrid (no Barcelona)
- Python fue creado en 1991 por Guido van Rossum
- El presidente actual es...

NORMAS:
- Siempre sé amable
- Si no sabes algo, dilo
- Usa ejemplos en las respuestas
```

**Cómo se usa**:

```python
# En brain.py, cuando se genera el sistema prompt:
system_prompt = "Eres BMO, un robot asistente..."
system_prompt += "\n" + open("data/brain_context.txt").read()

# El LLM recibe todo esto como contexto
```

**Prueba**:
```bash
# 1. Agregar contexto a brain_context.txt
# 2. Esperar a que se recargue (si hot_reload es true)
# 3. Preguntar: "¿Cuál es la capital de España?"
# Resultado: BMO responde "Madrid" correctamente
```

---

### B. Crear Saludos Personalizados

**Archivo**: `src/main.py`

Busca la función `saludo_fijo()`:

```python
def saludo_fijo(nombre: str) -> str:
    """Saludos especiales por persona"""
    saludos = {
        "Juan": "¡Hola Juan! ¿Cómo está mi amigo favorito?",
        "María": "¡María! Me alegra verte de nuevo!",
        "Admin": "Bienvenido jefe, ¿qué necesitas?",
    }
    
    if nombre in saludos:
        return saludos[nombre]
    else:
        return f"¡Hola {nombre}! ¿Cómo estás?"
```

**Agregar Saludo Personalizado**:

```python
def saludo_fijo(nombre: str) -> str:
    saludos = {
        "Juan": "¡Hola Juan! ¿Cómo está mi amigo favorito?",
        "María": "¡María! Me alegra verte de nuevo!",
        "Admin": "Bienvenido jefe, ¿qué necesitas?",
        "Pedro": "¡Pedro! ¿Viniste a hablar de fútbol?",  # ← NUEVO
    }
    
    if nombre in saludos:
        return saludos[nombre]
    else:
        return f"¡Hola {nombre}! ¿Cómo estás?"
```

**Resultado**:
- Juan registrado → Saludo especial
- Pedro registrado → Saludo especial nuevo
- Alguien más → Saludo genérico

---

### C. Agregar Respuestas Rápidas

**Archivo**: `src/main.py`, función `_ciclo_escucha()`

```python
def _ciclo_escucha(self):
    # ... código anterior ...
    
    # AGREGAR ANTES de "responder_con_tts()"
    
    # Respuesta rápida a chistes
    if "chiste" in texto.lower() or "bromea" in texto.lower():
        self.display.set_estado(Estado.SPEAKING)
        self.voz.hablar("Aquí va: Un byte le dice al otro: ¡Vas a tener suerte!")
        self.display.set_estado(Estado.IDLE)
        return  # ← IMPORTANTE: salir sin usar LLM
    
    # Respuesta rápida a saludos
    if texto.lower() in ["hola", "hey", "ey"]:
        self.display.set_estado(Estado.SPEAKING)
        self.voz.hablar("¡Hola! ¿Cómo estás?")
        self.display.set_estado(Estado.IDLE)
        return
    
    # Respuesta rápida a hora
    if "qué hora" in texto.lower():
        from datetime import datetime
        hora = datetime.now().strftime("%H:%M")
        self.display.set_estado(Estado.SPEAKING)
        self.voz.hablar(f"Son las {hora}")
        self.display.set_estado(Estado.IDLE)
        return
    
    # ... resto del código LLM ...
```

**Ventajas**:
- ✅ Respuestas instantáneas
- ✅ Ahorra recursos
- ✅ Más natural

---

## 3. AGREGAR FUNCIONALIDADES

### A. Agregar Nueva Categoría de Preguntas

**Archivo**: `src/brain/classifier.py`

```python
# 1. Agregar al enum (al inicio del archivo)
class QueryCategory(Enum):
    # ... existentes ...
    BROMA = "broma"              # ← NUEVO

# 2. Agregar patrón
PATRONES_BROMA = ["chiste", "hazme reír", "bromea", "cuéntame algo gracioso"]

# 3. Agregar tokens asignados
NUM_PREDICT_MAP = {
    # ... existentes ...
    "broma": 150,  # ← NUEVO (respuestas creativas, tokens medios)
}

# 4. Agregar a categorizar_pregunta()
def categorizar_pregunta(texto: str) -> QueryCategory:
    texto_lower = texto.lower()
    
    # ... otras categorías ...
    
    # AGREGAR ANTES del "else" final
    if any(p in texto_lower for p in PATRONES_BROMA):
        return QueryCategory.BROMA
    
    # ... resto del código ...
```

**Prueba**:
```bash
# 1. Pregunta: "Cuéntame un chiste"
# 2. Debería clasificarse como BROMA
# 3. LLM obtiene 150 tokens
# 4. Respuesta: Chiste completo
```

---

### B. Agregar Comando Personalizado

**Archivo**: `src/main.py`

```python
def _ciclo_escucha(self):
    # ... código anterior ...
    
    # Agregar después de "text = self.voz.escuchar()"
    
    # Comando: listar memorias
    if texto.lower() == "lista de personas":
        from src.memory.register import cargar_personas
        personas = cargar_personas()
        nombres = ", ".join([p["nombre"] for p in personas])
        self.display.set_estado(Estado.SPEAKING)
        self.voz.hablar(f"Las personas registradas son: {nombres}")
        self.display.set_estado(Estado.IDLE)
        return
    
    # Comando: decir estadísticas
    if texto.lower() == "estadísticas":
        from src.memory.register import cargar_personas
        personas = cargar_personas()
        self.display.set_estado(Estado.SPEAKING)
        self.voz.hablar(f"Tengo {len(personas)} personas registradas")
        self.display.set_estado(Estado.IDLE)
        return
    
    # ... resto del código ...
```

---

### C. Agregar Validación de Entrada

**Archivo**: `src/main.py`

```python
def _ciclo_escucha(self):
    # ... código anterior ...
    
    # Después de "texto = self.voz.escuchar()"
    
    # Validación de texto
    if len(texto) < 3:
        print("[LOG] Texto muy corto, ignorar")
        self.display.set_estado(Estado.IDLE)
        return  # Salir sin procesar
    
    if len(texto) > 500:
        print("[LOG] Texto muy largo, truncar")
        texto = texto[:500]
    
    # ... resto del código ...
```

---

## 4. OPTIMIZACIONES

### A. Reducir Latencia de Respuesta

**Problema**: BMO tarda mucho en responder

**Soluciones**:

1. **Reducir tokens**:
```json
{
  "llm_num_predict": 50
}
```

2. **Usar modelo más pequeño**:
```json
{
  "text_model": "qwen2.5:1.5b"  // Si usabas 3b
}
```

3. **Reducir beam size de Whisper**:
```json
{
  "whisper_beam_size": 1  // Más rápido, menos preciso
}
```

---

### B. Reducir Consumo de RAM

**Problema**: BMO usa mucha memoria

**Soluciones**:

1. **Liberar modelo del LLM cuando no se usa**:
```json
{
  "llm_keep_alive": 300  // 5 minutos, no siempre en RAM
}
```

2. **Usar modelo Whisper más pequeño**:
```json
{
  "whisper_model": "tiny"  // Usa 300MB en lugar de 1GB
}
```

3. **Deshabilitar reconocimiento facial**:
```python
# En main.py
# Comentar: self.vision = VisionBMO(camera_index)
self.vision = None
```

---

### C. Reducir Uso de CPU

**Problema**: RPi5 se calienta mucho

**Soluciones**:

1. **Reducir threads del LLM**:
```json
{
  "llm_num_thread": 2  // De 4 a 2 threads
}
```

2. **Aumentar VAD threshold** (menos detecciones):
```json
{
  "vad_threshold": 0.03  // De 0.015 a más sensible
}
```

3. **Aumentar silencio requerido**:
```json
{
  "vad_silence_duration": 2.0  // De 1.2s a 2.0s
}
```

---

## 5. DEBUGGING

### A. Activar Logs Completos

**Archivo**: `src/main.py`

```python
import logging

# Al inicio del archivo
logging.basicConfig(
    level=logging.DEBUG,  # Cambiar de INFO a DEBUG
    format='[%(name)s] %(levelname)s: %(message)s'
)

log = logging.getLogger("BMO")
```

**Resultado**:
```
[BMO] DEBUG: Cámara inicializada
[BMO] DEBUG: Modelo Whisper cargado
[BMO] DEBUG: LLM conectado a Ollama
```

---

### B. Ver Qué Está Haciendo BMO

**Archivo**: `src/brain/brain.py`

```python
def responder_con_tts(mensaje, hablar_fn, on_start_speaking=None, nombre_persona=None):
    # Agregar logs detallados
    log.info(f"[BRAIN] Usuario ({nombre_persona}): {mensaje}")
    
    # Obtener contexto
    memoria_context = obtener_contexto_persona(nombre_persona)
    log.info(f"[BRAIN] Contexto de memoria: {memoria_context[:100]}...")  # Primeros 100 chars
    
    # Clasificar pregunta
    categoria = categorizar_pregunta(mensaje)
    log.info(f"[BRAIN] Categoría: {categoria.value} → {NUM_PREDICT_MAP[categoria.value]} tokens")
    
    # ... resto del código ...
```

---

### C. Grabar Conversación para Debugging

**Archivo**: `src/main.py`

```python
from datetime import datetime

debug_log = []

def _ciclo_escucha(self):
    # ... código anterior ...
    
    # Después de escuchar
    debug_log.append({
        "time": datetime.now().isoformat(),
        "type": "user",
        "text": texto,
        "person": nombre_contexto
    })
    
    # Después de responder
    debug_log.append({
        "time": datetime.now().isoformat(),
        "type": "assistant",
        "text": respuesta_completa
    })
    
    # Guardar al salir
    def guardar_debug():
        import json
        with open("debug_log.json", "w") as f:
            json.dump(debug_log, f, indent=2)
    
    atexit.register(guardar_debug)
```

---

## 6. QUÉ NO HACER

### ❌ NO HACER

#### 1. Modificar memory.json manualmente

```json
// ❌ NO: Editar memory.json directamente
{
  "1": {
    "nombre": "Juan",
    "embeddings": [0.1, 0.2, ...]  // ← Cambiar esto
  }
}

// ✅ SÍ: Usar funciones de register.py
agregar_turno_persona("Juan", "hola", "hola!")
```

---

#### 2. Quitar sincronización de threads

```python
# ❌ NO: Quitar locks de vision.py
# with self._lock_camara:
#     self._nombre_actual = nombre

# Si dos hilos acceden al mismo tiempo, crash

# ✅ SÍ: Mantener locks
with self._lock_camara:
    self._nombre_actual = nombre
```

---

#### 3. Cambiar estructura de messages para LLM

```python
# ❌ NO: Cambiar estructura
messages = {
    "system": "...",
    "user": "..."
}

# ✅ SÍ: Mantener lista de diccionarios
messages = [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
]
```

---

#### 4. Eliminar try/except sin entender

```python
# ❌ NO: Quitar manejo de errores
self.vision = VisionBMO(camera_index)  # Si cámara no existe, crash

# ✅ SÍ: Mantener fallbacks
try:
    self.vision = VisionBMO(camera_index)
except RuntimeError:
    self.vision = None
```

---

#### 5. Cambiar rutas absolutas a relativas

```python
# ❌ NO: Ruta relativa (depende de cwd)
face_model = "data/face_model.onnx"

# ✅ SÍ: Ruta basada en proyecto
face_model = Path(__file__).parent.parent / "data" / "face_model.onnx"
```

---

#### 6. Ignorar memoria en llamadas LLM

```python
# ❌ NO: No usar memoria persistente
messages = [
    {"role": "system", "content": "Eres BMO"},
    {"role": "user", "content": texto}  # Sin historial
]

# ✅ SÍ: Incluir memoria
messages = persistent_memory.get_context_for_llm(nombre_persona)
```

---

#### 7. Cambiar parámetros sin validar

```python
# ❌ NO: Valores aleatorios
"llm_temperature": 5.0   # ← Demasiado alto
"llm_num_thread": 32     # ← RPi5 tiene 8 cores

# ✅ SÍ: Valores documentados
"llm_temperature": 0.75  // [0.0 - 2.0]
"llm_num_thread": 4      // [1 - num_cores]
```

---

#### 8. No probar cambios

```python
# ❌ NO: Cambiar código sin probar
# Modifico source.py
# Reinicio BMO
# "¡No funciona!" ← Qué pasó?

# ✅ SÍ: Probar cambios pequeños
# Cambio línea 1
# Pruebo en terminal: python -c "import src.brain.brain"
# Funciona ✓
# Cambio línea 2
# Pruebo
# Funciona ✓
```

---

## 📝 CHECKLIST DE MODIFICACIONES SEGURAS

Antes de hacer cualquier cambio:

- [ ] Leí la sección relevante en `EXPLICACION_CODIGO_COMPLETA.md`
- [ ] Identifiqué qué archivo cambiar
- [ ] Hice una copia de respaldo (git commit si usa git)
- [ ] Testé en una rama/copia de prueba
- [ ] Validé que el cambio hace lo que esperaba
- [ ] Comprobé que no rompe otras funcionalidades
- [ ] Agregué logs si es necesario
- [ ] Documenté el cambio (comentario en el código)
- [ ] Restauré valores originales si no funcionó

---

## 🎯 CASOS DE USO COMUNES

### Caso 1: Hacer BMO Más Rápido

```json
{
  "llm_num_predict": 50,
  "whisper_model": "base",
  "llm_num_thread": 2
}
```

### Caso 2: Mejorar Calidad de Respuestas

```json
{
  "llm_temperature": 0.5,
  "whisper_model": "small",
  "llm_num_predict": 150
}
```

### Caso 3: Ahorrar RAM en RPi5

```json
{
  "llm_keep_alive": 300,
  "whisper_model": "tiny",
  "llm_num_thread": 2
}
```

### Caso 4: Personalizar BMO

1. Editar `data/brain_context.txt` ← Nueva información
2. Agregar patrón a `classifier.py` ← Nuevas categorías
3. Editar `config.json` ← Nuevos parámetros
4. Agregar saludo a `main.py` ← Personalización

---

**Éxito = Cambios Pequeños + Pruebas + Documentación** ✓

