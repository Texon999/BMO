"""
Gestor de Audio Robusto para BMO
Basado en buenas prácticas de be-more-agent

Características:
- Auto-detección de dispositivos y sample rates
- Manejo robusto de errores ALSA
- Liberación explícita de recursos
- Fallbacks automáticos para compatibilidad
"""
import logging
import sounddevice as sd
import numpy as np
from typing import Optional, Tuple
import time

log = logging.getLogger("BMO.Audio")

class AudioManager:
    """Gestor robusto de audio con auto-detección y fallbacks"""
    
    def __init__(self):
        self.input_device = None
        self.output_device = None
        self.input_sample_rate = None
        self.output_sample_rate = None
        self._initialized = False
        
    def initialize(self, preferred_input_device=None, preferred_sample_rate=None):
        """Inicializa el sistema de audio con auto-detección"""
        try:
            self.input_device = self._resolve_input_device(preferred_input_device)
            self.input_sample_rate = self._choose_input_samplerate(
                self.input_device, preferred_sample_rate
            )
            self.output_sample_rate = self._get_output_samplerate()
            
            log.info(f"[AUDIO] Input: Device {self.input_device}, Rate {self.input_sample_rate}Hz")
            log.info(f"[AUDIO] Output: Rate {self.output_sample_rate}Hz")
            
            self._initialized = True
            return True
            
        except Exception as e:
            log.error(f"[AUDIO] Initialization failed: {e}")
            return False
    
    def _resolve_input_device(self, requested_device) -> Optional[int]:
        """Resuelve el dispositivo de entrada con fallbacks"""
        if requested_device in (None, "", "default"):
            return None
            
        try:
            devices = sd.query_devices()
        except Exception as e:
            log.warning(f"[AUDIO] Device query failed: {e}")
            return None
            
        # Si es un índice numérico
        if isinstance(requested_device, int) or (
            isinstance(requested_device, str) and requested_device.isdigit()
        ):
            index = int(requested_device)
            if 0 <= index < len(devices):
                return index
            log.warning(f"[AUDIO] Device index {index} not found")
            return None
            
        # Si es un nombre de dispositivo
        requested_lower = str(requested_device).lower()
        for idx, dev in enumerate(devices):
            if (dev.get("max_input_channels", 0) > 0 and 
                requested_lower in dev.get("name", "").lower()):
                log.info(f"[AUDIO] Found device: {dev.get('name')}")
                return idx
                
        log.warning(f"[AUDIO] Device '{requested_device}' not found")
        return None
    
    def _choose_input_samplerate(self, device, preferred=None) -> int:
        """Elige el sample rate óptimo con fallbacks"""
        candidates = []
        
        # Agregar preferencia del usuario
        if preferred:
            candidates.append(preferred)
            
        # Obtener sample rate por defecto del dispositivo
        try:
            device_info = sd.query_devices(device)
            if "default_samplerate" in device_info:
                candidates.append(int(device_info["default_samplerate"]))
        except Exception:
            pass
            
        # Agregar rates comunes
        candidates.extend([48000, 44100, 32000, 16000])
        
        # Probar cada candidato
        seen = set()
        for rate in candidates:
            if not rate or rate in seen:
                continue
            seen.add(rate)
            
            try:
                sd.check_input_settings(
                    device=device, 
                    samplerate=rate, 
                    channels=1, 
                    dtype="int16"
                )
                return rate
            except Exception:
                continue
                
        # Fallback final
        return 44100
    
    def _get_output_samplerate(self) -> int:
        """Obtiene el sample rate óptimo para salida"""
        try:
            device_info = sd.query_devices(kind='output')
            return int(device_info['default_samplerate'])
        except Exception:
            return 48000
    
    def create_input_stream(self, callback, blocksize=1024, **kwargs):
        """Crea un stream de entrada robusto con fallbacks"""
        if not self._initialized:
            raise RuntimeError("AudioManager not initialized")
            
        stream_args = {
            "samplerate": self.input_sample_rate,
            "channels": 1,
            "dtype": "int16",
            "device": self.input_device,
            "callback": callback,
            "blocksize": blocksize,
            **kwargs
        }
        
        # Primer intento: configuración estándar
        try:
            return sd.InputStream(**stream_args)
        except Exception as e:
            log.warning(f"[AUDIO] Standard stream failed: {e}")
            
        # Segundo intento: blocksize automático
        try:
            stream_args["blocksize"] = 0
            stream_args["latency"] = "high"
            return sd.InputStream(**stream_args)
        except Exception as e:
            log.warning(f"[AUDIO] Auto-blocksize failed: {e}")
            
        # Tercer intento: configuración mínima
        try:
            stream_args.update({
                "blocksize": 512,
                "latency": "high",
                "device": None  # Usar dispositivo por defecto
            })
            return sd.InputStream(**stream_args)
        except Exception as e:
            log.error(f"[AUDIO] All stream attempts failed: {e}")
            raise
    
    def create_output_stream(self, **kwargs):
        """Crea un stream de salida optimizado"""
        stream_args = {
            "samplerate": self.output_sample_rate,
            "channels": 1,
            "dtype": "int16",
            "latency": "low",
            "blocksize": 2048,
            **kwargs
        }
        
        try:
            return sd.RawOutputStream(**stream_args)
        except Exception as e:
            log.warning(f"[AUDIO] Output stream failed: {e}")
            # Fallback con configuración básica
            stream_args.update({
                "latency": "high",
                "blocksize": 4096
            })
            return sd.RawOutputStream(**stream_args)
    
    def stop_all_streams(self):
        """Detiene todos los streams activos"""
        try:
            sd.stop()
            time.sleep(0.2)  # Dar tiempo para liberación de recursos
        except Exception as e:
            log.warning(f"[AUDIO] Error stopping streams: {e}")
    
    def test_audio_system(self) -> bool:
        """Prueba el sistema de audio completo"""
        if not self._initialized:
            return False
            
        try:
            # Probar entrada
            def dummy_callback(indata, frames, time, status):
                pass
                
            with self.create_input_stream(dummy_callback):
                time.sleep(0.1)
                
            # Probar salida
            test_audio = np.zeros(1024, dtype=np.int16)
            with self.create_output_stream() as stream:
                stream.write(test_audio.tobytes())
                
            log.info("[AUDIO] System test passed")
            return True
            
        except Exception as e:
            log.error(f"[AUDIO] System test failed: {e}")
            return False

# Instancia global
audio_manager = AudioManager()