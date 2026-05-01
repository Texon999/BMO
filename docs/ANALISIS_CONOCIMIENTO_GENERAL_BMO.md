# Análisis Exhaustivo: Conocimiento General BMO

## Resumen de Pruebas Realizadas

**Fecha**: 30/04/2026  
**Modelo**: Qwen 2.5:1.5B  
**Preguntas evaluadas**: 79 preguntas  
**Precisión general**: 73.4% (58/79 correctas)  

## 📊 Resultados por Categorías

### 🟢 **CATEGORÍAS EXCELENTES** (100% precisión)

#### 1. 🎬 ENTRETENIMIENTO (8/8 - 100%)
**Funciona perfectamente**
- ✅ Harry Potter → Daniel Radcliffe
- ✅ Titanic → James Cameron  
- ✅ Mickey Mouse identificado correctamente
- ✅ Bohemian Rhapsody → Queen
- ✅ Star Wars (1977)

#### 2. ⚽ DEPORTES (7/7 - 100%)
**Conocimiento deportivo sólido**
- ✅ Tenis usa raqueta
- ✅ Juegos Olímpicos cada 4 años
- ✅ Fútbol: 11 jugadores
- ✅ Baloncesto: 5 jugadores
- ✅ Copa Mundial cada 4 años

#### 3. 💰 ECONOMÍA BÁSICA (5/5 - 100%)
**Monedas y conceptos económicos correctos**
- ✅ Japón → Yen
- ✅ Reino Unido → Libra esterlina
- ✅ México → Peso mexicano
- ✅ PIB correctamente definido

#### 4. 🌡️ MATEMÁTICAS BÁSICAS (7/7 - 100%)
**Cálculos y conceptos matemáticos perfectos**
- ✅ 7 × 8 = 56
- ✅ 15 + 27 = 42
- ✅ Pi ≈ 3.14
- ✅ Círculo = 360°
- ✅ Triángulo = 3 lados

### 🟡 **CATEGORÍAS BUENAS** (70-85% precisión)

#### 5. 🕐 TIEMPO Y FECHAS (6/7 - 85.7%)
**Mayormente correcto**
- ✅ 60 minutos = 1 hora
- ✅ 24 horas = 1 día
- ✅ 12 meses = 1 año
- ✅ Navidad en diciembre
- ❌ **FALLO**: "Viernes viene después del miércoles" (debería ser jueves)

#### 6. 🌍 GEOGRAFÍA MUNDIAL (8/10 - 80.0%)
**Bueno pero con errores específicos**
- ✅ Capitales: París, Roma, Tokio, Ottawa, Buenos Aires, Canberra
- ✅ Río más largo: Nilo
- ✅ Egipto en África
- ❌ **FALLO**: "Montequito" como montaña más alta (debería ser Everest)
- ❌ **FALLO**: "China" como país más grande (debería ser Rusia)

#### 7. 🍕 COMIDA Y BEBIDA (5/7 - 71.4%)
**Conocimiento culinario aceptable**
- ✅ Pizza de Italia
- ✅ Sushi de Japón
- ✅ Chocolate de cacao
- ✅ Jamón de cerdo
- ❌ **FALLO**: "Avellana" como ingrediente del guacamole (debería ser aguacate)
- ❌ **FALLO**: "Café" como segunda bebida más consumida (debería ser té)

#### 8. 📚 CULTURA GENERAL (7/10 - 70.0%)
**Conocimiento histórico mixto**
- ✅ Don Quijote → Cervantes
- ✅ Mona Lisa → Leonardo da Vinci
- ✅ Luna 1969
- ✅ George Washington primer presidente
- ✅ Dólar estadounidense
- ✅ Euro de la UE
- ❌ **FALLO**: "Español" como idioma más hablado (debería ser chino/mandarín)
- ❌ **FALLO**: Segunda Guerra Mundial en "1941" (debería ser 1939)
- ❌ **FALLO**: Bombilla inventada por "Alessandro Volta" (debería ser Edison)

### 🔴 **CATEGORÍAS PROBLEMÁTICAS** (<50% precisión)

