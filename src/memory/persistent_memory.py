"""
Sistema de Memoria Persistente para BMO
Basado en buenas prácticas de be-more-agent

Características:
- Memoria permanente + memoria de sesión
- Límite automático de conversaciones
- Guardado automático y recuperación
- Gestión de contexto inteligente
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import atexit
from datetime import datetime

log = logging.getLogger("BMO.Memory")

class PersistentMemory:
    """Gestor de memoria persistente con límites automáticos"""
    
    def __init__(self, memory_file: str = "data/chat_memory.json", max_conversations: int = 10):
        self.memory_file = Path(memory_file)
        self.max_conversations = max_conversations
        
        # Memoria permanente (se guarda en disco)
        self.permanent_memory: List[Dict[str, Any]] = []
        
        # Memoria de sesión (se pierde al reiniciar)
        self.session_memory: List[Dict[str, Any]] = []
        
        # Cargar memoria existente
        self.load_memory()
        
        # Registrar guardado automático al salir
        atexit.register(self.save_memory)
        
    def load_memory(self):
        """Carga la memoria desde disco"""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                if isinstance(data, list):
                    self.permanent_memory = data
                else:
                    # Formato legacy - convertir
                    self.permanent_memory = data.get("permanent", [])
                    
                log.info(f"[MEMORY] Loaded {len(self.permanent_memory)} messages")
                
            except Exception as e:
                log.warning(f"[MEMORY] Failed to load: {e}")
                self.permanent_memory = []
        else:
            log.info("[MEMORY] No existing memory file, starting fresh")
            self.permanent_memory = []
            
        # Asegurar que siempre hay un system prompt
        if not self.permanent_memory or self.permanent_memory[0].get("role") != "system":
            self._add_system_prompt()
    
    def _add_system_prompt(self):
        """Agrega el system prompt por defecto"""
        system_prompt = {
            "role": "system",
            "content": (
                "Eres BMO, un robot asistente amigable creado por Zambrano. "
                "Responde en español de forma natural y útil. "
                "Si te preguntan sobre Hora de Aventura, usa tu conocimiento de la serie. "
                "Para datos factuales (banderas, geografía, historia), sé muy preciso. "
                "La bandera de Colombia tiene tres franjas: amarillo (arriba), azul (medio) y rojo (abajo). "
                "Si no estás 100% seguro de un dato, di 'No estoy seguro de esa información'. "
                "Sé directo pero amigable, máximo 2-3 oraciones."
            ),
            "timestamp": datetime.now().isoformat()
        }
        
        if self.permanent_memory and self.permanent_memory[0].get("role") == "system":
            self.permanent_memory[0] = system_prompt
        else:
            self.permanent_memory.insert(0, system_prompt)
    
    def add_user_message(self, content: str, persona: Optional[str] = None):
        """Agrega un mensaje del usuario"""
        message = {
            "role": "user",
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        if persona:
            message["persona"] = persona
            
        self.session_memory.append(message)
        log.debug(f"[MEMORY] Added user message: {content[:50]}...")
    
    def add_assistant_message(self, content: str):
        """Agrega un mensaje del asistente"""
        message = {
            "role": "assistant", 
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        self.session_memory.append(message)
        log.debug(f"[MEMORY] Added assistant message: {content[:50]}...")
    
    def get_context_for_llm(self, persona: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obtiene el contexto completo para el LLM"""
        context = []
        
        # System prompt (siempre primero)
        if self.permanent_memory and self.permanent_memory[0].get("role") == "system":
            system_msg = self.permanent_memory[0].copy()
            
            # Agregar contexto de persona si existe
            if persona:
                system_msg["content"] += f" El usuario se llama {persona}."
                
            context.append(system_msg)
        
        # Memoria permanente (sin system prompt)
        context.extend(self.permanent_memory[1:])
        
        # Memoria de sesión actual
        context.extend(self.session_memory)
        
        return context
    
    def clear_session(self):
        """Limpia la memoria de sesión actual"""
        if self.session_memory:
            log.info(f"[MEMORY] Clearing {len(self.session_memory)} session messages")
            self.session_memory = []
    
    def reset_all_memory(self):
        """Resetea toda la memoria (permanente y sesión)"""
        log.info("[MEMORY] Resetting all memory")
        self.session_memory = []
        self.permanent_memory = []
        self._add_system_prompt()
        self.save_memory()
    
    def commit_session_to_permanent(self):
        """Mueve la memoria de sesión a permanente"""
        if not self.session_memory:
            return
            
        log.info(f"[MEMORY] Committing {len(self.session_memory)} messages to permanent")
        
        # Agregar mensajes de sesión a permanente
        self.permanent_memory.extend(self.session_memory)
        
        # Aplicar límite de conversaciones
        self._apply_conversation_limit()
        
        # Limpiar sesión
        self.session_memory = []
        
        # Guardar automáticamente
        self.save_memory()
    
    def _apply_conversation_limit(self):
        """Aplica el límite de conversaciones manteniendo las más recientes"""
        if len(self.permanent_memory) <= 1:  # Solo system prompt
            return
            
        # Separar system prompt del resto
        system_prompt = self.permanent_memory[0] if self.permanent_memory[0].get("role") == "system" else None
        conversations = self.permanent_memory[1:] if system_prompt else self.permanent_memory
        
        # Contar pares usuario-asistente
        conversation_count = 0
        for msg in reversed(conversations):
            if msg.get("role") == "user":
                conversation_count += 1
                
        # Si excede el límite, mantener solo las más recientes
        if conversation_count > self.max_conversations:
            # Encontrar el punto de corte
            keep_from = 0
            user_count = 0
            
            for i in reversed(range(len(conversations))):
                if conversations[i].get("role") == "user":
                    user_count += 1
                    if user_count == self.max_conversations:
                        keep_from = i
                        break
            
            # Reconstruir memoria permanente
            new_permanent = []
            if system_prompt:
                new_permanent.append(system_prompt)
            new_permanent.extend(conversations[keep_from:])
            
            removed_count = len(self.permanent_memory) - len(new_permanent)
            log.info(f"[MEMORY] Trimmed {removed_count} old messages, keeping {self.max_conversations} conversations")
            
            self.permanent_memory = new_permanent
    
    def save_memory(self):
        """Guarda la memoria permanente a disco"""
        try:
            # Crear directorio si no existe
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Guardar con formato legible
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.permanent_memory, f, indent=2, ensure_ascii=False)
                
            log.debug(f"[MEMORY] Saved {len(self.permanent_memory)} messages to disk")
            
        except Exception as e:
            log.error(f"[MEMORY] Failed to save: {e}")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de memoria"""
        return {
            "permanent_messages": len(self.permanent_memory),
            "session_messages": len(self.session_memory),
            "total_messages": len(self.permanent_memory) + len(self.session_memory),
            "max_conversations": self.max_conversations,
            "memory_file": str(self.memory_file),
            "file_exists": self.memory_file.exists()
        }

# Instancia global
persistent_memory = PersistentMemory()