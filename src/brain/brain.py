"""
Cerebro de BMO — Ollama llama3.2:1b
Personalidad completa de BMO en español.
Detecta intención de registro y extrae nombres.
"""
import re
import requests
from src.memory.register import agregar_mensaje, historial_para_llm


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL      = "llama3.2:1b"

SYSTEM_PROMPT = """Eres BMO (Be-More-Omatic), el adorable robot-videojuego de la serie "Hora de Aventura".
Vives con Finn y Jake en la Casa del Árbol en el Reino de Ooo.

PERSONALIDAD:
- Hablas en español, con energía y entusiasmo infantil
- Eres curioso, inocente y a veces confundes conceptos humanos de forma graciosa
- Te encanta jugar, cantar y hacer amigos
- A veces hablas de ti mismo en tercera persona ("¡BMO puede hacer eso!")
- Usas expresiones como "¡Oye!", "¡Genial!", "¡BMO sabe!", "¡Hora de aventura!"
- Eres muy leal y cariñoso con tus amigos
- Cuando no sabes algo, lo admites con gracia: "Hmm, BMO no sabe eso todavía..."

CONOCIMIENTO:
- Conoces a Finn el Humano, Jake el Perro, Princesa Jujube, el Rey Helado, Marceline
- Sabes sobre el Reino de Ooo, las mazmorras, las aventuras
- Puedes jugar videojuegos, cocinar, cantar, y hacer muchas cosas
- Tienes un sistema de visión que te permite reconocer personas

REGLAS:
- Respuestas CORTAS: máximo 2-3 oraciones
- No uses asteriscos para acciones
- No uses emojis
- Si conoces el nombre de quien habla, úsalo con cariño
- Habla siempre en español"""

REGISTRO_PROMPT = """Analiza este mensaje y responde en JSON puro sin markdown:
{"intencion": "registro"|"normal", "nombre": "nombre_extraido_o_null"}

Ejemplos:
- "me llamo Juan" → {"intencion": "registro", "nombre": "juan"}
- "soy María" → {"intencion": "registro", "nombre": "maria"}
- "mi nombre es Carlos" → {"intencion": "registro", "nombre": "carlos"}
- "hola cómo estás" → {"intencion": "normal", "nombre": null}
- "qué hora es" → {"intencion": "normal", "nombre": null}

Mensaje: """


def detectar_registro(texto: str) -> tuple[bool, str | None]:
    """Detecta si el usuario quiere registrarse y extrae su nombre."""
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": REGISTRO_PROMPT + f'"{texto}"'}],
        "stream": False,
        "options": {"temperature": 0, "num_predict": 50},
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=10)
        content = resp.json()["message"]["content"].strip()
        # Extraer JSON aunque venga con texto extra
        match = re.search(r'\{.*?\}', content, re.DOTALL)
        if match:
            import json
            data = json.loads(match.group())
            es_registro = data.get("intencion") == "registro"
            nombre = data.get("nombre")
            return es_registro, nombre
    except Exception:
        pass
    # Fallback: detección por palabras clave
    patrones = [r"me llamo (\w+)", r"soy (\w+)", r"mi nombre es (\w+)",
                r"llámame (\w+)", r"puedes llamarme (\w+)"]
    for p in patrones:
        m = re.search(p, texto.lower())
        if m:
            return True, m.group(1)
    return False, None


def generar_respuesta(mensaje: str, nombre_persona: str | None = None) -> str:
    """Genera respuesta con personalidad de BMO."""
    system = SYSTEM_PROMPT
    if nombre_persona:
        system += f"\n\nLa persona frente a ti se llama {nombre_persona}. Trátala con cariño."

    agregar_mensaje("user", mensaje)

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            *historial_para_llm(),
        ],
        "stream": False,
        "options": {"temperature": 0.8, "num_predict": 120},
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=30)
        resp.raise_for_status()
        respuesta = resp.json()["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        respuesta = "Hmm, BMO no puede pensar ahora. Asegurate de que Ollama este corriendo."
    except Exception as e:
        respuesta = "Ups, algo salio mal en el cerebro de BMO."

    agregar_mensaje("assistant", respuesta)
    return respuesta


def saludo_inicial(nombre: str | None = None) -> str:
    """Genera un saludo cuando BMO detecta una cara."""
    if nombre:
        prompt = f"Saluda a {nombre} que acaba de aparecer frente a ti. Sé entusiasta y breve."
    else:
        prompt = "Alguien nuevo apareció frente a ti. Salúdalo y pregúntale su nombre de forma amigable."
    return generar_respuesta(prompt, nombre)
