"""
Sistema de Logging Específico para el Sistema Híbrido de Conocimiento Factual.

Este módulo proporciona logging especializado para monitorear el rendimiento,
debuggear problemas de clasificación y recopilar métricas de uso del sistema híbrido.

Características:
- Logger separado para componentes híbridos
- Métricas de rendimiento y uso
- Logging de decisiones de clasificación
- Protección de privacidad (sin contenido de conversaciones)
- Rotación automática de logs
"""

import logging
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from collections import defaultdict, deque
from threading import Lock

from src.brain.models import QuestionType, ResponseSource, ClassificationResult


class HybridMetrics:
    """
    Recopilador de métricas del sistema híbrido.
    
    Mantiene estadísticas de uso, rendimiento y precisión sin almacenar
    contenido sensible de conversaciones.
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.lock = Lock()
        
        # Contadores generales
        self.total_questions = 0
        self.questions_by_category = defaultdict(int)
        self.responses_by_source = defaultdict(int)
        
        # Métricas de rendimiento
        self.classification_times = deque(maxlen=max_history)
        self.response_times = deque(maxlen=max_history)
        
        # Métricas de precisión (basadas en confianza)
        self.classification_confidences = defaultdict(list)
        self.response_confidences = defaultdict(list)
        
        # Uso de base de datos de hechos
        self.fact_usage = defaultdict(int)
        self.fallback_reasons = defaultdict(int)
        
        # Historial de sesión
        self.session_start = datetime.now()
        self.last_reset = datetime.now()
        
        # Cache de estadísticas calculadas
        self._stats_cache = {}
        self._cache_expiry = None
        self._cache_duration = timedelta(seconds=30)
    
    def record_classification(self, result: ClassificationResult, processing_time_ms: float):
        """Registra una clasificación de pregunta."""
        with self.lock:
            self.total_questions += 1
            self.questions_by_category[result.question_type.value] += 1
            self.classification_times.append(processing_time_ms)
            self.classification_confidences[result.question_type.value].append(result.confidence)
            
            # Limpiar cache
            self._invalidate_cache()
    
    def record_response(self, source: ResponseSource, confidence: float, 
                       processing_time_ms: float, fact_key: Optional[str] = None):
        """Registra una respuesta generada."""
        with self.lock:
            self.responses_by_source[source.value] += 1
            self.response_times.append(processing_time_ms)
            self.response_confidences[source.value].append(confidence)
            
            if fact_key:
                self.fact_usage[fact_key] += 1
            
            # Limpiar cache
            self._invalidate_cache()
    
    def record_fallback(self, reason: str):
        """Registra un fallback al LLM normal."""
        with self.lock:
            self.fallback_reasons[reason] += 1
            self._invalidate_cache()
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas completas del sistema."""
        with self.lock:
            # Verificar cache
            if (self._cache_expiry and datetime.now() < self._cache_expiry and 
                self._stats_cache):
                return self._stats_cache.copy()
            
            # Calcular estadísticas
            stats = {
                "session": {
                    "start_time": self.session_start.isoformat(),
                    "duration_minutes": (datetime.now() - self.session_start).total_seconds() / 60,
                    "last_reset": self.last_reset.isoformat()
                },
                "usage": {
                    "total_questions": self.total_questions,
                    "questions_by_category": dict(self.questions_by_category),
                    "responses_by_source": dict(self.responses_by_source),
                    "fallback_reasons": dict(self.fallback_reasons)
                },
                "performance": {
                    "classification": self._calculate_time_stats(self.classification_times),
                    "response": self._calculate_time_stats(self.response_times)
                },
                "confidence": {
                    "by_category": {
                        category: self._calculate_confidence_stats(confidences)
                        for category, confidences in self.classification_confidences.items()
                    },
                    "by_source": {
                        source: self._calculate_confidence_stats(confidences)
                        for source, confidences in self.response_confidences.items()
                    }
                },
                "fact_database": {
                    "most_used_facts": sorted(
                        self.fact_usage.items(), 
                        key=lambda x: x[1], 
                        reverse=True
                    )[:10],
                    "total_fact_uses": sum(self.fact_usage.values())
                }
            }
            
            # Actualizar cache
            self._stats_cache = stats
            self._cache_expiry = datetime.now() + self._cache_duration
            
            return stats.copy()
    
    def _calculate_time_stats(self, times: deque) -> Dict[str, float]:
        """Calcula estadísticas de tiempo."""
        if not times:
            return {"count": 0, "avg_ms": 0.0, "min_ms": 0.0, "max_ms": 0.0}
        
        times_list = list(times)
        return {
            "count": len(times_list),
            "avg_ms": sum(times_list) / len(times_list),
            "min_ms": min(times_list),
            "max_ms": max(times_list),
            "p95_ms": sorted(times_list)[int(len(times_list) * 0.95)] if len(times_list) > 1 else times_list[0]
        }
    
    def _calculate_confidence_stats(self, confidences: List[float]) -> Dict[str, float]:
        """Calcula estadísticas de confianza."""
        if not confidences:
            return {"count": 0, "avg": 0.0, "min": 0.0, "max": 0.0}
        
        return {
            "count": len(confidences),
            "avg": sum(confidences) / len(confidences),
            "min": min(confidences),
            "max": max(confidences)
        }
    
    def _invalidate_cache(self):
        """Invalida el cache de estadísticas."""
        self._cache_expiry = None
        self._stats_cache = {}
    
    def reset_stats(self):
        """Resetea todas las estadísticas."""
        with self.lock:
            self.total_questions = 0
            self.questions_by_category.clear()
            self.responses_by_source.clear()
            self.classification_times.clear()
            self.response_times.clear()
            self.classification_confidences.clear()
            self.response_confidences.clear()
            self.fact_usage.clear()
            self.fallback_reasons.clear()
            self.last_reset = datetime.now()
            self._invalidate_cache()


