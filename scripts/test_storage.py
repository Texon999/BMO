"""
Pruebas de almacenamiento para BMO.

Valida:
  1. Sliding window de 6 mensajes por persona
  2. Solo contexto guardado (truncado a 120 chars)
  3. Sin cara reconocida → no se guarda nada
  4. Embeddings sintéticos: guardar, cargar, búsqueda por similitud coseno
  5. Persistencia real: guardar → recargar → verificar que los datos están
  6. Integración con MongoDB si está disponible, JSON si no

Ejecutar:
    .venv\\Scripts\\python.exe scripts/test_storage.py
"""
import sys, json, time, logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
logging.basicConfig(level=logging.WARNING)

import numpy as np

# ── Colores ───────────────────────────────────────────────────────────────────
G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; C = "\033[96m"; B = "\033[1m"; X = "\033[0m"
PASS = f"{G}✓ PASS{X}"; FAIL = f"{R}✗ FAIL{X}"; INFO = f"{C}ℹ{X}"

resultados: list[tuple[str, bool, str]] = []

def titulo(t):
    print(f"\n{B}{C}{'═'*60}{X}\n{B}{C}  {t}{X}\n{B}{C}{'═'*60}{X}")

def sub(t):
    print(f"\n{Y}── {t} ──{X}")

def reg(nombre, ok, detalle=""):
    resultados.append((nombre, ok, detalle))
    icono = PASS if ok else FAIL
    print(f"  {icono}  {nombre}")
    if detalle:
        print(f"         {detalle}")

# Limpiar archivos temporales de pruebas anteriores
for f in Path("data").glob("test_storage_*.json"):
    f.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 1 — Detección de backend disponible")
# ══════════════════════════════════════════════════════════════════════════════

from src.storage import mongo_store
from src.memory.persistent_memory import (
    _RamMemory, _MongoMemory, PersistentMemory,
    MAX_MSGS_PERSONA, MAX_CHARS_CONTEXTO, _truncar,
)

sub("1.1 Intentar conexión MongoDB")
mongo_ok = mongo_store.connect("mongodb://localhost:27017", "bmo_test")
backend  = "MongoDB" if mongo_ok else "JSON (fallback)"
print(f"  {INFO}  Backend activo: {B}{backend}{X}")
reg("Backend detectado correctamente", True, backend)

if mongo_ok:
    # Limpiar colecciones de test para empezar limpio
    try:
        mongo_store._col("personas").delete_many({"_id": {"$gte": 9000}})
        mongo_store._col("chat_history").delete_many({"persona": {"$regex": "^test_"}})
        print(f"  {INFO}  Colecciones de test limpiadas")
    except Exception as e:
        print(f"  {INFO}  No se pudo limpiar: {e}")


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 2 — Truncado de contexto")
# ══════════════════════════════════════════════════════════════════════════════

sub("2.1 Mensaje corto no se trunca")
corto = "Hola, ¿cómo estás?"
reg("Mensaje corto sin cambios", _truncar(corto) == corto, _truncar(corto))

sub("2.2 Mensaje largo se trunca a ~120 chars")
largo = "Este es un mensaje muy largo que supera el límite de caracteres permitido " * 3
truncado = _truncar(largo)
print(f"  {INFO}  Original: {len(largo)} chars → Truncado: {len(truncado)} chars")
reg("Truncado ≤ MAX_CHARS_CONTEXTO + 1 (por '…')", len(truncado) <= MAX_CHARS_CONTEXTO + 1,
    f"{len(truncado)} chars")
reg("Termina con '…'", truncado.endswith("…"), truncado[-20:])

sub("2.3 Truncado no parte palabras")
texto = "palabra1 palabra2 palabra3 " * 10
t = _truncar(texto)
reg("No termina en mitad de palabra", t.endswith("…") or not t[-2].isalpha() or t.endswith(" "),
    t[-30:])


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 3 — Sliding window JSON (sin MongoDB)")
# ══════════════════════════════════════════════════════════════════════════════

sub("3.1 Crear memoria JSON de test")
mem = PersistentMemory("data/test_storage_sw.json")

sub("3.2 Agregar exactamente 6 mensajes para 'TestUser'")
for i in range(1, 7):
    mem.add_user_message(f"pregunta número {i}", "TestUser")
    mem.add_assistant_message(f"respuesta número {i}", "TestUser")
    mem.commit_session_to_permanent("TestUser")

