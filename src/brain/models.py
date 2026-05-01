"""
Modelos de datos para el Sistema Híbrido de Conocimiento Factual.

Este módulo define las estructuras de datos fundamentales que usa todo el sistema híbrido:
- FactEntry: Modelo principal para hechos verificados
- QuestionType: Categorías de preguntas problemáticas y conversacionales
- ClassificationResult: Resultado de clasificación de preguntas

Todos los modelos incluyen validación automática con Pydantic.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class QuestionType(str, Enum):
    """
    Categorías de preguntas que el sistema puede clasificar.
    
    Las categorías problemáticas son aquellas donde el LLM falla sistemáticamente
    y requieren consulta a la base de datos de hechos.
    """
    # Categorías problemáticas (requieren base de datos de hechos)
    FLAG_COLORS = "flag_colors"
    NATURAL_SCIENCES = "natural_sciences"
    SPECIFIC_GEOGRAPHY = "specific_geography"
    HISTORICAL_DATES = "historical_dates"
    
    # Categorías conversacionales (usan LLM normal)
    CONVERSATIONAL = "conversational"
    ENTERTAINMENT = "entertainment"
    SPORTS = "sports"
    MATHEMATICS = "mathematics"
    ECONOMICS = "economics"


class FactEntry(BaseModel):
    """
    Modelo para almacenar un hecho verificado en la base de datos offline.
    
    Cada FactEntry representa una pieza de información factual crítica
    que ha sido verificada y puede ser usada para responder preguntas
    donde el LLM falla sistemáticamente.
    """
    
    key: str = Field(
        ...,
        description="Identificador único del hecho en formato kebab-case",
        min_length=3,
        max_length=100,
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$"
    )
    
    question_patterns: List[str] = Field(
        ...,
        description="Patrones de preguntas que este hecho puede responder",
        min_items=1,
        max_items=20
    )
    
    verified_answer: str = Field(
        ...,
        description="Respuesta verificada y factualmente correcta",
        min_length=10,
        max_length=500
    )
    
    confidence_level: float = Field(
        ...,
        description="Nivel de confianza en la veracidad del hecho (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    
    category: QuestionType = Field(
        ...,
        description="Categoría de pregunta que este hecho responde"
    )
    
    source: str = Field(
        ...,
        description="Fuente de verificación del hecho",
        min_length=5,
        max_length=200
    )
    
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Fecha de última actualización del hecho"
    )
    
    usage_count: int = Field(
        default=0,
        description="Número de veces que este hecho ha sido usado",
        ge=0
    )
    
    aliases: List[str] = Field(
        default_factory=list,
        description="Nombres alternativos para las entidades en este hecho",
        max_items=10
    )
    
    @validator('question_patterns')
    def validate_question_patterns(cls, v):
        """Valida que los patrones de preguntas no estén vacíos."""
        for pattern in v:
            if not pattern.strip():
                raise ValueError("Los patrones de preguntas no pueden estar vacíos")
            if len(pattern) > 200:
                raise ValueError("Los patrones de preguntas no pueden exceder 200 caracteres")
        return v
    
    @validator('verified_answer')
    def validate_verified_answer(cls, v):
        """Valida que la respuesta verificada tenga contenido útil."""
        if not v.strip():
            raise ValueError("La respuesta verificada no puede estar vacía")
        return v.strip()
    
    @validator('source')
    def validate_source(cls, v):
        """Valida que la fuente sea descriptiva."""
        if not v.strip():
            raise ValueError("La fuente no puede estar vacía")
        return v.strip()
    
    @validator('aliases')
    def validate_aliases(cls, v):
        """Valida que los aliases no estén vacíos y sean únicos."""
        if v:
            # Eliminar aliases vacíos
            v = [alias.strip() for alias in v if alias.strip()]
            # Verificar unicidad (case-insensitive)
            lower_aliases = [alias.lower() for alias in v]
            if len(lower_aliases) != len(set(lower_aliases)):
                raise ValueError("Los aliases deben ser únicos (ignorando mayúsculas)")
        return v
    
    class Config:
        """Configuración del modelo Pydantic."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "key": "bandera-colombia-colores",
                "question_patterns": [
                    "colores de la bandera de colombia",
                    "qué colores tiene la bandera colombiana",
                    "de qué color es la bandera de colombia"
                ],
                "verified_answer": "La bandera de Colombia tiene tres franjas horizontales: amarilla (arriba, doble ancho), azul (medio) y roja (abajo)",
                "confidence_level": 0.95,
                "category": "flag_colors",
                "source": "Constitución Política de Colombia, Artículo 4",
                "last_updated": "2024-01-15T10:30:00",
                "usage_count": 0,
                "aliases": ["colombia", "república de colombia"]
            }
        }


