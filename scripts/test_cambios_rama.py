"""
Script de pruebas para validar los cambios de la rama dev/mejoras-rendimiento-memoria.

Prueba directamente contra Ollama y el sistema de brain/memoria sin necesidad
de micrófono, cámara ni TTS.

Ejecutar desde la raíz del proyecto:
    python scripts/test_cambios_rama.py
"""
import sys
import time
import json
import logging
import traceback
from pathlib import Path

# Agregar raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.WARNING,  # Silenciar logs internos durante las pruebas
    format="%(asctime)s [%(levelname)s] %(message)s",
)

import ollama
from src.config.config_manager import config_manager
from src.memory.persistent_memory import PersistentMemory
from src.brain.brain import get_system_prompt, detectar_nombre, saludo_fijo, precargar_modelo

# ── Colores para la consola ────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

PASS = f"{GREEN}✓ PASS{RESET}"
FAIL = f"{RED}✗ FAIL{RESET}"
INFO = f"{CYAN}ℹ{RESET}"

resultados = []

# Limpiar archivos temporales de ejecuciones anteriores
for _f in ["data/test_anonimo.json", "data/test_persona.json",
           "data/test_persona_fresh.json", "data/test_ctx.json",
           "data/test_ctx2.json", "data/test_real.json", "data/test_conv.json"]:
    Path(_f).unlink(missing_ok=True)

def titulo(texto: str):
    print(f"\n{BOLD}{CYAN}{'═'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {texto}{RESET}")
    print(f"{BOLD}{CYAN}{'═'*60}{RESET}")

def subtitulo(texto: str):
    print(f"\n{YELLOW}── {texto} ──{RESET}")

def registrar(nombre: str, ok: bool, detalle: str = ""):
    resultados.append((nombre, ok, detalle))
    estado = PASS if ok else FAIL
    print(f"  {estado}  {nombre}")
    if detalle:
        print(f"         {detalle}")

def preguntar_llm(pregunta: str, persona: str | None = None,
                  memoria: PersistentMemory | None = None) -> tuple[str, float]:
    """Hace una pregunta al LLM y devuelve (respuesta, tiempo_segundos)."""
    model = config_manager.get("text_model", "qwen2.5:1.5b")
    options = config_manager.get_ollama_options()

    if memoria:
        memoria.add_user_message(pregunta, persona)
        messages = memoria.get_context_for_llm(persona)
    else:
        system = get_system_prompt()
        if persona:
            system += f" El usuario se llama {persona}."
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": pregunta},
        ]

    t0 = time.time()
    respuesta_chunks = []
    stream = ollama.chat(model=model, messages=messages, stream=True, options=options)
    for chunk in stream:
        respuesta_chunks.append(chunk["message"]["content"])
    elapsed = time.time() - t0

    respuesta = "".join(respuesta_chunks).strip()

    if memoria:
        memoria.add_assistant_message(respuesta, persona)

    return respuesta, elapsed


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 1: Precarga del modelo
# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 1 — Precarga del modelo LLM")

subtitulo("Test 1.1: Primera respuesta SIN precarga (baseline)")
_, t_sin_precarga = preguntar_llm("hola")
print(f"  {INFO}  Tiempo sin precarga: {t_sin_precarga:.2f}s")
registrar("Primera respuesta sin precarga medida", True, f"{t_sin_precarga:.2f}s")

subtitulo("Test 1.2: Precarga bloqueante del modelo")
t0 = time.time()
precargar_modelo()
t_precarga = time.time() - t0
print(f"  {INFO}  Tiempo de precarga: {t_precarga:.2f}s")
registrar("precargar_modelo() ejecuta sin error", True, f"{t_precarga:.2f}s")

subtitulo("Test 1.3: Primera respuesta DESPUÉS de precarga")
_, t_con_precarga = preguntar_llm("hola")
print(f"  {INFO}  Tiempo con precarga: {t_con_precarga:.2f}s")
# Nota: el modelo ya estaba en RAM desde el test 1.1, así que comparamos
# contra el promedio de respuestas consecutivas (test 1.4).
# Lo que validamos aquí es que la respuesta es razonablemente rápida (< 30s).
registrar(
    "Respuesta post-precarga razonablemente rápida (< 30s)",
    t_con_precarga < 30.0,
    f"tiempo={t_con_precarga:.2f}s"
)

