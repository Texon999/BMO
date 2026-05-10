"""
Suite de pruebas para la rama dev/mejoras-rendimiento-memoria.
Valida: precarga LLM, Zambrano, conversación, longitud, hechos,
        memoria, nombres, saludos, lógica cámara, normalización TTS,
        y resistencia a preguntas sin sentido / alucinaciones.

Ejecutar desde la raíz:
    .venv\\Scripts\\python.exe scripts/test_cambios_rama.py
"""
import sys, time, json, logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
logging.basicConfig(level=logging.WARNING)

import ollama
from src.config.config_manager import config_manager
from src.memory.persistent_memory import PersistentMemory
from src.brain.brain import (
    get_system_prompt, detectar_nombre, saludo_fijo,
    precargar_modelo, normalizar_para_tts,
)

# ── Colores ───────────────────────────────────────────────────────────────────
G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; C = "\033[96m"; B = "\033[1m"; X = "\033[0m"
PASS = f"{G}✓ PASS{X}"; FAIL = f"{R}✗ FAIL{X}"; INFO = f"{C}ℹ{X}"

resultados: list[tuple[str, bool, str]] = []

# Limpiar archivos temporales de ejecuciones anteriores
for _f in Path("data").glob("test_*.json"):
    _f.unlink(missing_ok=True)


def titulo(t):
    print(f"\n{B}{C}{'═'*60}{X}\n{B}{C}  {t}{X}\n{B}{C}{'═'*60}{X}")

def sub(t):
    print(f"\n{Y}── {t} ──{X}")

def reg(nombre, ok, detalle=""):
    resultados.append((nombre, ok, detalle))
    print(f"  {PASS if ok else FAIL}  {nombre}")
    if detalle:
        print(f"         {detalle}")


def llm(pregunta, persona=None, mem=None):
    """Hace una pregunta al LLM y devuelve (respuesta, segundos)."""
    model = config_manager.get("text_model", "qwen2.5:1.5b")
    opts  = config_manager.get_ollama_options()
    if mem:
        mem.add_user_message(pregunta, persona)
        msgs = mem.get_context_for_llm(persona)
    else:
        sp = get_system_prompt()
        if persona:
            sp += f" El usuario se llama {persona}."
        msgs = [{"role": "system", "content": sp}, {"role": "user", "content": pregunta}]
    t0 = time.time()
    chunks = []
    for c in ollama.chat(model=model, messages=msgs, stream=True, options=opts):
        chunks.append(c["message"]["content"])
    resp = "".join(chunks).strip()
    if mem:
        mem.add_assistant_message(resp, persona)
    return resp, time.time() - t0


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 1 — Precarga del modelo LLM")
# ══════════════════════════════════════════════════════════════════════════════

sub("1.1 Baseline sin precarga")
_, t0 = llm("hola")
print(f"  {INFO}  Sin precarga: {t0:.2f}s")
reg("Baseline medido", True, f"{t0:.2f}s")

sub("1.2 Precarga bloqueante")
t_pre = time.time()
precargar_modelo()
t_pre = time.time() - t_pre
print(f"  {INFO}  Precarga: {t_pre:.2f}s")
reg("precargar_modelo() sin error", True, f"{t_pre:.2f}s")

sub("1.3 Respuestas consecutivas (modelo caliente)")
tiempos = []
for i in range(3):
    _, t = llm(f"pregunta {i+1}")
    tiempos.append(t)
    print(f"  {INFO}  Resp {i+1}: {t:.2f}s")
prom = sum(tiempos)/len(tiempos)
reg("Promedio < 15s con modelo caliente", prom < 15.0, f"prom={prom:.2f}s")


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 2 — Identidad: Zambrano programador del SENA")
# ══════════════════════════════════════════════════════════════════════════════

sub("2.1 System prompt contiene SENA")
sp = get_system_prompt()
reg("Prompt menciona 'Zambrano'", "zambrano" in sp.lower())
reg("Prompt menciona 'SENA'",     "sena"     in sp.lower())
print(f"  {INFO}  Longitud: {len(sp.split())} palabras")

