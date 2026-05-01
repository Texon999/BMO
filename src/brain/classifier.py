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
    QueryCategory.GREETING:  40,
    QueryCategory.OPINION:   80,
    QueryCategory.COMPARE:   120,
    QueryCategory.FACTUAL:   100,
    QueryCategory.TECHNICAL: 180,
    QueryCategory.EXPLAIN:   200,
    QueryCategory.CREATIVE:  280,
    QueryCategory.SIMPLE:    100,
}

# Máximo de oraciones permitidas por categoría.
# El stream se corta al llegar a este límite, independientemente de num_predict.
# Esto evita que el modelo genere oraciones extra que no se pidieron.
MAX_ORACIONES_MAP: dict[str, int] = {
    QueryCategory.GREETING:  1,
    QueryCategory.SIMPLE:    2,
    QueryCategory.OPINION:   2,
    QueryCategory.FACTUAL:   2,
    QueryCategory.COMPARE:   3,
    QueryCategory.TECHNICAL: 3,
    QueryCategory.EXPLAIN:   3,
    QueryCategory.CREATIVE:  5,
}

# Instrucción de longitud que se inyecta en el system prompt según categoría.
# El modelo recibe una regla concreta de cuántas oraciones usar.
LENGTH_HINT_MAP: dict[str, str] = {
    QueryCategory.GREETING:  "Responde en UNA sola oración corta y amigable. Nada más.",
    QueryCategory.SIMPLE:    "Responde en máximo 2 oraciones directas. Ve al punto.",
    QueryCategory.OPINION:   "Da tu opinión en 2 oraciones. Sé directo y personal.",
    QueryCategory.FACTUAL:   "Responde en 2 oraciones EXACTAS: primero la respuesta concreta, luego un dato de contexto. Si no estás seguro de algún dato, di que no lo sabes. Sin rodeos, sin inventar.",
    QueryCategory.COMPARE:   "Compara en 2-3 oraciones: diferencia clave y conclusión. Sin inventar datos.",
    QueryCategory.TECHNICAL: "Explica en 3 oraciones claras. Usa lenguaje sencillo. Si no sabes algo, dilo.",
    QueryCategory.EXPLAIN:   "Explica en 3 oraciones: idea principal, detalle clave, cierre. Si no sabes algo con certeza, admítelo.",
    QueryCategory.CREATIVE:  "Sé creativo y conciso. Máximo 4-5 oraciones bien construidas.",
}

# ---------------------------------------------------------------------------
# Patrones regex
# ---------------------------------------------------------------------------

PATRON_SALUDO    = r"^(hola|buenos|buenas|adiós|adios|hasta|chao|bye|gracias|ok|sí|si|no|bien|mal|genial|perfecto|claro|dale)\b"
PATRON_OPINION   = r"\b(qué piensas|que piensas|te gusta|cuál prefieres|cual prefieres|qué opinas|que opinas|crees que|tu favorit)\b"
PATRON_COMPARE   = r"\b(diferencia entre|diferencias entre|cuál es mejor|cual es mejor|comparar|comparación|versus|vs\.?)\b"
PATRON_TECNICO   = r"\b(código|codigo|programa|función|funcion|algoritmo|python|javascript|html|css|api|base de datos|servidor|variable|clase|objeto|método|metodo|error|bug|debug)\b"
PATRON_EXPLICAR  = r"\b(explica|explícame|explicame|cómo funciona|como funciona|por qué|por que|cuéntame|cuentame|describe|qué significa|que significa|cómo se hace|como se hace)\b"
PATRON_CREATIVO  = r"\b(cuento|historia|poema|lista|inventa|imagina|crea|escribe|redacta|genera|propón|propones|ideas para)\b"
PATRON_FACTUAL   = r"\b(qué es|que es|quién es|quien es|cuándo|cuando|dónde|donde|cuánto|cuanto|cuál|cual|qué son|que son|quiénes son|quienes son)\b"

# ---------------------------------------------------------------------------
# Funciones públicas
# ---------------------------------------------------------------------------

def categorizar_pregunta(texto: str) -> str:
    """
    Clasifica *texto* en una de las categorías de QueryCategory.

    Orden de prioridad:
      GREETING → OPINION → COMPARE → TECHNICAL → EXPLAIN → CREATIVE → FACTUAL → SIMPLE

    Nunca lanza excepción; ante cualquier error devuelve SIMPLE.
    """
    try:
        t = texto.lower().strip() if isinstance(texto, str) else ""

        if re.search(PATRON_SALUDO, t, re.IGNORECASE):
            return QueryCategory.GREETING

        if re.search(PATRON_OPINION, t, re.IGNORECASE):
            return QueryCategory.OPINION

        if re.search(PATRON_COMPARE, t, re.IGNORECASE):
            return QueryCategory.COMPARE

        if re.search(PATRON_TECNICO, t, re.IGNORECASE):
            return QueryCategory.TECHNICAL

        if re.search(PATRON_EXPLICAR, t, re.IGNORECASE):
            return QueryCategory.EXPLAIN

        if re.search(PATRON_CREATIVO, t, re.IGNORECASE):
            return QueryCategory.CREATIVE

        if re.search(PATRON_FACTUAL, t, re.IGNORECASE):
            return QueryCategory.FACTUAL

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
