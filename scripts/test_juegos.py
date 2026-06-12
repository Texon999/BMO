"""
Tests del sistema de juegos por comando de voz.
"""
import sys, time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]))

from src.brain.commands import construir_juegos, ejecutar_juego, _extraer_nombre_juego, _mejor_coincidencia_juego
from src.config.config_manager import config_manager

errors = 0
def test(name, ok):
    global errors
    if ok:
        print(f"  [OK] {name}")
    else:
        print(f"  [XX] {name}")
        errors += 1

# 1. construir_juegos from config
juegos = construir_juegos(config_manager.config)
test("construir_juegos from config", isinstance(juegos, dict))

# 2. _extraer_nombre_juego
extrae_tests = [
    ("quiero jugar hollow knight", "hollow knight"),
    ("quiero jugar al hollow knight", "hollow knight"),
    ("juguemos minecraft", "minecraft"),
    ("juguemos al minecraft", "minecraft"),
    ("vamos a jugar mario", "mario"),
    ("abre el juego hollow knight", "hollow knight"),
    ("pon hollow knight", "hollow knight"),
    ("ejecuta hollow knight", "hollow knight"),
    ("hola como estas", None),
]
extrae_ok = True
for texto, esperado in extrae_tests:
    res = _extraer_nombre_juego(texto)
    if esperado is None and res is not None:
        test(f"extraer('{texto}'): esperaba None, obtuve '{res}'", False)
        extrae_ok = False
    elif esperado is not None and res is None:
        test(f"extraer('{texto}'): esperaba '{esperado}', obtuve None", False)
        extrae_ok = False
    elif res is not None and esperado not in res and res not in esperado:
        test(f"extraer('{texto}'): esperaba '{esperado}', obtuve '{res}'", False)
        extrae_ok = False
if extrae_ok:
    test("_extraer_nombre_juego (9 casos)", True)

# 3. _mejor_coincidencia_juego
juegos_dict = {"hollow knight": "hk.exe", "minecraft": "mc.exe", "calculadora": "calc.exe"}
test("coincidencia exacta 'hollow knight'",
     _mejor_coincidencia_juego("hollow knight", juegos_dict) == "hollow knight")
test("coincidencia parcial 'juguemos hollow knight'",
     _mejor_coincidencia_juego("juguemos hollow knight", juegos_dict) == "hollow knight")
test("coincidencia 'minecraft'",
     _mejor_coincidencia_juego("minecraft", juegos_dict) == "minecraft")
test("coincidencia 'calculadora'",
     _mejor_coincidencia_juego("calculadora", juegos_dict) == "calculadora")
test("sin coincidencia 'desconocido'",
     _mejor_coincidencia_juego("desconocido", juegos_dict) is None)

# 4. ejecutar_juego funcional
config_manager.set("juegos", {"notepad": "notepad.exe"}, save=False)
juegos2 = construir_juegos(config_manager.config)
res = ejecutar_juego("quiero jugar notepad", juegos2)
test("ejecutar_juego notepad", res is not None and "notepad" in res.lower())

# 5. Sin juegos
res = ejecutar_juego("quiero jugar algo", {})
test("sin juegos => None", res is None)

# 6. Imports de main.py
from src.brain.commands import construir_juegos as cj, ejecutar_juego as ej
test("imports desde main.py", cj is not None and ej is not None)

# 7. Cleanup
config_manager.set("juegos", juegos, save=False)

print()
if errors:
    print(f"FALLOS: {errors}")
    sys.exit(1)
print("ALL GAME TESTS PASSED")
