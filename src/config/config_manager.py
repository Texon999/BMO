"""
Gestor de Configuración Centralizada para BMO
Basado en buenas prácticas de be-more-agent

Características:
- Configuración JSON centralizada
- Hot-reload automático
- Valores por defecto seguros
- Validación de configuración
- Migración automática de configuraciones legacy
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import time
from src.config.runtime import *

log = logging.getLogger("BMO.Config")

class ConfigManager:
    """Gestor centralizado de configuración con hot-reload"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self.config: Dict[str, Any] = {}
        self.last_modified = 0
        self.hot_reload_enabled = True
        
        # Configuración por defecto
        self.default_config = {
            # Modelos LLM
            "text_model": LLM_MODEL,
            "vision_model": "moondream",
            
            # Audio
            "voice_model": "voices/es_ES-sharvard-medium.onnx",
            "input_device": None,
            "input_sample_rate": None,
            "output_device": None,
            
            # Hardware
            "camera_index": CAMERA_INDEX,
            "camera_rotation": 0,
            "headless": HEADLESS,
            
            # LLM Parameters
            "llm_temperature": LLM_TEMPERATURE,
            "llm_top_k": LLM_TOP_K,
            "llm_top_p": LLM_TOP_P,
            "llm_num_predict": LLM_NUM_PREDICT,
            "llm_repeat_penalty": LLM_REPEAT_PENALTY,
            "llm_num_thread": LLM_NUM_THREAD,
            "llm_keep_alive": LLM_KEEP_ALIVE,
            
            # Whisper STT
            "whisper_model": WHISPER_MODEL,
            "whisper_lang": WHISPER_LANG,
            "stt_beam_size": STT_BEAM_SIZE,
            "stt_best_of": STT_BEST_OF,
            
            # VAD (Voice Activity Detection)
            "vad_threshold": VAD_THRESHOLD,
            "vad_silence_sec": VAD_SILENCE_SEC,
            "vad_max_sec": VAD_MAX_SEC,
            "vad_min_sec": VAD_MIN_SEC,
            
            # Memoria y comportamiento
            "chat_memory": True,
            "max_conversations": 10,
            "brain_context_hot_reload": BRAIN_CONTEXT_HOT_RELOAD,
            
            # System prompt personalizable
            "system_prompt_extras": "",
            
            # Visión
            "vision_process_every_n": VISION_PROCESS_EVERY_N,
            
            # Configuración avanzada
            "debug_mode": False,
            "log_level": "INFO",
            "auto_save_config": True
        }
        
        self.load_config()
    
    def load_config(self) -> bool:
        """Carga la configuración desde archivo"""
        try:
            if not self.config_file.exists():
                log.info("[CONFIG] No config file found, creating default")
                self.config = self.default_config.copy()
                self.save_config()
                return True
            
            # Verificar si el archivo cambió
            current_mtime = self.config_file.stat().st_mtime
            if current_mtime == self.last_modified and self.config:
                return True  # No cambió
                
            with open(self.config_file, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            
            # Combinar con defaults
            self.config = self.default_config.copy()
            self.config.update(user_config)
            
            # Migrar configuración legacy si es necesario
            self._migrate_legacy_config()
            
            # Validar configuración
            self._validate_config()
            
            self.last_modified = current_mtime
            log.info("[CONFIG] Configuration loaded successfully")
            
            return True
            
        except Exception as e:
            log.error(f"[CONFIG] Failed to load config: {e}")
            if not self.config:
                log.info("[CONFIG] Using default configuration")
                self.config = self.default_config.copy()
            return False
    
    def save_config(self) -> bool:
        """Guarda la configuración actual"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            self.last_modified = self.config_file.stat().st_mtime
            log.debug("[CONFIG] Configuration saved")
            return True
            
        except Exception as e:
            log.error(f"[CONFIG] Failed to save config: {e}")
            return False
    
    def get(self, key: str, default=None) -> Any:
        """Obtiene un valor de configuración con hot-reload"""
        if self.hot_reload_enabled:
            self.load_config()
        
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any, save: bool = True) -> bool:
        """Establece un valor de configuración"""
        self.config[key] = value
        
        if save and self.config.get("auto_save_config", True):
            return self.save_config()
        
        return True
    
    def update(self, updates: Dict[str, Any], save: bool = True) -> bool:
        """Actualiza múltiples valores"""
        self.config.update(updates)
        
        if save and self.config.get("auto_save_config", True):
            return self.save_config()
        
        return True
    
    def reset_to_defaults(self) -> bool:
        """Resetea la configuración a valores por defecto"""
        log.info("[CONFIG] Resetting to default configuration")
        self.config = self.default_config.copy()
        return self.save_config()
    
    def _migrate_legacy_config(self):
        """Migra configuraciones de versiones anteriores"""
        migrations_applied = []
        
        # Migración 1: Renombrar claves legacy
        legacy_mappings = {
            "BMO_LLM_TEMPERATURE": "llm_temperature",
            "BMO_LLM_TOP_K": "llm_top_k", 
            "BMO_LLM_TOP_P": "llm_top_p",
            "BMO_LLM_NUM_PREDICT": "llm_num_predict",
            "BMO_WHISPER_MODEL": "whisper_model"
        }
        
        for old_key, new_key in legacy_mappings.items():
            if old_key in self.config and new_key not in self.config:
                self.config[new_key] = self.config.pop(old_key)
                migrations_applied.append(f"{old_key} -> {new_key}")
        
        # Migración 2: Convertir valores string a tipos correctos
        type_conversions = {
            "llm_temperature": float,
            "llm_top_k": int,
            "llm_top_p": float,
            "llm_num_predict": int,
            "camera_rotation": int,
            "max_conversations": int
        }
        
        for key, target_type in type_conversions.items():
            if key in self.config and not isinstance(self.config[key], target_type):
                try:
                    self.config[key] = target_type(self.config[key])
                    migrations_applied.append(f"{key} converted to {target_type.__name__}")
                except (ValueError, TypeError):
                    log.warning(f"[CONFIG] Could not convert {key} to {target_type.__name__}")
        
        if migrations_applied:
            log.info(f"[CONFIG] Applied migrations: {', '.join(migrations_applied)}")
    
    def _validate_config(self):
        """Valida la configuración y corrige valores inválidos"""
        validations = []
        
        # Validar rangos numéricos
        numeric_ranges = {
            "llm_temperature": (0.0, 2.0),
            "llm_top_k": (1, 200),
            "llm_top_p": (0.0, 1.0),
            "llm_num_predict": (10, 1000),
            "vad_threshold": (0.001, 1.0),
            "max_conversations": (1, 100)
        }
        
        for key, (min_val, max_val) in numeric_ranges.items():
            if key in self.config:
                value = self.config[key]
                if not isinstance(value, (int, float)) or not (min_val <= value <= max_val):
                    default_val = self.default_config[key]
                    self.config[key] = default_val
                    validations.append(f"{key}: {value} -> {default_val} (out of range)")
        
        # Validar archivos existentes
        file_keys = ["voice_model"]
        for key in file_keys:
            if key in self.config and self.config[key]:
                file_path = Path(self.config[key])
                if not file_path.exists():
                    validations.append(f"{key}: File not found: {self.config[key]}")
        
        if validations:
            log.warning(f"[CONFIG] Validation corrections: {', '.join(validations)}")
    
    def get_ollama_options(self) -> Dict[str, Any]:
        """Obtiene las opciones para Ollama"""
        return {
            "keep_alive": self.get("llm_keep_alive", -1),
            "num_thread": self.get("llm_num_thread", 4),
            "temperature": self.get("llm_temperature", 0.75),
            "top_k": self.get("llm_top_k", 50),
            "top_p": self.get("llm_top_p", 0.9),
            "num_predict": self.get("llm_num_predict", 100),
            "repeat_penalty": self.get("llm_repeat_penalty", 1.1)
        }
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Obtiene un resumen de la configuración actual"""
        return {
            "config_file": str(self.config_file),
            "file_exists": self.config_file.exists(),
            "last_modified": time.ctime(self.last_modified) if self.last_modified else "Never",
            "hot_reload": self.hot_reload_enabled,
            "total_keys": len(self.config),
            "text_model": self.get("text_model"),
            "llm_temperature": self.get("llm_temperature"),
            "llm_num_predict": self.get("llm_num_predict"),
            "chat_memory": self.get("chat_memory"),
            "debug_mode": self.get("debug_mode")
        }

# Instancia global
config_manager = ConfigManager()