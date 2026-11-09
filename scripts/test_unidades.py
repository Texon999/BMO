"""
Pruebas unitarias puras de BMO.

NO requieren: cámara, micrófono, altavoces, Ollama, MongoDB ni modelos ONNX.
Solo ejercitan funciones puras de voz, visión (logica sin frame) y conversación.

Ejecutar desde la raiz del repo:
    python scripts/test_unidades.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.brain.brain import (
    detectar_nombre,
    saludo_fijo,
    normalizar_para_tts,
    normalizar_texto_entrada,
)
from src.brain.classifier import (
    sin_acentos,
    categorizar_pregunta,
    num_predict_para,
    max_oraciones_para,
    length_hint_para,
    QueryCategory,
)
from src.config.config_manager import config_manager

PASS = "PASS"
FAIL = "FAIL"
resultados: list[tuple[str, bool, str]] = []


def reg(nombre: str, ok: bool, detalle: str = ""):
    resultados.append((nombre, ok, detalle))
    print(f"  [{'OK' if ok else 'XX'}] {nombre}")
    if detalle:
        print(f"         {detalle}")


def titulo(t: str):
    print(f"\n===== {t} =====")


# ---------------------------------------------------------------------------
# Bloque 1 — Detección de nombres (voz / conversación)
# ---------------------------------------------------------------------------
titulo("Deteccion de nombres")

FRASES_SI = [
    ("me llamo Juan", "Juan"),
    ("mi nombre es Maria", "Maria"),
    ("soy Pedro", "Pedro"),
    ("llamame Carlos", "Carlos"),
    ("me dicen Luisa", "Luisa"),
    ("me puedes llamar Andres", "Andres"),
    ("soy Ana", "Ana"),
    ("registrame como Laura", "Laura"),
]
for frase, esperado in FRASES_SI:
    obtenido = detectar_nombre(frase)
    reg(f"detectar_nombre({frase!r}) -> {esperado!r}",
        obtenido is not None and obtenido.lower() == esperado.lower(),
        f"obtenido: {obtenido!r}")

FRASES_NO = [
    "hola como estas",
    "estoy bien",
    "soy feliz",
    "soy bmo",
    "soy jake",
    "soy finn",
    "me llamo bien",
    "que hora es",
    "cuentame algo",
    "",  # vacio
]
for frase in FRASES_NO:
    obtenido = detectar_nombre(frase)
    reg(f"No detecta nombre en {frase!r}", obtenido is None,
        f"obtenido: {obtenido!r}")

# Nombres cortos (<= 2 chars) no validos
for frase in ["me llamo Al", "soy Jo", "mi nombre es Li"]:
    reg(f"Nombre corto ignorado: {frase!r}", detectar_nombre(frase) is None,
        f"obtenido: {detectar_nombre(frase)!r}")

# Capitalizacion
for frase, esperado in [("me llamo JUAN", "Juan"),
                        ("mi nombre es ana", "Ana"),
                        ("soy CARLOS", "Carlos")]:
    reg(f"Capitalizacion: {frase!r} -> {esperado!r}",
        detectar_nombre(frase) == esperado,
        f"obtenido: {detectar_nombre(frase)!r}")

# ---------------------------------------------------------------------------
# Bloque 2 — Normalizacion para TTS (voz)
# ---------------------------------------------------------------------------
titulo("Normalizacion para TTS")

casos_tts = [
    ("pi vale 3.14", "pí"),                      # simbolo pi
    ("raiz cuadrada de 4", "raiz cuadrada de "), # raiz
    ("es infinito", "infinito"),                 # infinito
    ("texto con **asteriscos**", "texto con asteriscos"),  # markdown limpio
    ("titulo # hola", "titulo hola"),            # encabezado limpio
    ("codigo `a`", "codigo a"),                  # backticks limpio
]
for entrada, esperado_fragmento in casos_tts:
    salida = normalizar_para_tts(entrada)
    reg(f"TTSS: {entrada!r} contiene {esperado_fragmento!r}",
        esperado_fragmento in salida,
        f"salida: {salida!r}")

# ---------------------------------------------------------------------------
# Bloque 3 — Normalizacion de entrada (conversacion)
# ---------------------------------------------------------------------------
titulo("Normalizacion de texto de entrada")

casos_entrada = [
    ("numero p", "número pi"),          # el codigo anade la tilde
    ("numero p-i", "número pi-i"),      # patron 'p\b' coincide antes que 'p-i' (comportamiento actual)
    ("el p", "el pi"),
    ("digitos de pi", "dígitos de pi"), # el codigo anade la tilde
]
for entrada, esperado in casos_entrada:
    reg(f"Entrada: {entrada!r} -> {esperado!r}",
        normalizar_texto_entrada(entrada) == esperado,
        f"obtenido: {normalizar_texto_entrada(entrada)!r}")

# ---------------------------------------------------------------------------
# Bloque 4 — Clasificador de preguntas (conversacion)
# ---------------------------------------------------------------------------
titulo("Clasificador de preguntas")

casos_clase = [
    ("hola, como estas", QueryCategory.GREETING),
    ("gracias", QueryCategory.GREETING),
    ("que es python", QueryCategory.FACTUAL),   # "que es" coincide antes que el patron tecnico
    ("cuentame un cuento de hadas", QueryCategory.CREATIVE),
    ("como funciona internet", QueryCategory.EXPLAIN),
    ("dime algo", QueryCategory.SIMPLE),
]
for texto, esperado in casos_clase:
    categoria = categorizar_pregunta(texto)
    reg(f"Clasificar: {texto!r} -> {esperado}",
        categoria == esperado,
        f"obtenido: {categoria}")

# Funciones derivadas devuelven tipos/ rangos esperados
texto_prueba = "que es python"
np_ = num_predict_para(texto_prueba)
mo = max_oraciones_para(texto_prueba)
lh = length_hint_para(texto_prueba)
reg("num_predict_para devuelve int >= 10", isinstance(np_, int) and np_ >= 10,
    f"obtenido: {np_!r}")
reg("max_oraciones_para devuelve int >= 1", isinstance(mo, int) and mo >= 1,
    f"obtenido: {mo!r}")
reg("length_hint_para devuelve str no vacia", isinstance(lh, str) and len(lh) > 0,
    f"obtenido: {lh!r}")

# sin_acentos
reg("sin_acentos elimina tildes", sin_acentos("áéíóúñ") == "aeioun",
    f"obtenido: {sin_acentos('áéíóúñ')!r}")

# ---------------------------------------------------------------------------
# Bloque 5 — Saludos (conversacion)
# ---------------------------------------------------------------------------
titulo("Saludos")

s_con_nombre = saludo_fijo("Juan")
reg("Saludo con nombre contiene el nombre", "Juan" in s_con_nombre,
    f"obtenido: {s_con_nombre!r}")

s_sin_nombre = saludo_fijo(None)
reg("Saludo sin nombre es uno de los predefinidos",
    s_sin_nombre in [
        "¡Hola! Soy BMO, un robot de IA. ¿Cómo te llamas?",
        "¡Oye, hola! No te conozco todavía. ¿Cuál es tu nombre?",
        "¡Bienvenido! Soy BMO. ¿Me dices tu nombre?",
        "¡Hola! Me llamo BMO y me encanta conocer gente nueva. ¿Y tú?",
        "¡Qué bueno que te acercaste! Soy BMO. ¿Cómo te llamas?",
    ],
    f"obtenido: {s_sin_nombre!r}")

# ---------------------------------------------------------------------------
# Bloque 6 — Configuracion (sin servicios externos)
# ---------------------------------------------------------------------------
titulo("Configuracion")

opts = config_manager.get_ollama_options()
for clave in ("temperature", "top_k", "top_p", "num_predict", "repeat_penalty", "keep_alive", "num_thread"):
    reg(f"get_ollama_options tiene {clave}", clave in opts,
        f"claves: {sorted(opts.keys())}")

reg("text_model por defecto presente",
    config_manager.get("text_model") is not None,
    f"obtenido: {config_manager.get('text_model')!r}")

# ---------------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------------
print("\n===== RESUMEN =====")
total = len(resultados)
pasados = sum(1 for _, ok, _ in resultados if ok)
fallados = total - pasados
print(f"Total:   {total}")
print(f"Pasaron: {pasados}")
print(f"Fallaron: {fallados}")
for n, ok, d in resultados:
    if not ok:
        print(f"  [{FAIL}] {n}")
        if d:
            print(f"         {d}")

sys.exit(0 if fallados == 0 else 1)