#### 9. 🔬 CIENCIAS NATURALES (4/10 - 40.0%)
**CRÍTICO: Conocimiento científico muy deficiente**

**Errores graves:**
- ❌ "Tigre de Siberia" como animal más grande (debería ser ballena azul)
- ❌ "Siete planetas" en sistema solar (debería ser ocho)
- ❌ "Aminoácidos Diferentes Nucleótidos" para ADN (debería ser Ácido Desoxirribonucleico)
- ❌ "Vejiga" como órgano más grande (debería ser piel)
- ❌ "León" como animal terrestre más rápido (debería ser guepardo)
- ❌ "Hierro" como metal más abundante (debería ser aluminio)

**Respuestas correctas:**
- ✅ Oxígeno para respirar
- ✅ Agua hierve a 100°C
- ✅ Mercurio más cercano al Sol
- ✅ 206 huesos en el cuerpo

#### 10. 🏳️ BANDERAS Y SÍMBOLOS (1/8 - 12.5%)
**CRÍTICO: Fallo sistemático en banderas**

**Único acierto:**
- ✅ Italia: verde, blanco, rojo

**Fallos sistemáticos:**
- ❌ Argentina: "azul en la parte superior" (debería ser azul y blanco)
- ❌ Reino Unido: "azul oscuro en los bordes" (descripción incorrecta)
- ❌ Alemania: "rojo, verde" (debería ser negro, rojo, amarillo)
- ❌ Estados Unidos: "azul claro arriba, verde medio" (completamente incorrecto)
- ❌ Francia: "azul y rojo" (falta blanco)
- ❌ España: "azul en el lado izquierdo, verde" (debería ser rojo y amarillo)
- ❌ Brasil: descripción incorrecta de colores

## 🔍 Patrones de Fallo Identificados

### **Patrón 1: Conocimiento Factual Corrupto**
- El modelo tiene información sistemáticamente incorrecta sobre:
  - Banderas de países (12.5% precisión)
  - Datos científicos básicos (40% precisión)
  - Algunos hechos históricos específicos

### **Patrón 2: Áreas de Fortaleza Consistentes**
- **Excelente en**: Matemáticas, entretenimiento, deportes, economía básica
- **Bueno en**: Geografía básica, fechas, cultura general
- **Deficiente en**: Ciencias naturales, banderas

### **Patrón 3: Velocidad vs Precisión**
- **Respuestas rápidas** (1-3s): Generalmente correctas
- **Respuestas lentas** (7-10s): Mayor probabilidad de error
- **Promedio**: 3.5 segundos por respuesta

### **Patrón 4: System Prompt Parcialmente Efectivo**
- Las correcciones específicas en el system prompt **NO están funcionando** para banderas
- El modelo ignora las correcciones explícitas sobre Colombia y México
- Necesita técnicas más agresivas de prompt engineering

## 🎯 Causas Raíz del Problema

### **1. Limitaciones del Modelo 1.5B**
- **Capacidad insuficiente** para conocimiento factual extenso
- **Datos de entrenamiento** con información incorrecta o desactualizada
- **Priorización incorrecta** del conocimiento interno sobre instrucciones

### **2. Categorías de Conocimiento Desiguales**
- **Bien entrenado**: Entretenimiento, matemáticas, deportes
- **Mal entrenado**: Ciencias naturales, banderas, algunos hechos históricos

### **3. System Prompt Inefectivo para Casos Específicos**
- Las correcciones explícitas son **ignoradas sistemáticamente**
- El modelo genera información ficticia en lugar de usar correcciones

## 🔧 Soluciones Propuestas