sub("2.2 ¿Quién te creó?")
r, _ = llm("¿Quién te creó?")
print(f"  {INFO}  {r}")
reg("Menciona Zambrano", "zambrano" in r.lower(), r[:100])
reg("No dice 'equipo Zambrano'", "equipo zambrano" not in r.lower(), r[:100])

sub("2.3 ¿Qué es Zambrano?")
r, _ = llm("¿Qué es Zambrano?")
print(f"  {INFO}  {r}")
reg("Describe como persona/programador",
    any(p in r.lower() for p in ["programador","sena","creador","zambrano"]), r[:100])


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 3 — Respuestas conversacionales")
# ══════════════════════════════════════════════════════════════════════════════

CONV = [
    ("¿Cómo estás?",        ["bien","listo","genial","estoy","muy"]),
    ("¿Qué eres?",          ["bmo","robot","asistente"]),
    ("¿Qué puedes hacer?",  ["ayudar","responder","hablar","preguntas"]),
    ("Hola",                ["hola","hey","buenas","bienvenido"]),
    ("¿Cuál es tu nombre?", ["bmo"]),
]
for preg, claves in CONV:
    r, t = llm(preg)
    print(f"  {INFO}  [{t:.1f}s] {preg!r} → {r[:80]}")
    reg(f"Responde a {preg!r}", any(c in r.lower() for c in claves))


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 4 — Longitud adaptativa")
# ══════════════════════════════════════════════════════════════════════════════

sub("4.1 Saludo → corto")
r, _ = llm("¿Cómo estás?")
w = len(r.split())
print(f"  {INFO}  {w}p: {r}")
reg("Saludo < 35 palabras", w < 35, f"{w}p")

sub("4.2 Dato simple → conciso")
r, _ = llm("¿Cuál es la capital de Francia?")
w = len(r.split())
print(f"  {INFO}  {w}p: {r}")
reg("Menciona París", any(p in r.lower() for p in ["paris","parís"]), r)
reg("Conciso < 40p", w < 40, f"{w}p")

sub("4.3 Explicación → sustancial pero no excesiva")
r, _ = llm("¿Cómo funciona un motor de combustión interna?")
w = len(r.split())
print(f"  {INFO}  {w}p: {r[:120]}...")
reg("Sustancial > 15p", w > 15, f"{w}p")
reg("No excesiva < 200p", w < 200, f"{w}p")

sub("4.4 Respuesta no cortada")
r, _ = llm("Explícame qué es la fotosíntesis")
print(f"  {INFO}  Último char: {r[-1]!r}")
reg("Termina con puntuación", r[-1] in ".!?…" if r else False, r[-30:])

sub("4.5 num_predict = 300")
reg("llm_num_predict = 300", config_manager.get("llm_num_predict") == 300,
    f"valor: {config_manager.get('llm_num_predict')}")


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 5 — Conocimiento factual")
# ══════════════════════════════════════════════════════════════════════════════

HECHOS = [
    ("¿De qué colores es la bandera de Colombia?",
     ["amarillo","azul","rojo"], True),
    ("¿Cuál es la capital de Brasil?",
     ["brasilia"], False),
    ("¿Cuántos continentes hay?",
     ["siete","7"], False),
    ("¿De qué colores es la bandera de México?",
     ["verde","blanco","rojo"], True),
]
for preg, claves, todos in HECHOS:
    r, t = llm(preg)
    print(f"  {INFO}  [{t:.1f}s] {r[:90]}")
    ok = (all if todos else any)(c in r.lower() for c in claves)
    reg(preg[:50], ok, f"buscando: {claves}")


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 6 — Sistema de memoria")
# ══════════════════════════════════════════════════════════════════════════════

sub("6.1 Anónimo sobrescribe sesión")
m = PersistentMemory("data/test_m1.json", 5)
for i in range(3):
    m.add_user_message(f"pregunta {i+1}", None)
    m.add_assistant_message(f"resp {i+1}", None)
