"""
Patrones de Clasificación para el Sistema Híbrido.

Este paquete contiene patrones regex y entidades para detectar
diferentes tipos de preguntas problemáticas.
"""

from src.brain.patterns.flag_patterns import FLAG_PATTERNS, FLAG_ENTITIES, FLAG_KEYWORDS
from src.brain.patterns.science_patterns import SCIENCE_PATTERNS, SCIENCE_ENTITIES, SCIENCE_KEYWORDS

__all__ = [
    'FLAG_PATTERNS',
    'FLAG_ENTITIES',
    'FLAG_KEYWORDS',
    'SCIENCE_PATTERNS',
    'SCIENCE_ENTITIES',
    'SCIENCE_KEYWORDS',
]