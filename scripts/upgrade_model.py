#!/usr/bin/env python3
"""
Script para actualizar BMO a un modelo más grande con mejor conocimiento factual
"""
import sys
import os
import subprocess
import time
from pathlib import Path

# Configurar paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.config.config_manager import config_manager

def check_ollama_running():
    """Verifica si Ollama está ejecutándose"""
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def download_model(model_name):
    """Descarga un modelo de Ollama"""
    print(f"Descargando modelo {model_name}...")
    print("Esto puede tomar varios minutos dependiendo de tu conexión.")
    
    try:
        process = subprocess.Popen(
            ["ollama", "pull", model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            universal_newlines=True
        )
        
        for line in process.stdout:
            print(line.strip())
        
        process.wait()
        return process.returncode == 0
        
    except Exception as e:
        print(f"Error descargando modelo: {e}")
        return False

def test_model_response(model_name, test_question="¿Cuáles son los colores de la bandera de Colombia?"):
    """Prueba una respuesta del modelo"""
    print(f"\nProbando modelo {model_name}...")
    print(f"Pregunta: {test_question}")
    
    try:
        import ollama
        
        start_time = time.time()
        response = ollama.chat(
            model=model_name,
            messages=[
                {
                    "role": "system", 
                    "content": "Eres BMO. Responde en español de forma precisa y concisa."
                },
                {"role": "user", "content": test_question}
            ],
            options={
                "temperature": 0.75,
                "top_k": 50,
                "top_p": 0.9,
                "num_predict": 100
            }
        )
        end_time = time.time()
        
        answer = response['message']['content']
        duration = end_time - start_time
        
        print(f"Respuesta: {answer}")
        print(f"Tiempo: {duration:.1f} segundos")
        
        return True, answer, duration
        
    except Exception as e:
        print(f"Error probando modelo: {e}")
        return False, None, None

def update_config(new_model):
    """Actualiza la configuración con el nuevo modelo"""
    print(f"\nActualizando configuración a {new_model}...")
    
    try:
        config_manager.set("text_model", new_model)
        print("✅ Configuración actualizada")
        return True
    except Exception as e:
        print(f"❌ Error actualizando configuración: {e}")
        return False

def main():
    print("=== UPGRADE DE MODELO BMO ===")
    print("Mejorando conocimiento factual con modelo más grande")
    print()
    
    # Verificar Ollama
    if not check_ollama_running():
        print("❌ Ollama no está ejecutándose")
        print("Ejecuta: ollama serve")
        return
    
    print("✅ Ollama está ejecutándose")
    
    # Mostrar configuración actual
    current_model = config_manager.get("text_model", "qwen2.5:1.5b")
    print(f"Modelo actual: {current_model}")
    
    # Opciones de modelos
    models = {
        "1": ("qwen2.5:3b", "Modelo balanceado - Mejor conocimiento, velocidad aceptable"),
        "2": ("qwen2.5:7b", "Modelo avanzado - Excelente conocimiento, más lento"),
        "3": ("llama3.2:3b", "Alternativa - Modelo Meta, buen conocimiento"),
    }
    
    print("\nModelos disponibles:")
    for key, (model, desc) in models.items():
        print(f"{key}. {model} - {desc}")
    
    choice = input("\nSelecciona un modelo (1-3, Enter para qwen2.5:3b): ").strip()
    
    if not choice:
        choice = "1"
    
    if choice not in models:
        print("❌ Opción inválida")
        return
    
    new_model, description = models[choice]
    
    print(f"\nSeleccionado: {new_model}")
    print(f"Descripción: {description}")
    
    # Confirmar descarga
    confirm = input(f"\n¿Descargar {new_model}? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes', 'sí', 's']:
        print("❌ Operación cancelada")
        return
    
    # Descargar modelo
    if download_model(new_model):
        print("✅ Modelo descargado exitosamente")
    else:
        print("❌ Error descargando modelo")
        return
    
    # Probar modelo
    print("\n" + "="*50)
    print("PROBANDO MODELO NUEVO")
    
    success, answer, duration = test_model_response(new_model)
    
    if success:
        print(f"\n✅ Modelo funcionando correctamente")
        
        # Evaluar respuesta
        if "amarillo" in answer.lower() and "azul" in answer.lower() and "rojo" in answer.lower():
            print("✅ Respuesta sobre Colombia parece correcta")
        else:
            print("⚠️  Respuesta sobre Colombia puede ser incorrecta")
        
        if duration < 10:
            print("✅ Velocidad aceptable")
        else:
            print("⚠️  Velocidad lenta, considera un modelo más pequeño")
        
        # Actualizar configuración
        update_confirm = input(f"\n¿Actualizar BMO para usar {new_model}? (y/N): ").strip().lower()
        if update_confirm in ['y', 'yes', 'sí', 's']:
            if update_config(new_model):
                print(f"\n🎉 ¡BMO actualizado exitosamente!")
                print(f"Nuevo modelo: {new_model}")
                print("Reinicia BMO para usar el nuevo modelo")
            else:
                print("❌ Error actualizando configuración")
        else:
            print("Configuración no cambiada")
    else:
        print("❌ Error probando el modelo")
    
    # Comparar con modelo anterior si es diferente
    if new_model != current_model:
        print(f"\n" + "="*50)
        print("COMPARANDO CON MODELO ANTERIOR")
        
        print(f"\nProbando modelo anterior ({current_model})...")
        old_success, old_answer, old_duration = test_model_response(current_model)
        
        if old_success and success:
            print(f"\n📊 COMPARACIÓN:")
            print(f"Modelo anterior: {old_duration:.1f}s - {old_answer[:50]}...")
            print(f"Modelo nuevo:   {duration:.1f}s - {answer[:50]}...")
            
            if duration > old_duration:
                print(f"⚠️  Nuevo modelo es {duration - old_duration:.1f}s más lento")
            else:
                print(f"✅ Nuevo modelo es {old_duration - duration:.1f}s más rápido")

if __name__ == "__main__":
    main()