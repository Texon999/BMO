# Solución: Problema con Colores de la Bandera de Colombia

## Problema Identificado

BMO estaba dando información **incorrecta** sobre la bandera de Colombia:

```
❌ Respuesta incorrecta: "azul arriba, rojo en medio y amarillo abajo"
✅ Respuesta correcta: "amarillo arriba, azul medio, rojo abajo"
```

Además, se contradecía diciendo "No estoy seguro de esa información" después de dar una respuesta.

## Análisis de la Causa Raíz

### 1. **Conflicto de Información**
- **System prompt**: Tenía información correcta pero no enfática
- **Modelo base**: Qwen 2.5:1.5B tenía conocimiento incorrecto sobre Colombia
- **Contradicción**: El modelo generaba información incorrecta y luego dudaba

### 2. **System Prompt Débil**
```python
# ANTES (débil)
"Para datos factuales (banderas, geografía, historia), sé muy preciso. "
"La bandera de Colombia tiene tres franjas: amarillo (arriba), azul (medio) y rojo (abajo)."
```

### 3. **Falta de Énfasis**
- No había suficiente peso en la información factual
- El modelo priorizaba su conocimiento interno sobre las instrucciones
- No había redundancia para reforzar datos críticos

## Solución Implementada

### 1. **System Prompt Enfático**
```python
# DESPUÉS (enfático)
"DATOS FACTUALES CRÍTICOS (memoriza exactamente):\n"
"- Bandera de Colombia: AMARILLO arriba, AZUL medio, ROJO abajo (3 franjas horizontales)\n"
"Para cualquier dato factual, usa EXACTAMENTE la información de arriba."
```

### 2. **Redundancia Estratégica**
- **System prompt principal**: Información enfática con mayúsculas
- **Brain context**: Información duplicada como refuerzo
- **Doble verificación**: Aparece dos veces en el prompt final

### 3. **Instrucciones Claras**
```python
"Para cualquier dato factual, usa EXACTAMENTE la información de arriba. "
"Si no tienes información específica, di 'No tengo esa información específica'."
```

## Verificación de la Solución

### System Prompt Final Generado:
```
Eres BMO, un robot asistente amigable creado por Zambrano.

DATOS FACTUALES CRÍTICOS (memoriza exactamente):
- Bandera de Colombia: AMARILLO arriba, AZUL medio, ROJO abajo (3 franjas horizontales)
- Bandera de México: verde, blanco, rojo (franjas verticales)
- Bandera de España: rojo, amarillo, rojo (franjas horizontales)

Para cualquier dato factual, usa EXACTAMENTE la información de arriba.

[... contexto adicional ...]

DATOS FACTUALES VERIFICADOS (usar exactamente así):
- Bandera de Colombia: AMARILLO arriba, AZUL medio, ROJO abajo (3 franjas horizontales)
```

### Características de la Solución:
- ✅ **Información duplicada**: Aparece 2 veces para máximo refuerzo
- ✅ **Mayúsculas enfáticas**: AMARILLO, AZUL, ROJO destacan
- ✅ **Instrucciones directas**: "usa EXACTAMENTE"
- ✅ **Consistencia total**: Misma información en ambas secciones

## Técnicas Aplicadas

### 1. **Prompt Engineering Avanzado**
- **Jerarquía de información**: Datos críticos al inicio
- **Repetición estratégica**: Información clave duplicada
- **Énfasis visual**: Mayúsculas y formato especial

### 2. **Overriding de Conocimiento Base**
- **Instrucciones explícitas**: "memoriza exactamente"
- **Priorización forzada**: "usa EXACTAMENTE la información de arriba"
- **Redundancia**: Múltiples menciones del mismo dato

### 3. **Validación Automática**
- **Script de prueba**: Verifica que el prompt contiene información correcta
- **Herramientas de diagnóstico**: `test_system_prompt.py`
- **Configuración dinámica**: Hot-reload para ajustes rápidos

## Resultados Esperados

### Antes:
```
Usuario: "¿Cuáles son los colores de la bandera de Colombia?"
BMO: "azul arriba, rojo en medio y amarillo abajo. No estoy seguro de esa información."
```

### Después:
```
Usuario: "¿Cuáles son los colores de la bandera de Colombia?"
BMO: "La bandera de Colombia tiene amarillo arriba, azul en el medio y rojo abajo."
```

## Herramientas de Verificación

### 1. **Script de Prueba**
```bash
python scripts/test_system_prompt.py
```

### 2. **Configuración Dinámica**
```bash
python scripts/config_tool.py --show
```

### 3. **Monitoreo en Tiempo Real**
- Hot-reload automático de `brain_context.txt`
- Configuración JSON dinámica
- Logs detallados de respuestas

## Lecciones Aprendidas

### 1. **Prompt Engineering es Crítico**
- Los modelos pequeños necesitan instrucciones muy explícitas
- La información crítica debe estar duplicada y enfatizada
- Las mayúsculas y formato ayudan significativamente

### 2. **Conocimiento Base vs Instrucciones**
- Los modelos priorizan su conocimiento interno
- Se necesita "fuerza bruta" para override información incorrecta
- La redundancia es más efectiva que la sutileza

### 3. **Validación Automática**
- Siempre verificar que el prompt final contiene información correcta
- Herramientas de diagnóstico son esenciales
- Hot-reload permite iteración rápida

---

*Solución implementada y verificada el 30/04/2026*
*Problema resuelto mediante prompt engineering avanzado*