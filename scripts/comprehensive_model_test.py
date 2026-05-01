#!/usr/bin/env python3
"""
Pruebas exhaustivas del modelo BMO para identificar fallos y patrones
"""
import sys
import os
import time
import json
from pathlib import Path

# Configurar paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.config.config_manager import config_manager

def test_model_response(question, expected_keywords=None, category="General"):
    """Prueba una pregunta específica y evalúa la respuesta"""
    try:
        import ollama
    except ImportError:
        return {"error": "Ollama no disponible"}
    
    model = config_manager.get("text_model", "qwen2.5:1.5b")
    ollama_options = config_manager.get_ollama_options()
    
    try:
        start_time = time.time()
        
        response = ollama.chat(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Eres BMO, un robot asistente amigable creado por Zambrano. Responde en español de forma natural y útil. Si te preguntan sobre Hora de Aventura, usa tu conocimiento de la serie."
                },
                {"role": "user", "content": question}
            ],
            options=ollama_options
        )
        
        end_time = time.time()
        duration = end_time - start_time
        answer = response['message']['content'].strip()
        
        # Evaluar respuesta
        correct = True
        issues = []
        
        if expected_keywords:
            answer_lower = answer.lower()
            for keyword in expected_keywords:
                if keyword.lower() not in answer_lower:
                    correct = False
                    issues.append(f"Falta keyword: {keyword}")
        
        # Detectar problemas comunes
        if len(answer) > 500:
            issues.append("Respuesta demasiado larga")
        
        if "isaac asimov" in answer.lower() and "hora de aventura" in question.lower():
            correct = False
            issues.append("Confunde Hora de Aventura con ciencia ficción")
        
        if "netflix" in answer.lower() and "hora de aventura" in question.lower():
            correct = False
            issues.append("Información incorrecta sobre Netflix")
        
        return {
            "question": question,
            "answer": answer,
            "duration": duration,
            "correct": correct,
            "issues": issues,
            "category": category,
            "length": len(answer)
        }
        
    except Exception as e:
        return {
            "question": question,
            "answer": f"ERROR: {e}",
            "duration": 0,
            "correct": False,
            "issues": [f"Error técnico: {e}"],
            "category": category,
            "length": 0
        }

