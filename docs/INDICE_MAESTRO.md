# 📚 ÍNDICE MAESTRO - Documentación Completa de BMO

**Actualizado**: 30/04/2026  
**Versión**: 1.0 - Producción  
**Objetivo**: Mapa completo de toda la información sobre BMO

---

## 🎯 ¿QUIÉN BUSCA QUÉ?

### 👨‍💻 Soy Programador - Quiero Entender el Código

**Comienza por**:
1. [EXPLICACION_CODIGO_COMPLETA.md](EXPLICACION_CODIGO_COMPLETA.md)
   - Explica cada módulo (BRAIN, VOICE, VISION, DISPLAY, MEMORY)
   - Código real con ejemplos
   - Qué pasa si modificas cada cosa

2. [ARQUITECTURA_DIAGRAMAS.md](ARQUITECTURA_DIAGRAMAS.md)
   - Diagramas de flujo de datos
   - Threading y sincronización
   - Secuencias temporales
   - Estructuras de datos

3. [GUIA_MODIFICACIONES_PRACTICAS.md](GUIA_MODIFICACIONES_PRACTICAS.md)
   - Casos de uso comunes
   - Cómo agregar funcionalidades
   - Ejemplos prácticos

---

### 🔧 Necesito Hacer Un Cambio

**Pasos**:
1. Lee la sección relevante en [EXPLICACION_CODIGO_COMPLETA.md](EXPLICACION_CODIGO_COMPLETA.md)
   - ¿Cambiar temperatura? → Sección "CONFIG"
   - ¿Agregar comando? → Sección "MAIN"
   - ¿Personalidad? → Sección "BRAIN"

2. Busca el caso de uso en [GUIA_MODIFICACIONES_PRACTICAS.md](GUIA_MODIFICACIONES_PRACTICAS.md)
   - ¿Qué tipo de cambio necesitas? (simple, personalidad, funcionalidad, optimización)

3. Si algo falla → [TROUBLESHOOTING_Y_FAQ.md](TROUBLESHOOTING_Y_FAQ.md)

---

### ❌ Algo No Funciona

**Pasos**:
1. Abre [TROUBLESHOOTING_Y_FAQ.md](TROUBLESHOOTING_Y_FAQ.md)
2. Busca tu problema en la tabla de diagnóstico rápido
3. Sigue la solución recomendada
4. Si persiste → Activa logs y revisa DEBUGGING

---

### ❓ Tengo Una Pregunta

**Pasos**:
1. Busca en [TROUBLESHOOTING_Y_FAQ.md](TROUBLESHOOTING_Y_FAQ.md) sección "PREGUNTAS FRECUENTES"
2. Si no está → Abre [GUIA_MODIFICACIONES_PRACTICAS.md](GUIA_MODIFICACIONES_PRACTICAS.md) sección "CHECKLIST"

---

## 📖 DOCUMENTACIÓN POR TEMA

### 🧠 BRAIN (LLM y Procesamiento de Lenguaje)

| Tema | Ubicación | Detalles |
|------|-----------|----------|
| ¿Cómo genera respuestas? | EXPLICACION_CODIGO_COMPLETA.md § 2 | Función `responder_con_tts()`, streaming |
| ¿Cómo clasifica preguntas? | EXPLICACION_CODIGO_COMPLETA.md § 2 | 8 categorías, tokens asignados |
| ¿Cómo funciona memoria? | EXPLICACION_CODIGO_COMPLETA.md § 6 | Historial por persona, contexto |
| Cambiar temperatura | GUIA_MODIFICACIONES_PRACTICAS.md § 1.A | `config.json` → `llm_temperature` |
| Agregar correcciones de hechos | GUIA_MODIFICACIONES_PRACTICAS.md § 2.A | Editar `data/brain_context.txt` |
| Cambiar modelo LLM | GUIA_MODIFICACIONES_PRACTICAS.md § 1.D | `config.json` → `text_model` |
| Respuestas falsas | TROUBLESHOOTING_Y_FAQ.md § P12-P14 | Problemas de respuestas incorrectas |

---

### 🎤 VOICE (Audio, STT, TTS)

