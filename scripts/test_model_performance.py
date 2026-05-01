#!/usr/bin/env python3
"""
Script para probar el rendimiento del modelo actual de BMO
"""
import sys
import os
import time
from pathlib import Path

# Configurar paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.config.config_manager import config_manager

def test_model_knowledge():
    """Prueba el conocimiento factual del modelo actual"""
    
    try:
        import ollama
    except ImportError:
        print("❌ Ollama no está instalado")
        return
    
    model = config_manager.get("text_model", "qwen2.5:1.5b")
    ollama_options = config_manager.get_ollama_options()
    
    print(f"=== PRUEBA DE CONOCIMIENTO: {model} ===")
    print(f"Parámetros: {ollama_options}")
    print()
    
    # Preguntas de prueba
    test_questions = [
        "¿Cuáles son los colores de la bandera de Colombia?",
        "¿Cuál es la capital de Francia?",
        "¿Cuál es la capital de España?",
        "¿Cuántos continentes hay?",
        "¿En qué año llegó el hombre a la luna?",
        "¿Cuáles son los colores de la bandera de México?",
        "¿Cuál es el río más largo del mundo?",
        "¿Quién escribió Don Quijote?",
    ]
    
    # Respuestas esperadas (para evaluación)
    expected_keywords = [
        ["amarillo", "azul", "rojo"],  # Colombia
        ["parís"],                     # Francia
        ["madrid"],                    # España
        ["siete", "7"],               # Continentes
        ["1969"],                     # Luna
        ["verde", "blanco", "rojo"],  # México
        ["nilo", "amazonas"],         # Río más largo
        ["cervantes"],                # Don Quijote
    ]
    
    results = []
    total_time = 0
    
    for i, question in enumerate(test_questions):
        print(f"Pregunta {i+1}: {question}")
        
        try:
            start_time = time.time()
            
            response = ollama.chat(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres BMO. Responde en español de forma precisa y concisa."
                    },
                    {"role": "user", "content": question}
                ],
                options=ollama_options
            )
            
            end_time = time.time()
            duration = end_time - start_time
            total_time += duration
            
            answer = response['message']['content'].strip()
            
            # Evaluar respuesta
            expected = expected_keywords[i]
            answer_lower = answer.lower()
            
            correct = any(keyword in answer_lower for keyword in expected)
            
            status = "✅" if correct else "❌"
            print(f"{status} Respuesta ({duration:.1f}s): {answer}")
            
            results.append({
                'question': question,
                'answer': answer,
                'duration': duration,
                'correct': correct,
                'expected': expected
            })
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                'question': question,
                'answer': f"ERROR: {e}",
                'duration': 0,
                'correct': False,
                'expected': expected_keywords[i]
            })
        
        print()
    
    # Resumen de resultados
    print("=" * 60)
    print("RESUMEN DE RESULTADOS")
    print("=" * 60)
    
    correct_count = sum(1 for r in results if r['correct'])
    total_questions = len(results)
    avg_time = total_time / total_questions if total_questions > 0 else 0
    
    print(f"Modelo: {model}")
    print(f"Preguntas correctas: {correct_count}/{total_questions} ({correct_count/total_questions*100:.1f}%)")
    print(f"Tiempo promedio: {avg_time:.1f} segundos")
    print(f"Tiempo total: {total_time:.1f} segundos")
    
    # Detalles de respuestas incorrectas
    incorrect = [r for r in results if not r['correct']]
    if incorrect:
        print(f"\n❌ RESPUESTAS INCORRECTAS ({len(incorrect)}):")
        for r in incorrect:
            print(f"  • {r['question']}")
            print(f"    Respuesta: {r['answer'][:100]}...")
            print(f"    Esperaba: {', '.join(r['expected'])}")
            print()
    
    # Recomendaciones
    print("RECOMENDACIONES:")
    
    if correct_count / total_questions < 0.6:
        print("❌ Precisión baja - Considera actualizar a un modelo más grande")
        print("   Ejecuta: python scripts/upgrade_model.py")
    elif correct_count / total_questions < 0.8:
        print("⚠️  Precisión moderada - Modelo funcional pero mejorable")
    else:
        print("✅ Precisión buena - Modelo funcionando correctamente")
    
    if avg_time > 10:
        print("⚠️  Velocidad lenta - Considera optimizar parámetros")
    elif avg_time > 6:
        print("⚠️  Velocidad aceptable pero mejorable")
    else:
        print("✅ Velocidad buena")
    
    return results

def test_conversation_flow():
    """Prueba el flujo conversacional"""
    
    try:
        import ollama
    except ImportError:
        print("❌ Ollama no está instalado")
        return
    
    model = config_manager.get("text_model", "qwen2.5:1.5b")
    ollama_options = config_manager.get_ollama_options()
    
    print(f"=== PRUEBA CONVERSACIONAL: {model} ===")
    
    conversation = [
        "Hola BMO, ¿cómo estás?",
        "¿Me puedes ayudar con algo?",
        "¿Qué sabes sobre Hora de Aventura?",
        "Gracias, eres muy útil"
    ]
    
    messages = [
        {
            "role": "system",
            "content": "Eres BMO, un robot asistente amigable. Responde en español de forma natural."
        }
    ]
    
    for user_msg in conversation:
        print(f"Usuario: {user_msg}")
        
        messages.append({"role": "user", "content": user_msg})
        
        try:
            start_time = time.time()
            
            response = ollama.chat(
                model=model,
                messages=messages,
                options=ollama_options
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            answer = response['message']['content'].strip()
            messages.append({"role": "assistant", "content": answer})
            
            print(f"BMO ({duration:.1f}s): {answer}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()

def main():
    print("PRUEBA DE RENDIMIENTO DE BMO")
    print("=" * 50)
    
    # Mostrar configuración actual
    model = config_manager.get("text_model", "qwen2.5:1.5b")
    print(f"Modelo actual: {model}")
    
    config_summary = config_manager.get_config_summary()
    print(f"Temperatura: {config_summary.get('llm_temperature', 'N/A')}")
    print(f"Memoria habilitada: {config_summary.get('chat_memory', 'N/A')}")
    print()
    
    # Ejecutar pruebas
    try:
        print("1. PRUEBA DE CONOCIMIENTO FACTUAL")
        print("-" * 40)
        knowledge_results = test_model_knowledge()
        
        print("\n2. PRUEBA DE CONVERSACIÓN")
        print("-" * 40)
        test_conversation_flow()
        
        print("\n🎉 Pruebas completadas")
        
    except KeyboardInterrupt:
        print("\n❌ Pruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n❌ Error durante las pruebas: {e}")

if __name__ == "__main__":
    main()