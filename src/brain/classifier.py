"""
classifier.py — Sistema de Clasificación Inteligente de Preguntas para BMO.

PROPÓSITO:
Este módulo optimiza las respuestas de BMO clasificando cada pregunta del usuario
en una categoría específica y ajustando dinámicamente los parámetros del LLM
(num_predict, límite de oraciones) para reducir latencia y mejorar la calidad.

FUNCIONAMIENTO:
1. Analiza el texto de entrada con patrones regex específicos
2. Clasifica en una de 8 categorías (GREETING, FACTUAL, TECHNICAL, etc.)
3. Asigna parámetros optimizados según la categoría:
   - num_predict: tokens máximos que puede generar el LLM
   - max_oraciones: límite de oraciones antes de cortar el stream
   - length_hint: instrucción específica para el system prompt

BENEFICIOS:
- Respuestas más rápidas: saludos usan solo 40 tokens vs 150+ por defecto
- Mayor precisión: respuestas factuales limitadas a 2 oraciones exactas
- Mejor experiencia: evita respuestas largas innecesarias para preguntas simples
- Optimización para RPi5: reduce tiempo de inferencia en hardware limitado

CATEGORÍAS Y OPTIMIZACIÓN:
- GREETING (40 tokens, 1 oración): "hola", "gracias", "adiós"
- SIMPLE (100 tokens, 2 oraciones): preguntas cortas sin patrón específico
- FACTUAL (100 tokens, 2 oraciones): "qué es", "quién es", "cuándo"
- OPINION (80 tokens, 2 oraciones): "qué piensas", "te gusta"
- COMPARE (120 tokens, 3 oraciones): "diferencia entre", "cuál es mejor"
- TECHNICAL (180 tokens, 3 oraciones): programación, ciencia, matemáticas
- EXPLAIN (200 tokens, 3 oraciones): "explícame", "cómo funciona"
- CREATIVE (280 tokens, 5 oraciones): historias, listas, ideas creativas

ORDEN DE EVALUACIÓN:
GREETING → OPINION → COMPARE → TECHNICAL → EXPLAIN → CREATIVE → FACTUAL → SIMPLE

INTEGRACIÓN CON BRAIN.PY:
- categorizar_pregunta(): determina la categoría de la pregunta
- num_predict_para(): devuelve tokens máximos para esa categoría
- max_oraciones_para(): devuelve límite de oraciones para cortar el stream
- length_hint_para(): devuelve instrucción específica para el system prompt

EJEMPLO DE USO:
```python
pregunta = "¿Quién es Finn el humano?"
categoria = categorizar_pregunta(pregunta)  # → "factual"
tokens = num_predict_para(pregunta)         # → 100
limite = max_oraciones_para(pregunta)       # → 2
```

NOTA IMPORTANTE:
Si BMO está dando respuestas incorrectas o muy largas, puede ser debido a:
1. Clasificación incorrecta de la pregunta
2. Límites demasiado restrictivos
3. Conflicto entre el length_hint y el comportamiento esperado
Para debugging, revisar los logs que muestran: [CLASSIFY] pregunta → categoría
"""

import re
import unicodedata

# ---------------------------------------------------------------------------
# Categorías
# ---------------------------------------------------------------------------

class QueryCategory:
    GREETING  = "greeting"   # saludos, despedidas, reacciones cortas → 40 tokens
    OPINION   = "opinion"    # "qué piensas", "te gusta", "cuál prefieres" → 120 tokens
    COMPARE   = "compare"    # "diferencia entre", "cuál es mejor" → 180 tokens
    FACTUAL   = "factual"    # "qué es", "quién es", "cuándo" → 200 tokens
    TECHNICAL = "technical"  # programación, ciencia, matemáticas → 300 tokens
    EXPLAIN   = "explain"    # "explícame", "cómo funciona", "por qué" → 350 tokens
    CREATIVE  = "creative"   # historias, poemas, listas, ideas → 450 tokens
    SIMPLE    = "simple"     # default — preguntas cortas sin patrón claro → 150 tokens


NUM_PREDICT_MAP: dict[str, int] = {
    QueryCategory.GREETING:  40,   # 1 oración corta
    QueryCategory.SIMPLE:    180,  # 3 oraciones (aumentado de 100)
    QueryCategory.OPINION:   150,  # 3 oraciones (aumentado de 130)
    QueryCategory.FACTUAL:   200,  # 4 oraciones (aumentado de 130)
    QueryCategory.COMPARE:   180,  # 3 oraciones (aumentado de 150)
    QueryCategory.TECHNICAL: 250,  # 4-5 oraciones (aumentado de 200)
    QueryCategory.EXPLAIN:   280,  # 4-5 oraciones (aumentado de 220)
    QueryCategory.CREATIVE:  350,  # 5-7 oraciones (aumentado de 300)
}

# Máximo de oraciones permitidas por categoría.
# El stream se corta al llegar a este límite, independientemente de num_predict.
# Esto evita que el modelo genere oraciones extra que no se pidieron.
MAX_ORACIONES_MAP: dict[str, int] = {
    QueryCategory.GREETING:  1,   # "Hola, ¿cómo estás?"
    QueryCategory.SIMPLE:    3,   # Respuesta directa + contexto + detalle (aumentado de 2)
    QueryCategory.OPINION:   3,   # Opinión + razón + conclusión
    QueryCategory.FACTUAL:   4,   # Dato + contexto + detalle + cierre (aumentado de 3)
    QueryCategory.COMPARE:   4,   # Diferencia + ventaja/desventaja + detalle + conclusión (aumentado de 3)
    QueryCategory.TECHNICAL: 5,   # Concepto + explicación + ejemplo + detalle + cierre (aumentado de 4)
    QueryCategory.EXPLAIN:   5,   # Introducción + desarrollo + ejemplo + detalle + cierre (aumentado de 4)
    QueryCategory.CREATIVE:  7,   # Creatividad necesita más espacio (aumentado de 6)
}

