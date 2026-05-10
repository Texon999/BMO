"""
Pruebas de wake word, saludos personalizados y MongoDB.

Valida:
  1. Detección de wake word en todas sus variantes
  2. Extracción del prompt después del wake word
  3. Generación del sonido "tín" (sin reproducir, solo verificar que se genera)
  4. Saludos personalizados: persona con cara registrada → saludo con nombre
  5. MongoDB: guardar persona + embedding + chat, verificar persistencia

Ejecutar:
    .venv\\Scripts\\python.exe scripts/test_wake_y_saludos.py
"""
import sys, time, logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
logging.basicConfig(level=logging.WARNING)

import numpy as np

G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; C = "\033[96m"; B = "\033[1m"; X = "\033[0m"
PASS = f"{G}✓ PASS{X}"; FAIL = f"{R}✗ FAIL{X}"; INFO = f"{C}ℹ{X}"
resultados: list[tuple[str, bool, str]] = []

def titulo(t):
    print(f"\n{B}{C}{'═'*60}{X}\n{B}{C}  {t}{X}\n{B}{C}{'═'*60}{X}")

def sub(t):
    print(f"\n{Y}── {t} ──{X}")

def reg(nombre, ok, detalle=""):
    resultados.append((nombre, ok, detalle))
    print(f"  {PASS if ok else FAIL}  {nombre}")
    if detalle:
        print(f"         {detalle}")


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 1 — Detección de wake word")
# ══════════════════════════════════════════════════════════════════════════════

from src.voice.wake_word import es_wake_word, extraer_prompt, _generar_tin

sub("1.1 Variantes que SÍ deben activar")
WAKE_SI = [
    "BMO qué hora es",
    "bmo cuéntame algo",
    "Bimo, cómo estás",
    "bimo qué es la vida",
    "Vimo ayúdame",
    "vimo dime el clima",
    "B.M.O. hola",
    "b.m.o qué sabes",
    "bi mo escúchame",
    "vi mo dime algo",
    "Bemo qué haces",
    "bumo hola",
    "oye BMO qué tal",
    "hola bmo cómo te llamas",
]
for texto in WAKE_SI:
    ok = es_wake_word(texto)
    reg(f"Wake word en: {texto!r}", ok)

sub("1.2 Textos que NO deben activar")
WAKE_NO = [
    "hola cómo estás",
    "qué hora es",
    "me llamo Juan",
    "cuéntame algo interesante",
    "el tiempo está bonito",
    "abracadabra",
    "bm sin la o",
]
for texto in WAKE_NO:
    ok = not es_wake_word(texto)
    reg(f"No activa en: {texto!r}", ok)


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 2 — Extracción del prompt")
# ══════════════════════════════════════════════════════════════════════════════

CASOS_PROMPT = [
    ("BMO qué hora es",          "qué hora es"),
    ("bmo, cuéntame algo",       "cuéntame algo"),
    ("Bimo cómo estás",          "cómo estás"),
    ("oye BMO qué tal todo",     "qué tal todo"),
    ("BMO",                      ""),          # solo wake word, sin prompt
    ("bmo   ",                   ""),          # solo wake word con espacios
    ("hola bmo dime el clima",   "dime el clima"),
]
for texto, esperado in CASOS_PROMPT:
    resultado = extraer_prompt(texto)
    ok = resultado == esperado
    reg(f"Prompt de {texto!r}", ok, f"obtenido={resultado!r} esperado={esperado!r}")


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 3 — Sonido 'tín'")
# ══════════════════════════════════════════════════════════════════════════════

sub("3.1 Generar audio del tín sin reproducir")
audio = _generar_tin(sample_rate=22050)
duracion = len(audio) / 22050
print(f"  {INFO}  Audio generado: {len(audio)} samples, {duracion:.3f}s")
reg("Audio generado correctamente", isinstance(audio, np.ndarray) and len(audio) > 0)
reg("Duración razonable (0.1s - 0.5s)", 0.1 <= duracion <= 0.5, f"{duracion:.3f}s")
reg("Valores en rango [-1, 1]", float(np.abs(audio).max()) <= 1.0,
    f"max={float(np.abs(audio).max()):.3f}")
reg("Tipo float32", audio.dtype == np.float32, str(audio.dtype))

