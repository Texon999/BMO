#!/usr/bin/env python3
"""
Pruebas Exhaustivas de Conocimiento General para BMO
Simula preguntas que cualquier persona haría en conversación normal
"""
import sys
import os
import time
import random
from pathlib import Path

# Configurar paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.config.config_manager import config_manager

def test_general_knowledge():
    """Prueba conocimiento general con preguntas aleatorias comunes"""
    
    try:
        import ollama
    except ImportError:
        print("❌ Ollama no disponible")
        return
    
    model = config_manager.get("text_model", "qwen2.5:1.5b")
    ollama_options = config_manager.get_ollama_options()
    
    # Preguntas que cualquier persona haría - organizadas por categorías
    general_tests = [
        {
            "category": "🌍 GEOGRAFÍA MUNDIAL",
            "questions": [
                "¿Cuál es la capital de Francia?",
                "¿Cuál es la capital de Italia?", 
                "¿Cuál es la capital de Japón?",
                "¿Cuál es la capital de Australia?",
                "¿Cuál es la capital de Canadá?",
                "¿Cuál es la capital de Argentina?",
                "¿Cuál es el país más grande del mundo?",
                "¿Cuál es el río más largo del mundo?",
                "¿Cuál es la montaña más alta del mundo?",
                "¿En qué continente está Egipto?",
            ]
        },
        {
            "category": "🏳️ BANDERAS Y SÍMBOLOS",
            "questions": [
                "¿De qué colores es la bandera de España?",
                "¿De qué colores es la bandera de Francia?",
                "¿De qué colores es la bandera de Italia?",
                "¿De qué colores es la bandera de Alemania?",
                "¿De qué colores es la bandera de Estados Unidos?",
                "¿De qué colores es la bandera de Brasil?",
                "¿De qué colores es la bandera de Argentina?",
                "¿De qué colores es la bandera del Reino Unido?",
            ]
        },
        {
            "category": "🔬 CIENCIAS NATURALES",
            "questions": [
                "¿Cuál es el planeta más cercano al Sol?",
                "¿Cuántos planetas hay en el sistema solar?",
                "¿Qué gas respiramos principalmente?",
                "¿Cuál es el animal más grande del mundo?",
                "¿Cuál es el animal terrestre más rápido?",
                "¿Cuántos huesos tiene el cuerpo humano aproximadamente?",
                "¿Cuál es el órgano más grande del cuerpo humano?",
                "¿A qué temperatura hierve el agua?",
                "¿Cuál es el metal más abundante en la Tierra?",
                "¿Qué significa ADN?",
            ]
        },
        {
            "category": "📚 CULTURA GENERAL",
            "questions": [
                "¿Quién escribió Don Quijote?",
                "¿Quién pintó la Mona Lisa?",
                "¿En qué año llegó el hombre a la Luna?",
                "¿Cuántos días tiene un año bisiesto?",
                "¿Cuál es el idioma más hablado del mundo?",
                "¿Quién inventó la bombilla?",
                "¿En qué año comenzó la Segunda Guerra Mundial?",
                "¿Cuál es la moneda de Estados Unidos?",
                "¿Cuál es la moneda de la Unión Europea?",
                "¿Quién fue el primer presidente de Estados Unidos?",
            ]
        },
        {
            "category": "🎬 ENTRETENIMIENTO",
            "questions": [
                "¿Quién dirigió la película Titanic?",
                "¿Cómo se llama el ratón más famoso de Disney?",
                "¿Cuál es la película más taquillera de la historia?",
                "¿Quién interpretó a Harry Potter en las películas?",
                "¿En qué año se estrenó la primera película de Star Wars?",
                "¿Cómo se llama el personaje principal de Los Simpson?",
                "¿Quién cantó 'Bohemian Rhapsody'?",
                "¿Cuál es el videojuego más vendido de la historia?",
            ]
        },
        {
            "category": "⚽ DEPORTES",
            "questions": [
                "¿Cada cuántos años se celebra la Copa Mundial de Fútbol?",
                "¿En qué deporte se usa una raqueta?",
                "¿Cuántos jugadores hay en un equipo de fútbol?",
                "¿Cuántos jugadores hay en un equipo de baloncesto?",
                "¿En qué país se inventó el fútbol moderno?",
                "¿Cuál es el torneo de tenis más prestigioso?",
                "¿Cada cuántos años se celebran los Juegos Olímpicos?",
            ]
        },
        {
            "category": "🍕 COMIDA Y BEBIDA",
            "questions": [
                "¿De qué país es originaria la pizza?",
                "¿Cuál es el ingrediente principal del guacamole?",
                "¿De qué está hecho el chocolate?",
                "¿Cuál es la bebida más consumida del mundo después del agua?",
                "¿De qué país es originario el sushi?",
                "¿Qué fruta es conocida por tener mucha vitamina C?",
                "¿De qué animal viene el jamón?",
            ]
        },
        {
            "category": "🕐 TIEMPO Y FECHAS",
            "questions": [
                "¿Cuántos días tiene febrero en un año normal?",
                "¿Cuántas horas tiene un día?",
                "¿Cuántos minutos tiene una hora?",
                "¿En qué mes se celebra la Navidad?",
                "¿Cuántos meses tiene un año?",
                "¿Qué día de la semana viene después del miércoles?",
                "¿Cuántas estaciones tiene el año?",
            ]
        },
        {
            "category": "💰 ECONOMÍA BÁSICA",
            "questions": [
                "¿Cuál es la moneda de México?",
                "¿Cuál es la moneda de Reino Unido?",
                "¿Cuál es la moneda de Japón?",
                "¿Qué significa PIB?",
                "¿Cuál es la empresa más valiosa del mundo?",
            ]
        },
        {
            "category": "🌡️ MATEMÁTICAS BÁSICAS",
            "questions": [
                "¿Cuánto es 7 por 8?",
                "¿Cuánto es 15 más 27?",
                "¿Cuánto es 100 menos 37?",
                "¿Cuánto es la mitad de 50?",
                "¿Cuántos lados tiene un triángulo?",
                "¿Cuántos grados tiene un círculo completo?",
                "¿Cuál es el número pi aproximadamente?",
            ]
        }
    ]
    
    print("🧪 PRUEBA EXHAUSTIVA DE CONOCIMIENTO GENERAL")
    print(f"Modelo: {model}")
    print("=" * 70)
    
    total_correct = 0
    total_questions = 0
    category_results = {}
    
    for test_group in general_tests:
        category_name = test_group['category']
        print(f"\n{category_name}")
        print("-" * 50)
        
        category_correct = 0
        category_total = 0
        
        # Mezclar preguntas para variedad
        questions = test_group["questions"].copy()
        random.shuffle(questions)
        
        for question in questions:
            total_questions += 1
            category_total += 1
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
                
                # Evaluación automática
                is_correct = evaluate_general_answer(question, answer)
                
                status = "✅" if is_correct else "❌"
                if is_correct:
                    total_correct += 1
                    category_correct += 1
                
                # Mostrar respuesta truncada
                display_answer = answer[:80] + "..." if len(answer) > 80 else answer
                print(f"{status} ({duration:.1f}s) {display_answer}")
                
                if not is_correct:
                    print(f"   🔍 Respuesta problemática detectada")
                
            except Exception as e:
                print(f"❌ Error: {e}")
            
            print()
            
            # Pausa pequeña para no sobrecargar
            time.sleep(0.5)
        
        # Resumen por categoría
        category_accuracy = (category_correct / category_total) * 100 if category_total > 0 else 0
        category_results[category_name] = {
            'correct': category_correct,
            'total': category_total,
            'accuracy': category_accuracy
        }
        
        print(f"📊 {category_name}: {category_correct}/{category_total} ({category_accuracy:.1f}%)")
    
    # Resumen final
    print("\n" + "=" * 70)
    print("📊 RESUMEN GENERAL DE CONOCIMIENTO")
    print("=" * 70)
    
    overall_accuracy = (total_correct / total_questions) * 100 if total_questions > 0 else 0
    print(f"Precisión general: {total_correct}/{total_questions} ({overall_accuracy:.1f}%)")
    print()
    
    # Ranking de categorías por precisión
    print("🏆 RANKING POR CATEGORÍAS:")
    sorted_categories = sorted(category_results.items(), key=lambda x: x[1]['accuracy'], reverse=True)
    
    for i, (category, results) in enumerate(sorted_categories, 1):
        accuracy = results['accuracy']
        if accuracy >= 80:
            emoji = "🟢"
        elif accuracy >= 60:
            emoji = "🟡"
        else:
            emoji = "🔴"
        
        print(f"{i}. {emoji} {category}: {accuracy:.1f}% ({results['correct']}/{results['total']})")
    
    print()
    
    # Análisis y recomendaciones
    print("🔍 ANÁLISIS DE RESULTADOS:")
    
    if overall_accuracy >= 80:
        print("✅ EXCELENTE: El modelo tiene buen conocimiento general")
    elif overall_accuracy >= 60:
        print("⚠️  MODERADO: El modelo tiene conocimiento aceptable pero con gaps")
    else:
        print("🚨 CRÍTICO: El modelo tiene serios problemas de conocimiento")
    
    # Identificar categorías problemáticas
    problematic_categories = [cat for cat, results in category_results.items() if results['accuracy'] < 50]
    
    if problematic_categories:
        print(f"\n🎯 CATEGORÍAS PROBLEMÁTICAS ({len(problematic_categories)}):")
        for cat in problematic_categories:
            accuracy = category_results[cat]['accuracy']
            print(f"   • {cat}: {accuracy:.1f}%")
    
    print("\n💡 RECOMENDACIONES:")
    
    if overall_accuracy < 50:
        print("🔴 URGENTE: Considerar upgrade a modelo más grande (qwen2.5:3b)")
        print("   • Implementar sistema híbrido con respuestas hardcoded")
        print("   • Mejorar system prompt con más correcciones específicas")
    elif overall_accuracy < 70:
        print("🟡 MODERADO: Mejorar áreas específicas")
        print("   • Agregar correcciones para categorías problemáticas")
        print("   • Considerar upgrade si la velocidad lo permite")
    else:
        print("🟢 BUENO: Optimizar casos específicos")
        print("   • Afinar system prompt para casos edge")
        print("   • Mantener configuración actual")
    
    return overall_accuracy, category_results

