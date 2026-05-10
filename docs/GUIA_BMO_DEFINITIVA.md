# Guía BMO — Estado actual del sistema

> Rama activa: `dev/mejoras-rendimiento-memoria`

---

## Arquitectura general

```
BMO
├── src/
│   ├── main.py                  ← Agente principal (hilos: cámara, lógica, display)
│   ├── brain/
│   │   └── brain.py             ← LLM (Ollama), system prompt, normalización TTS
│   ├── voice/
│   │   ├── voice.py             ← STT (Whisper) + TTS (Piper)
│   │   └── wake_word.py         ← Detector de wake word "BMO" + sonido tín
│   ├── vision/
│   │   └── vision.py            ← Reconocimiento facial (OpenCV + ONNX)
│   ├── memory/
│   │   ├── persistent_memory.py ← Memoria MongoDB (solo backend activo)
│   │   └── register.py          ← Personas + embeddings (MongoDB + JSON backup)
│   ├── storage/
│   │   └── mongo_store.py       ← Capa de acceso a MongoDB
│   ├── config/
│   │   ├── config_manager.py    ← config.json con hot-reload
│   │   └── runtime.py           ← Variables de entorno
│   └── display/
│       └── display.py           ← Animación de cara (Pygame)
├── data/
│   └── memory.json              ← Backup JSON de personas y embeddings
├── scripts/
│   ├── ver_mongo.py             ← Ver datos en MongoDB desde terminal
│   ├── test_storage.py          ← Pruebas de almacenamiento
│   ├── test_wake_y_saludos.py   ← Pruebas de wake word y saludos
│   └── test_cambios_rama.py     ← Suite completa de pruebas
└── config.json                  ← Configuración central
```

---

## Requisitos

### MongoDB (obligatorio)

```bash
# Ubuntu/Debian ARM64 (Raspberry Pi 5)
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" \
  | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update && sudo apt install -y mongodb-org
sudo systemctl enable --now mongod

# Verificar
mongod --version
```

### Python y dependencias

```bash
python -m venv .venv
source .venv/bin/activate          # Linux/Mac
.venv\Scripts\activate             # Windows

pip install -r requirements.txt
# Incluye: pymongo==4.6.3, faster-whisper, piper-tts, ollama, opencv, etc.
```

### Ollama + modelo

```bash
ollama serve &
ollama pull qwen2.5:1.5b
```

---

## Ver datos en MongoDB

```bash
# Script incluido en el proyecto
.venv/Scripts/python.exe scripts/ver_mongo.py

# Salida ejemplo:
# === MongoDB bmo_db ===
# Personas registradas:       3
# Personas con embeddings:    3
# Mensajes de chat total:     6
#
# --- Personas ---
#   id=7001  nombre=Zambrano  visitas=1  embeddings=1x512dims
#
# --- Últimos 10 mensajes de chat ---
#   [Zambrano] user  2026-05-10 06:17:57  hola cómo estás
```

También puedes usar `mongosh` si está instalado:

```bash
mongosh bmo_db
> db.personas.find({}, {nombre:1, visitas:1}).pretty()
> db.chat_history.find({persona: "Zambrano"}).sort({ts:-1}).limit(6)
> db.chat_history.countDocuments()
```

---

## Colecciones MongoDB

### `personas`

```json
{
  "_id": 1,
  "nombre": "Zambrano",
  "visitas": 3,
  "ultima_vez": "2026-05-10T06:17:57Z",
  "embeddings": [[0.12, -0.34, ...]]   // array de 512 floats por embedding
}
```

### `chat_history`

```json
{
  "role": "user",
  "content": "hola cómo estás…",       // truncado a 120 chars
  "persona": "Zambrano",
  "ts": "2026-05-10T06:17:57Z"         // TTL: se borra automáticamente a los 90 días
}
```

**Reglas de negocio:**
- Máximo **6 mensajes por persona** (sliding window — el más viejo se borra al llegar el 7mo)
- Solo se guarda el **contexto** (primeros 120 chars), no el mensaje completo
- **Sin cara reconocida → no se guarda nada** en MongoDB
- TTL automático de 90 días sobre el campo `ts`

---

## Wake word "BMO"

BMO escucha continuamente en modo pasivo (bajo consumo). Solo procesa el prompt cuando detecta su nombre.

### Variantes reconocidas

Whisper en español transcribe "BMO" de muchas formas. El sistema reconoce todas:

| Lo que dices | Whisper transcribe | ¿Activa? |
|---|---|---|
| BMO | bmo / B.M.O | ✓ |
| Bimo | bimo | ✓ |
| Vimo | vimo | ✓ |
| Bemo | bemo | ✓ |
| Bi mo | bi mo | ✓ |
| Vi mo | vi mo | ✓ |
| Bumo | bumo | ✓ |