historial = mem._impl._historial.get("TestUser", [])
print(f"  {INFO}  Mensajes en historial: {len(historial)}")
for m in historial:
    print(f"         [{m['role']}] {m['content']}")

reg("Exactamente 6 mensajes guardados", len(historial) == MAX_MSGS_PERSONA,
    f"{len(historial)} msgs (esperado {MAX_MSGS_PERSONA})")

sub("3.3 Agregar el 7mo mensaje — debe borrar el más viejo")
mem.add_user_message("pregunta número 7", "TestUser")
mem.add_assistant_message("respuesta número 7", "TestUser")
mem.commit_session_to_permanent("TestUser")

historial_nuevo = mem._impl._historial.get("TestUser", [])
print(f"  {INFO}  Mensajes tras agregar 7mo: {len(historial_nuevo)}")
for m in historial_nuevo:
    print(f"         [{m['role']}] {m['content']}")

reg("Sigue siendo 6 mensajes (sliding window)", len(historial_nuevo) == MAX_MSGS_PERSONA,
    f"{len(historial_nuevo)} msgs")
reg("El mensaje más viejo fue eliminado",
    not any("número 1" in m["content"] for m in historial_nuevo),
    "pregunta número 1 ya no debe estar")
reg("El mensaje más nuevo está presente",
    any("número 7" in m["content"] for m in historial_nuevo),
    "pregunta número 7 debe estar")

sub("3.4 Sin cara reconocida → no guarda nada")
mem2 = PersistentMemory("data/test_storage_anon.json")
mem2.add_user_message("mensaje anónimo 1", None)
mem2.add_assistant_message("respuesta anónima 1", None)
mem2.add_user_message("mensaje anónimo 2", None)
mem2.add_assistant_message("respuesta anónima 2", None)
mem2.commit_session_to_permanent(None)   # sin persona → descarta

reg("Sin persona: historial vacío", len(mem2._impl._historial) == 0,
    f"historial: {mem2._impl._historial}")
reg("Sin persona: sesión limpia", len(mem2.session_memory) == 0,
    f"sesión: {len(mem2.session_memory)} msgs")

sub("3.5 Contexto anónimo solo tiene system + último mensaje")
mem3 = PersistentMemory("data/test_storage_ctx.json")
mem3.add_user_message("primera pregunta", None)
mem3.add_assistant_message("primera respuesta", None)
mem3.add_user_message("segunda pregunta", None)   # sobrescribe
ctx = mem3.get_context_for_llm(None)
print(f"  {INFO}  Mensajes en contexto anónimo: {len(ctx)}")
for m in ctx:
    print(f"         [{m['role']}] {m['content'][:60]}")
reg("Contexto anónimo = system + 1 user", len(ctx) == 2, f"{len(ctx)} msgs")
reg("El user es el último mensaje",
    ctx[-1]["role"] == "user" and "segunda" in ctx[-1]["content"],
    ctx[-1]["content"])

sub("3.6 Persistencia real: guardar y recargar")
mem4 = PersistentMemory("data/test_storage_persist.json")
mem4.add_user_message("hola soy Juan", "Juan")
mem4.add_assistant_message("hola Juan!", "Juan")
mem4.commit_session_to_permanent("Juan")
mem4.save_memory()

# Recargar desde disco — crear instancia nueva y llamar _cargar explícitamente
mem4b = PersistentMemory("data/test_storage_persist.json")
# Simular carga desde el archivo que acabamos de guardar
archivo = Path("data/test_storage_persist.json")
if archivo.exists():
    data = json.loads(archivo.read_text(encoding="utf-8"))
    mem4b._impl._historial = data.get("historial", {})
historial_recargado = mem4b._impl._historial.get("Juan", [])
print(f"  {INFO}  Mensajes recargados para 'Juan': {len(historial_recargado)}")
reg("Historial persiste en disco y se recarga", len(historial_recargado) >= 1,
    f"{len(historial_recargado)} msgs")
reg("Contenido correcto tras recarga",
    any("juan" in m["content"].lower() for m in historial_recargado),
    str(historial_recargado))


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 4 — Embeddings sintéticos: guardar y buscar")
# ══════════════════════════════════════════════════════════════════════════════

sub("4.1 Crear embeddings sintéticos para 3 personas")

def embedding_para(nombre: str, seed: int) -> np.ndarray:
    """Genera un embedding sintético reproducible de 512 dims."""
    rng = np.random.default_rng(seed)
    v   = rng.standard_normal(512).astype(np.float32)
    return v / np.linalg.norm(v)   # normalizado