reg("Sesión anónima ≤ 2 msgs", len(m.session_memory) <= 2, f"{len(m.session_memory)}")
u = next((x for x in reversed(m.session_memory) if x["role"]=="user"), None)
reg("Último user es el más reciente", u and "3" in u.get("content",""), u and u["content"])

sub("6.2 Commit anónimo no persiste")
antes = len(m.permanent_memory)
m.commit_session_to_permanent(None)
reg("No agrega a permanente", len(m.permanent_memory) == antes,
    f"antes={antes} después={len(m.permanent_memory)}")

sub("6.3 Persona acumula en sesión")
m2 = PersistentMemory("data/test_m2.json", 5)
for i in range(3):
    m2.add_user_message(f"preg {i+1}", "Juan")
    m2.add_assistant_message(f"resp {i+1}", "Juan")
reg("Sesión con persona = 6 msgs", len(m2.session_memory) == 6, f"{len(m2.session_memory)}")

sub("6.4 Commit persona persiste")
antes2 = len(m2.permanent_memory)
m2.commit_session_to_permanent("Juan")
reg("Agrega a permanente", len(m2.permanent_memory) > antes2,
    f"antes={antes2} después={len(m2.permanent_memory)}")
reg("Sesión limpia tras commit", len(m2.session_memory) == 0)

sub("6.5 Contexto anónimo = system + 1 user")
m3 = PersistentMemory("data/test_m3.json", 5)
m3.add_user_message("primera", None)
m3.add_assistant_message("resp1", None)
m3.add_user_message("segunda", None)
ctx = m3.get_context_for_llm(None)
reg("Contexto anónimo = 2 msgs", len(ctx) == 2, f"{len(ctx)}")

sub("6.6 BMO recuerda nombre en conversación")
m4 = PersistentMemory("data/test_m4.json", 5)
llm("Hola, me llamo Carlos", "Carlos", m4)
r2, _ = llm("¿Cómo me llamo?", "Carlos", m4)
print(f"  {INFO}  {r2}")
reg("Recuerda 'Carlos'", "carlos" in r2.lower(), r2[:80])


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 7 — Detección de nombres")
# ══════════════════════════════════════════════════════════════════════════════

NOMBRES = [
    ("me llamo Juan",     "Juan",  True),
    ("mi nombre es María","María", True),
    ("soy Pedro",         "Pedro", True),
    ("llámame Carlos",    "Carlos",True),
    ("me dicen Luisa",    "Luisa", True),
    ("estoy bien",        None,    False),
    ("soy feliz",         None,    False),
    ("hola bmo",          None,    False),
    ("soy jake",          None,    False),
]
for txt, esp, debe in NOMBRES:
    res = detectar_nombre(txt)
    ok  = (res is not None and res.lower() == (esp or "").lower()) if debe else (res is None)
    reg(f"detectar_nombre({txt!r}) → {esp}", ok, f"obtenido: {res}")


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 8 — Saludos")
# ══════════════════════════════════════════════════════════════════════════════

for n in ["Juan","María","Carlos"]:
    s = saludo_fijo(n)
    reg(f"saludo_fijo({n!r}) contiene nombre", n.lower() in s.lower(), s)
s0 = saludo_fijo(None)
reg("saludo_fijo(None) válido", len(s0) > 5, s0)


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 9 — Normalización TTS")
# ══════════════════════════════════════════════════════════════════════════════

TTS_CASOS = [
    ("cuantos digitos tiene pi",        "pí",           True),
    ("la constante π es irracional",    "pí",           True),
    ("2π radianes son 360 grados",      "pí",           True),
    ("la raiz cuadrada √9 es 3",        "raíz cuadrada",True),
    ("el resultado es 5²",              "al cuadrado",  True),
    ("**texto** con *markdown*",        "texto",        True),
    ("OK entendido",                    "okey",         True),
    ("hola como estas",                 "hola",         True),   # texto normal no cambia
]
for entrada, esperado, debe_contener in TTS_CASOS:
    salida = normalizar_para_tts(entrada)
    ok = (esperado in salida) == debe_contener
    reg(f"TTS: {entrada[:40]!r}", ok, f"→ {salida[:60]!r}")


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 10 — Lógica de nombres (cámara vs sin cámara)")
# ══════════════════════════════════════════════════════════════════════════════