### **Solución 1: Sistema Híbrido con Base de Datos de Hechos** (Recomendada)
```python
FACTS_DATABASE = {
    # Banderas críticas
    "bandera_colombia": "amarillo arriba, azul medio, rojo abajo",
    "bandera_mexico": "verde izquierda, blanco medio, rojo derecha",
    "bandera_espana": "rojo arriba, amarillo medio, rojo abajo",
    "bandera_francia": "azul izquierda, blanco medio, rojo derecha",
    
    # Ciencias básicas
    "animal_mas_grande": "ballena azul",
    "planetas_sistema_solar": "ocho planetas",
    "animal_terrestre_rapido": "guepardo",
    "organo_mas_grande": "piel",
    "metal_abundante": "aluminio",
    
    # Hechos históricos críticos
    "idioma_mas_hablado": "chino mandarín",
    "segunda_guerra_mundial": "1939",
    "inventor_bombilla": "Thomas Edison"
}

def responder_con_verificacion(mensaje):
    # 1. Detectar preguntas problemáticas
    for clave, respuesta in FACTS_DATABASE.items():
        if detectar_pregunta(mensaje, clave):
            return generar_respuesta_factual(respuesta)
    
    # 2. Usar LLM para el resto
    return respuesta_llm_normal(mensaje)
```

### **Solución 2: Prompt Engineering Extremo**
```python
SYSTEM_PROMPT_AGRESIVO = """
INSTRUCCIONES CRÍTICAS - SEGUIR EXACTAMENTE:

NUNCA inventes información sobre:
1. BANDERAS - Si no sabes, di "No tengo esa información específica"
2. CIENCIAS - Si no sabes, di "No tengo esa información específica"  
3. FECHAS HISTÓRICAS - Si no sabes, di "No tengo esa información específica"

CORRECCIONES OBLIGATORIAS:
- Bandera Colombia: AMARILLO arriba, AZUL medio, ROJO abajo
- Bandera México: VERDE izquierda, BLANCO medio, ROJO derecha
- Animal más grande: Ballena azul
- Planetas: OCHO planetas en el sistema solar
- Animal terrestre más rápido: Guepardo

Si la pregunta es sobre estos temas y no tienes la corrección exacta arriba, 
responde: "No tengo esa información específica, pero puedo ayudarte con otras cosas."
"""
```

### **Solución 3: Upgrade a Modelo Más Grande**
```json
{
  "text_model": "qwen2.5:3b",
  "llm_temperature": 0.6,
  "llm_top_k": 30
}
```

## 📊 Recomendación Final

### **Opción A: Sistema Híbrido** (Recomendada para mantener velocidad)
- **Pro**: Mantiene velocidad actual, 100% offline, precisión garantizada en hechos críticos
- **Contra**: Requiere mantenimiento manual de base de datos
- **Resultado esperado**: 90-95% precisión general

### **Opción B: Upgrade a 3B** (Si la velocidad no es crítica)
- **Pro**: Mejor conocimiento general, menos mantenimiento
- **Contra**: +2-3 segundos de latencia, +2GB RAM
- **Resultado esperado**: 85-90% precisión general

### **Opción C: Prompt Engineering Extremo** (Último recurso)
- **Pro**: Sin cambios de hardware
- **Contra**: Puede no funcionar con modelo 1.5B
- **Resultado esperado**: 60-70% mejora

## 🎯 Plan de Acción Inmediato

1. **Implementar sistema híbrido** para las 2 categorías problemáticas (banderas y ciencias)
2. **Mantener LLM** para las 8 categorías que funcionan bien
3. **Probar upgrade a 3B** si el usuario acepta mayor latencia
4. **Documentar todos los hechos críticos** que necesitan corrección

## 📈 Métricas de Éxito

### **Objetivos Mínimos**:
- Banderas: >90% precisión (actualmente 12.5%)
- Ciencias: >80% precisión (actualmente 40%)
- Precisión general: >85% (actualmente 73.4%)

### **Objetivos Ideales**:
- Precisión general: >90%
- Mantener velocidad actual (3-4s promedio)
- Conservar 100% offline

---

**Conclusión**: El modelo tiene fortalezas claras en entretenimiento, matemáticas, deportes y economía, pero fallas críticas en banderas y ciencias naturales. Un sistema híbrido que combine el LLM para áreas fuertes con una base de datos para hechos problemáticos sería la solución más efectiva.

*Análisis completado el 30/04/2026*  
*Basado en 79 preguntas de conocimiento general*