# GUÍA PASO A PASO: Implementar BMO en Raspberry Pi 5 8GB

## FASE 0: PREPARACIÓN

### 0.1 Verificar Hardware

```bash
# En RPi 5, ejecutar:
uname -m                    # Debe mostrar: aarch64
free -h                     # Debe mostrar: 8GB total
nproc                       # Debe mostrar: 8 cores
```

### 0.2 Instalar Dependencias del Sistema

```bash
sudo apt update
sudo apt upgrade -y

# Dependencias para compilar
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    build-essential \
    cmake \
    git \
    libopenblas-dev \
    libblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    libjasper-dev \
    libtiff5-dev \
    libjasper1 \
    libjpeg-dev \
    libpng-dev \
    libharfbuzz0b \
    libwebp6 \
    libtiff5 \
    libjasper1 \
    libjpeg62-turbo \
    libopenjp2-7 \
    libatlas3-base \
    libharfbuzz0b \
    libwebp6 \
    libtiff5 \
    libopenjp2-7

# Audio
sudo apt install -y \
    alsa-utils \
    pulseaudio \
    libsndfile1 \
    libsndfile1-dev

# Ollama
curl https://ollama.ai/install.sh | sh
```

### 0.3 Crear Entorno Virtual

```bash
cd /path/to/BMO
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
```

---

## FASE 1: INSTALAR DEPENDENCIAS PYTHON

### 1.1 Instalar desde requirements.txt

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

**Nota:** Esto puede tardar 10-20 minutos en RPi 5.

### 1.2 Verificar Instalación

```bash
python -c "import cv2; print(f'OpenCV: {cv2.__version__}')"
python -c "import faster_whisper; print('Whisper: OK')"
python -c "import piper; print('Piper: OK')"
python -c "import ollama; print('Ollama: OK')"
```

---

## FASE 2: DESCARGAR MODELOS

### 2.1 Descargar Modelo de Voz (Piper)

```bash
python scripts/download_voice.py
```

**Verificar:**
```bash
ls -lh voices/
# Debe mostrar:
# es_ES-sharvard-medium.onnx (~200MB)
# es_ES-sharvard-medium.onnx.json
```

### 2.2 Descargar Modelo LLM (Ollama)

```bash
# Iniciar Ollama en background
ollama serve &

# En otra terminal, descargar Qwen
ollama pull qwen2.5:1.5b

# Verificar
ollama list
# Debe mostrar: qwen2.5:1.5b
```

**Nota:** Esto descarga ~3.5GB, puede tardar 10-30 minutos.

### 2.3 Descargar Modelo STT (Whisper)

```bash
# Whisper se descarga automáticamente en primera ejecución
# Pero puedes pre-descargarlo:
python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"
```

---

## FASE 3: APLICAR FIXES

### 3.1 Fix TTS (Corta Palabras)

**Archivo:** `src/voice/voice.py`  
**Líneas:** 127-128

```python
# ANTES
silencio = np.zeros(int(0.3 * sr), dtype="float32")
audio_np = np.concatenate([audio_np, silencio])

# DESPUÉS
silencio_pre = np.zeros(int(0.1 * sr), dtype="float32")
silencio_post = np.zeros(int(0.5 * sr), dtype="float32")
audio_np = np.concatenate([silencio_pre, audio_np, silencio_post])
```

**Verificar:**
```bash
python -c "from src.voice.voice import VozBMO; v = VozBMO(); v.hablar('Hola mundo')"
# Debe reproducir sin cortes
```

### 3.2 Fix Regex (Respuestas Predefinidas)

**Archivo:** `src/brain/brain.py`  
**Líneas:** 60-90

Reemplazar `RESPUESTAS_PREDEFINIDAS` con:

```python
RESPUESTAS_PREDEFINIDAS = {
    r"(?:quién|quien)\s+(?:es|eres)\s+(?:finn|fin)": 
        "Finn es el héroe principal de Ooo, un chico valiente de 14 años. Es el mejor amigo de Jake el Perro y viven muchas aventuras juntos.",
    r"(?:qué|que)\s+(?:es|eres)\s+(?:finn|fin)":
        "Finn es un humano valiente que vive en Ooo. Es el protagonista de Adventure Time y siempre está buscando aventuras con su hermano Jake.",
    r"(?:quién|quien)\s+(?:es|eres)\s+(?:jake|el\s+perro)":
        "Jake es un perro mágico que puede estirarse y cambiar de forma. Es el hermano adoptivo de Finn y su mejor amigo.",
    r"(?:qué|que)\s+(?:es|eres)\s+(?:jake|el\s+perro)":
        "Jake es un perro mágico con poderes especiales. Puede estirarse, cambiar de forma y es muy sabio. Vive con Finn en el Árbol Casa.",
    r"(?:quién|quien)\s+(?:es|eres)\s+(?:princesa\s+chicle|princesa\s+bubblegum)":
        "Princesa Chicle es la gobernante del Reino de los Dulces. Es muy inteligente y científica, y crea muchas cosas increíbles.",
    r"(?:quién|quien)\s+(?:es|eres)\s+(?:marceline|la\s+reina\s+vampiro)":
        "Marceline es una vampira de 1000 años que ama la música. Es amiga de Finn y Jake, y toca la guitarra muy bien.",
    r"(?:quién|quien)\s+(?:es|eres)\s+(?:ice\s+king|el\s+rey\s+hielo)":
        "Ice King es un mago que controla el hielo. Antes era un humano llamado Simon Petrikov, pero una corona mágica lo volvió loco.",
    r"(?:qué|que)\s+(?:es|eres)\s+(?:ooo|el\s+mundo)":
        "Ooo es el mundo donde ocurre Adventure Time. Es un lugar post-apocalíptico lleno de magia, misterios y aventuras.",
    r"(?:dónde|donde)\s+(?:ocurre|pasa)\s+(?:adventure\s+time|la\s+serie)":
        "Adventure Time ocurre en Ooo, un mundo mágico y post-apocalíptico. Finn y Jake viven en el Árbol Casa.",
    r"(?:quién|quien)\s+(?:eres|soy)":
        "Soy BMO, un robot asistente creado por Juan David Zambrano. Tengo el aspecto de BMO de Adventure Time y estoy aquí para ayudarte.",
    r"(?:cómo|como)\s+te\s+llamas":
        "Me llamo BMO. Soy un robot asistente con el aspecto de BMO de la serie Adventure Time.",
    r"(?:qué|que)\s+eres":
        "Soy BMO, un robot asistente de IA. Puedo hablar contigo, reconocer caras y responder preguntas sobre Adventure Time.",
}
```

**Verificar:**
```bash
python -c "from src.brain.brain import obtener_respuesta_predefinida; print(obtener_respuesta_predefinida('¿Quién es Finn?'))"
# Debe mostrar la respuesta
```

### 3.3 Mejorar System Prompt

**Archivo:** `src/brain/brain.py`  
**Líneas:** 32-45

```python
SYSTEM_PROMPT = (
    "Eres BMO, un robot asistente de IA creado por Juan David Zambrano. "
    "Tienes el aspecto de BMO de Adventure Time y conoces esa serie. "
    "Respondes siempre en español, de forma directa y amable en 2-3 oraciones. "
    "No actúas ni haces roleplay. Eres un asistente, no un personaje. "
    "Si no sabes algo, dilo honestamente. No inventes información. "
    "IMPORTANTE: Nunca inventes hechos sobre Adventure Time. "
    "Sobre Adventure Time: "
    "- Finn es el héroe humano de Ooo, valiente, 14 años, mejor amigo de Jake. "
    "- Jake es un perro mágico que puede estirarse, hermano adoptivo de Finn. "
    "- Princesa Chicle gobierna el Reino de los Dulces. "
    "- Marceline es una vampira de 1000 años que ama la música. "
    "- Ice King era Simon Petrikov, un humano que enloqueció por una corona mágica. "
    "- Ooo es el mundo post-apocalíptico donde ocurre la serie. "
    "- Finn NUNCA destruye a Marceline. Son amigos. "
    "- Jake NUNCA pelea contra Finn. Son hermanos. "
)
```