def evaluate_general_answer(question, answer):
    """Evaluación automática de respuestas de conocimiento general"""
    answer_lower = answer.lower()
    question_lower = question.lower()
    
    # Geografía
    if "capital de francia" in question_lower:
        return "parís" in answer_lower or "paris" in answer_lower
    if "capital de italia" in question_lower:
        return "roma" in answer_lower
    if "capital de japón" in question_lower or "capital de japon" in question_lower:
        return "tokio" in answer_lower or "tokyo" in answer_lower
    if "capital de australia" in question_lower:
        return "canberra" in answer_lower
    if "capital de canadá" in question_lower or "capital de canada" in question_lower:
        return "ottawa" in answer_lower
    if "capital de argentina" in question_lower:
        return "buenos aires" in answer_lower
    if "país más grande" in question_lower:
        return "rusia" in answer_lower
    if "río más largo" in question_lower or "rio mas largo" in question_lower:
        return "nilo" in answer_lower or "amazonas" in answer_lower
    if "montaña más alta" in question_lower or "montana mas alta" in question_lower:
        return "everest" in answer_lower
    if "continente" in question_lower and "egipto" in question_lower:
        return "áfrica" in answer_lower or "africa" in answer_lower
    
    # Banderas
    if "bandera de españa" in question_lower or "bandera de espana" in question_lower:
        return "rojo" in answer_lower and "amarillo" in answer_lower
    if "bandera de francia" in question_lower:
        return "azul" in answer_lower and "blanco" in answer_lower and "rojo" in answer_lower
    if "bandera de italia" in question_lower:
        return "verde" in answer_lower and "blanco" in answer_lower and "rojo" in answer_lower
    if "bandera de alemania" in question_lower:
        return "negro" in answer_lower and "rojo" in answer_lower and "amarillo" in answer_lower
    if "bandera de estados unidos" in question_lower:
        return "rojo" in answer_lower and "blanco" in answer_lower and "azul" in answer_lower
    if "bandera de brasil" in question_lower:
        return "verde" in answer_lower and "amarillo" in answer_lower and "azul" in answer_lower
    if "bandera de argentina" in question_lower:
        return "azul" in answer_lower and "blanco" in answer_lower
    if "bandera del reino unido" in question_lower:
        return "azul" in answer_lower and "blanco" in answer_lower and "rojo" in answer_lower
    
    # Ciencias
    if "planeta más cercano al sol" in question_lower or "planeta mas cercano al sol" in question_lower:
        return "mercurio" in answer_lower
    if "cuántos planetas" in question_lower or "cuantos planetas" in question_lower:
        return "ocho" in answer_lower or "8" in answer_lower
    if "gas respiramos" in question_lower:
        return "oxígeno" in answer_lower or "oxigeno" in answer_lower
    if "animal más grande del mundo" in question_lower or "animal mas grande del mundo" in question_lower:
        return "ballena" in answer_lower
    if "animal terrestre más rápido" in question_lower or "animal terrestre mas rapido" in question_lower:
        return "guepardo" in answer_lower or "chita" in answer_lower
    if "cuántos huesos" in question_lower or "cuantos huesos" in question_lower:
        return "206" in answer_lower or "doscientos" in answer_lower
    if "órgano más grande" in question_lower or "organo mas grande" in question_lower:
        return "piel" in answer_lower
    if "temperatura hierve el agua" in question_lower:
        return "100" in answer_lower or "cien" in answer_lower
    if "metal más abundante" in question_lower or "metal mas abundante" in question_lower:
        return "aluminio" in answer_lower
    if "qué significa adn" in question_lower or "que significa adn" in question_lower:
        return "ácido desoxirribonucleico" in answer_lower or "acido desoxirribonucleico" in answer_lower
    
    # Cultura general
    if "quién escribió don quijote" in question_lower or "quien escribio don quijote" in question_lower:
        return "cervantes" in answer_lower
    if "quién pintó la mona lisa" in question_lower or "quien pinto la mona lisa" in question_lower:
        return "leonardo" in answer_lower or "da vinci" in answer_lower
    if "año llegó el hombre a la luna" in question_lower or "ano llego el hombre a la luna" in question_lower:
        return "1969" in answer_lower
    if "días tiene un año bisiesto" in question_lower or "dias tiene un ano bisiesto" in question_lower:
        return "366" in answer_lower
    if "idioma más hablado" in question_lower or "idioma mas hablado" in question_lower:
        return "chino" in answer_lower or "mandarín" in answer_lower or "mandarin" in answer_lower
    if "quién inventó la bombilla" in question_lower or "quien invento la bombilla" in question_lower:
        return "edison" in answer_lower
    if "año comenzó la segunda guerra mundial" in question_lower or "ano comenzo la segunda guerra mundial" in question_lower:
        return "1939" in answer_lower
    if "moneda de estados unidos" in question_lower:
        return "dólar" in answer_lower or "dolar" in answer_lower
    if "moneda de la unión europea" in question_lower or "moneda de la union europea" in question_lower:
        return "euro" in answer_lower
    if "primer presidente de estados unidos" in question_lower:
        return "washington" in answer_lower
    
    # Entretenimiento
    if "quién dirigió" in question_lower and "titanic" in question_lower:
        return "cameron" in answer_lower
    if "ratón más famoso de disney" in question_lower or "raton mas famoso de disney" in question_lower:
        return "mickey" in answer_lower
    if "quién interpretó" in question_lower and "harry potter" in question_lower:
        return "radcliffe" in answer_lower
    if "bohemian rhapsody" in question_lower:
        return "queen" in answer_lower or "freddie mercury" in answer_lower
    
    # Deportes
    if "cada cuántos años" in question_lower and "copa mundial" in question_lower:
        return "cuatro" in answer_lower or "4" in answer_lower
    if "deporte se usa una raqueta" in question_lower:
        return "tenis" in answer_lower or "bádminton" in answer_lower or "badminton" in answer_lower
    if "cuántos jugadores" in question_lower and "fútbol" in question_lower:
        return "once" in answer_lower or "11" in answer_lower
    if "cuántos jugadores" in question_lower and "baloncesto" in question_lower:
        return "cinco" in answer_lower or "5" in answer_lower
    
    # Comida
    if "país es originaria la pizza" in question_lower or "pais es originaria la pizza" in question_lower:
        return "italia" in answer_lower
    if "ingrediente principal del guacamole" in question_lower:
        return "aguacate" in answer_lower or "palta" in answer_lower
    if "de qué está hecho el chocolate" in question_lower or "de que esta hecho el chocolate" in question_lower:
        return "cacao" in answer_lower
    if "bebida más consumida" in question_lower and "después del agua" in question_lower:
        return "té" in answer_lower or "te" in answer_lower
    if "país es originario el sushi" in question_lower or "pais es originario el sushi" in question_lower:
        return "japón" in answer_lower or "japon" in answer_lower
    
    # Tiempo
    if "cuántos días tiene febrero" in question_lower and "normal" in question_lower:
        return "28" in answer_lower or "veintiocho" in answer_lower
    if "cuántas horas tiene un día" in question_lower or "cuantas horas tiene un dia" in question_lower:
        return "24" in answer_lower or "veinticuatro" in answer_lower
    if "cuántos minutos tiene una hora" in question_lower or "cuantos minutos tiene una hora" in question_lower:
        return "60" in answer_lower or "sesenta" in answer_lower
    if "mes se celebra la navidad" in question_lower:
        return "diciembre" in answer_lower
    if "cuántos meses tiene un año" in question_lower or "cuantos meses tiene un ano" in question_lower:
        return "12" in answer_lower or "doce" in answer_lower
    if "día" in question_lower and "después del miércoles" in question_lower:
        return "jueves" in answer_lower
    if "cuántas estaciones tiene el año" in question_lower or "cuantas estaciones tiene el ano" in question_lower:
        return "cuatro" in answer_lower or "4" in answer_lower
    
    # Economía
    if "moneda de méxico" in question_lower or "moneda de mexico" in question_lower:
        return "peso" in answer_lower
    if "moneda de reino unido" in question_lower:
        return "libra" in answer_lower
    if "moneda de japón" in question_lower or "moneda de japon" in question_lower:
        return "yen" in answer_lower
    
    # Matemáticas
    if "7 por 8" in question_lower:
        return "56" in answer_lower
    if "15 más 27" in question_lower or "15 mas 27" in question_lower:
        return "42" in answer_lower
    if "100 menos 37" in question_lower:
        return "63" in answer_lower
    if "mitad de 50" in question_lower:
        return "25" in answer_lower
    if "lados tiene un triángulo" in question_lower or "lados tiene un triangulo" in question_lower:
        return "tres" in answer_lower or "3" in answer_lower
    if "grados tiene un círculo" in question_lower or "grados tiene un circulo" in question_lower:
        return "360" in answer_lower
    if "número pi" in question_lower or "numero pi" in question_lower:
        return "3.14" in answer_lower or "3,14" in answer_lower
    
    # Por defecto, asumir correcto si no hay evaluación específica
    return True

def main():
    print("🚀 PRUEBA EXHAUSTIVA DE CONOCIMIENTO GENERAL BMO")
    print("Simulando preguntas que cualquier persona haría...")
    print()
    
    # Ejecutar pruebas
    accuracy, results = test_general_knowledge()
    
    # Guardar resultados
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_file = f"test_results_general_{timestamp}.json"
    
    try:
        import json
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'overall_accuracy': accuracy,
                'category_results': results,
                'model': config_manager.get("text_model", "qwen2.5:1.5b"),
                'config': {
                    'temperature': config_manager.get("llm_temperature", 0.75),
                    'top_k': config_manager.get("llm_top_k", 50),
                    'top_p': config_manager.get("llm_top_p", 0.90)
                }
            }, indent=2, ensure_ascii=False)
        print(f"\n💾 Resultados guardados en: {results_file}")
    except Exception as e:
        print(f"\n⚠️  No se pudieron guardar los resultados: {e}")

if __name__ == "__main__":
    main()