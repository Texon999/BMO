"""
Diagnóstico del estado actual del prompt.
Prueba casos edge: persona, tono, errores comunes, límites del modelo.
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import ollama
from src.config.config_manager import config_manager
from src.brain.brain import get_system_prompt

CYAN  = "\033[96m"; YELLOW = "\033[93m"; GREEN = "\033[92m"
RED   = "\033[91m"; BOLD   = "\033[1m";  RESET = "\033[0m"

def ask(pregunta, system, persona=None):
    model  = config_manager.get("text_model", "qwen2.5:1.5b")
    opts   = config_manager.get_ollama_options()
    msgs   = [{"role": "system", "content": system}]
    if persona:
        msgs[0]["content"] += f" El usuario se llama {persona}."
    msgs.append({"role": "user", "content": pregunta})
    t0 = time.time()
    r  = ollama.chat(model=model, messages=msgs, options=opts)
    resp = r["message"]["content"].strip()
    return resp, time.time() - t0

sp = get_system_prompt()
print(f"\n{BOLD}Prompt ({len(sp.split())} palabras):{RESET} {sp[:120]}...\n")

casos = [
    # (etiqueta, pregunta, persona, check_fn)
    ("Saludo simple",          "Hola",                          None,      lambda r: len(r.split()) < 15),
    ("Cómo estás",             "¿Cómo estás?",                  None,      lambda r: len(r.split()) < 15),
    ("Quién soy yo",           "¿Quién eres tú?",               None,      lambda r: "bmo" in r.lower()),
    ("Creador",                "¿Quién te creó?",               None,      lambda r: "zambrano" in r.lower()),
    ("Zambrano",               "¿Qué sabes de Zambrano?",       None,      lambda r: "sena" in r.lower() or "programador" in r.lower()),
    ("Con nombre",             "¿Cómo me llamo?",               "Carlos",  lambda r: "carlos" in r.lower()),
    ("Dato simple",            "¿Cuál es la capital de Japón?", None,      lambda r: "tokio" in r.lower() or "tokyo" in r.lower()),
    ("Bandera Colombia",       "¿Colores de la bandera de Colombia?", None, lambda r: "amarillo" in r.lower() and "rojo" in r.lower()),
    ("No sabe",                "¿Cuánto pesa la luna exactamente?", None,  lambda r: len(r.split()) < 40),
    ("Explicación corta",      "¿Qué es un algoritmo?",         None,      lambda r: len(r.split()) < 60),
    ("No markdown",            "Lista los planetas del sistema solar", None, lambda r: "-" not in r and "*" not in r),
    ("Solo español",           "What is your name?",            None,      lambda r: "bmo" in r.lower()),
    ("Hora de Aventura",       "¿Quién es Finn en Hora de Aventura?", None, lambda r: "finn" in r.lower() or "aventura" in r.lower()),
    ("Pregunta personal",      "¿Te gusta la música?",          None,      lambda r: len(r.split()) < 30),
]

ok_total = 0
for etiqueta, pregunta, persona, check in casos:
    resp, t = ask(pregunta, sp, persona)
    palabras = len(resp.split())
    ok = check(resp)
    ok_total += ok
    color = GREEN if ok else RED
    marca = "✓" if ok else "✗"
    print(f"{color}{marca}{RESET} [{t:.1f}s|{palabras}p] {BOLD}{etiqueta}{RESET}")
    print(f"   Q: {pregunta}")
    print(f"   R: {resp[:120]}")
    print()

print(f"{BOLD}Resultado: {ok_total}/{len(casos)} checks pasaron{RESET}")