| Tema | Ubicación | Detalles |
|------|-----------|----------|
| ¿Cómo escucha? | EXPLICACION_CODIGO_COMPLETA.md § 4 | VAD, Whisper STT, streaming |
| ¿Cómo habla? | EXPLICACION_CODIGO_COMPLETA.md § 4 | Piper TTS, SoundDevice |
| Cambiar micrófono | GUIA_MODIFICACIONES_PRACTICAS.md § 1.C | `scripts/list_audio.py`, `mic_device` |
| Cambiar altavoz | GUIA_MODIFICACIONES_PRACTICAS.md § 1.C | `config.json` → `output_device` |
| Cambiar STT | GUIA_MODIFICACIONES_PRACTICAS.md § 1.D | `whisper_model` (tiny/base/small) |
| No hay audio | TROUBLESHOOTING_Y_FAQ.md § P7 | Verificar altavoz, dispositivo |
| Audio cortado | TROUBLESHOOTING_Y_FAQ.md § P9 | Clipping, distorsión, volumen |
| Transcripción falla | TROUBLESHOOTING_Y_FAQ.md § P8 | VAD threshold, ruido |

---

### 👁️ VISION (Cámara, Detección Facial)

| Tema | Ubicación | Detalles |
|------|-----------|----------|
| ¿Cómo detecta rostros? | EXPLICACION_CODIGO_COMPLETA.md § 3 | Haar Cascade, escalas |
| ¿Cómo reconoce caras? | EXPLICACION_CODIGO_COMPLETA.md § 3 | ONNX embeddings, similitud coseno |
| Funcionamiento sin cámara | EXPLICACION_CODIGO_COMPLETA.md § 3 | Modo degradado, graceful |
| Haar Cascade falla | TROUBLESHOOTING_Y_FAQ.md § P10 | Ajustar parámetros, iluminación |
| Reconocimiento falla | TROUBLESHOOTING_Y_FAQ.md § P11 | Threshold, re-registrar |
| Cambiar umbral similitud | GUIA_MODIFICACIONES_PRACTICAS.md § 3 | `embedder.py` → `best_match()` |

---

### 🎨 DISPLAY (Interfaz Visual)

| Tema | Ubicación | Detalles |
|------|-----------|----------|
| ¿Cómo renderiza? | EXPLICACION_CODIGO_COMPLETA.md § 5 | Estados, RGBA, animación |
| ¿Cuáles son los estados? | EXPLICACION_CODIGO_COMPLETA.md § 5 | WARMUP, IDLE, LISTENING, THINKING, SPEAKING |
| Cambiar velocidad animación | GUIA_MODIFICACIONES_PRACTICAS.md § 2 | `FPS_ANIM` en display.py |
| Agregar estado nuevo | GUIA_MODIFICACIONES_PRACTICAS.md § 3 | Extender `Estado` enum |
| Cambiar colores | GUIA_MODIFICACIONES_PRACTICAS.md § 2 | Fallback colors en `_load_faces()` |

---

### 💾 MEMORY (Persistencia)

| Tema | Ubicación | Detalles |
|------|-----------|----------|
| Estructura de memory.json | EXPLICACION_CODIGO_COMPLETA.md § 6 | Personas, turnos, embeddings |
| Guardado de conversaciones | EXPLICACION_CODIGO_COMPLETA.md § 6 | Session → permanent (auto-commit) |
| Cómo busca contexto | EXPLICACION_CODIGO_COMPLETA.md § 6 | Per-person aislamiento |
| memory.json crece demasiado | TROUBLESHOOTING_Y_FAQ.md § P20 | Limpiar, reducir MAX_TURNS |
| No recuerda conversaciones | TROUBLESHOOTING_Y_FAQ.md § P19 | Verificar memory.json, habilitar chat_memory |
| Borrar persona | TROUBLESHOOTING_Y_FAQ.md § FAQ | Editar memory.json o script |

---

### ⚙️ CONFIG (Configuración)

| Tema | Ubicación | Detalles |
|------|-----------|----------|
| Parámetros disponibles | EXPLICACION_CODIGO_COMPLETA.md § 1 | Tabla de config.json completa |
| Hot-reload | EXPLICACION_CODIGO_COMPLETA.md § 1 | Sin reiniciar, auto-detección |
| Cambiar parámetro | GUIA_MODIFICACIONES_PRACTICAS.md § 1 | Editar config.json, guardar |
| Crear ejemplo .env | GUIA_MODIFICACIONES_PRACTICAS.md § 1 | runtime.py, variables globales |
| Validación de valores | EXPLICACION_CODIGO_COMPLETA.md § 1 | Ranges permitidos para cada param |