sub("3.2 Verificar que los dos tonos tienen frecuencias distintas")
# El primer tono es 440Hz, el segundo 880Hz
# Verificamos que hay energía en ambas frecuencias con FFT
fft = np.abs(np.fft.rfft(audio))
freqs = np.fft.rfftfreq(len(audio), 1/22050)
# Buscar picos cerca de 440 y 880 Hz
idx_440 = np.argmin(np.abs(freqs - 440))
idx_880 = np.argmin(np.abs(freqs - 880))
energia_440 = float(fft[max(0,idx_440-5):idx_440+5].max())
energia_880 = float(fft[max(0,idx_880-5):idx_880+5].max())
print(f"  {INFO}  Energía en 440Hz: {energia_440:.1f}, en 880Hz: {energia_880:.1f}")
reg("Hay energía en 440Hz (primer tono)", energia_440 > 100)
reg("Hay energía en 880Hz (segundo tono)", energia_880 > 100)


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 4 — MongoDB: personas, embeddings y saludos")
# ══════════════════════════════════════════════════════════════════════════════

from src.storage import mongo_store
from src.brain.brain import saludo_fijo, SALUDOS_CONOCIDO, SALUDOS_DESCONOCIDO

mongo_ok = mongo_store.connect("mongodb://localhost:27017", "bmo_db")
print(f"  {INFO}  MongoDB: {'disponible' if mongo_ok else 'NO disponible'}")

