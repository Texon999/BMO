"""
Patrones de Clasificación para Preguntas Científicas.

Este módulo contiene patrones regex y entidades para detectar
preguntas sobre ciencias naturales (astronomía, biología, química, física).
"""

# Patrones regex para detectar preguntas científicas
SCIENCE_PATTERNS = [
    # Astronomía
    r'planeta (mas|más) (grande|cercano|lejano)',
    r'cuantos planetas',
    r'sistema solar',
    r'velocidad de la luz',
    
    # Biología
    r'animal (mas|más) (grande|rapido|pequeño)',
    r'organo (mas|más) grande',
    r'cuantos (huesos|cromosomas)',
    r'que (es|significa) (adn|fotosintesis)',
    
    # Química
    r'temperatura (de )?(ebullicion|fusion)',
    r'metal (mas|más) abundante',
    r'(que|cual) gas',
    
    # Física
    r'velocidad de',
    r'que (es|significa)',
    
    # General
    r'cuantos continentes',
    r'oceano (mas|más) grande',
]

# Entidades científicas con sus aliases
SCIENCE_ENTITIES = {
    # Planetas
    'jupiter': ['jupiter', 'júpiter'],
    'mercurio': ['mercurio'],
    'venus': ['venus'],
    'marte': ['marte'],
    'saturno': ['saturno'],
    'urano': ['urano'],
    'neptuno': ['neptuno'],
    
    # Animales
    'ballena_azul': ['ballena azul', 'ballena'],
    'guepardo': ['guepardo', 'chita'],
    'elefante': ['elefante'],
    'tigre': ['tigre'],
    'leon': ['leon', 'león'],
    
    # Órganos
    'piel': ['piel'],
    'corazon': ['corazon', 'corazón'],
    'cerebro': ['cerebro'],
    'higado': ['higado', 'hígado'],
    'pulmon': ['pulmon', 'pulmón'],
    
    # Conceptos
    'oxigeno': ['oxigeno', 'oxígeno'],
    'agua': ['agua'],
    'aluminio': ['aluminio'],
    'hierro': ['hierro'],
    'adn': ['adn', 'ácido desoxirribonucleico'],
    'fotosintesis': ['fotosintesis', 'fotosíntesis'],
    
    # Geografía natural
    'continentes': ['continentes', 'continente'],
    'oceano': ['oceano', 'océano', 'pacifico', 'atlantico'],
}

# Keywords científicas que refuerzan la clasificación
SCIENCE_KEYWORDS = [
    'planeta',
    'animal',
    'organo',
    'hueso',
    'cromosoma',
    'gas',
    'temperatura',
    'metal',
    'sistema solar',
    'cuerpo humano',
    'continente',
    'oceano',
    'velocidad',
    'luz',
    'fotosintesis',
    'adn'
]