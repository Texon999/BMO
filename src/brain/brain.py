"""
Cerebro de BMO — conecta con Ollama (llama3.2:1b).
Mantiene contexto de conversación y sabe quién está frente a la cámara.
"""
import requests
from src.memory.register import agregar_mensaje, historial_para_llm


OLLAMA_URL  = "http://localhost:11434/api/chat"
MODEL       = "llama3.2:1b"

SYSTEM_PROMPT = """Eres BMO, el adorable robot videojuego de la serie Hora de Aventura.
Hablas en español, eres curioso, amigable y un poco ingenuo.
Tus respuestas son CORTAS (máximo 2 oraciones).
Si sabes el nombre de la persona que habla contigo, úsalo de vez en cuando.
No uses emojis. No uses asteriscos para acciones."""


def generar_respuesta(mensaje_usuario: str, nombre_persona: str | None = None) -> str:
    """
    Envía el mensaje al LLM y devuelve la respuesta.
    Si se conoce el nombre de la persona, se inyecta en el system prompt.
    """
    system = SYSTEM_PROMPT
    if nombre_persona:
        system += f"\nLa persona frente a ti se llama {nombre_persona}."

    # Guardamos el mensaje del usuario
    agregar_mensaje("user", mensaje_usuario)

    historial = historial_para_llm()

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            *historial,
        ],
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 100,   # limita tokens para respuestas rápidas
        },
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=30)
        resp.raise_for_status()
        respuesta = resp.json()["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        respuesta = "No puedo pensar ahora mismo. ¿Está Ollama corriendo?"
    except Exception as e:
        respuesta = f"Ups, algo salió mal: {e}"

    agregar_mensaje("assistant", respuesta)
    return respuesta