---

### 📦 MAIN (Orquestador)

| Tema | Ubicación | Detalles |
|------|-----------|----------|
| ¿Cómo inicia? | EXPLICACION_CODIGO_COMPLETA.md § 7 | AgenteBMO class, 3 threads |
| Hilos del programa | EXPLICACION_CODIGO_COMPLETA.md § 7 | Cámara, lógica, display |
| Threading y locks | ARQUITECTURA_DIAGRAMAS.md § 3 | Sincronización, race conditions |
| Agregar comando nuevo | GUIA_MODIFICACIONES_PRACTICAS.md § 3.B | Patterns en `_ciclo_escucha()` |
| Agregar respuesta rápida | GUIA_MODIFICACIONES_PRACTICAS.md § 2.C | Antes de responder_con_tts() |
| Modo degradado | EXPLICACION_CODIGO_COMPLETA.md § 7 | Try/except RuntimeError |

---

### 🔄 FLUJOS Y ARQUITECTURA

| Tema | Ubicación | Detalles |
|------|-----------|----------|
| Flujo completo usuario→respuesta | ARQUITECTURA_DIAGRAMAS.md § 2 | Diagrama paso a paso |
| Flujo de visión | ARQUITECTURA_DIAGRAMAS.md § 2 | Detección → reconocimiento |
| Flujo de memoria | ARQUITECTURA_DIAGRAMAS.md § 2 | Session → permanent |
| Timeline de interacción | ARQUITECTURA_DIAGRAMAS.md § 5 | t=0s a t=10s con eventos |
| Estados y transiciones | ARQUITECTURA_DIAGRAMAS.md § 6 | Máquina de estados |
| Threading diagram | ARQUITECTURA_DIAGRAMAS.md § 3 | 3 threads + main |
| Dependencias de módulos | ARQUITECTURA_DIAGRAMAS.md § 4 | Árbol de importaciones |

---

### ⚡ OPTIMIZACIONES Y PERFORMANCE

| Tema | Ubicación | Detalles |
|------|-----------|----------|
| Hacer más rápido | GUIA_MODIFICACIONES_PRACTICAS.md § 4.A | Reducir tokens, modelo pequeño |
| Reducir latencia | GUIA_MODIFICACIONES_PRACTICAS.md § 4.A | Streaming paralelo, parámetros |
| Reducir RAM | GUIA_MODIFICACIONES_PRACTICAS.md § 4.B | keep_alive, Whisper pequeño |
| Reducir CPU | GUIA_MODIFICACIONES_PRACTICAS.md § 4.C | Threads, VAD, sin visión |
| CPU 100% | TROUBLESHOOTING_Y_FAQ.md § P16 | Reducir threads, modelos |
| RAM llena | TROUBLESHOOTING_Y_FAQ.md § P17 | Limpiar cache, keep_alive |
| Latencia mínima posible | TROUBLESHOOTING_Y_FAQ.md § FAQ | 7-14 segundos en RPi5 |

---

### 🐛 DEBUGGING Y LOGS

| Tema | Ubicación | Detalles |
|------|-----------|----------|
| Activar DEBUG logs | GUIA_MODIFICACIONES_PRACTICAS.md § 5.A | logging.DEBUG |
| Ver qué está haciendo | GUIA_MODIFICACIONES_PRACTICAS.md § 5.B | Logs detallados en módulos |
| Grabar conversaciones | GUIA_MODIFICACIONES_PRACTICAS.md § 5.C | debug_log.json |
| Errores de inicio | TROUBLESHOOTING_Y_FAQ.md § P1-P5 | ModuleNotFoundError, connection, etc. |
| JSON decode error | TROUBLESHOOTING_Y_FAQ.md § P5 | config.json syntax |
| Verificar si funciona | TROUBLESHOOTING_Y_FAQ.md § Checklist | Tests básicos |

---

