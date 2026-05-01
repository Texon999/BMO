# OPTIMIZACIONES ESPECÍFICAS PARA RPi 5 8GB

## 1. FIX INMEDIATO: TTS Corta Palabras

**Archivo:** `src/voice/voice.py`  
**Líneas:** 127-128

**Problema:** El silencio se agrega después de generar audio, causando cortes.

**Cambio:**

```python
# ANTES (líneas 127-128)
silencio = np.zeros(int(0.3 * sr), dtype="float32")
audio_np = np.concatenate([audio_np, silencio])

# DESPUÉS
silencio_pre = np.zeros(int(0.1 * sr), dtype="float32")
silencio_post = np.zeros(int(0.5 * sr), dtype="float32")
audio_np = np.concatenate([silencio_pre, audio_np, silencio_post])
```

**Impacto:** Elimina cortes de palabras al final.

---

## 2. FIX: Respuestas Predefinidas No Funcionan

**Archivo:** `src/brain/brain.py`  
**Líneas:** 60-90

**Problema:** Patrones regex muy específicos, fallan con variaciones.

**Cambio:**

```python
RESPUESTAS_PREDEFINIDAS = {
    # Preguntas sobre Finn
    r"(?:quién|quien)\s+(?:es|eres)\s+(?:finn|fin)": 
        "Finn es el héroe principal de Ooo, un chico valiente de 14 años. Es el mejor amigo de Jake el Perro y viven muchas aventuras juntos.",
    r"(?:qué|que)\s+(?:es|eres)\s+(?:finn|fin)":
        "Finn es un humano valiente que vive en Ooo. Es el protagonista de Adventure Time y siempre está buscando aventuras con su hermano Jake.",
    
    # Preguntas sobre Jake
    r"(?:quién|quien)\s+(?:es|eres)\s+(?:jake|el\s+perro)":
        "Jake es un perro mágico que puede estirarse y cambiar de forma. Es el hermano adoptivo de Finn y su mejor amigo.",
    r"(?:qué|que)\s+(?:es|eres)\s+(?:jake|el\s+perro)":
        "Jake es un perro mágico con poderes especiales. Puede estirarse, cambiar de forma y es muy sabio. Vive con Finn en el Árbol Casa.",
    
    # Preguntas sobre Princesa Chicle
    r"(?:quién|quien)\s+(?:es|eres)\s+(?:princesa\s+chicle|princesa\s+bubblegum)":
        "Princesa Chicle es la gobernante del Reino de los Dulces. Es muy inteligente y científica, y crea muchas cosas increíbles.",
    
    # Preguntas sobre Marceline
    r"(?:quién|quien)\s+(?:es|eres)\s+(?:marceline|la\s+reina\s+vampiro)":
        "Marceline es una vampira de 1000 años que ama la música. Es amiga de Finn y Jake, y toca la guitarra muy bien.",
    
    # Preguntas sobre Ice King
    r"(?:quién|quien)\s+(?:es|eres)\s+(?:ice\s+king|el\s+rey\s+hielo)":
        "Ice King es un mago que controla el hielo. Antes era un humano llamado Simon Petrikov, pero una corona mágica lo volvió loco.",
    
    # Preguntas sobre Ooo
    r"(?:qué|que)\s+(?:es|eres)\s+(?:ooo|el\s+mundo)":
        "Ooo es el mundo donde ocurre Adventure Time. Es un lugar post-apocalíptico lleno de magia, misterios y aventuras.",
    r"(?:dónde|donde)\s+(?:ocurre|pasa)\s+(?:adventure\s+time|la\s+serie)":
        "Adventure Time ocurre en Ooo, un mundo mágico y post-apocalíptico. Finn y Jake viven en el Árbol Casa.",
    
    # Preguntas sobre BMO
    r"(?:quién|quien)\s+(?:eres|soy)":
        "Soy BMO, un robot asistente creado por Juan David Zambrano. Tengo el aspecto de BMO de Adventure Time y estoy aquí para ayudarte.",
    r"(?:cómo|como)\s+te\s+llamas":
        "Me llamo BMO. Soy un robot asistente con el aspecto de BMO de la serie Adventure Time.",
    r"(?:qué|que)\s+eres":
        "Soy BMO, un robot asistente de IA. Puedo hablar contigo, reconocer caras y responder preguntas sobre Adventure Time.",
}
```

