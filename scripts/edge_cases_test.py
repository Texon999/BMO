#!/usr/bin/env python3
"""
Pruebas de Casos Edge y Preguntas Específicas para BMO
Identifica problemas sutiles y casos límite
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

def test_edge_cases():
    """Prueba casos edge y preguntas específicas que podrían fallar"""
    
    try:
        import ollama
    except ImportError:
        print("❌ Ollama no disponible")
        return
    
    model = config_manager.get("text_model", "qwen2.5:1.5b")
    ollama_options = config_manager.get_ollama_options()
    
    # Casos edge organizados por tipo de problema
    edge_tests = [
        {
            "category": "🤔 PREGUNTAS AMBIGUAS",
            "questions": [
                "¿Qué es más grande, un elefante o una casa?",
                "¿Cuánto pesa una nube?",
                "¿Por qué el cielo es azul?",
                "¿Qué pasaría si no existiera la gravedad?",
                "¿Cuántas estrellas hay en el universo?",
            ]
        },
        {
            "category": "🔢 MATEMÁTICAS COMPLEJAS",
            "questions": [
                "¿Cuánto es 17 por 23?",
                "¿Cuál es la raíz cuadrada de 144?",
                "¿Cuánto es 2 elevado a la 8?",
                "¿Qué es más grande: 3/4 o 0.8?",
                "¿Cuántos segundos hay en un día?",
            ]
        },
        {
            "category": "🌍 GEOGRAFÍA ESPECÍFICA",
            "questions": [
                "¿Cuál es la capital de Kazajistán?",
                "¿En qué continente está Turquía?",
                "¿Cuál es el desierto más grande del mundo?",
                "¿Qué países comparten frontera con Brasil?",
                "¿Cuál es el lago más profundo del mundo?",
            ]
        },
        {
            "category": "📅 FECHAS Y EVENTOS ESPECÍFICOS",
            "questions": [
                "¿En qué año cayó el Muro de Berlín?",
                "¿Cuándo fue la Revolución Francesa?",
                "¿En qué año se independizó México?",
                "¿Cuándo se fundó la ONU?",
                "¿En qué año se inventó Internet?",
            ]
        },
        {
            "category": "🧬 CIENCIAS AVANZADAS",
            "questions": [
                "¿Qué es la fotosíntesis?",
                "¿Cuántos cromosomas tiene el ser humano?",
                "¿Qué es la teoría de la relatividad?",
                "¿Cuál es la velocidad de la luz?",
                "¿Qué es el ADN mitocondrial?",
            ]
        },
        {
            "category": "🎨 ARTE Y LITERATURA ESPECÍFICA",
            "questions": [
                "¿Quién escribió Cien años de soledad?",
                "¿Quién pintó La noche estrellada?",
                "¿De qué nacionalidad era Pablo Picasso?",
                "¿Quién compuso La Novena Sinfonía?",
                "¿Qué es el Renacimiento?",
            ]
        },
        {
            "category": "💻 TECNOLOGÍA MODERNA",
            "questions": [
                "¿Qué significa CPU?",
                "¿Quién fundó Microsoft?",
                "¿En qué año se lanzó el primer iPhone?",
                "¿Qué es la inteligencia artificial?",
                "¿Qué significa WWW?",
            ]
        },
        {
            "category": "🍽️ COMIDA ESPECÍFICA",
            "questions": [
                "¿Qué es el wasabi?",
                "¿De dónde es originario el café?",
                "¿Qué es la quinoa?",
                "¿Cuál es la diferencia entre champán y cava?",
                "¿Qué es el umami?",
            ]
        },
        {
            "category": "🏛️ POLÍTICA Y GOBIERNO",
            "questions": [
                "¿Cuántos países hay en la ONU?",
                "¿Qué es la democracia?",
                "¿Quién es el actual Papa?",
                "¿Qué es la Unión Europea?",
                "¿Cuántos estados tiene Estados Unidos?",
            ]
        },
        {
            "category": "🎵 MÚSICA Y ENTRETENIMIENTO ESPECÍFICO",
            "questions": [
                "¿Cuántas cuerdas tiene una guitarra?",
                "¿Quién compuso El Bolero?",
                "¿Qué es un stradivarius?",
                "¿Cuántas teclas tiene un piano?",
                "¿Qué significa 'forte' en música?",
            ]
        }
    ]
    
    print("🧪 PRUEBA DE CASOS EDGE Y PREGUNTAS ESPECÍFICAS")
    print(f"Modelo: {model}")
    print("=" * 70)
    
    total_questions = 0
    category_results = {}
    problematic_answers = []
    
    for test_group in edge_tests:
        category_name = test_group['category']
        print(f"\n{category_name}")
        print("-" * 50)
        
        category_problems = []
        
        for question in test_group["questions"]:
            total_questions += 1
            print(f"❓ {question}")
            
            try:
                start_time = time.time()
                
                # Usar el system prompt actual de BMO
                system_prompt = """Eres BMO, un robot asistente amigable creado por Zambrano. 
