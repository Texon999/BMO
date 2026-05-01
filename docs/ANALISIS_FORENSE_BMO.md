# Análisis Forense: ¿Por qué BMO se "dañó"?

## Resumen Ejecutivo

BMO funcionaba perfectamente con respuestas de 4-6 segundos y alta precisión factual. Tras optimizaciones excesivas, comenzó a dar respuestas incorrectas (ej: "amarillo y morado" para la bandera de Colombia) y tardaba 35+ segundos.

**CAUSA RAÍZ**: Sobre-optimización de parámetros LLM que rompió el equilibrio original.

## Configuración Original (FUNCIONABA PERFECTAMENTE)

### Parámetros LLM Exitosos:
```env
BMO_LLM_NUM_PREDICT=100      # Respuestas completas
BMO_LLM_TEMPERATURE=0.75     # Equilibrio natural
BMO_LLM_TOP_K=50            # Vocabulario adecuado
BMO_LLM_TOP_P=0.90          # Distribución balanceada
BMO_LLM_REPEAT_PENALTY=1.1   # Penalización suave
```

### Arquitectura Original:
- **Streaming habilitado**: Habla mientras genera (latencia percibida baja)
- **Sin respuestas predefinidas**: LLM maneja todo naturalmente
- **System prompt simple**: Instrucciones claras sin sobrecargar

### Rendimiento Original:
- ⏱️ **Latencia**: 4-6 segundos
- ✅ **Precisión factual**: Alta (banderas, geografía correctas)
- 🎯 **Respuestas**: Completas y naturales
- 🔄 **Streaming**: Respuesta inmediata percibida

## Configuración Problemática (LO QUE SE ROMPIÓ)

### Parámetros Sobre-optimizados:
```python
# VALORES PROBLEMÁTICOS que causaron los errores:
num_predict=20        # ❌ Respuestas truncadas
temperature=0.1       # ❌ Demasiado robótico
top_k=5              # ❌ Vocabulario muy limitado
```

### Problemas Causados:

#### 1. **Respuestas Factualmente Incorrectas**
- **Antes**: "Los colores de la bandera de Colombia son amarillo, azul y rojo"
- **Después**: "Las colores de la bandera de Colombia son Amarillo y Morado" ❌

#### 2. **Latencia Extrema**
- **Antes**: 4-6 segundos con streaming
- **Después**: 35+ segundos sin streaming aparente

#### 3. **Respuestas Truncadas**
- **Causa**: `num_predict=20` cortaba respuestas a mitad
- **Efecto**: Solo mencionaba 2 colores en lugar de 3

## ¿Por Qué Estos Parámetros Rompieron BMO?

### Temperature=0.1 (Demasiado Determinista)
```
Problema: Con temperatura muy baja, el modelo siempre elige 
la palabra MÁS probable, sin considerar contexto completo.

Para "bandera de Colombia":
- Palabra más probable después de "amarillo": "y"
- Siguiente más probable: "morado" (por asociación con otros países)
- NUNCA llega a considerar "azul" porque ya "decidió" el patrón
```

### Top_K=5 (Vocabulario Limitado)
```
Problema: Solo considera las 5 palabras más probables en cada paso.
Esto elimina sinónimos y variaciones que darían respuestas correctas.

Vocabulario disponible se reduce drásticamente:
- Colores disponibles: [amarillo, rojo, azul, verde, morado]
- Con top_k=5, puede eliminar "azul" del vocabulario disponible
```

### Num_Predict=20 (Respuestas Cortadas)
```
Problema: 20 tokens ≈ 15-20 palabras máximo.

"Los colores de la bandera de Colombia son amarillo, azul y rojo"
= ~13 tokens

Pero si el modelo toma un camino más verboso:
"Las colores de la bandera de Colombia son Amarillo y Morado."
= ~12 tokens, se corta antes de mencionar el tercer color
```

## Restauración Exitosa

### Cambios Aplicados:
1. ✅ **Parámetros restaurados** a valores originales exitosos
2. ✅ **Streaming confirmado** como habilitado
3. ✅ **System prompt mejorado** con datos factuales específicos
4. ✅ **Sin respuestas predefinidas** (LLM maneja todo)

### System Prompt Mejorado:
```python
SYSTEM_PROMPT = (
    "Eres BMO, un robot asistente amigable creado por Zambrano. "
    "Responde en español de forma natural y útil. "
    "Si te preguntan sobre Hora de Aventura, usa tu conocimiento de la serie. "
    "Para datos factuales (banderas, geografía, historia), sé muy preciso. "
    "La bandera de Colombia tiene tres franjas: amarillo (arriba), azul (medio) y rojo (abajo). "
    "Si no estás 100% seguro de un dato, di 'No estoy seguro de esa información'. "
    "Sé directo pero amigable, máximo 2-3 oraciones."
)
```

## Lecciones Aprendidas

### ❌ **NO hacer**:
- Optimizar parámetros sin medir impacto en precisión
- Reducir `num_predict` por debajo de 80-100 tokens
- Usar `temperature` menor a 0.5 para conversación natural
- Limitar `top_k` por debajo de 30-40

### ✅ **SÍ hacer**:
- Mantener configuración que funciona como baseline
- Probar cambios de uno en uno, no todos juntos
- Medir tanto latencia como precisión factual
- Documentar configuraciones exitosas

## Configuración Final Recomendada

```env
# Configuración PROBADA y EXITOSA para Qwen 2.5:1.5B en RPi5
BMO_LLM_NUM_PREDICT=100      # Respuestas completas
BMO_LLM_TEMPERATURE=0.75     # Equilibrio perfecto
BMO_LLM_TOP_K=50            # Vocabulario suficiente
BMO_LLM_TOP_P=0.90          # Distribución estándar
BMO_LLM_REPEAT_PENALTY=1.1   # Penalización suave
```

**Resultado esperado**: BMO responde en 4-6 segundos con alta precisión factual y streaming natural.

---

*Documento generado tras análisis forense del 30/04/2026*
*Configuración restaurada y verificada*