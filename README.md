# BMO - Local AI Agent

Robot conversacional local inspirado en BMO de Hora de Aventura.
Corre 100% offline en PC o Raspberry Pi 5.

## Stack

| Módulo | Tecnología |
|--------|-----------|
| Visión | OpenCV LBPH + Haar Cascade |
| STT    | faster-whisper (tiny/base) |
| LLM    | Ollama — llama3.2:1b |
| TTS    | Piper TTS — es_ES-sharvard-medium |

## Instalación

### 1. Dependencias Python

```bash
pip install -r requirements.txt
```

### 2. Ollama + modelo

```bash
# Instalar Ollama: https://ollama.com
ollama pull llama3.2:1b
```

### 3. Voz española

```bash
python scripts/download_voice.py
```

### 4. Ejecutar

```bash
python -m src.main
```

## Controles

| Tecla | Acción |
|-------|--------|
| `V`   | BMO te escucha y responde |
| `R`   | Registrar nuevo visitante |
| `Q`   | Salir |

## Estructura

```
BMO/
├── src/
│   ├── main.py          # Loop principal
│   ├── vision/vision.py # Reconocimiento facial
│   ├── voice/voice.py   # STT (Whisper) + TTS (Piper)
│   ├── brain/brain.py   # LLM via Ollama
│   └── memory/register.py # Memoria unificada
├── data/
│   ├── trainer.yml      # Modelo facial entrenado
│   └── memory.json      # Personas + historial
├── voices/              # Modelos de voz Piper (.onnx)
├── scripts/
│   └── download_voice.py
└── requirements.txt
```

## Migración a Raspberry Pi 5

1. Clonar el repo en la Pi
2. Instalar dependencias igual
3. Cambiar en `voice.py`: `WHISPER_MODEL = "tiny"` (ya está por defecto)
4. Ollama corre igual en ARM64