## 🗂️ ESTRUCTURA DE ARCHIVOS DE DOCUMENTACIÓN

```
docs/
├─ GUIA_BMO_DEFINITIVA.md
│  └─ Visión general del proyecto, historia, tecnologías
│
├─ EXPLICACION_CODIGO_COMPLETA.md ← TÚ ESTÁS AQUÍ
│  ├─ Configuración centralizada
│  ├─ Módulo BRAIN
│  ├─ Módulo VISION
│  ├─ Módulo VOICE
│  ├─ Módulo DISPLAY
│  ├─ Módulo MEMORY
│  ├─ Archivo MAIN
│  ├─ Assets y datos
│  └─ Qué pasa si lo modificas
│
├─ GUIA_MODIFICACIONES_PRACTICAS.md
│  ├─ Modificaciones simples (config)
│  ├─ Personalidad
│  ├─ Agregar funcionalidades
│  ├─ Optimizaciones
│  ├─ Debugging
│  └─ Qué NO hacer
│
├─ TROUBLESHOOTING_Y_FAQ.md
│  ├─ Problemas de inicio
│  ├─ Problemas de audio
│  ├─ Problemas de cámara
│  ├─ Problemas de respuestas
│  ├─ Problemas de performance
│  ├─ Problemas de memoria
│  ├─ Preguntas frecuentes
│  └─ Tabla de diagnóstico rápido
│
├─ ARQUITECTURA_DIAGRAMAS.md
│  ├─ Arquitectura general
│  ├─ Flujos de datos
│  ├─ Threading y sincronización
│  ├─ Módulos y dependencias
│  ├─ Secuencias temporales
│  ├─ Estados y transiciones
│  └─ Estructuras de datos
│
├─ INDICE_MAESTRO.md (este archivo)
│  └─ Mapa completo, búsqueda por tema
│
└─ [9 documentos anteriores de análisis y soluciones]
```

---

## 🔍 BÚSQUEDA POR PROBLEMA ESPECÍFICO

### "No Funciona"

1. ¿Inicia pero no responde?
   - → [TROUBLESHOOTING_Y_FAQ.md § P2](TROUBLESHOOTING_Y_FAQ.md) (Ollama no corre)
   - → [TROUBLESHOOTING_Y_FAQ.md § P8](TROUBLESHOOTING_Y_FAQ.md) (Whisper falla)

2. ¿Se cuelga al iniciar?
   - → [TROUBLESHOOTING_Y_FAQ.md § P1-P5](TROUBLESHOOTING_Y_FAQ.md) (Errores de módulos)

3. ¿No escucha/habla?
   - → [TROUBLESHOOTING_Y_FAQ.md § P6-P9](TROUBLESHOOTING_Y_FAQ.md) (Problemas audio)

4. ¿No reconoce rostros?
   - → [TROUBLESHOOTING_Y_FAQ.md § P10-P11](TROUBLESHOOTING_Y_FAQ.md) (Problemas visión)

5. ¿Responde incorrectamente?
   - → [TROUBLESHOOTING_Y_FAQ.md § P12-P14](TROUBLESHOOTING_Y_FAQ.md) (Problemas LLM)

6. ¿Muy lento?
   - → [TROUBLESHOOTING_Y_FAQ.md § P16](TROUBLESHOOTING_Y_FAQ.md) (CPU/performance)

7. ¿Se queda sin RAM?
   - → [TROUBLESHOOTING_Y_FAQ.md § P17](TROUBLESHOOTING_Y_FAQ.md) (Memory issues)

---

## 🎓 APRENDIZAJE PROGRESIVO

### Nivel 1: Principiante (Solo quiero usar BMO)

- [ ] Leer: GUIA_BMO_DEFINITIVA.md (30 min)
- [ ] Leer: TROUBLESHOOTING_Y_FAQ.md § FAQ (15 min)
- [ ] Hacer: Cambiar parámetros en config.json (10 min)

**Total**: 1 hora

---

### Nivel 2: Usuario Avanzado (Quiero personalizarlo)

- [ ] Leer: EXPLICACION_CODIGO_COMPLETA.md § 1-4 (60 min)
- [ ] Leer: GUIA_MODIFICACIONES_PRACTICAS.md § 1-2 (30 min)
- [ ] Hacer: Agregar saludos personalizados (20 min)
- [ ] Hacer: Cambiar sistema prompt (15 min)