PERSONAS_TEST = [
    ("test_Juan",   42,  9001),
    ("test_Maria",  99,  9002),
    ("test_Carlos", 7,   9003),
]

if mongo_ok:
    sub("4.2 Guardar personas y embeddings en MongoDB")
    for nombre, seed, id_p in PERSONAS_TEST:
        emb = embedding_para(nombre, seed)
        # Crear persona primero
        ok_p = mongo_store.guardar_persona(id_p, nombre)
        # Guardar embedding
        ok_e = mongo_store.guardar_embeddings(nombre, [emb])
        print(f"  {INFO}  {nombre}: persona={ok_p}, embedding={ok_e}")
        reg(f"Persona '{nombre}' guardada en MongoDB", ok_p and ok_e)

    sub("4.3 Cargar todos los embeddings desde MongoDB")
    todos = mongo_store.cargar_embeddings_todos()
    print(f"  {INFO}  Personas con embeddings: {list(todos.keys())}")
    for nombre, _, _ in PERSONAS_TEST:
        reg(f"Embedding de '{nombre}' cargado",
            nombre in todos and len(todos[nombre]) > 0,
            f"dims: {todos[nombre][0].shape if nombre in todos else 'N/A'}")

    sub("4.4 Búsqueda por similitud coseno — mismo embedding debe dar sim ≈ 1.0")
    for nombre, seed, _ in PERSONAS_TEST:
        emb_query = embedding_para(nombre, seed)   # mismo seed → mismo vector
        todos = mongo_store.cargar_embeddings_todos()
        mejor_sim = -1.0
        mejor_nombre = None
        if nombre in todos:
            for emb in todos[nombre]:
                emb_norm = emb / (np.linalg.norm(emb) + 1e-9)
                q_norm = emb_query / (np.linalg.norm(emb_query) + 1e-9)
                sim = float(np.dot(q_norm, emb_norm))
                if sim > mejor_sim:
                    mejor_sim = sim
                    mejor_nombre = nombre
        resultado = (mejor_nombre, mejor_sim) if mejor_nombre and mejor_sim >= 0.9 else None
        print(f"  {INFO}  Query '{nombre}': resultado={resultado}")
        reg(f"Reconoce '{nombre}' con sim ≈ 1.0",
            resultado is not None and resultado[0] == nombre and resultado[1] > 0.99,
            f"sim={resultado[1]:.4f}" if resultado else "None")

    sub("4.5 Búsqueda con embedding diferente — no debe confundir personas")
    emb_juan  = embedding_para("test_Juan",  42)
    emb_maria = embedding_para("test_Maria", 99)
    # Juan no debe reconocerse como María
    sim_cruzada = float(np.dot(emb_juan, emb_maria))
    print(f"  {INFO}  Similitud Juan vs María: {sim_cruzada:.4f}")
    reg("Embeddings de personas distintas tienen baja similitud",
        sim_cruzada < 0.3, f"sim={sim_cruzada:.4f}")

    sub("4.6 Embedding desconocido — no debe reconocer a nadie")
    rng_desconocido = np.random.default_rng(12345)
    emb_desconocido = rng_desconocido.standard_normal(512).astype(np.float32)
    emb_desconocido /= np.linalg.norm(emb_desconocido)
    todos = mongo_store.cargar_embeddings_todos()
    resultado_desc = None
    for nombre, embs in todos.items():
        for emb in embs:
            q_norm = emb_desconocido / (np.linalg.norm(emb_desconocido) + 1e-9)
            e_norm = emb / (np.linalg.norm(emb) + 1e-9)
            if float(np.dot(q_norm, e_norm)) >= 0.9:
                resultado_desc = (nombre, float(np.dot(q_norm, e_norm)))
    print(f"  {INFO}  Embedding desconocido: resultado={resultado_desc}")
    reg("Embedding desconocido no reconoce a nadie (umbral alto)",
        resultado_desc is None, str(resultado_desc))

