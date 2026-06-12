"""
Normalizador de Texto para el Sistema Híbrido.

Este módulo proporciona funciones para normalizar texto de preguntas,
facilitando el matching de patrones y la búsqueda en la base de datos.
"""

import re
import unicodedata
from typing import List


def normalize_question(text: str) -> str:
    """
    Normaliza una pregunta para análisis y búsqueda.
    
    Args:
        text: Texto original
        
    Returns:
        Texto normalizado
    """
    # Convertir a minúsculas
    normalized = text.lower().strip()
    
    # Eliminar signos de puntuación al final
    normalized = normalized.rstrip('?!.,;:')
    
    # Normalizar espacios múltiples
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized


def remove_accents(text: str) -> str:
    """
    Elimina acentos de un texto para matching más flexible.
    
    Args:
        text: Texto con acentos
        
    Returns:
        Texto sin acentos
    """
    # Normalizar a NFD (descomponer caracteres acentuados)
    nfd = unicodedata.normalize('NFD', text)
    
    # Filtrar marcas diacríticas
    without_accents = ''.join(
        char for char in nfd 
        if unicodedata.category(char) != 'Mn'
    )
    
    return without_accents


def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """
    Extrae keywords de un texto.
    
    Args:
        text: Texto original
        min_length: Longitud mínima de keywords
        
    Returns:
        Lista de keywords
    """
    # Normalizar
    normalized = normalize_question(text)
    
    # Eliminar palabras comunes (stopwords)
    stopwords = {
        'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
        'de', 'del', 'al', 'a', 'en', 'por', 'para', 'con',
        'que', 'cual', 'cuales', 'como', 'cuando', 'donde',
        'es', 'son', 'esta', 'estan', 'tiene', 'tienen',
        'hay', 'fue', 'sera', 'puede', 'pueden'
    }
    
    # Dividir en palabras
    words = normalized.split()
    
    # Filtrar stopwords y palabras cortas
    keywords = [
        word for word in words 
        if word not in stopwords and len(word) >= min_length
    ]
    
    return keywords


def clean_text(text: str) -> str:
    """
    Limpia un texto eliminando caracteres especiales.
    
    Args:
        text: Texto original
        
    Returns:
        Texto limpio
    """
    # Eliminar caracteres especiales excepto letras, números y espacios
    cleaned = re.sub(r'[^a-záéíóúñü0-9\s]', '', text.lower())
    
    # Normalizar espacios
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned


def tokenize(text: str) -> List[str]:
    """
    Tokeniza un texto en palabras.
    
    Args:
        text: Texto original
        
    Returns:
        Lista de tokens
    """
    # Normalizar
    normalized = normalize_question(text)
    
    # Dividir por espacios
    tokens = normalized.split()
    
    return tokens


def calculate_word_overlap(text1: str, text2: str) -> float:
    """
    Calcula el overlap de palabras entre dos textos.
    
    Args:
        text1: Primer texto
        text2: Segundo texto
        
    Returns:
        Score de overlap (0.0-1.0)
    """
    # Tokenizar
    tokens1 = set(tokenize(text1))
    tokens2 = set(tokenize(text2))
    
    if not tokens1 or not tokens2:
        return 0.0
    
    # Calcular intersección
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    
    # Jaccard similarity
    return len(intersection) / len(union) if union else 0.0


def contains_pattern(text: str, pattern: str) -> bool:
    """
    Verifica si un texto contiene un patrón regex.
    
    Args:
        text: Texto a verificar
        pattern: Patrón regex
        
    Returns:
        True si contiene el patrón
    """
    normalized = normalize_question(text)
    return bool(re.search(pattern, normalized))


def extract_entities_by_pattern(text: str, entity_dict: dict) -> List[str]:
    """
    Extrae entidades de un texto usando un diccionario de aliases.
    
    Args:
        text: Texto original
        entity_dict: Diccionario {entidad: [aliases]}
        
    Returns:
        Lista de entidades encontradas
    """
    normalized = normalize_question(text)
    entities = []
    
    for entity, aliases in entity_dict.items():
        for alias in aliases:
            if alias in normalized:
                entities.append(entity)
                break
    
    return list(set(entities))