class ClassificationResult(BaseModel):
    """
    Resultado de la clasificación de una pregunta por el QuestionClassifier.
    
    Contiene toda la información necesaria para decidir si usar la base de datos
    de hechos o el LLM normal para generar la respuesta.
    """
    
    question_type: QuestionType = Field(
        ...,
        description="Tipo de pregunta clasificada"
    )
    
    confidence: float = Field(
        ...,
        description="Nivel de confianza en la clasificación (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    
    extracted_entities: List[str] = Field(
        default_factory=list,
        description="Entidades extraídas de la pregunta (países, conceptos, etc.)",
        max_items=20
    )
    
    should_use_factdb: bool = Field(
        ...,
        description="Si debe usar la base de datos de hechos para responder"
    )
    
    reasoning: str = Field(
        ...,
        description="Explicación del proceso de clasificación para debugging",
        min_length=10,
        max_length=500
    )
    
    processing_time_ms: Optional[float] = Field(
        default=None,
        description="Tiempo de procesamiento en milisegundos",
        ge=0.0
    )
    
    @validator('extracted_entities')
    def validate_extracted_entities(cls, v):
        """Valida que las entidades extraídas no estén vacías."""
        if v:
            # Eliminar entidades vacías y duplicadas
            v = list(set([entity.strip().lower() for entity in v if entity.strip()]))
        return v
    
    @validator('reasoning')
    def validate_reasoning(cls, v):
        """Valida que el reasoning tenga contenido útil."""
        if not v.strip():
            raise ValueError("El reasoning no puede estar vacío")
        return v.strip()
    
    class Config:
        """Configuración del modelo Pydantic."""
        json_schema_extra = {
            "example": {
                "question_type": "flag_colors",
                "confidence": 0.92,
                "extracted_entities": ["colombia"],
                "should_use_factdb": True,
                "reasoning": "Patrón de bandera detectado con alta confianza. Entidad 'colombia' extraída.",
                "processing_time_ms": 15.5
            }
        }


class DatabaseStats(BaseModel):
    """
    Estadísticas de la base de datos de hechos para monitoreo y debugging.
    """
    
    total_facts: int = Field(
        ...,
        description="Número total de hechos en la base de datos",
        ge=0
    )
    
    facts_by_category: dict = Field(
        default_factory=dict,
        description="Número de hechos por categoría"
    )
    
    most_used_facts: List[str] = Field(
        default_factory=list,
        description="Keys de los hechos más utilizados",
        max_items=10
    )
    
    last_reload_time: Optional[datetime] = Field(
        default=None,
        description="Última vez que se recargó la base de datos"
    )
    
    database_size_mb: Optional[float] = Field(
        default=None,
        description="Tamaño de la base de datos en MB",
        ge=0.0
    )
    
    class Config:
        """Configuración del modelo Pydantic."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ResponseSource(str, Enum):
    """
    Fuente de una respuesta generada por el sistema híbrido.
    """
    FACT_DATABASE = "fact_database"
    LLM_NORMAL = "llm_normal"
    HYBRID_BLEND = "hybrid_blend"
    FALLBACK_ERROR = "fallback_error"


class Response(BaseModel):
    """
    Respuesta generada por el sistema híbrido con metadatos.
    """
    
    content: str = Field(
        ...,
        description="Contenido de la respuesta",
        min_length=1,
        max_length=1000
    )
    
    source: ResponseSource = Field(
        ...,
        description="Fuente de la respuesta"
    )
    
    confidence: float = Field(
        ...,
        description="Confianza en la respuesta (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    
    processing_time_ms: Optional[float] = Field(
        default=None,
        description="Tiempo de procesamiento en milisegundos",
        ge=0.0
    )
    
    fact_key_used: Optional[str] = Field(
        default=None,
        description="Key del hecho usado (si aplica)"
    )
    
    class Config:
        """Configuración del modelo Pydantic."""
        json_schema_extra = {
            "example": {
                "content": "La bandera de Colombia tiene tres franjas: amarilla arriba, azul en el medio y roja abajo. ¡Son colores muy bonitos!",
                "source": "fact_database",
                "confidence": 0.95,
                "processing_time_ms": 125.5,
                "fact_key_used": "bandera-colombia-colores"
            }
        }


# Constantes útiles para el sistema

PROBLEMATIC_CATEGORIES = [
    QuestionType.FLAG_COLORS,
    QuestionType.NATURAL_SCIENCES,
    QuestionType.SPECIFIC_GEOGRAPHY,
    QuestionType.HISTORICAL_DATES
]

CONVERSATIONAL_CATEGORIES = [
    QuestionType.CONVERSATIONAL,
    QuestionType.ENTERTAINMENT,
    QuestionType.SPORTS,
    QuestionType.MATHEMATICS,
    QuestionType.ECONOMICS
]

# Umbrales por defecto para clasificación
DEFAULT_CLASSIFICATION_THRESHOLDS = {
    QuestionType.FLAG_COLORS: 0.8,
    QuestionType.NATURAL_SCIENCES: 0.75,
    QuestionType.SPECIFIC_GEOGRAPHY: 0.7,
    QuestionType.HISTORICAL_DATES: 0.7,
    QuestionType.CONVERSATIONAL: 0.9,
    QuestionType.ENTERTAINMENT: 0.9,
    QuestionType.SPORTS: 0.9,
    QuestionType.MATHEMATICS: 0.9,
    QuestionType.ECONOMICS: 0.9
}