# Instrucción de longitud que se inyecta en el system prompt según categoría.
# El modelo recibe una regla concreta de cuántas oraciones usar.
# El límite de oraciones es el control principal, los tokens son generosos para no cortar.
LENGTH_HINT_MAP: dict[str, str] = {
    QueryCategory.GREETING:  "Responde en 1 oración corta.",
    QueryCategory.SIMPLE:    "Responde en 2-3 oraciones: respuesta + contexto + detalle breve.",
    QueryCategory.OPINION:   "Responde en 2-3 oraciones: opinión + razón + cierre.",
    QueryCategory.FACTUAL:   "Responde en 3-4 oraciones: dato + contexto + explicación + cierre.",
    QueryCategory.COMPARE:   "Responde en 3-4 oraciones: diferencia + detalles + ventaja + conclusión.",
    QueryCategory.TECHNICAL: "Responde en 4-5 oraciones: concepto + funcionamiento + ejemplo + detalle + cierre.",
    QueryCategory.EXPLAIN:   "Responde en 4-5 oraciones: definición + explicación + ejemplo + importancia + cierre.",
    QueryCategory.CREATIVE:  "Responde en 5-7 oraciones bien desarrolladas con estructura completa.",
}

# ---------------------------------------------------------------------------
# Normalización para clasificación
# ---------------------------------------------------------------------------

def sin_acentos(texto: str) -> str:
    """Elimina tildes/diacríticos para que patrones coincidan con o sin acentos."""
    nfkd = unicodedata.normalize('NFKD', texto)
    return nfkd.encode('ascii', 'ignore').decode('ascii')


# ---------------------------------------------------------------------------
# Patrones regex
# ---------------------------------------------------------------------------

PATRON_SALUDO    = r"^(hola|buenos|buenas|adios|hasta|chao|bye|gracias|ok|si|no|bien|mal|genial|perfecto|claro|dale)\b"
PATRON_OPINION   = r"\b(que piensas|te gusta|cual prefieres|crees que|tu favorit)\b"
PATRON_COMPARE   = r"\b(diferencia entre|diferencias entre|cual es mejor|comparar|comparacion|versus|vs\.?)\b"
PATRON_TECNICO   = r"\b(codigo|programa|funcion|algoritmo|python|javascript|html|css|api|base de datos|servidor|variable|clase|objeto|metodo|error|bug|debug|linux|windows|terminal|consola|framework|libreria|dependencia|compilar|ejecutar|instalar|docker|git|servicio|proceso)\b"
PATRON_EXPLICAR  = r"\b(explica|explicame|como funciona|por que|describe|que significa|como se hace|como se usa|como usar)\b"
PATRON_CREATIVO  = r"\b(cuento|historia|poema|lista|inventa|imagina|crea|escribe|redacta|genera|propon|ideas para)\b"
PATRON_PREGUNTA  = r"^(que\s+(es|son|fue|era|significa)|que\s+\w+\s+(es|son|fue)|cual\s+(es|son|fue)|como\s+(se|era|es|puedo|hago)|por\s+que|para\s+que|donde\s+esta|cuando\s+fue|cuanto\s+(es|vale|cuesta|tiene)|existe|hay\s+algun|sabes\s+(que|como|donde|cuando|por que))\b"
PATRON_FACTUAL   = r"\b(quien es|quienes son|digitos|numero)\b"

# ---------------------------------------------------------------------------
# Funciones públicas
# ---------------------------------------------------------------------------

def categorizar_pregunta(texto: str) -> str:
    """
    Clasifica *texto* en una de las categorías de QueryCategory.

    Orden de prioridad:
      OPINION → COMPARE → CREATIVE → EXPLAIN → PREGUNTA → FACTUAL → TECHNICAL → GREETING → SIMPLE

    Nunca lanza excepción; ante cualquier error devuelve SIMPLE.
    """
    try:
        t = texto.lower().strip() if isinstance(texto, str) else ""
        t = sin_acentos(t)

        if re.search(PATRON_OPINION, t, re.IGNORECASE):
            return QueryCategory.OPINION

        if re.search(PATRON_COMPARE, t, re.IGNORECASE):
            return QueryCategory.COMPARE

        if re.search(PATRON_CREATIVO, t, re.IGNORECASE):
            return QueryCategory.CREATIVE

        if re.search(PATRON_EXPLICAR, t, re.IGNORECASE):
            return QueryCategory.EXPLAIN

        if re.search(PATRON_PREGUNTA, t, re.IGNORECASE):
            return QueryCategory.FACTUAL

        if re.search(PATRON_FACTUAL, t, re.IGNORECASE):
            return QueryCategory.FACTUAL

        if re.search(PATRON_TECNICO, t, re.IGNORECASE):
            return QueryCategory.TECHNICAL

        if re.search(PATRON_SALUDO, t, re.IGNORECASE):
            return QueryCategory.GREETING

        return QueryCategory.SIMPLE

    except Exception:
        return QueryCategory.SIMPLE


def num_predict_para(texto: str) -> int:
    """Devuelve el num_predict apropiado para el texto dado."""
    return NUM_PREDICT_MAP[categorizar_pregunta(texto)]


def length_hint_para(texto: str) -> str:
    """Devuelve la instrucción de longitud para inyectar en el system prompt."""
    return LENGTH_HINT_MAP[categorizar_pregunta(texto)]


def max_oraciones_para(texto: str) -> int:
    """Devuelve el máximo de oraciones permitidas para el texto dado."""
    return MAX_ORACIONES_MAP[categorizar_pregunta(texto)]