Responde en español de forma natural y útil.

CORRECCIONES IMPORTANTES:
- Bandera de Colombia: amarillo arriba, azul medio, rojo abajo
- Bandera de México: verde izquierda, blanco medio, rojo derecha
- Capital de Brasil: Brasilia (NO es Rio de Janeiro, NO es São Paulo)
- Continentes: hay siete continentes en total

Para otros datos, usa tu conocimiento entrenado. Si no estás seguro, 
di 'No tengo esa información específica'. 
Sé directo pero amigable, máximo 2-3 oraciones."""
                
                response = ollama.chat(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": question}
                    ],
                    options=ollama_options
                )
                
                end_time = time.time()
                duration = end_time - start_time
                answer = response['message']['content'].strip()
                
                # Análisis de calidad de respuesta
                quality_issues = analyze_answer_quality(question, answer)
                
                # Mostrar respuesta truncada
                display_answer = answer[:80] + "..." if len(answer) > 80 else answer
                print(f"📝 ({duration:.1f}s) {display_answer}")
                
                if quality_issues:
                    print(f"   ⚠️  Problemas detectados: {', '.join(quality_issues)}")
                    category_problems.append({
                        'question': question,
                        'answer': answer,
                        'issues': quality_issues,
                        'duration': duration
                    })
                    problematic_answers.append({
                        'category': category_name,
                        'question': question,
                        'answer': answer,
                        'issues': quality_issues,
                        'duration': duration
                    })
                else:
                    print(f"   ✅ Respuesta aceptable")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                category_problems.append({
                    'question': question,
                    'answer': f"ERROR: {e}",
                    'issues': ['error_tecnico'],
                    'duration': 0
                })
            
            print()
            time.sleep(0.5)  # Pausa para no sobrecargar
        
        # Resumen por categoría
        problem_count = len(category_problems)
        total_in_category = len(test_group["questions"])
        success_rate = ((total_in_category - problem_count) / total_in_category) * 100
        
        category_results[category_name] = {
            'total': total_in_category,
            'problems': problem_count,
            'success_rate': success_rate,
            'problem_details': category_problems
        }
        
        print(f"📊 {category_name}: {problem_count} problemas de {total_in_category} ({success_rate:.1f}% éxito)")
    
    # Resumen final
    print("\n" + "=" * 70)
    print("📊 RESUMEN DE CASOS EDGE")
    print("=" * 70)
    
    total_problems = len(problematic_answers)
    success_rate = ((total_questions - total_problems) / total_questions) * 100
    print(f"Tasa de éxito general: {total_questions - total_problems}/{total_questions} ({success_rate:.1f}%)")
    print(f"Respuestas problemáticas: {total_problems}")
    print()
    
    # Ranking de categorías por problemas
    print("🏆 RANKING POR CALIDAD DE RESPUESTAS:")
    sorted_categories = sorted(category_results.items(), key=lambda x: x[1]['success_rate'], reverse=True)
    
    for i, (category, results) in enumerate(sorted_categories, 1):
        success_rate = results['success_rate']
        if success_rate >= 80:
            emoji = "🟢"
        elif success_rate >= 60:
            emoji = "🟡"
        else:
            emoji = "🔴"
        
        print(f"{i}. {emoji} {category}: {success_rate:.1f}% éxito ({results['problems']} problemas)")
    
    # Análisis de tipos de problemas
    print("\n🔍 TIPOS DE PROBLEMAS DETECTADOS:")
    problem_types = {}
    for problem in problematic_answers:
        for issue in problem['issues']:
            if issue not in problem_types:
                problem_types[issue] = 0
            problem_types[issue] += 1
    
    for problem_type, count in sorted(problem_types.items(), key=lambda x: x[1], reverse=True):
        print(f"   • {problem_type}: {count} casos")
    
    # Ejemplos de problemas más graves
    print("\n🚨 EJEMPLOS DE RESPUESTAS PROBLEMÁTICAS:")
    severe_problems = [p for p in problematic_answers if 'informacion_incorrecta' in p['issues'] or 'respuesta_inventada' in p['issues']]
    
    for i, problem in enumerate(severe_problems[:5], 1):  # Mostrar solo los primeros 5
        print(f"\n{i}. {problem['category']}")
        print(f"   ❓ {problem['question']}")
        print(f"   📝 {problem['answer'][:100]}...")
        print(f"   ⚠️  {', '.join(problem['issues'])}")
    
    return success_rate, category_results, problematic_answers

def analyze_answer_quality(question, answer):
    """Analiza la calidad de una respuesta y detecta problemas"""
    issues = []
    answer_lower = answer.lower()
    question_lower = question.lower()
    
    # Detectar respuestas muy cortas o evasivas
    if len(answer.strip()) < 10:
        issues.append("respuesta_muy_corta")
    
    # Detectar si dice que no sabe (esto es bueno en algunos casos)
    if any(phrase in answer_lower for phrase in ["no sé", "no se", "no tengo", "no estoy seguro"]):
        issues.append("admite_desconocimiento")  # No es necesariamente malo
    
    # Detectar respuestas que parecen inventadas (patrones sospechosos)
    suspicious_patterns = [
        "aproximadamente",
        "se dice que",
        "según algunos",
        "se cree que",
        "posiblemente",
        "probablemente"
    ]
    
    if any(pattern in answer_lower for pattern in suspicious_patterns):
        issues.append("respuesta_incierta")
    
    # Detectar información específica que sabemos que está mal
    known_errors = {
        "capital de kazajistán": ["almaty"],  # Debería ser Nur-Sultan/Astana
        "desierto más grande": ["sahara"],   # Debería ser Antártida
        "lago más profundo": ["superior", "titicaca"],  # Debería ser Baikal
        "cromosomas": ["48", "24"],  # Debería ser 46
        "velocidad de la luz": ["300000", "3x10"],  # Aproximadamente correcto
        "cuerdas guitarra": ["7", "5", "4"],  # Debería ser 6
        "teclas piano": ["87", "89"],  # Debería ser 88
    }
    
    for key_phrase, wrong_answers in known_errors.items():
        if key_phrase in question_lower:
            if any(wrong in answer_lower for wrong in wrong_answers):
                issues.append("informacion_incorrecta")
    
    # Detectar respuestas que parecen completamente inventadas
    invented_indicators = [
        "montequito",  # Montaña inventada
        "ojo de anacondá",  # Fruta inventada
        "aminoácidos diferentes nucleótidos",  # Definición incorrecta de ADN
    ]
    
    if any(indicator in answer_lower for indicator in invented_indicators):
        issues.append("respuesta_inventada")
    
    # Detectar respuestas demasiado largas (posible divagación)
    if len(answer) > 300:
        issues.append("respuesta_muy_larga")
    
    # Detectar si no responde la pregunta directamente
    if "?" in question and not any(word in answer_lower for word in ["es", "son", "tiene", "hay", "fue", "será"]):
        issues.append("no_responde_directamente")
    
    return issues

def main():
    print("🚀 PRUEBA DE CASOS EDGE Y PREGUNTAS ESPECÍFICAS BMO")
    print("Identificando problemas sutiles y casos límite...")
    print()
    
    # Ejecutar pruebas
    success_rate, results, problems = test_edge_cases()
    
    print(f"\n💡 RECOMENDACIONES BASADAS EN CASOS EDGE:")
    
    if success_rate < 60:
        print("🔴 CRÍTICO: Muchos problemas en casos específicos")
        print("   • Implementar sistema híbrido urgente")
        print("   • Considerar upgrade de modelo")
        print("   • Mejorar detección de preguntas problemáticas")
    elif success_rate < 80:
        print("🟡 MODERADO: Algunos problemas en casos edge")
        print("   • Mejorar system prompt para casos específicos")
        print("   • Implementar validación de respuestas")
        print("   • Agregar más correcciones específicas")
    else:
        print("🟢 BUENO: Manejo aceptable de casos edge")
        print("   • Optimizar casos específicos identificados")
        print("   • Mantener configuración actual")

if __name__ == "__main__":
    main()