#!/usr/bin/env python3
"""
Script de prueba para verificar el system prompt mejorado
"""
import sys
import os
from pathlib import Path

# Configurar paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.brain.brain import get_system_prompt

def main():
    print("=== SYSTEM PROMPT ACTUAL ===")
    prompt = get_system_prompt()
    print(prompt)
    print("\n" + "="*50)
    
    # Verificar que contiene información de Colombia
    if "amarillo arriba, azul medio, rojo abajo" in prompt:
        print("✅ Información de Colombia correcta en system prompt")
    else:
        print("❌ Información de Colombia no encontrada o incorrecta")
    
    # Verificar que es enfático
    if "CORRECCIONES IMPORTANTES" in prompt:
        print("✅ System prompt tiene correcciones específicas")
    else:
        print("❌ System prompt no tiene correcciones específicas")

if __name__ == "__main__":
    main()