**Cambios clave:**
- Usar `(?:...)` para grupos no capturadores (más eficiente)
- Usar `\s+` para espacios flexibles
- Patrones más generales que capturan variaciones

**Impacto:** Respuestas predefinidas funcionan correctamente.

---

## 3. CAMBIO DE MODELO: Qwen 2.5:1.5B

**Archivo:** `src/brain/brain.py`  
**Línea:** 18

**Cambio:**

```python
# ANTES
MODEL = "qwen2.5:1.5b"

# DESPUÉS (ya está, pero confirmar)
MODEL = "qwen2.5:1.5b"
```

**Configuración de Ollama:**

```python
OLLAMA_OPTIONS = {
    "keep_alive": 300,        # Descargar modelo después de 5 min inactividad
    "num_thread": 4,          # Usar 4 threads (RPi 5 tiene 8 cores)
    "temperature": 0.75,      # Reducir de 0.85 a 0.75 (menos alucinaciones)
    "top_k": 50,              # Aumentar de 40 a 50 (más opciones coherentes)
    "top_p": 0.90,
    "num_predict": 100,       # Reducir de 150 a 100 (respuestas más cortas)
    "repeat_penalty": 1.15,
}
```

**Instalación en RPi 5:**

```bash
ollama pull qwen2.5:1.5b
```

**Impacto:**
- Mejor calidad de respuestas
- Menos alucinaciones
- Latencia aceptable (6-10s)

---

## 4. OPTIMIZACIÓN: Reducir Consumo de RAM

**Archivo:** `src/brain/brain.py`  
**Línea:** 20-30

**Cambio:**

```python
OLLAMA_OPTIONS = {
    "keep_alive": 300,        # Descargar modelo después de 5 min inactividad
    "num_thread": 3,          # Reducir de 4 a 3 si RAM es crítica
    "temperature": 0.75,
    "top_k": 50,
    "top_p": 0.90,
    "num_predict": 80,        # Reducir de 100 a 80 si necesitas más buffer
    "repeat_penalty": 1.15,
}
```

**Impacto:**
- Ahorro de ~0.2-0.3GB RAM
- Latencia ligeramente mayor (+1-2s)
- Mejor estabilidad en RPi 5

---

## 5. MEJORA: Prompt Más Específico

**Archivo:** `src/brain/brain.py`  
**Líneas:** 32-45

**Cambio:**

```python
SYSTEM_PROMPT = (
    "Eres BMO, un robot asistente de IA creado por Juan David Zambrano. "
    "Tienes el aspecto de BMO de Adventure Time y conoces esa serie. "
    "Respondes siempre en español, de forma directa y amable en 2-3 oraciones. "
    "No actúas ni haces roleplay. Eres un asistente, no un personaje. "
    "Si no sabes algo, dilo honestamente. No inventes información. "
    "IMPORTANTE: Nunca inventes hechos sobre Adventure Time. "
    "Sobre Adventure Time: "
    "- Finn es el héroe humano de Ooo, valiente, 14 años, mejor amigo de Jake. "
    "- Jake es un perro mágico que puede estirarse, hermano adoptivo de Finn. "
    "- Princesa Chicle gobierna el Reino de los Dulces. "
    "- Marceline es una vampira de 1000 años que ama la música. "
    "- Ice King era Simon Petrikov, un humano que enloqueció por una corona mágica. "
    "- Ooo es el mundo post-apocalíptico donde ocurre la serie. "
    "- Finn NUNCA destruye a Marceline. Son amigos. "
    "- Jake NUNCA pelea contra Finn. Son hermanos. "
)
```

**Cambios clave:**
- Agregar "IMPORTANTE" para énfasis
- Agregar negaciones explícitas de alucinaciones comunes
- Más específico sobre relaciones entre personajes

**Impacto:** Reduce alucinaciones en Qwen.

---

## 6. MONITOREO: Script para Verificar RAM

**Archivo:** `scripts/monitor_ram.py` (crear nuevo)