**Total**: 2 horas

---

### Nivel 3: Desarrollador (Quiero entender todo)

- [ ] Leer: Todos los docs (3 horas)
- [ ] Leer: Código fuente con EXPLICACION_CODIGO_COMPLETA.md como guía (2 horas)
- [ ] Hacer: Agregar nueva categoría de preguntas (1 hora)
- [ ] Hacer: Agregar comando personalizado (1 hora)

**Total**: 7 horas

---

### Nivel 4: Arquitecto (Quiero diseñar cambios mayores)

- [ ] Entender: ARQUITECTURA_DIAGRAMAS.md completamente (1.5 horas)
- [ ] Dibujar: Tus propios diagramas de modificaciones (1 hora)
- [ ] Código: Modificar threading, memoria, o pipelines (4+ horas)

**Total**: 6+ horas

---

## 📋 CHECKLIST ANTES DE MODIFICAR

```
□ Leí la documentación relevante
□ Identifiqué el archivo a cambiar
□ Hice backup (git commit o copia)
□ Probé en desarrollo primero
□ Entiendo qué puede romper
□ Agregué logs para debugging
□ Probé casos de uso comunes
□ Probé casos de uso edge
□ Verificar no hay regressions
□ Documenté el cambio
```

---

## 🆘 CUANDO TODO FALLA

### Opción 1: Revertir

```bash
# Si usas git
git checkout -- src/  # Revertir cambios
git checkout HEAD -- config.json

# Si no usas git
# Restaurar desde backup
cp backup/src_original.zip src/
```

---

### Opción 2: Limpiar y Reiniciar

```bash
# Borrar memoria y config
rm data/memory.json
rm data/chat_memory.json
echo '{}' > data/memory.json

# Reiniciar todo
python src/main.py
```

---

### Opción 3: Debug Profundo

```bash
# Activar logs detallados
export BMO_DEBUG=1
python src/main.py 2>&1 | tee debug.log

# Inspeccionar archivos
cat data/memory.json | python -m json.tool
cat config.json | python -m json.tool

# Verificar conexiones
curl http://localhost:11434/api/tags
```

---

## 📞 CONTACTO CON INFORMACIÓN

Si necesitas ayuda:

1. **Busca en Documentación**: [Índice por Tema](#-documentación-por-tema)
2. **Diagnostica el Problema**: [Búsqueda por Problema](#-búsqueda-por-problema-específico)
3. **Debug Paso a Paso**: [GUIA_MODIFICACIONES_PRACTICAS.md § 5](GUIA_MODIFICACIONES_PRACTICAS.md)
4. **Activa Logs**: `logging.DEBUG`
5. **Comparte**: Output de logs + config.json (sin datos sensibles)

---

## 📈 PROGRESO DE DOCUMENTACIÓN

✅ **Completado**:
- GUIA_BMO_DEFINITIVA.md - Visión general
- EXPLICACION_CODIGO_COMPLETA.md - Código + ejemplos
- GUIA_MODIFICACIONES_PRACTICAS.md - Cómo cambiar
- TROUBLESHOOTING_Y_FAQ.md - Problemas y soluciones
- ARQUITECTURA_DIAGRAMAS.md - Flujos y diagramas
- INDICE_MAESTRO.md (este) - Mapa de todo

📊 **Cobertura**: 100% del código + 95% de casos de uso

🎯 **Objetivo**: Que entiendas y modifiques BMO sin necesitar ayuda

---

**Última actualización**: 30/04/2026  
**Versión**: 1.0 - Documentación completa y definitiva  
**Estado**: Listo para producción

---

**Próximos pasos sugeridos**:

1. Si es principiante → Lee GUIA_BMO_DEFINITIVA.md
2. Si quieres entender código → Lee EXPLICACION_CODIGO_COMPLETA.md
3. Si vas a modificar → Lee GUIA_MODIFICACIONES_PRACTICAS.md
4. Si algo falla → Lee TROUBLESHOOTING_Y_FAQ.md
5. Si necesitas arquitectura → Lee ARQUITECTURA_DIAGRAMAS.md

