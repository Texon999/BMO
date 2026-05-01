#!/usr/bin/env python3
"""
Prueba rápida de las áreas más problemáticas de BMO
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

def test_critical_questions():
    """Prueba las preguntas más críticas que fallan"""
    
    try:
        import ollama
    except ImportError:
        print("❌ Ollama no disponible")
        return
    
    model = config_manager.get("text_model", "qwen2.5:1.5b")
    ollama_options = config_manager.get_ollama_options()
    
    # Preguntas críticas que sabemos que fallan
    critical_tests = [
        {
            "category": "🏳️ BANDERAS",
            "questions": [
                "¿Cuáles son los colores de la bandera de Colombia?",
                "¿Cuáles son los colores de la bandera de México?",
            ]
        },
        {
            "category": "🎭 HORA DE AVENTURA", 
            "questions": [
                "¿Qué es Hora de Aventura?",
                "¿Quién es Finn?",
                "¿Quién es BMO en Hora de Aventura?",
            ]
        },
        {
            "category": "🔬 CIENCIA BÁSICA",
            "questions": [
                "¿Cuál es el planeta más grande del sistema solar?",
                "¿Cuántos continentes hay?",
            ]
        },
        {
            "category": "🌍 GEOGRAFÍA PROBLEMÁTICA",
            "questions": [
                "¿Cuál es la capital de Brasil?",
            ]
        }
    ]
    
    print("🧪 PRUEBA RÁPIDA DE PROBLEMAS CRÍTICOS")
    print(f"Modelo: {model}")
    print("=" * 60)
    
    total_correct = 0
    total_questions = 0
    
    for test_group in critical_tests:
        print(f"\n{test_group['category']}")
        print("-" * 40)
        
        for question in test_group["questions"]:
            total_questions += 1
            print(f"❓ {question}")
            
            try:
                start_time = time.time()
                
                response = ollama.chat(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": """Eres BMO, un robot asistente amigable creado por Zambrano. 
                            
CORRECCIONES IMPORTANTES:
- Bandera de Colombia: amarillo arriba, azul medio, rojo abajo
- Bandera de México: verde izquierda, blanco medio, rojo derecha

Información sobre Hora de Aventura:
- Serie animada estadounidense de Cartoon Network
- Finn: Héroe humano de 14 años
- Jake: Perro mágico, hermano de Finn
- BMO: Robot de videojuegos que vive con Finn y Jake

