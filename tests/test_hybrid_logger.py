"""
Tests unitarios para el sistema de logging híbrido.

Valida que el HybridLogger funcione correctamente y registre
todas las métricas necesarias sin comprometer la privacidad.
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

from src.brain.hybrid_logger import (
    HybridLogger, QuestionType, ResponseSource,
    log_classification, log_response, log_database_op, log_hybrid_error,
    get_hybrid_stats, export_hybrid_metrics
)


class TestHybridLogger:
    """Tests para la clase HybridLogger."""
    
    def setup_method(self):
        """Configuración para cada test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.logger = HybridLogger(log_dir=self.temp_dir, max_metrics_memory=100)
    
    def teardown_method(self):
        """Limpieza después de cada test."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_logger_initialization(self):
        """Test que el logger se inicializa correctamente."""
        assert self.logger.log_dir == self.temp_dir
        assert self.logger.max_metrics_memory == 100
        assert self.logger.logger.name == "BMO.Hybrid"
        
        # Verificar que se crearon los directorios
        assert self.logger.log_dir.exists()
        
        # Verificar que se creó el archivo de log
        log_file = self.temp_dir / "hybrid_system.log"
        assert log_file.exists()
    
    def test_log_classification(self):
        """Test del logging de clasificación de preguntas."""
        # Log una clasificación
        self.logger.log_classification(
            question_type=QuestionType.FLAG_COLORS,
            confidence=0.95,
            processing_time_ms=15.5,
            entities_count=1,
            used_factdb=True,
            pattern_matches=3,
            reasoning="Patrón de bandera detectado"
        )
        
        # Verificar que se guardó en memoria
        assert len(self.logger._classification_metrics) == 1
        metric = self.logger._classification_metrics[0]
        
        assert metric.question_type == QuestionType.FLAG_COLORS
        assert metric.confidence == 0.95
        assert metric.processing_time_ms == 15.5
        assert metric.entities_count == 1
        assert metric.used_factdb == True
        assert metric.pattern_matches == 3
        
        # Verificar contadores
        assert self.logger._counters["classification_flag_colors"] == 1
        assert self.logger._counters["classification_total"] == 1
        assert self.logger._counters["classification_factdb_used"] == 1
        
        # Verificar que se escribió al archivo de métricas
        metrics_file = self.temp_dir / "hybrid_metrics.jsonl"
        assert metrics_file.exists()
        
        with open(metrics_file, 'r', encoding='utf-8') as f:
            line = f.readline().strip()
            data = json.loads(line)
            assert data["type"] == "classification"
            assert data["data"]["question_type"] == "flag_colors"
    
    def test_log_response_generation(self):
        """Test del logging de generación de respuestas."""
        self.logger.log_response_generation(
            source=ResponseSource.FACT_DATABASE,
            processing_time_ms=125.0,
            response_length=85,
            confidence=0.98,
            fact_key_used="bandera-colombia-colores",
            fallback_triggered=False
        )
        
        # Verificar que se guardó en memoria
        assert len(self.logger._response_metrics) == 1
        metric = self.logger._response_metrics[0]
        
        assert metric.source == ResponseSource.FACT_DATABASE
        assert metric.processing_time_ms == 125.0
        assert metric.response_length == 85
        assert metric.confidence == 0.98
        assert metric.fact_key_used == "bandera-colombia-colores"
        assert metric.fallback_triggered == False
        
        # Verificar contadores
        assert self.logger._counters["response_fact_database"] == 1
        assert self.logger._counters["response_total"] == 1
        assert self.logger._counters["response_fallback"] == 0
    
    def test_log_database_operation(self):
        """Test del logging de operaciones de base de datos."""
        self.logger.log_database_operation(
            operation="search",
            processing_time_ms=8.5,
            results_count=2,
            cache_hit=True,
            error_occurred=False,
            details="Búsqueda por clave directa"
        )
        
        # Verificar que se guardó en memoria
        assert len(self.logger._database_metrics) == 1
        metric = self.logger._database_metrics[0]
        
        assert metric.operation == "search"
        assert metric.processing_time_ms == 8.5
        assert metric.results_count == 2
        assert metric.cache_hit == True
        assert metric.error_occurred == False
        
        # Verificar contadores
        assert self.logger._counters["database_search"] == 1
        assert self.logger._counters["database_total"] == 1
        assert self.logger._counters["database_cache_hits"] == 1
        assert self.logger._counters["database_errors"] == 0
    
    def test_log_error(self):
        """Test del logging de errores."""
        self.logger.log_error(
            component="QuestionClassifier",
            error_type="PatternMatchError",
            error_message="No se pudo compilar patrón regex",
            context={"pattern": "invalid[regex", "line": 42}
        )
        
        # Verificar contadores
        assert self.logger._counters["error_QuestionClassifier_PatternMatchError"] == 1
        assert self.logger._counters["error_total"] == 1
    
    def test_performance_snapshot(self):
        """Test del snapshot de rendimiento."""
        # Agregar algunas métricas
        self.logger.log_classification(
            QuestionType.FLAG_COLORS, 0.9, 10.0, used_factdb=True
        )
        self.logger.log_classification(
            QuestionType.CONVERSATIONAL, 0.8, 15.0, used_factdb=False
        )
        self.logger.log_response_generation(
            ResponseSource.FACT_DATABASE, 100.0, 50
        )
        
        snapshot = self.logger.get_performance_snapshot()
        
        assert isinstance(snapshot.timestamp, datetime)
        assert snapshot.avg_classification_time_ms == 12.5  # (10+15)/2
        assert snapshot.avg_response_time_ms == 100.0
        assert snapshot.factdb_hit_rate == 0.5  # 1 de 2 usó factdb
        assert snapshot.memory_usage_mb > 0
    
    def test_usage_stats(self):
        """Test de estadísticas de uso."""
        # Agregar métricas de diferentes tipos
        self.logger.log_classification(
            QuestionType.FLAG_COLORS, 0.9, 10.0, used_factdb=True
        )
        self.logger.log_classification(
            QuestionType.NATURAL_SCIENCES, 0.85, 12.0, used_factdb=True
        )
        self.logger.log_classification(
            QuestionType.CONVERSATIONAL, 0.95, 8.0, used_factdb=False
        )
        
        self.logger.log_response_generation(
            ResponseSource.FACT_DATABASE, 120.0, 60
        )
        self.logger.log_response_generation(
            ResponseSource.LLM_NORMAL, 200.0, 80
        )
        
        stats = self.logger.get_usage_stats(24)
        
        assert stats["total_classifications"] == 3
        assert stats["total_responses"] == 2
        assert stats["question_types"]["flag_colors"] == 1
        assert stats["question_types"]["natural_sciences"] == 1
        assert stats["question_types"]["conversational"] == 1
        assert stats["response_sources"]["fact_database"] == 1
        assert stats["response_sources"]["llm_normal"] == 1
        assert stats["factdb_usage_rate"] == 2/3  # 2 de 3 usaron factdb
        
        # Verificar tiempos promedio
        assert "classification" in stats["average_times_ms"]
        assert "response" in stats["average_times_ms"]
        assert stats["average_times_ms"]["classification"] == 10.0  # (10+12+8)/3
        assert stats["average_times_ms"]["response"] == 160.0  # (120+200)/2
    
    def test_export_metrics(self):
        """Test de exportación de métricas."""
        # Agregar algunas métricas
        self.logger.log_classification(
            QuestionType.FLAG_COLORS, 0.9, 10.0
        )
        self.logger.log_response_generation(
            ResponseSource.FACT_DATABASE, 100.0, 50
        )
        
        # Exportar métricas
        export_file = self.logger.export_metrics()
        
        assert export_file.exists()
        assert export_file.parent == self.temp_dir
        
        # Verificar contenido del archivo
        with open(export_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert "export_timestamp" in data
        assert "counters" in data
        assert "performance_snapshot" in data
        assert "usage_stats_24h" in data
        assert "classification_metrics" in data
        assert "response_metrics" in data
        assert "database_metrics" in data
        
        assert len(data["classification_metrics"]) == 1
        assert len(data["response_metrics"]) == 1
    
    def test_clear_old_metrics(self):
        """Test de limpieza de métricas antiguas."""
        # Agregar métricas con timestamps simulados
        old_time = datetime.now() - timedelta(days=10)
        recent_time = datetime.now()
        
        # Simular métricas antiguas modificando timestamp
        self.logger.log_classification(
            QuestionType.FLAG_COLORS, 0.9, 10.0
        )
        self.logger._classification_metrics[0].timestamp = old_time
        
        # Agregar métrica reciente
        self.logger.log_classification(
            QuestionType.CONVERSATIONAL, 0.8, 15.0
        )
        self.logger._classification_metrics[1].timestamp = recent_time
        
        assert len(self.logger._classification_metrics) == 2
        
        # Limpiar métricas antiguas (mantener últimos 7 días)
        self.logger.clear_old_metrics(days_back=7)
        
        # Solo debe quedar la métrica reciente
        assert len(self.logger._classification_metrics) == 1
        assert self.logger._classification_metrics[0].timestamp == recent_time
    
    def test_privacy_compliance(self):
        """Test que verifica que no se registra información privada."""
        # Log con información que podría ser sensible
        self.logger.log_classification(
            question_type=QuestionType.FLAG_COLORS,
            confidence=0.9,
            processing_time_ms=10.0,
            reasoning="Usuario preguntó sobre bandera de Colombia específicamente"
        )
        
        # Verificar que el reasoning se trunca
        log_file = self.temp_dir / "hybrid_system.log"
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # No debe contener información específica del usuario
        assert "Colombia específicamente" not in content
        assert "Usuario preguntó" in content  # Pero sí el inicio truncado
        
        # Verificar archivo de métricas
        metrics_file = self.temp_dir / "hybrid_metrics.jsonl"
        with open(metrics_file, 'r', encoding='utf-8') as f:
            line = f.readline()
            data = json.loads(line)
        
        # No debe contener el reasoning completo
        assert len(data["data"]["reasoning"]) <= 100


class TestConvenienceFunctions:
    """Tests para las funciones de conveniencia."""
    
    def setup_method(self):
        """Configuración para cada test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Patch del logger global
        self.patcher = patch('src.brain.hybrid_logger.hybrid_logger')
        self.mock_logger = self.patcher.start()
    
    def teardown_method(self):
        """Limpieza después de cada test."""
        self.patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_log_classification_convenience(self):
        """Test de la función de conveniencia para clasificación."""
        log_classification(
            question_type="flag_colors",
            confidence=0.9,
            processing_time_ms=10.0,
            entities_count=1
        )
        
        self.mock_logger.log_classification.assert_called_once()
        args, kwargs = self.mock_logger.log_classification.call_args
        
        assert kwargs["question_type"] == QuestionType.FLAG_COLORS
        assert kwargs["confidence"] == 0.9
        assert kwargs["processing_time_ms"] == 10.0
        assert kwargs["entities_count"] == 1
    
    def test_log_response_convenience(self):
        """Test de la función de conveniencia para respuestas."""
        log_response(
            source="fact_database",
            processing_time_ms=100.0,
            response_length=50,
            confidence=0.95
        )
        
        self.mock_logger.log_response_generation.assert_called_once()
        args, kwargs = self.mock_logger.log_response_generation.call_args
        
        assert kwargs["source"] == ResponseSource.FACT_DATABASE
        assert kwargs["processing_time_ms"] == 100.0
        assert kwargs["response_length"] == 50
        assert kwargs["confidence"] == 0.95
    
    def test_log_database_op_convenience(self):
        """Test de la función de conveniencia para operaciones de BD."""
        log_database_op(
            operation="search",
            processing_time_ms=8.0,
            results_count=2
        )
        
        self.mock_logger.log_database_operation.assert_called_once()
        args, kwargs = self.mock_logger.log_database_operation.call_args
        
        assert kwargs["operation"] == "search"
        assert kwargs["processing_time_ms"] == 8.0
        assert kwargs["results_count"] == 2
    
    def test_log_hybrid_error_convenience(self):
        """Test de la función de conveniencia para errores."""
        log_hybrid_error(
            component="TestComponent",
            error_type="TestError",
            error_message="Test error message"
        )
        
        self.mock_logger.log_error.assert_called_once()
        args, kwargs = self.mock_logger.log_error.call_args
        
        assert kwargs["component"] == "TestComponent"
        assert kwargs["error_type"] == "TestError"
        assert kwargs["error_message"] == "Test error message"
    
    def test_get_hybrid_stats_convenience(self):
        """Test de la función de conveniencia para estadísticas."""
        get_hybrid_stats(hours_back=12)
        
        self.mock_logger.get_usage_stats.assert_called_once_with(12)
    
    def test_export_hybrid_metrics_convenience(self):
        """Test de la función de conveniencia para exportar métricas."""
        test_path = Path("/test/path")
        export_hybrid_metrics(output_file=test_path)
        
        self.mock_logger.export_metrics.assert_called_once_with(test_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])