---

## FASE 4: CAMBIAR MODELO LLM

### 4.1 Cambiar a Qwen 2.5:1.5B

**Archivo:** `src/brain/brain.py`  
**Línea:** 18

```python
# ANTES
MODEL = "qwen2.5:1.5b"

# DESPUÉS (ya está, pero confirmar)
MODEL = "qwen2.5:1.5b"
```

### 4.2 Ajustar Ollama Options

**Archivo:** `src/brain/brain.py`  
**Líneas:** 20-30

```python
OLLAMA_OPTIONS = {
    "keep_alive": 300,        # Descargar modelo después de 5 min
    "num_thread": 4,          # Usar 4 threads
    "temperature": 0.75,      # Reducir de 0.85 a 0.75
    "top_k": 50,              # Aumentar de 40 a 50
    "top_p": 0.90,
    "num_predict": 100,       # Reducir de 150 a 100
    "repeat_penalty": 1.15,
}
```

### 4.3 Verificar Configuración

```bash
python -c "from src.brain.brain import MODEL, OLLAMA_OPTIONS; print(f'Modelo: {MODEL}'); print(f'Options: {OLLAMA_OPTIONS}')"
```

---

## FASE 5: TESTING

### 5.1 Test de Componentes Individuales

```bash
# Test STT
python -c "from src.voice.voice import VozBMO; v = VozBMO(); print('STT: OK')"

# Test TTS
python -c "from src.voice.voice import VozBMO; v = VozBMO(); v.hablar('Hola, soy BMO')"

# Test Visión
python -c "from src.vision.vision import VisionBMO; v = VisionBMO(); print('Visión: OK')"

# Test LLM
python -c "from src.brain.brain import responder_con_tts; print('LLM: OK')"
```

### 5.2 Test de Respuestas Predefinidas

```bash
python << 'EOF'
from src.brain.brain import obtener_respuesta_predefinida

preguntas = [
    "¿Quién es Finn?",
    "¿Qué es Jake?",
    "¿Quién es Marceline?",
    "¿Dónde ocurre Adventure Time?",
]

for pregunta in preguntas:
    respuesta = obtener_respuesta_predefinida(pregunta)
    print(f"Q: {pregunta}")
    print(f"A: {respuesta}\n")
EOF
```

### 5.3 Test de Latencia

```bash
python << 'EOF'
import time
from src.brain.brain import responder_con_tts
from src.voice.voice import VozBMO

voz = VozBMO()

def dummy_hablar(texto):
    print(f"[TTS] {texto}")

start = time.time()
responder_con_tts(
    mensaje="¿Quién es Finn?",
    hablar_fn=dummy_hablar,
    nombre_persona=None
)
elapsed = time.time() - start
print(f"\nLatencia LLM: {elapsed:.1f}s")
EOF
```

### 5.4 Test de Monitoreo de RAM

```bash
# En una terminal
watch -n 1 free -h

# En otra terminal
python -m src.main
```

**Verificar:**
- RAM usada no debe exceder 7GB
- Buffer disponible debe ser > 0.5GB
- Temperatura CPU < 70°C

---

## FASE 6: EJECUCIÓN

### 6.1 Ejecutar BMO

```bash
source .venv/bin/activate
python -m src.main
```

### 6.2 Controles

| Tecla | Acción |
|-------|--------|
| `V` | BMO te escucha y responde |
| `R` | Registrar nuevo visitante |
| `Q` | Salir |

