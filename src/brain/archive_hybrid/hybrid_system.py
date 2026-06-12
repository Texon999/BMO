"""
Sistema Híbrido de Conocimiento Factual - Interfaz Principal.

Este módulo proporciona la interfaz principal para el sistema híbrido,
integrando todos los componentes (clasificador, base de datos, generador).
"""

import logging
from typing import Optional, Callable, Tuple

from src.brain.question_classifier import question_classifier
from src.brain.fact_database import fact_database_manager
from src.brain.hybrid_response_generator import hybrid_response_generator
from src.brain.fallback_handler import fallback_handler, FallbackReason
from src.brain.models import ResponseSource
from src.config.config_manager import config_manager


class HybridSystem:
    """
    Sistema Híbrido de Conocimiento Factual.
    
    Interfaz principal que coordina todos los componentes del sistema híbrido
    para generar respuestas precisas manteniendo la personalidad de BMO.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("BMO.Hybrid")
        
        # Componentes del sistema
        self.classifier = question_classifier
        self.fact_db = fact_database_manager
        self.response_gen = hybrid_response_generator
        self.fallback = fallback_handler
        
        # Estado del sistema
        self.is_enabled = config_manager.is_hybrid_mode_enabled()
        self.is_initialized = False
        
        self.logger.info("HybridSystem created")
    
    def initialize(self) -> bool:
        """
        Inicializa el sistema híbrido.
        
        Returns:
            True si se inicializó correctamente
        """
        try:
            # Verificar que la base de datos esté cargada
            stats = self.fact_db.get_database_stats()
            
            if stats.total_facts == 0:
                self.logger.warning("Fact database is empty, loading...")
                self.fact_db.load_database()
                stats = self.fact_db.get_database_stats()
            
            self.logger.info(
                f"Hybrid system initialized with {stats.total_facts} facts"
            )
            
            self.is_initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize hybrid system: {e}")
            self.is_initialized = False
            return False
    
    def process_question(self, question: str, 
                        llm_callback: Optional[Callable] = None) -> Tuple[str, ResponseSource]:
        """
        Procesa una pregunta usando el sistema híbrido.
        
        Args:
            question: Pregunta del usuario
            llm_callback: Función para generar respuesta con LLM
            
        Returns:
            (respuesta, fuente)
        """
        # Verificar si el sistema está habilitado
        if not self.is_enabled:
            if llm_callback:
                response = llm_callback(question)
                return response, ResponseSource.LLM_NORMAL
            return "Sistema híbrido desactivado.", ResponseSource.FALLBACK_ERROR
        
        # Inicializar si es necesario
        if not self.is_initialized:
            self.initialize()
        
        # Generar respuesta
        try:
            response, source = self.response_gen.generate_response(
                question=question,
                llm_callback=llm_callback
            )
            return response, source
            
        except Exception as e:
            self.logger.error(f"Error processing question: {e}")
            
            # Fallback en caso de error
            response = self.fallback.handle_fallback(
                question=question,
                reason=FallbackReason.SYSTEM_ERROR,
                llm_callback=llm_callback,
                error=e
            )
            return response, ResponseSource.FALLBACK_ERROR
    
    def reload_database(self) -> bool:
        """
        Recarga la base de datos de hechos (hot-reload).
        
        Returns:
            True si se recargó correctamente
        """
        try:
            success = self.fact_db.reload_database()
            
            if success:
                stats = self.fact_db.get_database_stats()
                self.logger.info(f"Database reloaded: {stats.total_facts} facts")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to reload database: {e}")
            return False
    
    def enable(self):
        """Habilita el sistema híbrido."""
        self.is_enabled = True
        config_manager.set_hybrid_mode(True)
        self.logger.info("Hybrid system enabled")
    
    def disable(self):
        """Deshabilita el sistema híbrido."""
        self.is_enabled = False
        config_manager.set_hybrid_mode(False)
        self.logger.info("Hybrid system disabled")
    
    def get_system_stats(self) -> dict:
        """
        Obtiene estadísticas completas del sistema híbrido.
        
        Returns:
            Diccionario con estadísticas de todos los componentes
        """
        return {
            'enabled': self.is_enabled,
            'initialized': self.is_initialized,
            'database': self.fact_db.get_database_stats().dict(),
            'classifier': self.classifier.get_stats(),
            'response_generator': self.response_gen.get_stats(),
            'fallback': self.fallback.get_stats()
        }
    
    def classify_question(self, question: str) -> dict:
        """
        Clasifica una pregunta sin generar respuesta.
        
        Args:
            question: Pregunta a clasificar
            
        Returns:
            Resultado de clasificación como diccionario
        """
        result = self.classifier.classify_question(question)
        return result.dict()
    
    def search_facts(self, query: str, category: Optional[str] = None) -> list:
        """
        Busca hechos en la base de datos.
        
        Args:
            query: Query de búsqueda
            category: Categoría opcional
            
        Returns:
            Lista de hechos encontrados
        """
        from src.brain.models import QuestionType
        
        cat = QuestionType(category) if category else None
        facts = self.fact_db.search_facts(query=query, category=cat)
        
        return [fact.dict() for fact in facts]
    
    def get_fact(self, key: str) -> Optional[dict]:
        """
        Obtiene un hecho específico por su clave.
        
        Args:
            key: Clave del hecho
            
        Returns:
            Hecho como diccionario o None
        """
        fact = self.fact_db.get_fact(key)
        return fact.dict() if fact else None


# Instancia global del sistema híbrido
hybrid_system = HybridSystem()