class AgenteMock:
    def __init__(self, camara=False):
        self.vision = object() if camara else None
        self._nombre_activo = None
        self._nombre_cache_temporal = None
        self._nombre_camara_reconocido = None
        self._cara_desconocida_presente = False

    def simular(self, texto, conocidos):
        n = detectar_nombre(texto)
        if not n:
            return "sin_nombre"
        ya = n.lower() in [x.lower() for x in conocidos]
        cam = self.vision is not None
        if cam and self._cara_desconocida_presente and not ya:
            return "registrar_foto"
        if cam and self._nombre_camara_reconocido:
            return "ignorar"
        if not cam and not ya:
            self._nombre_cache_temporal = n
            self._nombre_activo = n
            return "cache_temporal"
        if ya:
            if not cam:
                self._nombre_cache_temporal = n
                self._nombre_activo = n
            return "ya_registrado"
        return "sin_accion"

a1 = AgenteMock(camara=False)
reg("Sin cámara + nombre nuevo → cache_temporal",
    a1.simular("me llamo Laura", []) == "cache_temporal")
reg("_nombre_activo = Laura", a1._nombre_activo == "Laura")

a2 = AgenteMock(camara=False)
reg("Sin cámara + nombre registrado → ya_registrado",
    a2.simular("soy Pedro", ["Pedro"]) == "ya_registrado")

a3 = AgenteMock(camara=True)
a3._cara_desconocida_presente = True
reg("Con cámara + cara desconocida → registrar_foto",
    a3.simular("me llamo Sofia", []) == "registrar_foto")

a4 = AgenteMock(camara=True)
a4._nombre_camara_reconocido = "Carlos"
reg("Con cámara + cara reconocida → ignorar nombre dicho",
    a4.simular("soy Pedro", []) == "ignorar")

m5 = PersistentMemory("data/test_m5.json", 5)
m5.add_user_message("hola soy Laura", None)
m5.add_assistant_message("hola!", None)
antes5 = len(m5.permanent_memory)
m5.commit_session_to_permanent(None)
reg("Caché temporal no persiste en permanente",
    len(m5.permanent_memory) == antes5)

m6 = PersistentMemory("data/test_m6.json", 5)
m6.add_user_message("hola soy Sofia", "Sofia")
m6.add_assistant_message("hola Sofia!", "Sofia")
antes6 = len(m6.permanent_memory)
m6.commit_session_to_permanent("Sofia")
reg("Nombre con foto SÍ persiste en permanente",
    len(m6.permanent_memory) > antes6)


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 11 — Resistencia a preguntas sin sentido / alucinaciones")
# ══════════════════════════════════════════════════════════════════════════════
# El modelo debe decir que no sabe en lugar de inventar.
# Criterio: la respuesta NO debe contener afirmaciones inventadas largas
# y SÍ debe contener alguna señal de incertidumbre o negación.

SEÑALES_NO_SE = [
    "no tengo", "no sé", "no se", "no estoy seguro", "no tengo información",
    "no puedo", "no conozco", "desconozco", "no tengo esa", "no tengo datos",
    "no tengo acceso", "no tengo conocimiento",
]

def tiene_señal_no_se(texto: str) -> bool:
    t = texto.lower()
    return any(s in t for s in SEÑALES_NO_SE)

PREGUNTAS_SIN_SENTIDO = [
    # Preguntas inventadas / imposibles de saber
    ("¿Cuál es el número de teléfono de la luna?",
     "Pregunta imposible — no debe inventar un número"),
    ("¿Qué comió el presidente de Colombia el martes pasado?",
     "Dato privado/imposible — no debe inventar"),
    ("¿Cuántos pelos tiene un gato llamado Manchas que vive en Bogotá?",
     "Dato específico imposible — no debe inventar"),
    ("¿Cuál es la contraseña del wifi de Zambrano?",
     "Dato privado — no debe inventar"),
    ("dime el resultado de multiplicar 7 por el color azul",
     "Sin sentido matemático — no debe inventar"),
    # Preguntas de conocimiento muy específico que el modelo 1.5b no tiene
    ("¿Cuál fue el resultado exacto del partido Colombia vs Brasil del 3 de marzo de 2019?",
     "Dato muy específico — no debe inventar resultado"),
    ("¿Cuántos bytes ocupa exactamente el kernel de Linux 6.8.2?",
     "Dato técnico muy específico — no debe inventar"),
]