### 6.3 Monitoreo en Tiempo Real

En otra terminal:

```bash
# Monitorear RAM
watch -n 1 free -h

# Monitorear CPU
watch -n 1 top -b -n 1 | head -20

# Monitorear temperatura
watch -n 1 vcgencmd measure_temp
```

---

## FASE 7: OPTIMIZACIÓN

### 7.1 Si RAM es Crítica

```python
# En src/brain/brain.py
OLLAMA_OPTIONS = {
    "keep_alive": 60,         # Descargar modelo más rápido
    "num_thread": 2,          # Reducir threads
    "temperature": 0.75,
    "top_k": 50,
    "top_p": 0.90,
    "num_predict": 80,        # Reducir tokens
    "repeat_penalty": 1.15,
}
```

### 7.2 Si Latencia es Crítica

```python
# Cambiar a Phi 3.5 Mini int4
MODEL = "phi:3.5-mini-instruct-q4_K_M"

# O cambiar a Gemma
MODEL = "gemma:1b"
```

### 7.3 Si Calidad es Crítica

```python
# Mantener Qwen pero mejorar prompt
# Agregar más ejemplos en SYSTEM_PROMPT
# Usar más respuestas predefinidas
```

---

## TROUBLESHOOTING

### Problema: "ModuleNotFoundError: No module named 'cv2'"

```bash
pip install opencv-python-headless
```

### Problema: "No audio device found"

```bash
# Listar dispositivos de audio
python scripts/list_audio.py

# Probar micrófono
python scripts/test_mics.py
```

### Problema: "Ollama connection refused"

```bash
# Iniciar Ollama
ollama serve &

# Esperar 5 segundos
sleep 5

# Ejecutar BMO
python -m src.main
```

### Problema: "Out of Memory"

```bash
# Reducir num_predict
# Reducir num_thread
# Cambiar a modelo más pequeño
# Reiniciar RPi
```

### Problema: "TTS sigue cortando palabras"

```bash
# Aumentar silencio_post
silencio_post = np.zeros(int(0.7 * sr), dtype="float32")

# O cambiar dispositivo de audio
MIC_DEVICE = 0  # Probar diferentes índices
```

---

## CHECKLIST FINAL

- [ ] Hardware verificado (8GB RAM, 8 cores)
- [ ] Dependencias del sistema instaladas
- [ ] Entorno virtual creado
- [ ] Dependencias Python instaladas
- [ ] Modelos descargados (Whisper, Piper, Qwen)
- [ ] Fix TTS aplicado
- [ ] Fix regex aplicado
- [ ] System prompt mejorado
- [ ] Modelo cambiado a Qwen 2.5:1.5B
- [ ] Ollama options ajustadas
- [ ] Tests de componentes pasados
- [ ] Tests de latencia pasados
- [ ] Monitoreo de RAM verificado
- [ ] BMO ejecutándose correctamente
- [ ] Respuestas predefinidas funcionando
- [ ] Reconocimiento facial funcionando
- [ ] STT funcionando
- [ ] TTS funcionando sin cortes
- [ ] LLM respondiendo correctamente
- [ ] Estabilidad verificada (24h)

---

## TIEMPO ESTIMADO

| Fase | Tiempo |
|------|--------|
| 0. Preparación | 30 min |
| 1. Instalar dependencias | 20 min |
| 2. Descargar modelos | 30 min |
| 3. Aplicar fixes | 15 min |
| 4. Cambiar modelo | 10 min |
| 5. Testing | 30 min |
| 6. Ejecución | 5 min |
| 7. Optimización | 30 min |
| **TOTAL** | **3 horas** |

---

## SOPORTE

Si encuentras problemas:

1. Revisar logs en consola
2. Consultar TROUBLESHOOTING
3. Revisar ANALISIS_RPI5_8GB.md
4. Revisar OPTIMIZACIONES_RPI5.md

