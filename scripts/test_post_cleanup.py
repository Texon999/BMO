"""
Tests post-limpieza: verifica que todo el código activo funciona correctamente.
"""
import sys, importlib
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]))

errors = 0
def test(name, ok):
    global errors
    if ok:
        print(f"  [OK] {name}")
    else:
        print(f"  [XX] {name}")
        errors += 1

# ── 1. Imports core ──────────────────────────────────────────────────────────
from src.brain.classifier import sin_acentos, categorizar_pregunta
from src.brain.brain import buscar_respuesta_predefinida, saludo_fijo, detectar_nombre, normalizar_para_tts, normalizar_texto_entrada
from src.brain.commands import ComandoVoz
from src.display.display import DisplayBMO, Estado
from src.storage.mongo_store import _contexto
from src.memory.persistent_memory import _truncar, _RamMemory
import src.brain.brain as bm
import src.storage.mongo_store as ms
test("Imports core", True)

# ── 2. No unicodedata en brain ──────────────────────────────────────────────
test("brain no tiene unicodedata", 'unicodedata' not in dir(bm))

# ── 3. sin_acentos ───────────────────────────────────────────────────────────
test("sin_acentos 'cancion'", sin_acentos('cancion') == 'cancion')
test("sin_acentos 'arbol'", sin_acentos('arbol') == 'arbol')

# ── 4. categorizar_pregunta ──────────────────────────────────────────────────
test("categorizar 'hola' => greeting", categorizar_pregunta('hola') == 'greeting')
test("categorizar 'gracias' => greeting", categorizar_pregunta('gracias') == 'greeting')
test("categorizar 'explica' => explain", categorizar_pregunta('explica la teoria') == 'explain')
test("categorizar 'que es python' => factual", categorizar_pregunta('que es python') == 'factual')
test("categorizar 'diferencia' => compare", categorizar_pregunta('diferencia entre gato y perro') == 'compare')
test("categorizar 'cuentame un cuento' => creative", categorizar_pregunta('cuentame un cuento') == 'creative')
test("categorizar 'que piensas' => opinion", categorizar_pregunta('que piensas de la ia') == 'opinion')
test("categorizar 'codigo' => technical", categorizar_pregunta('codigo fuente') == 'technical')

# ── 5. respuestas_predefinidas ──────────────────────────────────────────────
test("predefinida 'quien eres'", 'BMO' in buscar_respuesta_predefinida('quien eres'))
test("predefinida 'que es minecraft'", 'Minecraft' in buscar_respuesta_predefinida('que es minecraft'))
test("predefinida 'bandera colombia'", 'Colombia' in buscar_respuesta_predefinida('bandera de colombia'))
test("predefinida 'capital brasil'", 'Brasilia' in buscar_respuesta_predefinida('capital de brasil'))
test("predefinida random => None", buscar_respuesta_predefinida('xyzrandom') is None)

# ── 6. saludo_fijo ──────────────────────────────────────────────────────────
test("saludo_fijo con nombre", 'Juan' in saludo_fijo('Juan'))
s2 = saludo_fijo(None)
test("saludo_fijo sin nombre", 'BMO' in s2 or 'Hola' in s2)

# ── 7. detectar_nombre ──────────────────────────────────────────────────────
test("detectar 'me llamo Juan'", detectar_nombre('me llamo Juan') == 'Juan')
test("detectar 'mi nombre es Maria'", detectar_nombre('mi nombre es Maria') == 'Maria')
test("detectar 'hola' => None", detectar_nombre('hola') is None)
test("detectar 'me llamo bien' => None", detectar_nombre('me llamo bien') is None)

# ── 8. normalizar_para_tts ──────────────────────────────────────────────────
t1 = normalizar_para_tts('OK')
test("tts OK => okey", 'okey' in t1.lower())
test("tts **bold** => bold", normalizar_para_tts('**Hola**') == 'Hola')
test("tts ## markdown", normalizar_para_tts('# titulo') == 'titulo')

# ── 9. normalizar_texto_entrada ─────────────────────────────────────────────
test("entrada 'numero p' => pi", 'pi' in normalizar_texto_entrada('numero p').lower())
test("entrada 'numero p-i' => pi", 'pi' in normalizar_texto_entrada('numero p-i').lower())

# ── 10. _contexto / _truncar dedup ─────────────────────────────────────────
test("_contexto corto", _contexto('Hola mundo') == 'Hola mundo')
test("_contexto truncado", len(_contexto('A' * 200)) <= 123)
test("_truncar (from mongo) corto", _truncar('Hola') == 'Hola')
test("_truncar (from mongo) truncado", len(_truncar('A' * 200)) <= 123)

# ── 11. Display sin get_info ────────────────────────────────────────────────
d = DisplayBMO()
test("display estado warmup", d.estado == Estado.WARMUP)
test("display sin get_info", not hasattr(d, 'get_info'))
d.cerrar()

# ── 12. _RamMemory ──────────────────────────────────────────────────────────
ram = _RamMemory()
ram.add_user_message('Hola', persona='test')
ram.add_assistant_message('Hola que tal', persona='test')
ctx = ram.get_context_for_llm(persona='test')
test("RamMemory context length", len(ctx) >= 3)
ram.clear_session()
test("RamMemory clear", len(ram.session_memory) == 0)

# ── 13. mongo_store sin buscar_persona_por_similitud ────────────────────────
test("mongo sin buscar_persona", not hasattr(ms, 'buscar_persona_por_similitud'))

# ── 14. Config sin hybrid methods ───────────────────────────────────────────
cfg = __import__('src.config.config_manager', fromlist=['config_manager']).config_manager
test("config sin is_hybrid_mode_enabled", not hasattr(cfg, 'is_hybrid_mode_enabled'))
test("config sin get_hybrid_config_summary", not hasattr(cfg, 'get_hybrid_config_summary'))
summary = cfg.get_config_summary()
test("config summary sin hybrid_mode_enabled", 'hybrid_mode_enabled' not in summary)
test("config summary tiene text_model", summary.get('text_model') is not None)

# ── 15. ComandoVoz ──────────────────────────────────────────────────────────
cv = ComandoVoz("test", "abrir.*chrome", "Abriendo Chrome", lambda: None)
test("ComandoVoz coincide", cv.coincide("abrir chrome"))
test("ComandoVoz no coincide", not cv.coincide("que hora es"))

# ── Resumen ──────────────────────────────────────────────────────────────────
print()
if errors:
    print(f"FALLOS: {errors}")
    sys.exit(1)
print("ALL TESTS PASSED")
