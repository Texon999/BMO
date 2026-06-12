"""
Formateador de Respuestas Factuales con Personalidad BMO.

Este módulo formatea respuestas desde la base de datos de hechos
manteniendo el tono amigable y natural de BMO.
"""

import random
from typing import Optional

from src.brain.models import FactEntry, QuestionType


# Templates de respuestas por categoría
RESPONSE_TEMPLATES = {
    QuestionType.FLAG_COLORS: [
        "{answer}. ¡Son colores muy bonitos!",
        "{answer}. Me gustan esas banderas.",
        "{answer}.",
        "{answer}. ¡Qué interesante!",
    ],
    QuestionType.NATURAL_SCIENCES: [
        "{answer}. ¡La ciencia es genial!",
        "{answer}. ¿No es fascinante?",
        "{answer}.",
        "{answer}. Me encanta aprender sobre esto.",
    ],
    QuestionType.SPECIFIC_GEOGRAPHY: [
        "{answer}. ¡Me gustaría visitar ese lugar!",
        "{answer}.",
        "{answer}. La geografía es interesante.",
        "{answer}. ¿Sabías eso?",
    ],
    QuestionType.HISTORICAL_DATES: [
        "{answer}. ¡La historia es fascinante!",
        "{answer}.",
        "{answer}. Me gusta aprender sobre el pasado.",
        "{answer}. ¿Interesante, verdad?",
    ]
}

# Frases de introducción opcionales
INTRO_PHRASES = [
    "¡Claro! ",
    "¡Por supuesto! ",
    "¡Déjame decirte! ",
    "",  # Sin introducción
    "",
    "",
]

# Frases de cierre opcionales
CLOSING_PHRASES = [
    " ¿Te ayudo con algo más?",
    " ¿Quieres saber algo más?",
    "",  # Sin cierre
    "",
    "",
    "",
]


def format_factual_response(fact: FactEntry, question: str, 
                            add_personality: bool = True) -> str:
    """
    Formatea una respuesta factual con personalidad BMO.
    
    Args:
        fact: Hecho verificado de la base de datos
        question: Pregunta original del usuario
        add_personality: Si agregar frases de personalidad
        
    Returns:
        Respuesta formateada con tono natural
    """
    # Obtener respuesta base
    answer = fact.verified_answer
    
    if not add_personality:
        return answer
    
    # Seleccionar template según categoría
    templates = RESPONSE_TEMPLATES.get(
        fact.category,
        ["{answer}."]  # Template por defecto
    )
    
    template = random.choice(templates)
    
    # Formatear con el template
    formatted = template.format(answer=answer)
    
    # Agregar introducción ocasionalmente (30% de probabilidad)
    if random.random() < 0.3:
        intro = random.choice(INTRO_PHRASES)
        formatted = intro + formatted
    
    # Agregar cierre ocasionalmente (20% de probabilidad)
    if random.random() < 0.2:
        closing = random.choice(CLOSING_PHRASES)
        formatted = formatted + closing
    
    return formatted


def format_error_response(reason: str = "unknown") -> str:
    """
    Formatea una respuesta de error con personalidad BMO.
    
    Args:
        reason: Razón del error
        
    Returns:
        Respuesta de error amigable
    """
    error_responses = [
        "Ups, BMO no puede responder eso ahora. ¿Puedes intentar de otra forma?",
        "Hmm, no tengo esa información específica. ¿Puedo ayudarte con algo más?",
        "Lo siento, no estoy seguro de esa respuesta. ¿Quieres preguntarme otra cosa?",
        "BMO no sabe eso todavía. ¡Pero estoy aprendiendo cada día!",
    ]
    
    return random.choice(error_responses)


def format_fallback_response() -> str:
    """
    Formatea una respuesta de fallback cuando el sistema híbrido falla.
    
    Returns:
        Respuesta de fallback amigable
    """
    fallback_responses = [
        "Déjame pensar en eso de otra manera...",
        "Hmm, voy a intentar responder eso...",
        "Interesante pregunta, déjame ver...",
    ]
    
    return random.choice(fallback_responses)


def should_add_enthusiasm(fact: FactEntry) -> bool:
    """
    Determina si agregar entusiasmo a la respuesta basado en el hecho.
    
    Args:
        fact: Hecho verificado
        
    Returns:
        True si debe agregar entusiasmo
    """
    # Agregar entusiasmo para hechos científicos y geográficos
    enthusiastic_categories = [
        QuestionType.NATURAL_SCIENCES,
        QuestionType.SPECIFIC_GEOGRAPHY
    ]
    
    return fact.category in enthusiastic_categories


def format_confidence_qualifier(confidence: float) -> str:
    """
    Genera un calificador basado en el nivel de confianza.
    
    Args:
        confidence: Nivel de confianza (0.0-1.0)
        
    Returns:
        Calificador de confianza
    """
    if confidence >= 0.95:
        return ""  # Sin calificador, muy confiado
    elif confidence >= 0.85:
        return "Creo que "
    elif confidence >= 0.75:
        return "Si no me equivoco, "
    else:
        return "No estoy completamente seguro, pero "


def blend_responses(factual: str, llm: str, confidence: float) -> str:
    """
    Combina una respuesta factual con información adicional del LLM.
    
    Args:
        factual: Respuesta factual verificada
        llm: Información adicional del LLM
        confidence: Confianza en la respuesta factual
        
    Returns:
        Respuesta combinada
    """
    # Si la confianza es muy alta, priorizar respuesta factual
    if confidence >= 0.9:
        return f"{factual} {llm}"
    
    # Si la confianza es media, mezclar más equilibradamente
    return f"{factual} {llm}"


def format_multiple_facts(facts: list, question: str) -> str:
    """
    Formatea una respuesta cuando hay múltiples hechos relevantes.
    
    Args:
        facts: Lista de hechos relevantes
        question: Pregunta original
        
    Returns:
        Respuesta formateada con múltiples hechos
    """
    if not facts:
        return format_error_response("no_facts")
    
    if len(facts) == 1:
        return format_factual_response(facts[0], question)
    
    # Múltiples hechos: usar el más relevante y mencionar que hay más info
    main_response = format_factual_response(facts[0], question, add_personality=False)
    
    additional_info = " También hay más información relacionada si te interesa."
    
    return main_response + additional_info