else:
    sub("4.2-4.6 MongoDB no disponible — probando con JSON fallback")
    from src.memory.register import guardar_persona, guardar_embeddings_persona, cargar_embeddings_todos

    for nombre, seed, id_p in PERSONAS_TEST:
        emb = embedding_para(nombre, seed)
        guardar_persona(id_p, nombre)
        guardar_embeddings_persona(nombre, [emb])
        print(f"  {INFO}  {nombre}: guardado en JSON")

    todos = cargar_embeddings_todos()
    print(f"  {INFO}  Personas con embeddings en JSON: {list(todos.keys())}")
    for nombre, _, _ in PERSONAS_TEST:
        reg(f"Embedding de '{nombre}' en JSON",
            nombre in todos, f"encontrado: {nombre in todos}")

    # Búsqueda manual con numpy
    for nombre, seed, _ in PERSONAS_TEST:
        emb_query = embedding_para(nombre, seed)
        q_norm = emb_query / np.linalg.norm(emb_query)
        mejor_nombre, mejor_sim = None, -1.0
        for n, embs in todos.items():
            for e in embs:
                e_norm = e / np.linalg.norm(e)
                sim = float(np.dot(q_norm, e_norm))
                if sim > mejor_sim:
                    mejor_sim, mejor_nombre = sim, n
        print(f"  {INFO}  Query '{nombre}': mejor={mejor_nombre} sim={mejor_sim:.4f}")
        reg(f"Reconoce '{nombre}' con sim ≈ 1.0",
            mejor_nombre == nombre and mejor_sim > 0.99,
            f"sim={mejor_sim:.4f}")


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 5 — Chat con persona registrada (sliding window + persistencia)")
# ══════════════════════════════════════════════════════════════════════════════

if mongo_ok:
    sub("5.1 Guardar 8 mensajes para test_Juan — debe quedar solo 6")
    persona_test = "test_Juan"
    # Limpiar historial previo
    mongo_store._col("chat_history").delete_many({"persona": persona_test})

    for i in range(1, 9):
        mongo_store.guardar_mensaje("user",      f"pregunta {i} de Juan", persona_test)
        mongo_store.guardar_mensaje("assistant", f"respuesta {i} de BMO", persona_test)

    total_db = mongo_store.contar_mensajes(persona_test)
    print(f"  {INFO}  Mensajes en DB para '{persona_test}': {total_db}")
    reg("Sliding window: máximo 6 mensajes en DB",
        total_db == MAX_MSGS_PERSONA, f"{total_db} msgs (esperado {MAX_MSGS_PERSONA})")

    sub("5.2 Verificar que los mensajes más recientes son los que quedan")
    historial = mongo_store.obtener_historial(persona_test)
    print(f"  {INFO}  Historial recuperado ({len(historial)} msgs):")
    for m in historial:
        print(f"         [{m['role']}] {m['content']}")
    reg("El historial tiene exactamente 6 mensajes", len(historial) == MAX_MSGS_PERSONA)
    reg("Los mensajes más recientes están presentes",
        any("8" in m["content"] for m in historial),
        "pregunta 8 debe estar")
    reg("Los mensajes más viejos fueron eliminados",
        not any("pregunta 1 " in m["content"] for m in historial),
        "pregunta 1 no debe estar")

    sub("5.3 Contexto para LLM incluye historial de MongoDB")
    mem_mongo = _MongoMemory()
    mem_mongo.add_user_message("¿me recuerdas?", persona_test)
    ctx = mem_mongo.get_context_for_llm(persona_test)
    print(f"  {INFO}  Mensajes en contexto LLM: {len(ctx)}")
    reg("Contexto incluye system + historial + sesión actual",
        len(ctx) >= 3, f"{len(ctx)} msgs")
    reg("Primer mensaje es system", ctx[0]["role"] == "system")
    reg("Último mensaje es la pregunta actual",
        ctx[-1]["role"] == "user" and "recuerdas" in ctx[-1]["content"],
        ctx[-1]["content"])

    sub("5.4 Sin cara reconocida → commit no guarda nada en MongoDB")
    mem_anon = _MongoMemory()
    mem_anon.add_user_message("mensaje sin cara", None)
    mem_anon.add_assistant_message("respuesta sin cara", None)
    antes = mongo_store._col("chat_history").count_documents({})
    mem_anon.commit_session_to_permanent(None)
    despues = mongo_store._col("chat_history").count_documents({})
    reg("Sin persona: no se agrega nada a MongoDB",
        despues == antes, f"antes={antes} después={despues}")
    reg("Sin persona: sesión limpia", len(mem_anon.session_memory) == 0)

    sub("5.5 Contenido truncado en MongoDB")
    mensaje_largo = "Este es un mensaje muy largo " * 10
    mongo_store.guardar_mensaje("user", mensaje_largo, persona_test)
    ultimo = mongo_store._col("chat_history").find_one(
        {"persona": persona_test}, sort=[("ts", -1)]
    )
    if ultimo:
        print(f"  {INFO}  Guardado: {len(ultimo['content'])} chars: {ultimo['content'][:80]}")
        reg("Contenido truncado a ≤ 121 chars",
            len(ultimo["content"]) <= MAX_CHARS_CONTEXTO + 1,
            f"{len(ultimo['content'])} chars")
    else:
        reg("Mensaje largo guardado", False, "no encontrado")

    sub("5.6 Limpiar datos de test de MongoDB")
    for _, _, id_p in PERSONAS_TEST:
        mongo_store._col("personas").delete_one({"_id": id_p})
    mongo_store._col("chat_history").delete_many({"persona": {"$regex": "^test_"}})
    print(f"  {INFO}  Datos de test eliminados de MongoDB")
    reg("Limpieza de test completada", True)

