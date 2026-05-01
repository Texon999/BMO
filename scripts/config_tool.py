#!/usr/bin/env python3
"""
Herramienta de Configuración para BMO
Permite gestionar la configuración de forma interactiva

Uso:
    python scripts/config_tool.py --show          # Mostrar configuración actual
    python scripts/config_tool.py --reset         # Resetear a defaults
    python scripts/config_tool.py --memory-stats  # Estadísticas de memoria
    python scripts/config_tool.py --test-audio    # Probar sistema de audio
"""
import sys
import argparse
from pathlib import Path
import os

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Cambiar al directorio del proyecto para imports relativos
os.chdir(project_root)

try:
    from src.config.config_manager import config_manager
    from src.memory.persistent_memory import persistent_memory
    from src.config.audio_manager import audio_manager
except ImportError as e:
    print(f"Error importando módulos: {e}")
    print("Asegúrate de ejecutar desde el directorio raíz del proyecto BMO")
    sys.exit(1)

def show_config():
    """Muestra la configuración actual"""
    print("=== CONFIGURACIÓN ACTUAL DE BMO ===")
    
    summary = config_manager.get_config_summary()
    for key, value in summary.items():
        print(f"{key:20}: {value}")
    
    print("\n=== PARÁMETROS LLM ===")
    ollama_opts = config_manager.get_ollama_options()
    for key, value in ollama_opts.items():
        print(f"{key:20}: {value}")

def show_memory_stats():
    """Muestra estadísticas de memoria"""
    print("=== ESTADÍSTICAS DE MEMORIA ===")
    
    stats = persistent_memory.get_memory_stats()
    for key, value in stats.items():
        print(f"{key:20}: {value}")

def reset_config():
    """Resetea la configuración a defaults"""
    print("¿Estás seguro de que quieres resetear la configuración? (y/N): ", end="")
    response = input().strip().lower()
    
    if response in ['y', 'yes', 'sí', 's']:
        config_manager.reset_to_defaults()
        print("✅ Configuración reseteada a valores por defecto")
    else:
        print("❌ Operación cancelada")

def reset_memory():
    """Resetea la memoria persistente"""
    print("¿Estás seguro de que quieres borrar toda la memoria? (y/N): ", end="")
    response = input().strip().lower()
    
    if response in ['y', 'yes', 'sí', 's']:
        persistent_memory.reset_all_memory()
        print("✅ Memoria reseteada")
    else:
        print("❌ Operación cancelada")

def test_audio():
    """Prueba el sistema de audio"""
    print("=== PRUEBA DEL SISTEMA DE AUDIO ===")
    
    # Inicializar audio manager
    if audio_manager.initialize():
        print("✅ Audio manager inicializado correctamente")
        
        if audio_manager.test_audio_system():
            print("✅ Sistema de audio funcionando correctamente")
        else:
            print("❌ Error en el sistema de audio")
    else:
        print("❌ Error inicializando audio manager")

def interactive_config():
    """Configuración interactiva"""
    print("=== CONFIGURACIÓN INTERACTIVA DE BMO ===")
    
    # Configurar modelo LLM
    current_model = config_manager.get("text_model")
    print(f"\nModelo LLM actual: {current_model}")
    new_model = input("Nuevo modelo (Enter para mantener): ").strip()
    if new_model:
        config_manager.set("text_model", new_model)
        print(f"✅ Modelo cambiado a: {new_model}")
    
    # Configurar temperatura
    current_temp = config_manager.get("llm_temperature")
    print(f"\nTemperatura actual: {current_temp}")
    new_temp = input("Nueva temperatura (0.0-2.0, Enter para mantener): ").strip()
    if new_temp:
        try:
            temp_val = float(new_temp)
            if 0.0 <= temp_val <= 2.0:
                config_manager.set("llm_temperature", temp_val)
                print(f"✅ Temperatura cambiada a: {temp_val}")
            else:
                print("❌ Temperatura debe estar entre 0.0 y 2.0")
        except ValueError:
            print("❌ Valor inválido para temperatura")
    
    # Configurar memoria
    current_memory = config_manager.get("chat_memory")
    print(f"\nMemoria persistente: {'Habilitada' if current_memory else 'Deshabilitada'}")
    toggle_memory = input("¿Cambiar estado de memoria? (y/N): ").strip().lower()
    if toggle_memory in ['y', 'yes', 'sí', 's']:
        config_manager.set("chat_memory", not current_memory)
        new_state = "Habilitada" if not current_memory else "Deshabilitada"
        print(f"✅ Memoria persistente: {new_state}")
    
    print("\n✅ Configuración guardada")

def main():
    parser = argparse.ArgumentParser(description="Herramienta de configuración para BMO")
    parser.add_argument("--show", action="store_true", help="Mostrar configuración actual")
    parser.add_argument("--reset", action="store_true", help="Resetear configuración")
    parser.add_argument("--memory-stats", action="store_true", help="Estadísticas de memoria")
    parser.add_argument("--reset-memory", action="store_true", help="Resetear memoria")
    parser.add_argument("--test-audio", action="store_true", help="Probar sistema de audio")
    parser.add_argument("--interactive", action="store_true", help="Configuración interactiva")
    
    args = parser.parse_args()
    
    if args.show:
        show_config()
    elif args.reset:
        reset_config()
    elif args.memory_stats:
        show_memory_stats()
    elif args.reset_memory:
        reset_memory()
    elif args.test_audio:
        test_audio()
    elif args.interactive:
        interactive_config()
    else:
        # Mostrar menú interactivo
        print("=== HERRAMIENTA DE CONFIGURACIÓN BMO ===")
        print("1. Mostrar configuración")
        print("2. Configuración interactiva")
        print("3. Estadísticas de memoria")
        print("4. Probar audio")
        print("5. Resetear configuración")
        print("6. Resetear memoria")
        print("0. Salir")
        
        while True:
            choice = input("\nSelecciona una opción: ").strip()
            
            if choice == "1":
                show_config()
            elif choice == "2":
                interactive_config()
            elif choice == "3":
                show_memory_stats()
            elif choice == "4":
                test_audio()
            elif choice == "5":
                reset_config()
            elif choice == "6":
                reset_memory()
            elif choice == "0":
                break
            else:
                print("Opción inválida")

if __name__ == "__main__":
    main()