def run_comprehensive_tests():
    """Ejecuta pruebas exhaustivas en múltiples categorías"""
    
    test_categories = {
        "Geografía Básica": [
            ("¿Cuál es la capital de Francia?", ["parís"]),
            ("¿Cuál es la capital de España?", ["madrid"]),
            ("¿Cuál es la capital de Italia?", ["roma"]),
            ("¿Cuál es la capital de Alemania?", ["berlín"]),
            ("¿Cuál es la capital de Brasil?", ["brasilia"]),
            ("¿Cuál es la capital de Argentina?", ["buenos aires"]),
            ("¿Cuál es la capital de Chile?", ["santiago"]),
            ("¿Cuál es la capital de Perú?", ["lima"]),
        ],
        
        "Banderas": [
            ("¿Cuáles son los colores de la bandera de Colombia?", ["amarillo", "azul", "rojo"]),
            ("¿Cuáles son los colores de la bandera de México?", ["verde", "blanco", "rojo"]),
            ("¿Cuáles son los colores de la bandera de España?", ["rojo", "amarillo"]),
            ("¿Cuáles son los colores de la bandera de Francia?", ["azul", "blanco", "rojo"]),
            ("¿Cuáles son los colores de la bandera de Italia?", ["verde", "blanco", "rojo"]),
            ("¿Cuáles son los colores de la bandera de Argentina?", ["azul", "blanco"]),
        ],
        
        "Historia": [
            ("¿En qué año llegó el hombre a la luna?", ["1969"]),
            ("¿En qué año se descubrió América?", ["1492"]),
            ("¿Cuándo terminó la Segunda Guerra Mundial?", ["1945"]),
            ("¿En qué año se independizó Colombia?", ["1810", "1819"]),
            ("¿Quién fue el primer presidente de Estados Unidos?", ["washington"]),
            ("¿En qué año cayó el Muro de Berlín?", ["1989"]),
        ],
        
        "Ciencia Básica": [
            ("¿Cuántos planetas hay en el sistema solar?", ["ocho", "8"]),
            ("¿Cuál es el planeta más grande del sistema solar?", ["júpiter"]),
            ("¿Cuál es la velocidad de la luz?", ["300000", "300.000"]),
            ("¿Cuántos continentes hay?", ["siete", "7"]),
            ("¿Cuál es el océano más grande?", ["pacífico"]),
            ("¿Cuál es el río más largo del mundo?", ["nilo", "amazonas"]),
        ],
        
        "Literatura": [
            ("¿Quién escribió Don Quijote?", ["cervantes"]),
            ("¿Quién escribió Cien años de soledad?", ["garcía márquez", "gabriel garcía"]),
            ("¿Quién escribió Romeo y Julieta?", ["shakespeare"]),
            ("¿Quién escribió El Principito?", ["saint-exupéry", "antoine"]),
        ],
        
        "Hora de Aventura": [
            ("¿Qué es Hora de Aventura?", ["serie", "cartoon", "animación", "finn", "jake"]),
            ("¿Quién es Finn en Hora de Aventura?", ["humano", "héroe", "14 años"]),
            ("¿Quién es Jake en Hora de Aventura?", ["perro", "mágico", "hermano"]),
            ("¿Quién es BMO en Hora de Aventura?", ["robot", "videojuegos", "consola"]),
            ("¿Qué es el Reino de los Dulces?", ["reino", "princesa chicle", "dulces"]),
            ("¿Quién es Marceline?", ["vampiro", "reina", "música"]),
        ],
        
        "Matemáticas Básicas": [
            ("¿Cuánto es 2 + 2?", ["4", "cuatro"]),
            ("¿Cuánto es 10 x 10?", ["100", "cien"]),
            ("¿Cuál es el valor de pi?", ["3.14", "3,14"]),
            ("¿Cuántos grados tiene un círculo?", ["360"]),
        ],
        
        "Conversación Natural": [
            ("Hola, ¿cómo estás?", None),
            ("¿Qué tal tu día?", None),
            ("¿Me puedes ayudar?", None),
            ("Gracias por tu ayuda", None),
            ("¿Cuál es tu comida favorita?", None),
            ("¿Te gusta la música?", None),
        ],
        
        "Preguntas Trampa": [
            ("¿Cuántas patas tiene un pez?", ["cero", "0", "no tiene"]),
            ("¿De qué color es el caballo blanco de Napoleón?", ["blanco"]),
            ("¿Cuántos meses tienen 28 días?", ["todos", "12", "doce"]),
            ("¿Qué pesa más, un kilo de plumas o un kilo de hierro?", ["igual", "mismo"]),
        ]
    }
    
    all_results = []
    category_stats = {}
    
    print("=== PRUEBAS EXHAUSTIVAS DEL MODELO BMO ===")
    print(f"Modelo: {config_manager.get('text_model')}")
    print(f"Total de categorías: {len(test_categories)}")
    print()
    
    for category, questions in test_categories.items():
        print(f"📂 CATEGORÍA: {category}")
        print("-" * 50)
        
        category_results = []
        
        for question, expected in questions:
            print(f"❓ {question}")
            
            result = test_model_response(question, expected, category)
            category_results.append(result)
            all_results.append(result)
            
            # Mostrar resultado
            status = "✅" if result["correct"] else "❌"
            print(f"{status} ({result['duration']:.1f}s) {result['answer'][:100]}...")
            
            if result["issues"]:
                for issue in result["issues"]:
                    print(f"   ⚠️  {issue}")
            
            print()
        
        # Estadísticas de categoría
        correct_count = sum(1 for r in category_results if r["correct"])
        total_count = len(category_results)
        avg_time = sum(r["duration"] for r in category_results) / total_count
        
        category_stats[category] = {
            "correct": correct_count,
            "total": total_count,
            "accuracy": correct_count / total_count * 100,
            "avg_time": avg_time
        }
        
        print(f"📊 {category}: {correct_count}/{total_count} ({correct_count/total_count*100:.1f}%) - {avg_time:.1f}s promedio")
        print()
    
    return all_results, category_stats