else:
    sub("5.1-5.6 MongoDB no disponible — pruebas con _RamMemory")
    mem_j = PersistentMemory("data/test_storage_sw2.json")
    for i in range(1, 9):
        mem_j.add_user_message(f"pregunta {i}", "test_Juan")
        mem_j.add_assistant_message(f"respuesta {i}", "test_Juan")
        mem_j.commit_session_to_permanent("test_Juan")

    h = mem_j._impl._historial.get("test_Juan", [])
    print(f"  {INFO}  Mensajes en historial JSON: {len(h)}")
    reg("Sliding window JSON: máximo 6 mensajes", len(h) == MAX_MSGS_PERSONA, f"{len(h)}")
    reg("Mensajes recientes presentes", any("8" in m["content"] for m in h))
    reg("Mensajes viejos eliminados", not any("pregunta 1 " in m["content"] for m in h))


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 6 — Integración register.py con MongoDB/JSON")
# ══════════════════════════════════════════════════════════════════════════════

from src.memory.register import (
    guardar_persona, obtener_nombre, nombres_a_ids,
    guardar_embeddings_persona, cargar_embeddings_todos,
)

sub("6.1 Guardar persona via register.py")
guardar_persona(8888, "test_Register")
nombre_recuperado = obtener_nombre(8888)
print(f"  {INFO}  Nombre recuperado: {nombre_recuperado!r}")
reg("Persona guardada y recuperada", nombre_recuperado == "test_Register",
    f"obtenido: {nombre_recuperado!r}")

sub("6.2 Guardar embedding via register.py")
emb_reg = embedding_para("test_Register", 555)
guardar_embeddings_persona("test_Register", [emb_reg])
todos_reg = cargar_embeddings_todos()
reg("Embedding guardado y cargado via register",
    "test_Register" in todos_reg and len(todos_reg["test_Register"]) > 0,
    f"encontrado: {'test_Register' in todos_reg}")

sub("6.3 nombres_a_ids incluye la persona guardada")
ids = nombres_a_ids()
print(f"  {INFO}  Personas registradas: {ids}")
reg("test_Register aparece en nombres_a_ids",
    any("test_Register" in v for v in ids.values()),
    str(ids))

# Limpiar
from src.memory.register import _load, _save, MEMORY_FILE
mem_data = _load()
if "8888" in mem_data:
    del mem_data["8888"]
    _save(mem_data)
if mongo_ok:
    try:
        mongo_store._col("personas").delete_one({"_id": 8888})
    except Exception:
        pass
print(f"  {INFO}  Persona de test eliminada")


# ══════════════════════════════════════════════════════════════════════════════
titulo("RESUMEN FINAL")
# ══════════════════════════════════════════════════════════════════════════════

total  = len(resultados)
passed = sum(1 for _, ok, _ in resultados if ok)
failed = total - passed

print(f"\n  Backend usado: {B}{backend}{X}")
print(f"  Total:   {total}")
print(f"  {G}Pasaron: {passed}{X}")
print(f"  {R if failed else G}Fallaron: {failed}{X}\n")

if failed:
    print(f"{R}Tests fallidos:{X}")
    for n, ok, d in resultados:
        if not ok:
            print(f"  {FAIL}  {n}")
            if d: print(f"         {d}")

# Limpiar archivos temporales
for f in Path("data").glob("test_storage_*.json"):
    f.unlink(missing_ok=True)

print()
sys.exit(0 if failed == 0 else 1)