```python
#!/usr/bin/env python3
"""
Monitorea consumo de RAM durante ejecución de BMO.
Útil para verificar que no hay memory leaks.
"""
import psutil
import time
import sys

def monitor_ram(interval=5, duration=300):
    """Monitorea RAM cada `interval` segundos durante `duration` segundos."""
    print(f"Monitoreando RAM cada {interval}s durante {duration}s...")
    print("Tiempo(s) | RAM Total | RAM Usada | RAM Libre | % Usado")
    print("-" * 60)
    
    start_time = time.time()
    while time.time() - start_time < duration:
        mem = psutil.virtual_memory()
        elapsed = int(time.time() - start_time)
        print(f"{elapsed:8d} | {mem.total/1e9:8.1f}GB | {mem.used/1e9:8.1f}GB | {mem.available/1e9:8.1f}GB | {mem.percent:6.1f}%")
        time.sleep(interval)

if __name__ == "__main__":
    try:
        monitor_ram()
    except KeyboardInterrupt:
        print("\nMonitoreo detenido.")
        sys.exit(0)
```

**Uso:**

```bash
python scripts/monitor_ram.py
```

---

## 7. CHECKLIST DE IMPLEMENTACIÓN

- [ ] Fix TTS (agregar silencio pre/post)
- [ ] Fix regex de respuestas predefinidas
- [ ] Cambiar modelo a Qwen 2.5:1.5B
- [ ] Ajustar OLLAMA_OPTIONS
- [ ] Mejorar SYSTEM_PROMPT
- [ ] Crear script de monitoreo
- [ ] Testear en RPi 5
- [ ] Verificar latencia total
- [ ] Verificar consumo de RAM
- [ ] Verificar estabilidad (24h de operación)

---

## 8. BENCHMARKS ESPERADOS EN RPi 5

### Configuración Recomendada: Qwen 2.5:1.5B

| Operación | Tiempo | Notas |
|-----------|--------|-------|
| Warmup | 3s | Carga inicial |
| STT (10s audio) | 6-10s | Whisper base |
| LLM (50 tokens) | 6-10s | Qwen 2.5:1.5B |
| TTS (oración típica) | 2-3s | Piper |
| **Total respuesta** | **14-23s** | Aceptable |
| RAM pico | ~6.5GB | Con buffer |
| CPU promedio | 70-80% | 4 threads |

### Alternativa Rápida: Phi 3.5 Mini int4

| Operación | Tiempo | Notas |
|-----------|--------|-------|
| STT (10s audio) | 6-10s | Whisper base |
| LLM (50 tokens) | 3-5s | Phi 3.5 Mini int4 |
| TTS (oración típica) | 2-3s | Piper |
| **Total respuesta** | **11-18s** | Más rápido |
| RAM pico | ~5.5GB | Menos RAM |
| CPU promedio | 60-70% | Menos carga |

---

## 9. TROUBLESHOOTING

### Problema: "Out of Memory"

**Solución:**
1. Reducir `num_predict` a 60
2. Reducir `num_thread` a 2
3. Usar `keep_alive: 60` (descargar modelo más rápido)
4. Considerar Phi 3.5 Mini int4

### Problema: "Respuestas muy lentas"

**Solución:**
1. Cambiar a Phi 3.5 Mini int4
2. Reducir `num_predict` a 80
3. Aumentar `num_thread` a 4 (si hay RAM)

### Problema: "Alucinaciones frecuentes"

**Solución:**
1. Reducir `temperature` a 0.7
2. Aumentar `top_k` a 60
3. Mejorar SYSTEM_PROMPT
4. Usar respuestas predefinidas más agresivamente

### Problema: "TTS sigue cortando palabras"

**Solución:**
1. Aumentar silencio_post a 0.7s
2. Verificar que sounddevice está actualizado
3. Probar con dispositivo de audio diferente

---

## 10. PRÓXIMOS PASOS

1. **Implementar fixes inmediatos** (TTS, regex)
2. **Cambiar a Qwen 2.5:1.5B**
3. **Testear en RPi 5 real**
4. **Monitorear RAM y latencia**
5. **Ajustar parámetros según resultados**
6. **Documentar configuración final**