def analyze_results(results, category_stats):
    """Analiza los resultados y genera reporte detallado"""
    
    print("=" * 80)
    print("📊 ANÁLISIS DETALLADO DE RESULTADOS")
    print("=" * 80)
    
    # Estadísticas generales
    total_questions = len(results)
    correct_answers = sum(1 for r in results if r["correct"])
    total_time = sum(r["duration"] for r in results)
    avg_time = total_time / total_questions
    
    print(f"📈 ESTADÍSTICAS GENERALES:")
    print(f"   Total de preguntas: {total_questions}")
    print(f"   Respuestas correctas: {correct_answers} ({correct_answers/total_questions*100:.1f}%)")
    print(f"   Tiempo promedio: {avg_time:.1f} segundos")
    print(f"   Tiempo total: {total_time:.1f} segundos")
    print()
    
    # Estadísticas por categoría
    print(f"📂 RENDIMIENTO POR CATEGORÍA:")
    for category, stats in category_stats.items():
        accuracy = stats["accuracy"]
        status = "✅" if accuracy >= 80 else "⚠️" if accuracy >= 60 else "❌"
        print(f"   {status} {category}: {stats['correct']}/{stats['total']} ({accuracy:.1f}%) - {stats['avg_time']:.1f}s")
    print()
    
    # Problemas más comunes
    all_issues = []
    for result in results:
        all_issues.extend(result["issues"])
    
    issue_counts = {}
    for issue in all_issues:
        issue_counts[issue] = issue_counts.get(issue, 0) + 1
    
    if issue_counts:
        print(f"⚠️  PROBLEMAS MÁS COMUNES:")
        sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        for issue, count in sorted_issues[:10]:
            print(f"   • {issue}: {count} veces")
        print()
    
    # Respuestas más lentas
    slow_responses = sorted([r for r in results if r["duration"] > 8], 
                          key=lambda x: x["duration"], reverse=True)
    
    if slow_responses:
        print(f"🐌 RESPUESTAS MÁS LENTAS:")
        for r in slow_responses[:5]:
            print(f"   • {r['duration']:.1f}s: {r['question']}")
        print()
    
    # Respuestas incorrectas críticas
    critical_errors = [r for r in results if not r["correct"] and r["category"] in ["Geografía Básica", "Banderas", "Historia"]]
    
    if critical_errors:
        print(f"🚨 ERRORES CRÍTICOS (Datos Factuales):")
        for r in critical_errors:
            print(f"   ❌ {r['question']}")
            print(f"      Respuesta: {r['answer'][:150]}...")
            print(f"      Problemas: {', '.join(r['issues'])}")
            print()
    
    # Recomendaciones
    print(f"💡 RECOMENDACIONES:")
    
    overall_accuracy = correct_answers / total_questions * 100
    
    if overall_accuracy < 70:
        print("   🔴 CRÍTICO: Precisión muy baja - Considera upgrade urgente del modelo")
    elif overall_accuracy < 85:
        print("   🟡 MODERADO: Precisión aceptable pero mejorable")
    else:
        print("   🟢 BUENO: Precisión alta - Modelo funcionando bien")
    
    if avg_time > 8:
        print("   ⚠️  Velocidad lenta - Optimizar parámetros o hardware")
    elif avg_time > 5:
        print("   ⚠️  Velocidad aceptable pero mejorable")
    else:
        print("   ✅ Velocidad excelente")
    
    # Categorías problemáticas
    problem_categories = [cat for cat, stats in category_stats.items() if stats["accuracy"] < 70]
    if problem_categories:
        print(f"   🎯 Categorías problemáticas: {', '.join(problem_categories)}")
        print("      Considera agregar correcciones específicas para estas áreas")
    
    return {
        "overall_accuracy": overall_accuracy,
        "avg_time": avg_time,
        "problem_categories": problem_categories,
        "critical_errors": len(critical_errors),
        "total_questions": total_questions
    }

def save_results(results, filename="test_results.json"):
    """Guarda los resultados en un archivo JSON"""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"📄 Resultados guardados en: {filename}")
    except Exception as e:
        print(f"❌ Error guardando resultados: {e}")

def main():
    print("🧪 INICIANDO PRUEBAS EXHAUSTIVAS DE BMO")
    print("Esto puede tomar varios minutos...")
    print()
    
    try:
        # Ejecutar pruebas
        results, category_stats = run_comprehensive_tests()
        
        # Analizar resultados
        analysis = analyze_results(results, category_stats)
        
        # Guardar resultados
        save_results({
            "results": results,
            "category_stats": category_stats,
            "analysis": analysis,
            "timestamp": time.time(),
            "model": config_manager.get("text_model"),
            "config": config_manager.get_ollama_options()
        })
        
        print("🎉 PRUEBAS COMPLETADAS")
        
    except KeyboardInterrupt:
        print("\n❌ Pruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n❌ Error durante las pruebas: {e}")

if __name__ == "__main__":
    main()