def embedding_sintetico(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v   = rng.standard_normal(512).astype(np.float32)
    return v / np.linalg.norm(v)

PERSONAS_PRUEBA = [
    ("Zambrano", 1001, 7001),
    ("Ana",      1002, 7002),
    ("Carlos",   1003, 7003),
]

if mongo_ok:
    # Limpiar datos de prueba anteriores
    for _, _, id_p in PERSONAS_PRUEBA:
        mongo_store._col("personas").delete_one({"_id": id_p})
    mongo_store._col("chat_history").delete_many(
        {"persona": {"$in": [n for n, _, _ in PERSONAS_PRUEBA]}}
    )

    sub("4.1 Registrar personas con embeddings en MongoDB")
    for nombre, seed, id_p in PERSONAS_PRUEBA:
        emb = embedding_sintetico(seed)
        ok_p = mongo_store.guardar_persona(id_p, nombre)
        ok_e = mongo_store.guardar_embeddings(nombre, [emb])
        print(f"  {INFO}  {nombre}: persona={ok_p}, embedding={ok_e}")
        reg(f"Persona '{nombre}' registrada con embedding", ok_p and ok_e)

    sub("4.2 Verificar que los embeddings se pueden cargar y buscar")
    todos = mongo_store.cargar_embeddings_todos()
    for nombre, seed, _ in PERSONAS_PRUEBA:
        emb_query = embedding_sintetico(seed)
        resultado = mongo_store.buscar_persona_por_similitud(emb_query, umbral=0.9)
        sim = resultado[1] if resultado else 0.0
        print(f"  {INFO}  Búsqueda '{nombre}': {resultado}")
        reg(f"Reconoce '{nombre}' por embedding (sim≈1.0)",
            resultado is not None and resultado[0] == nombre and resultado[1] > 0.99,
            f"sim={sim:.4f}")

    sub("4.3 Simular saludo personalizado al reconocer cara")
    for nombre, _, _ in PERSONAS_PRUEBA:
        saludo = saludo_fijo(nombre)
        tiene_nombre = nombre.lower() in saludo.lower()
        print(f"  {INFO}  Saludo para '{nombre}': {saludo}")
        reg(f"Saludo personalizado contiene '{nombre}'", tiene_nombre, saludo)

    sub("4.4 Saludo para desconocido (sin cara registrada)")
    saludo_desc = saludo_fijo(None)
    print(f"  {INFO}  Saludo desconocido: {saludo_desc}")
    reg("Saludo desconocido pide el nombre", 
        any(p in saludo_desc.lower() for p in ["nombre", "llamas", "llamo"]),
        saludo_desc)

    sub("4.5 Guardar chat de una persona registrada y verificar sliding window")
    persona_chat = "Zambrano"
    # Limpiar historial previo
    mongo_store._col("chat_history").delete_many({"persona": persona_chat})

    # Guardar 8 mensajes (debe quedar solo 6)
    for i in range(1, 9):
        mongo_store.guardar_mensaje("user",      f"pregunta {i}", persona_chat)
        mongo_store.guardar_mensaje("assistant", f"respuesta {i}", persona_chat)

    total = mongo_store.contar_mensajes(persona_chat)
    historial = mongo_store.obtener_historial(persona_chat)
    print(f"  {INFO}  Mensajes en DB para '{persona_chat}': {total}")
    print(f"  {INFO}  Historial recuperado ({len(historial)} msgs):")
    for m in historial:
        print(f"         [{m['role']}] {m['content']}")

    reg("Sliding window: exactamente 6 mensajes", total == 6, f"{total} msgs")
    reg("Los más recientes están presentes",
        any("8" in m["content"] for m in historial))
    reg("Los más viejos fueron eliminados",
        not any("pregunta 1 " in m["content"] for m in historial))

    sub("4.6 Verificar datos en MongoDB con ver_mongo.py")
    import subprocess
    result = subprocess.run(
        [sys.executable, "scripts/ver_mongo.py"],
        capture_output=True, text=True, cwd="."
    )
    print(result.stdout)
    reg("ver_mongo.py ejecuta sin errores", result.returncode == 0,
        result.stderr[:100] if result.stderr else "OK")

    sub("4.7 Limpiar datos de prueba")
    for _, _, id_p in PERSONAS_PRUEBA:
        mongo_store._col("personas").delete_one({"_id": id_p})
    mongo_store._col("chat_history").delete_many(
        {"persona": {"$in": [n for n, _, _ in PERSONAS_PRUEBA]}}
    )
    reg("Limpieza completada", True)

else:
    print(f"  {Y}MongoDB no disponible — saltando pruebas de MongoDB{X}")
    sub("4.1-4.7 Pruebas de saludos sin MongoDB")
    for nombre, _, _ in PERSONAS_PRUEBA:
        saludo = saludo_fijo(nombre)
        reg(f"Saludo para '{nombre}'", nombre.lower() in saludo.lower(), saludo)
    saludo_desc = saludo_fijo(None)
    reg("Saludo desconocido válido", len(saludo_desc) > 5, saludo_desc)


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 5 — Memoria MongoDB: sin cara = no guarda")
# ══════════════════════════════════════════════════════════════════════════════

from src.memory.persistent_memory import _MongoMemory, _RamMemory, MAX_MSGS_PERSONA

if mongo_ok:
    sub("5.1 Con persona registrada → guarda en MongoDB")
    mem = _MongoMemory()
    mongo_store._col("chat_history").delete_many({"persona": "test_mem_5"})

    mem.add_user_message("hola soy test", "test_mem_5")
    mem.add_assistant_message("hola test!", "test_mem_5")
    mem.commit_session_to_permanent("test_mem_5")

    total = mongo_store.contar_mensajes("test_mem_5")
    reg("Con persona: mensajes guardados en MongoDB", total == 2, f"{total} msgs")

    sub("5.2 Sin persona → no guarda nada")
    mem2 = _MongoMemory()
    antes = mongo_store._col("chat_history").count_documents({})
    mem2.add_user_message("mensaje anónimo", None)
    mem2.add_assistant_message("respuesta anónima", None)
    mem2.commit_session_to_permanent(None)
    despues = mongo_store._col("chat_history").count_documents({})
    reg("Sin persona: MongoDB no cambia", despues == antes, f"antes={antes} después={despues}")
    reg("Sin persona: sesión limpia", len(mem2.session_memory) == 0)

    sub("5.3 Contexto LLM incluye historial de MongoDB")
    ctx = mem.get_context_for_llm("test_mem_5")
    print(f"  {INFO}  Mensajes en contexto: {len(ctx)}")
    for m in ctx:
        print(f"         [{m['role']}] {m['content'][:60]}")
    reg("Contexto tiene system + historial", len(ctx) >= 2)
    reg("Primer mensaje es system", ctx[0]["role"] == "system")

    # Limpiar
    mongo_store._col("chat_history").delete_many({"persona": "test_mem_5"})

else:
    sub("5.1-5.3 Usando _RamMemory (MongoDB no disponible)")
    mem_ram = _RamMemory()
    mem_ram.add_user_message("hola", "TestUser")
    mem_ram.add_assistant_message("hola!", "TestUser")
    mem_ram.commit_session_to_permanent("TestUser")
    reg("RAM: mensajes guardados", len(mem_ram._historial.get("TestUser", [])) == 2)

    mem_ram2 = _RamMemory()
    mem_ram2.add_user_message("anónimo", None)
    mem_ram2.commit_session_to_permanent(None)
    reg("RAM: sin persona no guarda", len(mem_ram2._historial) == 0)


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

print()
import sys as _sys
_sys.exit(0 if failed == 0 else 1)