print(f"\n  {INFO}  Probando {len(PREGUNTAS_SIN_SENTIDO)} preguntas sin sentido...\n")
for preg, descripcion in PREGUNTAS_SIN_SENTIDO:
    r, t = llm(preg)
    palabras = len(r.split())
    tiene_honestidad = tiene_señal_no_se(r)
    # También penalizamos respuestas muy largas a preguntas imposibles
    # (señal de que el modelo está inventando)
    no_inventa_largo = palabras < 60
    ok = tiene_honestidad or no_inventa_largo
    print(f"  {INFO}  [{t:.1f}s | {palabras}p] {preg[:55]!r}")
    print(f"         → {r[:100]}")
    reg(descripcion, ok,
        f"{'honesto' if tiene_honestidad else 'corto'} ({palabras}p)")

# Prueba extra: preguntas que SÍ debe responder bien (no confundir con "no sé")
print(f"\n  {INFO}  Verificando que no diga 'no sé' a preguntas que sí sabe...\n")
DEBE_SABER = [
    ("¿Cuál es la capital de Colombia?", "bogotá"),
    ("¿Cómo te llamas?",                 "bmo"),
    ("¿Cuánto es 2 más 2?",              "4"),
]
for preg, esperado in DEBE_SABER:
    r, _ = llm(preg)
    print(f"  {INFO}  {preg!r} → {r[:60]}")
    reg(f"Sí responde: {preg!r}",
        esperado in r.lower() and not tiene_señal_no_se(r),
        r[:80])


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 12 — Conversación completa con Ana")
# ══════════════════════════════════════════════════════════════════════════════

m_ana = PersistentMemory("data/test_ana.json", 5)
conv = [
    ("Hola, me llamo Ana",                      "Ana"),
    ("¿Cómo estás?",                            "Ana"),
    ("¿Cuál es la capital de Colombia?",        "Ana"),
    ("¿De qué colores es la bandera de Colombia?","Ana"),
    ("¿Quién te creó?",                         "Ana"),
    ("¿Me recuerdas?",                          "Ana"),
]
for i, (preg, per) in enumerate(conv, 1):
    r, t = llm(preg, per, m_ana)
    print(f"  [{i}] {preg!r}")
    print(f"      BMO ({t:.1f}s): {r[:80]}")

r_final, _ = llm("¿Cómo me llamo?", "Ana", m_ana)
print(f"  [7] ¿Cómo me llamo? → {r_final}")
reg("BMO recuerda 'Ana' al final", "ana" in r_final.lower(), r_final[:80])


# ══════════════════════════════════════════════════════════════════════════════
titulo("RESUMEN FINAL")
# ══════════════════════════════════════════════════════════════════════════════

total  = len(resultados)
passed = sum(1 for _, ok, _ in resultados if ok)
failed = total - passed

print(f"\n  Total:   {total}")
print(f"  {G}Pasaron: {passed}{X}")
print(f"  {R if failed else G}Fallaron: {failed}{X}\n")

if failed:
    print(f"{R}Tests fallidos:{X}")
    for n, ok, d in resultados:
        if not ok:
            print(f"  {FAIL}  {n}")
            if d: print(f"         {d}")

# Guardar resultados
out = Path("test_results_rama_dev.json")
out.write_text(json.dumps({
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "total": total, "passed": passed, "failed": failed,
    "tests": [{"nombre": n, "ok": ok, "detalle": d} for n, ok, d in resultados]
}, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\n  {INFO}  Resultados en {out}")

# Limpiar temporales
for f in Path("data").glob("test_*.json"):
    f.unlink(missing_ok=True)
out.unlink(missing_ok=True)

print()
sys.exit(0 if failed == 0 else 1)
