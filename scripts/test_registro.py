"""
Pruebas del flujo de registro de personas en BMO.

Valida:
  1. Detección de frases de presentación (todos los patrones)
  2. Flujo completo de registro según estado de cámara:
     - Ya registrado → confirmar sin registrar de nuevo
     - Sin cámara → caché temporal
     - Cámara sin cara → pedir que se acerque
     - Cara desconocida → registrar foto
     - Cara ya reconocida → ignorar nombre dicho
  3. Integración con MongoDB: persona registrada persiste

Ejecutar:
    .venv\\Scripts\\python.exe scripts/test_registro.py
"""
import sys, logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
logging.basicConfig(level=logging.WARNING)

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
titulo("BLOQUE 1 — Detección de frases de presentación")
# ══════════════════════════════════════════════════════════════════════════════

from src.brain.brain import detectar_nombre

sub("1.1 Frases que SÍ deben detectar nombre")
FRASES_SI = [
    ("me llamo Juan",               "Juan"),
    ("mi nombre es María",          "María"),
    ("soy Pedro",                   "Pedro"),
    ("llámame Carlos",              "Carlos"),
    ("me dicen Luisa",              "Luisa"),
    ("me puedes llamar Andrés",     "Andrés"),
    ("me llaman Sofia",             "Sofia"),
    ("puedes llamarme Diego",       "Diego"),
    ("registrame como Laura",       "Laura"),
    ("guárdame como Roberto",       "Roberto"),
    ("recuérdame como Valentina",   "Valentina"),
    # Con wake word antes (como llegaría en la práctica)
    ("mi nombre es Zambrano",       "Zambrano"),
    ("hola me llamo Ana",           "Ana"),
    ("oye mi nombre es Carlos",     "Carlos"),
]
for frase, esperado in FRASES_SI:
    resultado = detectar_nombre(frase)
    ok = resultado is not None and resultado.lower() == esperado.lower()
    reg(f"detectar_nombre({frase!r}) → {esperado!r}", ok,
        f"obtenido: {resultado!r}")

sub("1.2 Frases que NO deben detectar nombre")
FRASES_NO = [
    "hola cómo estás",
    "estoy bien",
    "soy feliz",
    "soy bmo",
    "soy jake",
    "soy finn",
    "me llamo bien",
    "qué hora es",
    "cuéntame algo",
]
for frase in FRASES_NO:
    resultado = detectar_nombre(frase)
    ok = resultado is None
    reg(f"No detecta nombre en {frase!r}", ok, f"obtenido: {resultado!r}")


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 2 — Simulación del flujo de registro")
# ══════════════════════════════════════════════════════════════════════════════
# Simulamos el comportamiento de _ciclo_escucha sin hardware real.

from src.memory.register import nombres_a_ids
from src.storage import mongo_store

mongo_ok = mongo_store.connect("mongodb://localhost:27017", "bmo_db")
print(f"  {INFO}  MongoDB: {'disponible' if mongo_ok else 'NO disponible'}")

# Limpiar personas de test
if mongo_ok:
    mongo_store._col("personas").delete_many({"nombre": {"$regex": "^test_reg_"}})

import numpy as np