### Flujo

```
[Escucha pasiva continua]
    ↓ detecta voz
[Transcripción rápida (beam_size=1)]
    ↓ ¿contiene wake word?
    NO → volver a escuchar pasiva
    SÍ → reproducir "tín" (440Hz → 880Hz)
         ↓
    ¿hay prompt inline? ("BMO qué hora es")
    SÍ → usar ese prompt directamente
    NO → escuchar prompt completo
         ↓
    [Procesar con LLM]
```

### Sonido "tín"

Generado con numpy, sin archivos externos. Dos tonos cortos ascendentes (440Hz → 880Hz, 80ms cada uno) con fade in/out para evitar clicks.

---

## Memoria y contexto

### Con cara reconocida (persona registrada)

```
Contexto LLM = [system_prompt] + [últimos 6 msgs de MongoDB] + [sesión actual]
```

Al terminar la conversación, los mensajes de sesión se persisten en MongoDB con sliding window.

### Sin cara reconocida (anónimo)

```
Contexto LLM = [system_prompt] + [último mensaje]
```

La sesión se descarta al terminar. **No se guarda nada en MongoDB.**

---

## System prompt

Minimalista (93 palabras) para reducir alucinaciones en el modelo 1.5B:

```
Eres BMO, un robot asistente creado por Zambrano,
un joven programador del SENA apasionado por la tecnología.
Responde siempre en español. Sé amable y directo.
Máximo 2 oraciones para preguntas simples, 4 para explicaciones.
Sin listas, sin markdown, solo texto natural.
Si no sabes algo o la pregunta no tiene sentido, di exactamente:
'No tengo esa información.' y no agregues nada más.
Bandera de Colombia: amarillo arriba, azul medio, rojo abajo.
Capital de Brasil: Brasilia.
```

**Regla principal:** cuanto más corto el prompt, menos alucina el modelo 1.5B.

---

## Normalización TTS

Antes de enviar texto a Piper TTS, se normalizan símbolos que Piper pronuncia mal:

| Entrada | Salida |
|---|---|
| `pi` / `π` | `pí` (con tilde) |
| `√9` | `raíz cuadrada de 9` |
| `5²` | `5 al cuadrado` |
| `∞` | `infinito` |
| `**texto**` | `texto` |
| `OK` | `okey` |

---

## Lógica de nombres y cámara

| Situación | Comportamiento |
|---|---|
| Cámara activa + cara desconocida + dice nombre | Registra foto → nombre **persistente** en MongoDB |
| Cámara activa + cara ya reconocida | Usa el nombre de la cámara, ignora lo que diga |
| Sin cámara + dice nombre nuevo | Caché temporal en RAM (se borra al reiniciar) |
| Sin cámara + nombre ya registrado | Usa ese nombre como contexto temporal |

---

## Ejecutar pruebas

```bash
# Pruebas de wake word y saludos (no requiere micrófono)
.venv/Scripts/python.exe scripts/test_wake_y_saludos.py

# Pruebas de almacenamiento MongoDB
.venv/Scripts/python.exe scripts/test_storage.py

# Suite completa (requiere Ollama corriendo)
.venv/Scripts/python.exe scripts/test_cambios_rama.py

# Ver datos en MongoDB
.venv/Scripts/python.exe scripts/ver_mongo.py
```

---

## Iniciar BMO

```bash
# Asegurarse de que MongoDB y Ollama están corriendo
sudo systemctl start mongod
ollama serve &

# Iniciar BMO
.venv/Scripts/python.exe -m src.main
# o en Linux:
.venv/bin/python -m src.main
```

---

## Configuración (config.json)

```json
{
  "text_model":    "qwen2.5:1.5b",
  "mongo_uri":     "mongodb://localhost:27017",
  "mongo_db":      "bmo_db",
  "llm_num_predict": 300,
  "llm_temperature": 0.75,
  "whisper_model": "base",
  "whisper_lang":  "es",
  "camera_index":  0,
  "headless":      false
}
```

---

## Instalar MongoDB en Raspberry Pi 5

```bash
# 1. Importar clave GPG
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc \
  | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor

# 2. Agregar repositorio ARM64
echo "deb [ arch=arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] \
  https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" \
  | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# 3. Instalar
sudo apt update && sudo apt install -y mongodb-org

# 4. Habilitar y arrancar
sudo systemctl enable mongod
sudo systemctl start mongod

# 5. Verificar
sudo systemctl status mongod
mongod --version
```
