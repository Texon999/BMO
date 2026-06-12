"""
Manejador de Fallback para el Sistema Híbrido.

Este módulo maneja situaciones de error y proporciona fallbacks robustos
cuando el sistema híbrido no puede generar una respuesta.
"""

import logging
from enum import Enum
from typing import Optional, Callable

from src.brain.hybrid_logger import hybrid_logger, create_question_hash
from src.config.config_manager import config_manager


class FallbackReason(str, Enum):
    """Razones de fallback al LLM normal."""
    NO_FACTS_FOUND = "no_facts_found"
    DATABASE_ERROR = "database_error"
    CLASSIFICATION_ERROR = "classification_error"
    LOW_CONFIDENCE = "low_confidence"
    SYSTEM_ERROR = "system_error"
    DATABASE_UNAVAILABLE = "database_unavailable"


class FallbackHandler:
    """
    Manejador de fallbacks del sistema híbrido.
    
    Proporciona estrategias de recuperación cuando el sistema híbrido
    no puede generar una respuesta desde la base de datos de hechos.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("BMO.Hybrid.Fallback")
        
        # Estadísticas de fallbacks
        self.total_fallbacks = 0
        self.fallbacks_by_reason = {}
        
        self.logger.info("FallbackHandler initialized")
    
    def handle_fallback(self, question: str, reason: FallbackReason, 
                       llm_callback: Optional[Callable] = None,
                       error: Optional[Exception] = None) -> str:
        """
        Maneja un fallback al LLM normal.
        
        Args:
            question: Pregunta original
            reason: Razón del fallback
            llm_callback: Función para generar respuesta con LLM
            error: Excepción original (si aplica)
            
        Returns:
            Respuesta generada
        """
        # Registrar fallback
        self.total_fallbacks += 1
        self.fallbacks_by_reason[reason.value] = \
            self.fallbacks_by_reason.get(reason.value, 0) + 1
        
        # Log del fallback
        question_hash = create_question_hash(question)
        hybrid_logger.log_fallback(
            question_hash=question_hash,
            reason=reason.value,
            original_error=str(error) if error else None
        )
        
        self.logger.info(f"Fallback triggered: {reason.value}")
        
        # Obtener estrategia de fallback configurada
        strategy = config_manager.get_hybrid_fallback_strategy()
        
        if strategy == "llm_normal":
            return self._fallback_llm_normal(question, llm_callback)
        elif strategy == "llm_enhanced":
            return self._fallback_llm_enhanced(question, reason, llm_callback)
        elif strategy == "error_response":
            return self._fallback_error_response(reason)
        else:
            # Estrategia por defecto
            return self._fallback_llm_normal(question, llm_callback)
    
    def _fallback_llm_normal(self, question: str, 
                            llm_callback: Optional[Callable]) -> str:
        """
        Fallback usando LLM normal sin modificaciones.
        
        Args:
            question: Pregunta original
            llm_callback: Callback del LLM
            
        Returns:
            Respuesta del LLM
        """
        if llm_callback:
            try:
                return llm_callback(question)
            except Exception as e:
                self.logger.error(f"LLM callback failed: {e}")
                return self._fallback_error_response(FallbackReason.SYSTEM_ERROR)
        else:
            return self._fallback_error_response(FallbackReason.SYSTEM_ERROR)
    
    def _fallback_llm_enhanced(self, question: str, reason: FallbackReason,
                              llm_callback: Optional[Callable]) -> str:
        """
        Fallback usando LLM con system prompt mejorado.
        
        Args:
            question: Pregunta original
            reason: Razón del fallback
            llm_callback: Callback del LLM
            
        Returns:
            Respuesta del LLM con contexto mejorado
        """
        # TODO: Implementar system prompt mejorado basado en la razón
        # Por ahora, usar LLM normal
        return self._fallback_llm_normal(question, llm_callback)
    
    def _fallback_error_response(self, reason: FallbackReason) -> str:
        """
        Genera una respuesta de error amigable.
        
        Args:
            reason: Razón del error
            
        Returns:
            Respuesta de error con personalidad BMO
        """
        error_responses = {
            FallbackReason.NO_FACTS_FOUND: 
                "No tengo esa información específica en mi base de datos. ¿Puedo ayudarte con algo más?",
            FallbackReason.DATABASE_ERROR:
                "Ups, tuve un problema accediendo a mi base de datos. ¿Puedes intentar de nuevo?",
            FallbackReason.CLASSIFICATION_ERROR:
                "Hmm, no entendí bien la pregunta. ¿Puedes reformularla?",
            FallbackReason.LOW_CONFIDENCE:
                "No estoy muy seguro de esa respuesta. ¿Quieres que intente de otra forma?",
            FallbackReason.SYSTEM_ERROR:
                "Ups, BMO tuvo un pequeño problema. ¿Puedes repetir la pregunta?",
            FallbackReason.DATABASE_UNAVAILABLE:
                "Mi base de datos no está disponible ahora. Intentaré responder de otra forma.",
        }
        
        return error_responses.get(
            reason,
            "Lo siento, no puedo responder eso ahora. ¿Puedo ayudarte con algo más?"
        )
    
    def should_fallback(self, confidence: float, threshold: float) -> bool:
        """
        Determina si debe hacer fallback basado en confianza.
        
        Args:
            confidence: Nivel de confianza de la clasificación
            threshold: Umbral mínimo
            
        Returns:
            True si debe hacer fallback
        """
        return confidence < threshold
    
    def get_stats(self) -> dict:
        """Obtiene estadísticas de fallbacks."""
        return {
            'total_fallbacks': self.total_fallbacks,
            'fallbacks_by_reason': self.fallbacks_by_reason
        }
    
    def reset_stats(self):
        """Resetea las estadísticas de fallbacks."""
        self.total_fallbacks = 0
        self.fallbacks_by_reason.clear()


# Instancia global del manejador de fallback
fallback_handler = FallbackHandler()