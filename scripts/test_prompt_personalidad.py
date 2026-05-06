"""
Prueba rápida del nuevo system prompt con personalidad de BMO.
Ejecutar: .venv\Scripts\python.exe scripts/test_prompt_personalidad.py
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import ollama
from src.config.config_manager import config_manager
from src.brain.brain import get_system_prompt

GREEN  = "\033[92m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def preguntar(pregunta: str, system: str) -> tuple[str, float]:
    model = config_manager.get("text_model", "qwen2.5:1.5b")
    options = config_manager.get_ollama_options()
    t0 = time.time()
    resp = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": pregunta},
        ],
        options=options,
    )
    return resp["message"]["content"].strip(), time.time() - t0

system = get_system_prompt()

print(f"\n{BOLD}{CYAN}System prompt activo:{RESET}")
print(f"{YELLOW}{system[:300]}...{RESET}\n")

PREGUNTAS = [
    "Hola!",
    "¿Cómo estás?",
    "¿Quién eres?",
    "¿Quién te creó?",
    "¿Qué es Zambrano?",
    "¿De qué colores es la bandera de Colombia?",
    "¿Cuál es la capital de Brasil?",
    "¿Qué es la fotosíntesis?",
    "No entiendo nada de programación, ¿me puedes ayudar?",
    "¿Conoces Hora de Aventura?",
]

for p in PREGUNTAS:
    resp, t = preguntar(p, system)
    palabras = len(resp.split())
    print(f"{BOLD}[{t:.1f}s | {palabras}p]{RESET} {YELLOW}{p}{RESET}")
    print(f"  → {resp}\n")
