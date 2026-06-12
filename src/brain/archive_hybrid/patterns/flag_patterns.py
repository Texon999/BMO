"""
Patrones de Clasificación para Preguntas sobre Banderas.

Este módulo contiene patrones regex y entidades para detectar
preguntas sobre colores y diseños de banderas nacionales.
"""

# Patrones regex para detectar preguntas sobre banderas
FLAG_PATTERNS = [
    r'color(es)? de la bandera',
    r'que color(es)? (tiene|son|lleva)',
    r'de que color es la bandera',
    r'cuales son los colores de la bandera',
    r'como es la bandera de',
    r'bandera de \w+ (tiene|es|lleva)',
]

# Entidades de países con sus aliases
FLAG_ENTITIES = {
    'colombia': ['colombia', 'colombiana', 'republica de colombia'],
    'mexico': ['mexico', 'méxico', 'mexicana', 'estados unidos mexicanos'],
    'espana': ['espana', 'españa', 'española', 'reino de españa'],
    'francia': ['francia', 'francesa', 'republica francesa'],
    'italia': ['italia', 'italiana', 'republica italiana'],
    'alemania': ['alemania', 'alemana', 'republica federal de alemania'],
    'brasil': ['brasil', 'brasileña', 'republica federativa del brasil'],
    'argentina': ['argentina', 'argentina', 'republica argentina'],
    'reino_unido': ['reino unido', 'inglaterra', 'gran bretaña', 'britanica', 'union jack'],
    'estados_unidos': ['estados unidos', 'usa', 'eeuu', 'america', 'estadounidense', 'americana'],
    'canada': ['canada', 'canadá', 'canadiense'],
    'japon': ['japon', 'japón', 'japonesa', 'nipon'],
    'china': ['china', 'china', 'republica popular china'],
    'india': ['india', 'india', 'republica de la india'],
    'australia': ['australia', 'australiana', 'commonwealth de australia'],
}

# Keywords adicionales que refuerzan la clasificación
FLAG_KEYWORDS = [
    'bandera',
    'colores',
    'franjas',
    'escudo',
    'simbolo nacional',
    'enseña nacional'
]