subtitulo("Test 1.4: Respuestas consecutivas (deben ser rápidas)")
tiempos = []
for i in range(3):
    _, t = preguntar_llm(f"pregunta número {i+1}")
    tiempos.append(t)
    print(f"  {INFO}  Respuesta {i+1}: {t:.2f}s")
promedio = sum(tiempos) / len(tiempos)
registrar(
    "Respuestas consecutivas < 15s promedio",
    promedio < 15.0,
    f"promedio={promedio:.2f}s"
)


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 2: System prompt — Zambrano es un equipo
# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 2 — Zambrano es un equipo, no una persona")

subtitulo("Test 2.1: Verificar system prompt contiene 'equipo'")
sp = get_system_prompt()
tiene_equipo = "equipo" in sp.lower()
registrar("System prompt menciona 'equipo Zambrano'", tiene_equipo,
          sp[:120] + "..." if not tiene_equipo else "OK")

subtitulo("Test 2.2: Preguntar quién creó a BMO")
resp, _ = preguntar_llm("¿Quién te creó?")
print(f"  {INFO}  Respuesta: {resp}")
# Debe mencionar equipo o Zambrano, NO debe decir "una persona llamada Zambrano"
ok = "zambrano" in resp.lower() or "equipo" in resp.lower()
no_persona = "persona llamada" not in resp.lower() and "señor zambrano" not in resp.lower()
registrar("Menciona Zambrano o equipo", ok, resp[:100])
registrar("No lo describe como persona individual", no_persona, resp[:100])

subtitulo("Test 2.3: Preguntar directamente sobre Zambrano")
resp, _ = preguntar_llm("¿Qué es Zambrano?")
print(f"  {INFO}  Respuesta: {resp}")
ok_equipo = "equipo" in resp.lower() or "desarrollo" in resp.lower() or "creador" in resp.lower()
registrar("Describe Zambrano como equipo/creadores", ok_equipo, resp[:100])


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 3: Respuestas conversacionales
# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 3 — Respuestas conversacionales")

PREGUNTAS_CONV = [
    ("¿Cómo estás?",           ["bien", "listo", "genial", "perfecto", "estoy", "muy"]),
    ("¿Qué eres?",             ["bmo", "robot", "asistente"]),
    ("¿Qué puedes hacer?",     ["ayudar", "responder", "hablar", "preguntas"]),
    ("Hola",                   ["hola", "hey", "buenas", "bienvenido"]),
    ("¿Cuál es tu nombre?",    ["bmo"]),
]