def embedding_sintetico(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v   = rng.standard_normal(512).astype(np.float32)
    return v / np.linalg.norm(v)


class SimuladorRegistro:
    """
    Simula la lógica de _ciclo_escucha para el manejo de nombres,
    sin necesitar hardware (cámara, micrófono, TTS).
    """
    def __init__(self, camara_disponible: bool, cara_reconocida: str | None,
                 cara_desconocida: bool):
        self.camara_disponible  = camara_disponible
        self.cara_reconocida    = cara_reconocida
        self.cara_desconocida   = cara_desconocida
        self.hay_cara_en_camara = cara_reconocida is not None or cara_desconocida

        self._nombre_activo         = cara_reconocida
        self._nombre_cache_temporal = None

        # Registro de acciones tomadas
        self.accion: str = ""
        self.mensaje: str = ""

    def procesar(self, texto: str) -> str:
        """Simula el procesamiento de un texto y devuelve la acción tomada."""
        nombre_nuevo = detectar_nombre(texto)
        if not nombre_nuevo:
            return "sin_nombre"

        conocidos     = list(nombres_a_ids().values())
        ya_registrado = nombre_nuevo.lower() in [n.lower() for n in conocidos]

        if ya_registrado:
            self.accion  = "ya_registrado"
            self.mensaje = f"Ya te conozco, {nombre_nuevo}!"
            if not self.cara_reconocida:
                self._nombre_cache_temporal = nombre_nuevo
                self._nombre_activo = nombre_nuevo
            return self.accion

        if not self.camara_disponible:
            self._nombre_cache_temporal = nombre_nuevo
            self._nombre_activo = nombre_nuevo
            self.accion  = "cache_temporal"
            self.mensaje = f"Hola {nombre_nuevo}! Te recuerdo mientras hablamos, pero sin cámara no puedo guardar tu cara."
            return self.accion

        if not self.hay_cara_en_camara:
            self.accion  = "pedir_acercarse"
            self.mensaje = f"Hola {nombre_nuevo}! Acércate a la cámara para que pueda verte bien."
            return self.accion

        if self.cara_reconocida:
            self.accion  = "ignorar_nombre"
            self.mensaje = f"(ignorado, cámara ya reconoció a {self.cara_reconocida})"
            return self.accion

        # Cara desconocida + nombre nuevo → registrar
        self.accion  = "registrar_foto"
        self.mensaje = f"Hola {nombre_nuevo}! Voy a recordar tu cara."
        return self.accion


sub("2.1 Nombre ya registrado → confirmar sin registrar de nuevo")
# Registrar a test_reg_Existente primero
if mongo_ok:
    mongo_store.guardar_persona(8001, "test_reg_Existente")
    from src.memory.register import _load, _save, MEMORY_FILE
    mem = _load()
    mem["8001"] = {"nombre": "test_reg_Existente", "visitas": 1, "embeddings": []}
    _save(mem)

sim = SimuladorRegistro(camara_disponible=True, cara_reconocida=None, cara_desconocida=True)
accion = sim.procesar("mi nombre es test_reg_Existente")
print(f"  {INFO}  Acción: {accion!r}, Mensaje: {sim.mensaje!r}")
reg("Ya registrado → acción 'ya_registrado'", accion == "ya_registrado", accion)
reg("Mensaje confirma que ya lo conoce", "ya te conozco" in sim.mensaje.lower(), sim.mensaje)

sub("2.2 Sin cámara + nombre nuevo → caché temporal")
sim2 = SimuladorRegistro(camara_disponible=False, cara_reconocida=None, cara_desconocida=False)
accion2 = sim2.procesar("me llamo NuevoSinCamara")
print(f"  {INFO}  Acción: {accion2!r}, Mensaje: {sim2.mensaje!r}")
reg("Sin cámara → acción 'cache_temporal'", accion2 == "cache_temporal", accion2)
reg("_nombre_activo se establece", sim2._nombre_activo == "Nuevosincamara" or
    sim2._nombre_activo is not None, str(sim2._nombre_activo))
reg("Mensaje menciona que no puede guardar cara",
    "sin cámara" in sim2.mensaje.lower() or "cámara" in sim2.mensaje.lower(), sim2.mensaje)

sub("2.3 Cámara disponible pero sin cara → pedir que se acerque")
sim3 = SimuladorRegistro(camara_disponible=True, cara_reconocida=None, cara_desconocida=False)
accion3 = sim3.procesar("mi nombre es SinCaraEnCamara")
print(f"  {INFO}  Acción: {accion3!r}, Mensaje: {sim3.mensaje!r}")
reg("Sin cara en cámara → acción 'pedir_acercarse'", accion3 == "pedir_acercarse", accion3)
reg("Mensaje pide acercarse a la cámara",
    "acércate" in sim3.mensaje.lower() or "cámara" in sim3.mensaje.lower(), sim3.mensaje)

sub("2.4 Cara desconocida + nombre nuevo → registrar foto")
sim4 = SimuladorRegistro(camara_disponible=True, cara_reconocida=None, cara_desconocida=True)
accion4 = sim4.procesar("me llamo NuevoConCara")
print(f"  {INFO}  Acción: {accion4!r}, Mensaje: {sim4.mensaje!r}")
reg("Cara desconocida + nombre nuevo → acción 'registrar_foto'",
    accion4 == "registrar_foto", accion4)
reg("Mensaje indica que va a recordar la cara",
    "cara" in sim4.mensaje.lower() or "recordar" in sim4.mensaje.lower(), sim4.mensaje)

sub("2.5 Cara ya reconocida → ignorar nombre dicho")
sim5 = SimuladorRegistro(camara_disponible=True, cara_reconocida="Carlos", cara_desconocida=False)
accion5 = sim5.procesar("soy Pedro")
print(f"  {INFO}  Acción: {accion5!r}, Mensaje: {sim5.mensaje!r}")
reg("Cara reconocida → acción 'ignorar_nombre'", accion5 == "ignorar_nombre", accion5)

sub("2.6 Múltiples frases de presentación → todas detectan nombre")
frases_registro = [
    "mi nombre es test_reg_Multi",
    "me llamo test_reg_Multi",
    "soy test_reg_Multi",
    "llámame test_reg_Multi",
    "me dicen test_reg_Multi",
]
for frase in frases_registro:
    sim_f = SimuladorRegistro(camara_disponible=True, cara_reconocida=None, cara_desconocida=True)
    accion_f = sim_f.procesar(frase)
    reg(f"Frase {frase!r} → registrar_foto", accion_f == "registrar_foto", accion_f)


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 3 — Persistencia en MongoDB tras registro")
# ══════════════════════════════════════════════════════════════════════════════

if mongo_ok:
    sub("3.1 Simular registro completo: guardar persona + embedding en MongoDB")
    nombre_test = "test_reg_Nuevo"
    id_test     = 8002
    emb_test    = embedding_sintetico(42)

    # Limpiar si existe
    mongo_store._col("personas").delete_one({"_id": id_test})

    # Simular lo que hace vision.aprender_rostro → register.guardar_persona + guardar_embeddings
    from src.memory.register import guardar_persona, guardar_embeddings_persona, cargar_embeddings_todos

    guardar_persona(id_test, nombre_test)
    guardar_embeddings_persona(nombre_test, [emb_test])

    sub("3.2 Verificar que aparece en nombres_a_ids (ya no se puede registrar de nuevo)")
    ids = nombres_a_ids()
    print(f"  {INFO}  Personas registradas: {list(ids.values())}")
    reg(f"'{nombre_test}' aparece en nombres_a_ids",
        any(nombre_test.lower() in v.lower() for v in ids.values()),
        str(ids))

    sub("3.3 Verificar que el simulador lo detecta como ya registrado")
    sim_post = SimuladorRegistro(camara_disponible=True, cara_reconocida=None, cara_desconocida=True)
    accion_post = sim_post.procesar(f"me llamo {nombre_test}")
    print(f"  {INFO}  Acción tras registro: {accion_post!r}")
    reg("Tras registrar → ya no intenta registrar de nuevo",
        accion_post == "ya_registrado", accion_post)

    sub("3.4 Búsqueda por embedding: reconoce a la persona registrada")
    todos = cargar_embeddings_todos()
    resultado = mongo_store.buscar_persona_por_similitud(emb_test, umbral=0.9)
    print(f"  {INFO}  Búsqueda embedding: {resultado}")
    reg("Embedding registrado se reconoce correctamente",
        resultado is not None and nombre_test.lower() in resultado[0].lower(),
        str(resultado))

    sub("3.5 Limpiar datos de test")
    mongo_store._col("personas").delete_many({"nombre": {"$regex": "^test_reg_"}})
    from src.memory.register import _load, _save
    mem = _load()
    for k in [k for k, v in mem.items() if isinstance(v, dict) and
              v.get("nombre", "").startswith("test_reg_")]:
        del mem[k]
    _save(mem)
    reg("Limpieza completada", True)

else:
    sub("3.1-3.5 MongoDB no disponible — prueba básica con JSON")
    from src.memory.register import guardar_persona, nombres_a_ids as n2i
    guardar_persona(8002, "test_reg_JsonOnly")
    ids = n2i()
    reg("Persona guardada en JSON", any("test_reg_JsonOnly" in v for v in ids.values()))
    # Limpiar
    from src.memory.register import _load, _save
    mem = _load()
    if "8002" in mem:
        del mem["8002"]
        _save(mem)


# ══════════════════════════════════════════════════════════════════════════════
titulo("BLOQUE 4 — Casos edge")
# ══════════════════════════════════════════════════════════════════════════════

sub("4.1 Nombre muy corto (≤ 2 chars) no se registra")
for frase in ["me llamo Al", "soy Jo", "mi nombre es Li"]:
    resultado = detectar_nombre(frase)
    reg(f"Nombre corto ignorado: {frase!r}", resultado is None,
        f"obtenido: {resultado!r}")

sub("4.2 Palabras reservadas no se toman como nombres")
reservadas = [
    ("soy bien",    None),
    ("soy bmo",     None),
    ("soy jake",    None),
    ("soy finn",    None),
    ("soy feliz",   None),
    ("soy solo",    None),
    ("soy hola",    None),
]
for frase, esperado in reservadas:
    resultado = detectar_nombre(frase)
    ok = resultado == esperado
    reg(f"Reservada ignorada: {frase!r}", ok, f"obtenido: {resultado!r}")

sub("4.3 Nombre con mayúsculas se capitaliza correctamente")
casos_mayus = [
    ("me llamo JUAN",    "Juan"),
    ("mi nombre es ana", "Ana"),
    ("soy CARLOS",       "Carlos"),
]
for frase, esperado in casos_mayus:
    resultado = detectar_nombre(frase)
    ok = resultado == esperado
    reg(f"Capitalización: {frase!r} → {esperado!r}", ok, f"obtenido: {resultado!r}")


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