class HybridLogger:
    """
    Logger especializado para el Sistema Híbrido de Conocimiento Factual.
    
    Proporciona logging estructurado con métricas integradas y protección de privacidad.
    """
    
    def __init__(self, log_dir: str = "logs", max_log_files: int = 10):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Configurar logger principal
        self.logger = logging.getLogger("BMO.Hybrid")
        self.logger.setLevel(logging.INFO)
        
        # Evitar duplicar handlers
        if not self.logger.handlers:
            self._setup_handlers(max_log_files)
        
        # Métricas integradas
        self.metrics = HybridMetrics()
        
        # Logger de decisiones (más detallado)
        self.decision_logger = logging.getLogger("BMO.Hybrid.Decisions")
        self.decision_logger.setLevel(logging.DEBUG)
        
        if not self.decision_logger.handlers:
            self._setup_decision_handler()
    
    def _setup_handlers(self, max_log_files: int):
        """Configura los handlers de logging."""
        # Handler para archivo con rotación
        from logging.handlers import RotatingFileHandler
        
        file_handler = RotatingFileHandler(
            self.log_dir / "hybrid_system.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=max_log_files
        )
        file_handler.setLevel(logging.INFO)
        
        # Handler para consola (solo errores)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Formato estructurado
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def _setup_decision_handler(self):
        """Configura handler específico para decisiones de clasificación."""
        from logging.handlers import RotatingFileHandler
        
        decision_handler = RotatingFileHandler(
            self.log_dir / "hybrid_decisions.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5
        )
        decision_handler.setLevel(logging.DEBUG)
        
        # Formato JSON para decisiones
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "component": record.name,
                    "message": record.getMessage()
                }
                
                # Agregar datos extra si existen
                if hasattr(record, 'extra_data'):
                    log_entry.update(record.extra_data)
                
                return json.dumps(log_entry, ensure_ascii=False)
        
        decision_handler.setFormatter(JSONFormatter())
        self.decision_logger.addHandler(decision_handler)
    
    def log_classification(self, question_hash: str, result: ClassificationResult, 
                          processing_time_ms: float):
        """
        Registra una decisión de clasificación.
        
        Args:
            question_hash: Hash de la pregunta (para privacidad)
            result: Resultado de la clasificación
            processing_time_ms: Tiempo de procesamiento
        """
        # Registrar métricas
        self.metrics.record_classification(result, processing_time_ms)
        
        # Log estructurado de la decisión
        extra_data = {
            "question_hash": question_hash,
            "question_type": result.question_type.value,
            "confidence": result.confidence,
            "should_use_factdb": result.should_use_factdb,
            "entities_count": len(result.extracted_entities),
            "processing_time_ms": processing_time_ms,
            "reasoning": result.reasoning
        }
        
        self.decision_logger.info(
            f"Classification: {result.question_type.value} (confidence: {result.confidence:.2f})",
            extra={"extra_data": extra_data}
        )
        
        # Log general
        self.logger.info(
            f"Question classified as {result.question_type.value} "
            f"(confidence: {result.confidence:.2f}, time: {processing_time_ms:.1f}ms)"
        )
    
    def log_response_generation(self, question_hash: str, source: ResponseSource, 
                               confidence: float, processing_time_ms: float,
                               fact_key: Optional[str] = None):
        """
        Registra la generación de una respuesta.
        
        Args:
            question_hash: Hash de la pregunta
            source: Fuente de la respuesta
            confidence: Confianza en la respuesta
            processing_time_ms: Tiempo de procesamiento
            fact_key: Key del hecho usado (si aplica)
        """
        # Registrar métricas
        self.metrics.record_response(source, confidence, processing_time_ms, fact_key)
        
        # Log estructurado
        extra_data = {
            "question_hash": question_hash,
            "response_source": source.value,
            "confidence": confidence,
            "processing_time_ms": processing_time_ms,
            "fact_key_used": fact_key
        }
        
        self.decision_logger.info(
            f"Response generated from {source.value} (confidence: {confidence:.2f})",
            extra={"extra_data": extra_data}
        )
        
        # Log general
        source_desc = f" using fact '{fact_key}'" if fact_key else ""
        self.logger.info(
            f"Response generated from {source.value}{source_desc} "
            f"(confidence: {confidence:.2f}, time: {processing_time_ms:.1f}ms)"
        )
    
    def log_fallback(self, question_hash: str, reason: str, original_error: Optional[str] = None):
        """
        Registra un fallback al LLM normal.
        
        Args:
            question_hash: Hash de la pregunta
            reason: Razón del fallback
            original_error: Error original (si aplica)
        """
        # Registrar métricas
        self.metrics.record_fallback(reason)
        
        # Log estructurado
        extra_data = {
            "question_hash": question_hash,
            "fallback_reason": reason,
            "original_error": original_error
        }
        
        self.decision_logger.warning(
            f"Fallback to LLM: {reason}",
            extra={"extra_data": extra_data}
        )
        
        # Log general
        error_desc = f" (error: {original_error})" if original_error else ""
        self.logger.warning(f"Fallback to LLM normal: {reason}{error_desc}")
    
    def log_database_operation(self, operation: str, details: Dict[str, Any]):
        """
        Registra operaciones de la base de datos de hechos.
        
        Args:
            operation: Tipo de operación (load, reload, search, etc.)
            details: Detalles de la operación
        """
        self.logger.info(f"Database operation: {operation} - {details}")
    
    def log_performance_warning(self, component: str, metric: str, value: float, threshold: float):
        """
        Registra advertencias de rendimiento.
        
        Args:
            component: Componente que genera la advertencia
            metric: Métrica que excede el umbral
            value: Valor actual
            threshold: Umbral excedido
        """
        self.logger.warning(
            f"Performance warning in {component}: {metric} = {value:.2f} "
            f"(threshold: {threshold:.2f})"
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtiene las métricas actuales del sistema."""
        return self.metrics.get_stats()
    
    def reset_metrics(self):
        """Resetea las métricas del sistema."""
        self.metrics.reset_stats()
        self.logger.info("Hybrid system metrics reset")
    
    def export_metrics(self, filepath: Optional[str] = None) -> str:
        """
        Exporta las métricas a un archivo JSON.
        
        Args:
            filepath: Ruta del archivo (opcional)
            
        Returns:
            Ruta del archivo exportado
        """
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self.log_dir / f"hybrid_metrics_{timestamp}.json"
        
        metrics = self.get_metrics()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Metrics exported to {filepath}")
        return str(filepath)


# Instancia global del logger híbrido
hybrid_logger = HybridLogger()


# Funciones de conveniencia para uso directo
def log_classification(question_hash: str, result: ClassificationResult, processing_time_ms: float):
    """Función de conveniencia para logging de clasificación."""
    hybrid_logger.log_classification(question_hash, result, processing_time_ms)


def log_response(question_hash: str, source: ResponseSource, confidence: float, 
                processing_time_ms: float, fact_key: Optional[str] = None):
    """Función de conveniencia para logging de respuestas."""
    hybrid_logger.log_response_generation(question_hash, source, confidence, 
                                        processing_time_ms, fact_key)


def log_fallback(question_hash: str, reason: str, original_error: Optional[str] = None):
    """Función de conveniencia para logging de fallbacks."""
    hybrid_logger.log_fallback(question_hash, reason, original_error)


def get_hybrid_metrics() -> Dict[str, Any]:
    """Función de conveniencia para obtener métricas."""
    return hybrid_logger.get_metrics()


def create_question_hash(question: str) -> str:
    """
    Crea un hash de la pregunta para logging sin comprometer privacidad.
    
    Args:
        question: Pregunta original
        
    Returns:
        Hash SHA-256 truncado de la pregunta
    """
    import hashlib
    
    # Normalizar pregunta
    normalized = question.lower().strip()
    
    # Crear hash
    hash_obj = hashlib.sha256(normalized.encode('utf-8'))
    
    # Retornar hash truncado (primeros 16 caracteres)
    return hash_obj.hexdigest()[:16]