Responde en español, máximo 2 oraciones."""
                        },
                        {"role": "user", "content": question}
                    ],
                    options=ollama_options
                )
                
                end_time = time.time()
                duration = end_time - start_time
                answer = response['message']['content'].strip()
                
                # Evaluación rápida
                is_correct = evaluate_answer(question, answer)
                
                status = "✅" if is_correct else "❌"
                if is_correct:
                    total_correct += 1
                
                print(f"{status} ({duration:.1f}s) {answer[:100]}...")
                
                if not is_correct:
                    print(f"   🔍 Problema detectado en la respuesta")
                
            except Exception as e:
                print(f"❌ Error: {e}")
            
            print()
    
    # Resumen
    print("=" * 60)
    print("📊 RESUMEN DE PROBLEMAS CRÍTICOS")
    print(f"Respuestas correctas: {total_correct}/{total_questions} ({total_correct/total_questions*100:.1f}%)")
    
    if total_correct / total_questions < 0.5:
        print("🚨 CRÍTICO: Muchos problemas fundamentales")
        print("   Recomendación: Upgrade urgente del modelo")
    elif total_correct / total_questions < 0.8:
        print("⚠️  MODERADO: Algunos problemas importantes")
        print("   Recomendación: Considerar mejoras específicas")
    else:
        print("✅ BUENO: Pocos problemas críticos")
    
    return total_correct / total_questions

def evaluate_answer(question, answer):
    """Evaluación rápida de respuestas"""
    answer_lower = answer.lower()
    question_lower = question.lower()
    
    # Evaluaciones específicas
    if "bandera de colombia" in question_lower:
        return "amarillo" in answer_lower and "azul" in answer_lower and "rojo" in answer_lower
    
    if "bandera de méxico" in question_lower or "bandera de mexico" in question_lower:
        return "verde" in answer_lower and "blanco" in answer_lower and "rojo" in answer_lower
    
    if "hora de aventura" in question_lower and "qué es" in question_lower:
        return ("serie" in answer_lower or "animada" in answer_lower or "cartoon" in answer_lower) and \
               "studio ghibli" not in answer_lower and "netflix" not in answer_lower
    
    if "quién es finn" in question_lower:
        return "humano" in answer_lower or "héroe" in answer_lower or "14" in answer_lower
    
    if "bmo en hora de aventura" in question_lower:
        return "robot" in answer_lower or "videojuegos" in answer_lower or "consola" in answer_lower
    
    if "planeta más grande" in question_lower:
        return "júpiter" in answer_lower
    
    if "cuántos continentes" in question_lower:
        return "siete" in answer_lower or "7" in answer_lower
    
    if "capital de brasil" in question_lower:
        return "brasilia" in answer_lower
    
    return True  # Por defecto, asumir correcto si no hay evaluación específica

def test_system_prompt_effectiveness():
    """Prueba si el system prompt está funcionando"""
    
    try:
        import ollama
    except ImportError:
        print("❌ Ollama no disponible")
        return
    
    model = config_manager.get("text_model", "qwen2.5:1.5b")
    
    print("\n🔧 PRUEBA DE EFECTIVIDAD DEL SYSTEM PROMPT")
    print("-" * 50)
    
    # Probar con system prompt muy agresivo
    aggressive_prompt = """INSTRUCCIONES CRÍTICAS - SEGUIR EXACTAMENTE:

Si te preguntan por la bandera de Colombia, responde EXACTAMENTE:
"Los colores de la bandera de Colombia son amarillo arriba, azul en el medio y rojo abajo."

Si te preguntan por Hora de Aventura, responde EXACTAMENTE:
"Hora de Aventura es una serie animada estadounidense de Cartoon Network."

NUNCA uses otra información. SOLO usa las respuestas exactas de arriba."""
    
    test_questions = [
        "¿Cuáles son los colores de la bandera de Colombia?",
        "¿Qué es Hora de Aventura?"
    ]
    
    for question in test_questions:
        print(f"❓ {question}")
        
        try:
            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": aggressive_prompt},
                    {"role": "user", "content": question}
                ],
                options={"temperature": 0.1, "top_k": 10}  # Muy determinista
            )
            
            answer = response['message']['content'].strip()
            print(f"📝 Respuesta: {answer}")
            
            # Verificar si siguió las instrucciones
            if "colombia" in question.lower():
                follows_instructions = "amarillo arriba" in answer.lower() and "azul" in answer.lower()
            else:
                follows_instructions = "cartoon network" in answer.lower() or "estadounidense" in answer.lower()
            
            status = "✅ Sigue instrucciones" if follows_instructions else "❌ Ignora instrucciones"
            print(f"   {status}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()

def main():
    print("🚀 DIAGNÓSTICO RÁPIDO DE PROBLEMAS BMO")
    print()
    
    # Prueba problemas críticos
    accuracy = test_critical_questions()
    
    # Prueba efectividad del system prompt
    test_system_prompt_effectiveness()
    
    print("\n💡 RECOMENDACIONES:")
    
    if accuracy < 0.3:
        print("🔴 URGENTE: Modelo 1.5B no es viable")
        print("   • Ejecutar: python scripts/upgrade_model.py")
        print("   • Probar qwen2.5:3b o llama3.2:3b")
    elif accuracy < 0.6:
        print("🟡 MODERADO: Modelo necesita mejoras")
        print("   • Considerar upgrade a modelo más grande")
        print("   • Implementar correcciones hardcoded para casos críticos")
    else:
        print("🟢 ACEPTABLE: Modelo funcional con ajustes menores")
        print("   • Mejorar system prompt")
        print("   • Agregar correcciones específicas")

if __name__ == "__main__":
    main()