for pregunta, palabras_clave in PREGUNTAS_CONV:
    subtitulo(f"Test: '{pregunta}'")
    resp, t = preguntar_llm(pregunta)
    print(f"  {INFO}  Respuesta ({t:.1f}s): {resp}")
    resp_lower = resp.lower()
    tiene_respuesta = any(p in resp_lower for p in palabras_clave)
    registrar(
        f"Responde correctamente a '{pregunta}'",
        tiene_respuesta,
        f"Buscando: {palabras_clave} → {'encontrado' if tiene_respuesta else 'NO encontrado'}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 4: Longitud de respuestas adaptativa
# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 4 — Longitud adaptativa de respuestas")

subtitulo("Test 4.1: Pregunta corta → respuesta corta")
resp, _ = preguntar_llm("¿Cómo estás?")
palabras = len(resp.split())
print(f"  {INFO}  Respuesta ({palabras} palabras): {resp}")
registrar("Saludo → respuesta corta (< 30 palabras)", palabras < 30, f"{palabras} palabras")

subtitulo("Test 4.2: Pregunta de dato simple → respuesta concisa")
resp, _ = preguntar_llm("¿Cuál es la capital de Francia?")
palabras = len(resp.split())
print(f"  {INFO}  Respuesta ({palabras} palabras): {resp}")
tiene_paris = "paris" in resp.lower() or "parís" in resp.lower()
registrar("Capital de Francia → menciona París", tiene_paris, resp)
registrar("Respuesta concisa (< 40 palabras)", palabras < 40, f"{palabras} palabras")

subtitulo("Test 4.3: Pregunta de explicación → respuesta más larga pero no excesiva")
resp, _ = preguntar_llm("¿Cómo funciona un motor de combustión interna?")
palabras = len(resp.split())
print(f"  {INFO}  Respuesta ({palabras} palabras): {resp}")
registrar("Explicación → respuesta sustancial (> 20 palabras)", palabras > 20, f"{palabras} palabras")
registrar("Explicación → no excesiva (< 200 palabras)", palabras < 200, f"{palabras} palabras")

subtitulo("Test 4.4: Respuesta no cortada (verifica que termina con puntuación)")
resp, _ = preguntar_llm("Explícame qué es la fotosíntesis")
print(f"  {INFO}  Respuesta: {resp}")
termina_bien = resp.endswith((".", "!", "?", "…")) if resp else False
registrar("Respuesta termina con puntuación (no cortada)", termina_bien,
          f"Último char: '{resp[-1] if resp else 'vacío'}'")

subtitulo("Test 4.5: Verificar num_predict = 300 en config")
num_predict = config_manager.get("llm_num_predict", 0)
registrar("llm_num_predict = 300 en config", num_predict == 300, f"valor actual: {num_predict}")


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 5: Conocimiento factual
# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 5 — Conocimiento factual")

HECHOS = [
    ("¿De qué colores es la bandera de Colombia?",
     ["amarillo", "azul", "rojo"],
     "Bandera Colombia"),
    ("¿Cuál es la capital de Brasil?",
     ["brasilia"],
     "Capital Brasil"),
    ("¿Cuántos continentes hay?",
     ["siete", "7", "7 continentes", "siete continentes"],
     "Número de continentes"),
    ("¿De qué colores es la bandera de México?",
     ["verde", "blanco", "rojo"],
     "Bandera México"),
]

for pregunta, palabras_clave, nombre_test in HECHOS:
    subtitulo(f"Test: {nombre_test}")
    resp, t = preguntar_llm(pregunta)
    print(f"  {INFO}  Respuesta ({t:.1f}s): {resp}")
    resp_lower = resp.lower()
    # Para banderas necesitamos todos los colores; para datos únicos basta uno
    if "bandera" in pregunta.lower():
        ok = all(p in resp_lower for p in palabras_clave)
        detalle = f"Buscando todos: {palabras_clave}"
    else:
        ok = any(p in resp_lower for p in palabras_clave)
        detalle = f"Buscando alguno: {palabras_clave}"
    registrar(f"{nombre_test} — respuesta correcta", ok, detalle)


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 6: Sistema de memoria
# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 6 — Sistema de memoria")

subtitulo("Test 6.1: Memoria anónima sobrescribe (no acumula)")
mem_anonima = PersistentMemory(memory_file="data/test_anonimo.json", max_conversations=5)

# Simular 3 intercambios anónimos
for i in range(3):
    mem_anonima.add_user_message(f"pregunta anónima número {i+1}", persona=None)
    mem_anonima.add_assistant_message(f"respuesta {i+1}", persona=None)

# La sesión solo debe tener el último par (user sobrescribe, assistant se agrega)
msgs_sesion = mem_anonima.session_memory
print(f"  {INFO}  Mensajes en sesión anónima: {len(msgs_sesion)}")
for m in msgs_sesion:
    print(f"         [{m['role']}] {m['content']}")

# Debe haber solo 2 mensajes: el último user + el último assistant
registrar(
    "Sesión anónima tiene solo el último intercambio (≤ 2 msgs)",
    len(msgs_sesion) <= 2,
    f"{len(msgs_sesion)} mensajes en sesión"
)
if msgs_sesion:
    ultimo_user = next((m for m in reversed(msgs_sesion) if m["role"] == "user"), None)
    registrar(
        "Último mensaje de usuario es el más reciente",
        ultimo_user and "número 3" in ultimo_user.get("content", ""),
        ultimo_user.get("content", "") if ultimo_user else "no hay user"
    )

subtitulo("Test 6.2: commit_session anónimo NO persiste en permanente")
msgs_antes = len(mem_anonima.permanent_memory)
mem_anonima.commit_session_to_permanent(persona=None)
msgs_despues = len(mem_anonima.permanent_memory)
print(f"  {INFO}  Permanente antes: {msgs_antes}, después: {msgs_despues}")
registrar(
    "Commit anónimo no agrega a permanente",
    msgs_despues == msgs_antes,
    f"antes={msgs_antes}, después={msgs_despues}"
)

subtitulo("Test 6.3: Memoria con persona registrada acumula en sesión")
mem_persona = PersistentMemory(memory_file="data/test_persona.json", max_conversations=5)

for i in range(3):
    mem_persona.add_user_message(f"pregunta de Juan número {i+1}", persona="Juan")
    mem_persona.add_assistant_message(f"respuesta {i+1}", persona="Juan")

msgs_sesion_persona = mem_persona.session_memory
print(f"  {INFO}  Mensajes en sesión con persona: {len(msgs_sesion_persona)}")
registrar(
    "Sesión con persona acumula todos los mensajes (6 msgs)",
    len(msgs_sesion_persona) == 6,
    f"{len(msgs_sesion_persona)} mensajes"
)

subtitulo("Test 6.4: commit_session con persona SÍ persiste en permanente")
# Usar instancia fresca para evitar estado de ejecuciones anteriores
mem_persona_fresh = PersistentMemory(memory_file="data/test_persona_fresh.json", max_conversations=5)
for i in range(3):
    mem_persona_fresh.add_user_message(f"pregunta de Juan número {i+1}", persona="Juan")
    mem_persona_fresh.add_assistant_message(f"respuesta {i+1}", persona="Juan")
msgs_antes = len(mem_persona_fresh.permanent_memory)
mem_persona_fresh.commit_session_to_permanent(persona="Juan")
msgs_despues = len(mem_persona_fresh.permanent_memory)
print(f"  {INFO}  Permanente antes: {msgs_antes}, después: {msgs_despues}")
registrar(
    "Commit con persona agrega mensajes a permanente",
    msgs_despues > msgs_antes,
    f"antes={msgs_antes}, después={msgs_despues}"
)
registrar(
    "Sesión se limpia después del commit",
    len(mem_persona_fresh.session_memory) == 0,
    f"{len(mem_persona_fresh.session_memory)} mensajes en sesión"
)

subtitulo("Test 6.5: Contexto LLM anónimo solo tiene system + último mensaje")
mem_ctx = PersistentMemory(memory_file="data/test_ctx.json", max_conversations=5)
mem_ctx.add_user_message("primera pregunta", persona=None)
mem_ctx.add_assistant_message("primera respuesta", persona=None)
mem_ctx.add_user_message("segunda pregunta", persona=None)  # sobrescribe

ctx = mem_ctx.get_context_for_llm(persona=None)
print(f"  {INFO}  Mensajes en contexto anónimo: {len(ctx)}")
for m in ctx:
    print(f"         [{m['role']}] {m['content'][:60]}")
registrar(
    "Contexto anónimo = system + 1 user (no acumula historial)",
    len(ctx) == 2,
    f"{len(ctx)} mensajes (esperado: 2)"
)

subtitulo("Test 6.6: Contexto LLM con persona incluye historial")
mem_ctx2 = PersistentMemory(memory_file="data/test_ctx2.json", max_conversations=5)
# Simular historial permanente de Juan
mem_ctx2.add_user_message("hola soy Juan", persona="Juan")
mem_ctx2.add_assistant_message("hola Juan!", persona="Juan")
mem_ctx2.commit_session_to_permanent(persona="Juan")
# Nueva sesión
mem_ctx2.add_user_message("¿me recuerdas?", persona="Juan")

ctx2 = mem_ctx2.get_context_for_llm(persona="Juan")
print(f"  {INFO}  Mensajes en contexto con persona: {len(ctx2)}")
for m in ctx2:
    print(f"         [{m['role']}] {m['content'][:60]}")
registrar(
    "Contexto con persona incluye historial previo (> 2 msgs)",
    len(ctx2) > 2,
    f"{len(ctx2)} mensajes"
)

subtitulo("Test 6.7: Prueba real — BMO recuerda el nombre en conversación")
mem_real = PersistentMemory(memory_file="data/test_real.json", max_conversations=5)
# Primer turno: presentación
resp1, _ = preguntar_llm("Hola, me llamo Carlos", persona="Carlos", memoria=mem_real)
print(f"  {INFO}  Respuesta 1: {resp1}")
# Segundo turno: verificar que recuerda
resp2, _ = preguntar_llm("¿Cómo me llamo?", persona="Carlos", memoria=mem_real)
print(f"  {INFO}  Respuesta 2: {resp2}")
registrar(
    "BMO recuerda el nombre en conversación continua",
    "carlos" in resp2.lower(),
    resp2[:100]
)


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 7: Detección de nombres
# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 7 — Detección de nombres")

CASOS_NOMBRE = [
    ("me llamo Juan",          "Juan",  True),
    ("mi nombre es María",     "María", True),
    ("soy Pedro",              "Pedro", True),
    ("llámame Carlos",         "Carlos",True),
    ("me dicen Luisa",         "Luisa", True),
    ("estoy bien",             None,    False),
    ("soy feliz",              None,    False),
    ("hola bmo",               None,    False),
    ("soy jake",               None,    False),  # nombre en lista negra
]

for texto, nombre_esperado, debe_detectar in CASOS_NOMBRE:
    resultado = detectar_nombre(texto)
    if debe_detectar:
        ok = resultado is not None and resultado.lower() == (nombre_esperado or "").lower()
    else:
        ok = resultado is None
    registrar(
        f"detectar_nombre('{texto}') → {nombre_esperado or 'None'}",
        ok,
        f"obtenido: {resultado}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 8: Saludos
# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 8 — Saludos")

subtitulo("Test 8.1: Saludo con nombre conocido")
for nombre in ["Juan", "María", "Carlos"]:
    saludo = saludo_fijo(nombre)
    ok = nombre.lower() in saludo.lower()
    registrar(f"saludo_fijo('{nombre}') contiene el nombre", ok, saludo)

subtitulo("Test 8.2: Saludo sin nombre (desconocido)")
saludo_desc = saludo_fijo(None)
ok = len(saludo_desc) > 5
registrar("saludo_fijo(None) devuelve texto válido", ok, saludo_desc)


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 9: Prueba de conversación completa simulada
# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 9 — Conversación completa simulada")

print(f"\n  {INFO}  Simulando conversación con persona registrada 'Ana'...\n")
mem_conv = PersistentMemory(memory_file="data/test_conv.json", max_conversations=5)

conversacion = [
    ("Hola, me llamo Ana",                    "Ana"),
    ("¿Cómo estás?",                          "Ana"),
    ("¿Cuál es la capital de Colombia?",      "Ana"),
    ("¿De qué colores es la bandera de Colombia?", "Ana"),
    ("¿Quién te creó?",                       "Ana"),
    ("¿Me recuerdas?",                        "Ana"),
]

for i, (pregunta, persona) in enumerate(conversacion, 1):
    resp, t = preguntar_llm(pregunta, persona=persona, memoria=mem_conv)
    print(f"  [{i}] Usuario: {pregunta}")
    print(f"      BMO ({t:.1f}s): {resp}")
    print()

# Verificar que la última respuesta recuerda a Ana
resp_final, _ = preguntar_llm("¿Cómo me llamo?", persona="Ana", memoria=mem_conv)
print(f"  [7] Usuario: ¿Cómo me llamo?")
print(f"      BMO: {resp_final}")
registrar(
    "BMO recuerda el nombre 'Ana' al final de la conversación",
    "ana" in resp_final.lower(),
    resp_final[:100]
)


# ══════════════════════════════════════════════════════════════════════════════
# RESUMEN FINAL
# ══════════════════════════════════════════════════════════════════════════════
titulo("RESUMEN DE RESULTADOS")

total  = len(resultados)
passed = sum(1 for _, ok, _ in resultados if ok)
failed = total - passed

print(f"\n  Total:   {total}")
print(f"  {GREEN}Pasaron: {passed}{RESET}")
print(f"  {RED if failed else GREEN}Fallaron: {failed}{RESET}")
print()

if failed:
    print(f"{RED}Tests fallidos:{RESET}")
    for nombre, ok, detalle in resultados:
        if not ok:
            print(f"  {FAIL}  {nombre}")
            if detalle:
                print(f"         {detalle}")

# Guardar resultados en JSON
resultado_json = {
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "total": total,
    "passed": passed,
    "failed": failed,
    "tests": [
        {"nombre": n, "ok": ok, "detalle": d}
        for n, ok, d in resultados
    ]
}
out_path = Path("test_results_rama_dev.json")
out_path.write_text(json.dumps(resultado_json, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\n  {INFO}  Resultados guardados en {out_path}")

# Limpiar archivos temporales de prueba
for f in ["data/test_anonimo.json", "data/test_persona.json",
          "data/test_persona_fresh.json", "data/test_ctx.json",
          "data/test_ctx2.json", "data/test_real.json", "data/test_conv.json"]:
    Path(f).unlink(missing_ok=True)

print()
sys.exit(0 if failed == 0 else 1)
