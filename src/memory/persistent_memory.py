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
                "Eres BMO, un robot asistente amigable creado por Zambrano, un programador del SENA. "
                "Responde siempre en español de forma natural y conversacional. "
                "REGLAS DE LONGITUD: preguntas cortas o saludos → 1 oración; "
                "preguntas simples de dato → 1-2 oraciones; "
                "preguntas que piden explicación → máximo 3-4 oraciones. "
                "NUNCA cortes una respuesta a la mitad, si no cabe resume. "
                "No uses listas con viñetas ni markdown, habla natural. "
                "Si te preguntan cómo estás, responde algo como 'Muy bien, listo para ayudarte!'. "
                "Si te preguntan sobre Hora de Aventura, usa tu conocimiento de la serie. "
                "La bandera de Colombia: amarillo arriba, azul medio, rojo abajo. "
                "Capital de Brasil: Brasilia. "
                "Si no estás seguro de un dato, di 'No tengo esa información'."
            ),
            "timestamp": datetime.now().isoformat()
        }
        
        if self.permanent_memory and self.permanent_memory[0].get("role") == "system":
            self.permanent_memory[0] = system_prompt
        else:
            self.permanent_memory.insert(0, system_prompt)
    
    def add_user_message(self, content: str, persona: str | None = None):
        """Agrega un mensaje del usuario.
        
        - Sin persona (anónimo): la sesión solo guarda el último intercambio
          (sobrescribe) para no acumular contexto de desconocidos.
        - Con persona registrada: acumula normalmente en sesión.
        """
        message = {
            "role": "user",
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        if persona:
            message["persona"] = persona
            self.session_memory.append(message)
        else:
            # Anónimo: solo conservar el último mensaje de usuario
            # (eliminar mensajes anteriores de sesión para no acumular)
            self.session_memory = [message]
            
        log.debug(f"[MEMORY] Added user message (persona={persona}): {content[:50]}...")
    
    def add_assistant_message(self, content: str, persona: str | None = None):
        """Agrega un mensaje del asistente."""
        message = {
            "role": "assistant", 
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        self.session_memory.append(message)
        log.debug(f"[MEMORY] Added assistant message: {content[:50]}...")    
    def get_context_for_llm(self, persona: str | None = None) -> list[dict]:
        """Obtiene el contexto completo para el LLM.
        
        - Con persona: system prompt + historial permanente de esa persona + sesión actual.
        - Sin persona (anónimo): system prompt + solo el último mensaje de sesión
          (no se acumula historial de desconocidos).
        """
        context = []
        
        # System prompt (siempre primero)
        if self.permanent_memory and self.permanent_memory[0].get("role") == "system":
            system_msg = self.permanent_memory[0].copy()
            if persona:
                system_msg["content"] += f" El usuario se llama {persona}."
            context.append(system_msg)
        
        if persona:
            # Con persona: incluir historial permanente filtrado por esa persona
            persona_history = [
                m for m in self.permanent_memory[1:]
                if m.get("persona") == persona or m.get("role") == "assistant"
                   or "persona" not in m
            ]
            # Limitar a las últimas MAX_PERSONA_HISTORY_MSGS para no saturar el contexto
            MAX_PERSONA_HISTORY_MSGS = 6  # 3 intercambios del historial permanente
            if len(persona_history) > MAX_PERSONA_HISTORY_MSGS:
                persona_history = persona_history[-MAX_PERSONA_HISTORY_MSGS:]
            context.extend(persona_history)
            
            # Sesión actual: limitar a los últimos 4 mensajes (2 intercambios recientes)
            MAX_SESSION_MSGS = 4
            session_reciente = self.session_memory[-MAX_SESSION_MSGS:] if len(self.session_memory) > MAX_SESSION_MSGS else self.session_memory
            context.extend(session_reciente)
        else:
            # Anónimo: solo el último mensaje de sesión (ya fue sobrescrito en add_user_message)
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
    
    def commit_session_to_permanent(self, persona: str | None = None):
        """Mueve la memoria de sesión a permanente.
        
        Solo persiste si hay una persona registrada (cara conocida).
        Las conversaciones anónimas no se guardan en permanente.
        """
        if not self.session_memory:
            return
        
        if persona is None:
            # Sin persona registrada: no persistir, solo limpiar sesión
            log.debug("[MEMORY] Sesión anónima, no se persiste en permanente")
            self.session_memory = []
            return
            
        log.info(f"[MEMORY] Guardando {len(self.session_memory)} mensajes de '{persona}' en permanente")
        
        # Etiquetar mensajes de usuario con la persona
        for msg in self.session_memory:
            if msg.get("role") == "user" and "persona" not in msg:
                msg["persona"] = persona
        
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
    
    def get_memory_stats(self) -> dict:
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