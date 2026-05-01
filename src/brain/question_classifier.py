"""
Clasificador de Preguntas para el Sistema Híbrido de Conocimiento Factual.

Este módulo detecta automáticamente preguntas sobre temas donde el LLM falla
sistemáticamente y determina si debe usar la base de datos de hechos.

Características:
- Detección de preguntas problemáticas (banderas, ciencias, geografía)
- Extracción de entidades (países, conceptos científicos)
- Cálculo de niveles de confianza
- Cache LRU para clasificaciones frecuentes
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from functools import lru_cache
import time

from src.brain.models import QuestionType, ClassificationResult, PROBLEMATIC_CATEGORIES
from src.brain.hybrid_logger import hybrid_logger, create_question_hash
from src.config.config_manager import config_manager


class QuestionClassifier:
    """
    Clasificador de preguntas que detecta temas problemáticos para el LLM.
    
    Usa patrones regex y análisis de keywords para determinar si una pregunta
    debe ser respondida con la base de datos de hechos o el LLM normal.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("BMO.Hybrid.Classifier")
        
        # Importar patrones
        from src.brain.patterns.flag_patterns import FLAG_PATTERNS, FLAG_ENTITIES
        from src.brain.patterns.science_patterns import SCIENCE_PATTERNS, SCIENCE_ENTITIES
        
        self.flag_patterns = FLAG_PATTERNS
        self.flag_entities = FLAG_ENTITIES
        self.science_patterns = SCIENCE_PATTERNS
        self.science_entities = SCIENCE_ENTITIES
        
        # Estadísticas
        self.total_classifications = 0
        self.classifications_by_type = {}
        
        self.logger.info("QuestionClassifier initialized")
    
    def classify_question(self, question: str) -> ClassificationResult:
        """
        Clasifica una pregunta para determinar su tipo y si debe usar la base de datos.
        
        Args:
            question: Pregunta del usuario
            
        Returns:
            ClassificationResult con tipo, confianza y decisión
        """
        start_time = time.time()
        
        # Normalizar pregunta
        normalized = self._normalize_question(question)
        
        # Evaluar cada categoría problemática
        scores = {}
        
        # Banderas
        flag_score, flag_entities = self._evaluate_flag_question(normalized)
        scores[QuestionType.FLAG_COLORS] = (flag_score, flag_entities)
        
        # Ciencias naturales
        science_score, science_entities = self._evaluate_science_question(normalized)
        scores[QuestionType.NATURAL_SCIENCES] = (science_score, science_entities)
        
        # Geografía específica
        geo_score, geo_entities = self._evaluate_geography_question(normalized)
        scores[QuestionType.SPECIFIC_GEOGRAPHY] = (geo_score, geo_entities)
        
        # Fechas históricas
        history_score, history_entities = self._evaluate_history_question(normalized)
        scores[QuestionType.HISTORICAL_DATES] = (history_score, history_entities)
        
        # Determinar mejor categoría
        best_category = max(scores.items(), key=lambda x: x[1][0])
        question_type = best_category[0]
        confidence = best_category[1][0]
        extracted_entities = best_category[1][1]
        
        # Si no es problemática, clasificar como conversacional
        if confidence < 0.3:
            question_type = self._classify_conversational(normalized)
            confidence = 0.9  # Alta confianza en categorías conversacionales
            extracted_entities = []
        
        # Determinar si debe usar base de datos
        threshold = config_manager.get_classification_threshold(question_type.value)
        should_use_factdb = (
            question_type in PROBLEMATIC_CATEGORIES and 
            confidence > threshold
        )
        
        # Crear resultado
        processing_time_ms = (time.time() - start_time) * 1000
        
        result = ClassificationResult(
            question_type=question_type,
            confidence=confidence,
            extracted_entities=extracted_entities,
            should_use_factdb=should_use_factdb,
            reasoning=f"Pattern match score: {confidence:.2f}, threshold: {threshold:.2f}, entities: {len(extracted_entities)}",
            processing_time_ms=processing_time_ms
        )
        
        # Actualizar estadísticas
        self.total_classifications += 1
        self.classifications_by_type[question_type.value] = \
            self.classifications_by_type.get(question_type.value, 0) + 1
        
        # Log clasificación
        question_hash = create_question_hash(question)
        hybrid_logger.log_classification(question_hash, result, processing_time_ms)
        
        return result
    
    @staticmethod
    def _normalize_question(question: str) -> str:
        """
        Normaliza una pregunta para análisis.
        
        Args:
            question: Pregunta original
            
        Returns:
            Pregunta normalizada
        """
        # Convertir a minúsculas
        normalized = question.lower().strip()
        
        # Eliminar signos de puntuación al final
        normalized = normalized.rstrip('?!.,;:')
        
        # Normalizar espacios múltiples
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Eliminar acentos para matching más flexible
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ñ': 'n', 'ü': 'u'
        }
        for accented, plain in replacements.items():
            normalized = normalized.replace(accented, plain)
        
        return normalized
    
    def _evaluate_flag_question(self, question: str) -> Tuple[float, List[str]]:
        """
        Evalúa si la pregunta es sobre banderas.
        
        Args:
            question: Pregunta normalizada
            
        Returns:
            (score, entidades_extraídas)
        """
        score = 0.0
        entities = []
        
        # Verificar patrones de banderas
        for pattern in self.flag_patterns:
            if re.search(pattern, question):
                score += 0.4
        
        # Extraer países mencionados
        for country, aliases in self.flag_entities.items():
            for alias in aliases:
                if alias in question:
                    entities.append(country)
                    score += 0.3
                    break
        
        # Bonus si menciona "colores" y un país
        if 'color' in question and entities:
            score += 0.3
        
        return min(score, 1.0), list(set(entities))
    
    def _evaluate_science_question(self, question: str) -> Tuple[float, List[str]]:
        """
        Evalúa si la pregunta es sobre ciencias naturales.
        
        Args:
            question: Pregunta normalizada
            
        Returns:
            (score, entidades_extraídas)
        """
        score = 0.0
        entities = []
        
        # Verificar patrones científicos
        for pattern in self.science_patterns:
            if re.search(pattern, question):
                score += 0.3
        
        # Extraer conceptos científicos
        for concept, aliases in self.science_entities.items():
            for alias in aliases:
                if alias in question:
                    entities.append(concept)
                    score += 0.2
                    break
        
        # Bonus por palabras clave científicas
        science_keywords = ['planeta', 'animal', 'organo', 'hueso', 'gas', 'temperatura', 'metal']
        for keyword in science_keywords:
            if keyword in question:
                score += 0.15
        
        return min(score, 1.0), list(set(entities))
    
    def _evaluate_geography_question(self, question: str) -> Tuple[float, List[str]]:
        """
        Evalúa si la pregunta es sobre geografía específica.
        
        Args:
            question: Pregunta normalizada
            
        Returns:
            (score, entidades_extraídas)
        """
        score = 0.0
        entities = []
        
        # Patrones geográficos
        geo_patterns = [
            r'capital de \w+',
            r'pais mas grande',
            r'rio mas largo',
            r'montana mas alta',
            r'desierto mas grande',
            r'lago mas profundo',
            r'en que continente'
        ]
        
        for pattern in geo_patterns:
            if re.search(pattern, question):
                score += 0.4
        
        # Extraer países/lugares mencionados
        geo_entities = {
            'brasil': ['brasil'],
            'kazajistan': ['kazajistan', 'kazajstan'],
            'rusia': ['rusia'],
            'egipto': ['egipto'],
            'turquia': ['turquia']
        }
        
        for place, aliases in geo_entities.items():
            for alias in aliases:
                if alias in question:
                    entities.append(place)
                    score += 0.3
                    break
        
        return min(score, 1.0), list(set(entities))
    
    def _evaluate_history_question(self, question: str) -> Tuple[float, List[str]]:
        """
        Evalúa si la pregunta es sobre fechas históricas.
        
        Args:
            question: Pregunta normalizada
            
        Returns:
            (score, entidades_extraídas)
        """
        score = 0.0
        entities = []
        
        # Patrones históricos
        history_patterns = [
            r'en que ano',
            r'cuando fue',
            r'cuando se',
            r'fecha de',
            r'ano de'
        ]
        
        for pattern in history_patterns:
            if re.search(pattern, question):
                score += 0.3
        
        # Eventos históricos conocidos
        historical_events = {
            'segunda_guerra_mundial': ['segunda guerra mundial', 'guerra mundial'],
            'revolucion_francesa': ['revolucion francesa'],
            'independencia_mexico': ['independencia de mexico'],
            'muro_berlin': ['muro de berlin']
        }
        
        for event, aliases in historical_events.items():
            for alias in aliases:
                if alias in question:
                    entities.append(event)
                    score += 0.4
                    break
        
        return min(score, 1.0), list(set(entities))
    
    def _classify_conversational(self, question: str) -> QuestionType:
        """
        Clasifica preguntas conversacionales en categorías específicas.
        
        Args:
            question: Pregunta normalizada
            
        Returns:
            QuestionType conversacional
        """
        # Entretenimiento
        entertainment_keywords = ['pelicula', 'actor', 'cancion', 'musica', 'serie', 'libro']
        if any(kw in question for kw in entertainment_keywords):
            return QuestionType.ENTERTAINMENT
        
        # Deportes
        sports_keywords = ['futbol', 'deporte', 'jugador', 'equipo', 'copa', 'olimpico']
        if any(kw in question for kw in sports_keywords):
            return QuestionType.SPORTS
        
        # Matemáticas
        math_keywords = ['cuanto es', 'suma', 'resta', 'multiplica', 'divide', 'raiz']
        if any(kw in question for kw in math_keywords):
            return QuestionType.MATHEMATICS
        
        # Economía
        econ_keywords = ['moneda', 'precio', 'costo', 'dinero', 'economia']
        if any(kw in question for kw in econ_keywords):
            return QuestionType.ECONOMICS
        
        # Por defecto, conversacional
        return QuestionType.CONVERSATIONAL
    
    def extract_entities(self, question: str) -> List[str]:
        """
        Extrae entidades de una pregunta (países, conceptos, etc.).
        
        Args:
            question: Pregunta original
            
        Returns:
            Lista de entidades extraídas
        """
        normalized = self._normalize_question(question)
        entities = []
        
        # Extraer de todas las categorías
        _, flag_entities = self._evaluate_flag_question(normalized)
        _, science_entities = self._evaluate_science_question(normalized)
        _, geo_entities = self._evaluate_geography_question(normalized)
        _, history_entities = self._evaluate_history_question(normalized)
        
        entities.extend(flag_entities)
        entities.extend(science_entities)
        entities.extend(geo_entities)
        entities.extend(history_entities)
        
        return list(set(entities))
    
    def is_problematic_topic(self, question: str) -> bool:
        """
        Verifica rápidamente si una pregunta es sobre un tema problemático.
        
        Args:
            question: Pregunta original
            
        Returns:
            True si es tema problemático
        """
        result = self.classify_question(question)
        return result.should_use_factdb
    
    def get_confidence_score(self, question: str, category: QuestionType) -> float:
        """
        Obtiene el score de confianza para una categoría específica.
        
        Args:
            question: Pregunta original
            category: Categoría a evaluar
            
        Returns:
            Score de confianza (0.0-1.0)
        """
        normalized = self._normalize_question(question)
        
        if category == QuestionType.FLAG_COLORS:
            score, _ = self._evaluate_flag_question(normalized)
        elif category == QuestionType.NATURAL_SCIENCES:
            score, _ = self._evaluate_science_question(normalized)
        elif category == QuestionType.SPECIFIC_GEOGRAPHY:
            score, _ = self._evaluate_geography_question(normalized)
        elif category == QuestionType.HISTORICAL_DATES:
            score, _ = self._evaluate_history_question(normalized)
        else:
            score = 0.0
        
        return score
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas del clasificador."""
        return {
            'total_classifications': self.total_classifications,
            'classifications_by_type': self.classifications_by_type
        }


# Instancia global del clasificador
question_classifier = QuestionClassifier()