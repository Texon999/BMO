#!/usr/bin/env python3
"""
Script de prueba para el sistema de verificación de hechos
"""
import sys
import os
from pathlib import Path

# Configurar paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.brain.fact_checker import fact_checker

def test_factual_detection():
    """Prueba la detección de preguntas factuales"""
    print("=== PRUEBA DE DETECCIÓN DE PREGUNTAS FACTUALES ===")
    
    test_questions = [
        "¿Cuáles son los colores de la bandera de Colombia?",
        "¿Cuál es la capital de Francia?",
        "¿Cómo estás hoy?",
        "¿Qué colores tiene la bandera de México?",
        "¿Cuántos habitantes tiene España?",
        "Me gusta la pizza",
        "¿Cuándo se fundó Bogotá?",
    ]
    
    for question in test_questions:
        result = fact_checker.is_factual_question(question)
        if result:
            print(f"✅ FACTUAL: '{question}'")
            print(f"   Tipo: {result['type']}, Entidad: {result['entity']}, Query: {result['query']}")
        else:
            print(f"❌ NO FACTUAL: '{question}'")
        print()

def test_fact_search():
    """Prueba la búsqueda de hechos"""
    print("=== PRUEBA DE BÚSQUEDA DE HECHOS ===")
    
    test_queries = [
        "colores bandera Colombia",
        "capital Francia",
        "población España",
    ]
    
    for query in test_queries:
        print(f"Buscando: '{query}'")
        try:
            result = fact_checker.search_fact(query)
            if result:
                print(f"✅ Encontrado: {result[:100]}...")
            else:
                print("❌ No se encontró información")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()

def test_full_response():
    """Prueba respuestas completas"""
    print("=== PRUEBA DE RESPUESTAS COMPLETAS ===")
    
    test_questions = [
        "¿Cuáles son los colores de la bandera de Colombia?",
        "¿Cuál es la capital de Francia?",
        "¿Hola, cómo estás?",
    ]
    
    for question in test_questions:
        print(f"Pregunta: '{question}'")
        try:
            response = fact_checker.get_factual_response(question)
            if response:
                print(f"✅ Respuesta: {response}")
            else:
                print("❌ No es pregunta factual o no se encontró información")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()

def main():
    print("PROBANDO SISTEMA DE VERIFICACIÓN DE HECHOS")
    print("=" * 50)
    
    try:
        test_factual_detection()
        test_fact_search()
        test_full_response()
        
        print("✅ Todas las pruebas completadas")
        
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        print("Instala duckduckgo-search: pip install duckduckgo-search")
    except Exception as e:
        print(f"❌ Error general: {e}")

if __name__ == "__main__":
    main()