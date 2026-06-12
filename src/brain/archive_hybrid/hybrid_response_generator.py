"""
Generador de Respuestas Híbridas para el Sistema de Conocimiento Factual.

Este módulo coordina la generación de respuestas entre la base de datos de hechos
y el LLM, decidiendo cuándo usar cada fuente y cómo combinarlas.

Características:
- Decisión inteligente entre fuentes de información
- Formateo natural de respuestas factuales
- Blending de respuestas cuando se requiere información mixta
- Fallback robusto al LLM normal
"""

import logging
import time
from typing import Optional, Tuple

from src.brain.models import Response, ResponseSource, QuestionType
from src.brain.question_classifier import question_classifier
from src.brain.fact_database import fact_database_manager
from src.brain.response_formatter import format_factual_response
from src.brain.hybrid_logger import hybrid_logger, create_question_hash
from src.config.config_manager import config_manager


class HybridResponseGenerator:
    """
    Coordinador principal del sistema híbrido.
    
    Decide entre usar la base de datos de hechos o el LLM normal,
    y genera respuestas coherentes manteniendo la personalidad de BMO.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("BMO.Hybrid.ResponseGen")
        
        # Estadísticas
        self.total_responses = 0
        self.factdb_responses = 0
        self.llm_responses = 0
        self.hybrid_responses = 0
        self.fallback_responses = 0
        
        self.logger.info("HybridResponseGenerator initialized")
    
    def generate_response(self, question: str, llm_callback=None) -> Tuple[str, ResponseSource]:
        """
        Genera una respuesta usando el sistema híbrido.
        
        Args:
            question: Pregunta del usuario
            llm_callback: Función callback para generar respuesta con LLM
            
        Returns:
            (respuesta, fuente)
        """
        start_time = time.time()
        
        # Verificar si el modo híbrido está habilitado
        if not config_manager.is_hybrid_mode_enabled():
            # Modo híbrido desactivado, usar LLM normal
            if llm_callback:
                response_text = llm_callback(question)
                return response_text, ResponseSource.LLM_NORMAL
            return "El modo híbrido está desactivado.", ResponseSource.FALLBACK_ERROR
        
        try:
            # 1. Clasificar pregunta
            classification = question_classifier.classify_question(question)
            
            # 2. Decidir estrategia de respuesta
            if classification.should_use_factdb:
                # Intentar respuesta desde base de datos de hechos
                response_text, source = self._generate_factual_response(
                    question, classification, llm_callback
                )
            else:
                # Usar LLM normal para preguntas conversacionales
                if llm_callback:
                    response_text = llm_callback(question)
                    source = ResponseSource.LLM_NORMAL
                    self.llm_responses += 1
                else:
                    response_text = "No puedo generar una respuesta en este momento."
                    source = ResponseSource.FALLBACK_ERROR
                    self.fallback_responses += 1
            
            # 3. Registrar respuesta
            processing_time_ms = (time.time() - start_time) * 1000
            question_hash = create_question_hash(question)
            
            hybrid_logger.log_response_generation(
                question_hash=question_hash,
                source=source,
                confidence=classification.confidence,
                processing_time_ms=processing_time_ms,
                fact_key=None  # TODO: agregar fact_key si aplica
            )
            
            self.total_responses += 1
            
            return response_text, source
            
        except Exception as e:
            self.logger.error(f"Error generating hybrid response: {e}")
            
            # Fallback a LLM normal
            question_hash = create_question_hash(question)
            hybrid_logger.log_fallback(
                question_hash=question_hash,
                reason="error_in_hybrid_system",
                original_error=str(e)
            )
            
            if llm_callback:
                response_text = llm_callback(question)
                source = ResponseSource.LLM_NORMAL
            else:
                response_text = "Ups, BMO tuvo un problema. ¿Puedes repetir la pregunta?"
                source = ResponseSource.FALLBACK_ERROR
            
            self.fallback_responses += 1
            self.total_responses += 1
            
            return response_text, source
    
    def _generate_factual_response(self, question: str, classification, 
                                   llm_callback=None) -> Tuple[str, ResponseSource]:
        """
        Genera respuesta desde la base de datos de hechos.
        
        Args:
            question: Pregunta del usuario
            classification: Resultado de clasificación
            llm_callback: Callback para LLM si se necesita blending
            
        Returns:
            (respuesta, fuente)
        """
        # Buscar hechos relevantes
        facts = fact_database_manager.search_facts(
            query=question,
            entities=classification.extracted_entities,
            category=classification.question_type
        )
        
        if not facts:
            # No se encontró hecho, fallback a LLM
            self.logger.info(f"No facts found for question type {classification.question_type.value}")
            
            question_hash = create_question_hash(question)
            hybrid_logger.log_fallback(
                question_hash=question_hash,
                reason="no_facts_found",
                original_error=None
            )
            
            if llm_callback:
                response_text = llm_callback(question)
                source = ResponseSource.LLM_NORMAL
                self.llm_responses += 1
            else:
                response_text = "No tengo esa información específica en este momento."
                source = ResponseSource.FALLBACK_ERROR
                self.fallback_responses += 1
            
            return response_text, source
        
        # Usar el hecho más relevante (primero en la lista)
        best_fact = facts[0]
        
        # Formatear respuesta con personalidad BMO
        response_text = format_factual_response(best_fact, question)
        
        # Verificar si necesita blending con LLM
        if config_manager.is_hybrid_response_blending_enabled() and self._requires_llm_enhancement(question, best_fact):
            # TODO: Implementar blending de respuestas
            # Por ahora, usar solo la respuesta factual
            source = ResponseSource.FACT_DATABASE
            self.factdb_responses += 1
        else:
            source = ResponseSource.FACT_DATABASE
            self.factdb_responses += 1
        
        return response_text, source
    
    def _requires_llm_enhancement(self, question: str, fact) -> bool:
        """
        Determina si una respuesta factual necesita información adicional del LLM.
        
        Args:
            question: Pregunta original
            fact: Hecho encontrado
            
        Returns:
            True si necesita enhancement
        """
        # Por ahora, no requerir enhancement
        # TODO: Implementar lógica más sofisticada
        return False
    
    def get_stats(self) -> dict:
        """Obtiene estadísticas del generador de respuestas."""
        return {
            'total_responses': self.total_responses,
            'factdb_responses': self.factdb_responses,
            'llm_responses': self.llm_responses,
            'hybrid_responses': self.hybrid_responses,
            'fallback_responses': self.fallback_responses,
            'factdb_percentage': (self.factdb_responses / self.total_responses * 100) if self.total_responses > 0 else 0,
            'llm_percentage': (self.llm_responses / self.total_responses * 100) if self.total_responses > 0 else 0
        }


# Instancia global del generador de respuestas
hybrid_response_generator = HybridResponseGenerator()