"""
Algoritmos de Similitud para el Sistema Híbrido.

Este módulo proporciona funciones optimizadas para calcular similitud
entre textos, usado para matching de patrones y búsqueda de hechos.
"""

from functools import lru_cache
from typing import Tuple


@lru_cache(maxsize=1000)
def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calcula la distancia de Levenshtein entre dos strings.
    
    La distancia de Levenshtein es el número mínimo de operaciones
    (inserción, eliminación, sustitución) necesarias para transformar
    un string en otro.
    
    Args:
        s1: Primer string
        s2: Segundo string
        
    Returns:
        Distancia de Levenshtein
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        
        for j, c2 in enumerate(s2):
            # Costo de inserción, eliminación, sustitución
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            
            current_row.append(min(insertions, deletions, substitutions))
        
        previous_row = current_row
    
    return previous_row[-1]


@lru_cache(maxsize=1000)
def normalized_levenshtein_similarity(s1: str, s2: str) -> float:
    """
    Calcula similitud normalizada usando distancia de Levenshtein.
    
    Args:
        s1: Primer string
        s2: Segundo string
        
    Returns:
        Similitud entre 0.0 (completamente diferente) y 1.0 (idéntico)
    """
    if s1 == s2:
        return 1.0
    
    if not s1 or not s2:
        return 0.0
    
    # Optimización: si la diferencia de longitud es muy grande, baja similitud
    len1, len2 = len(s1), len(s2)
    if abs(len1 - len2) > max(len1, len2) * 0.5:
        return 0.0
    
    distance = levenshtein_distance(s1, s2)
    max_len = max(len1, len2)
    
    similarity = 1.0 - (distance / max_len)
    
    return max(0.0, similarity)


def jaccard_similarity(set1: set, set2: set) -> float:
    """
    Calcula similitud de Jaccard entre dos conjuntos.
    
    Args:
        set1: Primer conjunto
        set2: Segundo conjunto
        
    Returns:
        Similitud entre 0.0 y 1.0
    """
    if not set1 or not set2:
        return 0.0
    
    intersection = set1 & set2
    union = set1 | set2
    
    return len(intersection) / len(union) if union else 0.0


def cosine_similarity_simple(text1: str, text2: str) -> float:
    """
    Calcula similitud de coseno simple basada en palabras.
    
    Args:
        text1: Primer texto
        text2: Segundo texto
        
    Returns:
        Similitud entre 0.0 y 1.0
    """
    # Tokenizar
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    # Intersección
    intersection = words1 & words2
    
    # Magnitudes
    magnitude1 = len(words1) ** 0.5
    magnitude2 = len(words2) ** 0.5
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    # Similitud de coseno
    return len(intersection) / (magnitude1 * magnitude2)


def fuzzy_match(query: str, target: str, threshold: float = 0.7) -> bool:
    """
    Verifica si dos strings hacen match fuzzy.
    
    Args:
        query: String de búsqueda
        target: String objetivo
        threshold: Umbral de similitud mínimo
        
    Returns:
        True si la similitud supera el umbral
    """
    similarity = normalized_levenshtein_similarity(query.lower(), target.lower())
    return similarity >= threshold


def best_match(query: str, candidates: list, threshold: float = 0.7) -> Tuple[str, float]:
    """
    Encuentra el mejor match de una query en una lista de candidatos.
    
    Args:
        query: String de búsqueda
        candidates: Lista de strings candidatos
        threshold: Umbral de similitud mínimo
        
    Returns:
        (mejor_candidato, score) o (None, 0.0) si no hay match
    """
    best_candidate = None
    best_score = 0.0
    
    query_lower = query.lower()
    
    for candidate in candidates:
        score = normalized_levenshtein_similarity(query_lower, candidate.lower())
        
        if score > best_score and score >= threshold:
            best_score = score
            best_candidate = candidate
    
    return (best_candidate, best_score) if best_candidate else (None, 0.0)


def contains_fuzzy(query: str, text: str, threshold: float = 0.8) -> bool:
    """
    Verifica si una query está contenida fuzzy en un texto.
    
    Args:
        query: String de búsqueda
        text: Texto donde buscar
        threshold: Umbral de similitud
        
    Returns:
        True si se encuentra match fuzzy
    """
    query_lower = query.lower()
    text_lower = text.lower()
    
    # Búsqueda exacta primero
    if query_lower in text_lower:
        return True
    
    # Búsqueda fuzzy por palabras
    query_words = query_lower.split()
    text_words = text_lower.split()
    
    for query_word in query_words:
        found = False
        for text_word in text_words:
            if normalized_levenshtein_similarity(query_word, text_word) >= threshold:
                found = True
                break
        
        if not found:
            return False
    
    return True


def calculate_pattern_match_score(text: str, patterns: list) -> float:
    """
    Calcula un score de match contra múltiples patrones.
    
    Args:
        text: Texto a evaluar
        patterns: Lista de patrones regex
        
    Returns:
        Score entre 0.0 y 1.0
    """
    import re
    
    if not patterns:
        return 0.0
    
    matches = 0
    for pattern in patterns:
        if re.search(pattern, text.lower()):
            matches += 1
    
    return matches / len(patterns)