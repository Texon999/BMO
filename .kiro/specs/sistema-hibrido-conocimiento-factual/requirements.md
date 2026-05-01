# Requisitos del Sistema: Sistema Híbrido de Conocimiento Factual

## 1. Requisitos Funcionales

### 1.1 Detección Automática de Preguntas Problemáticas

**RF-001**: El sistema DEBE detectar automáticamente preguntas sobre temas donde el modelo LLM falla sistemáticamente
- **Criterio de Aceptación**: Precisión de detección >95% para categorías problemáticas (banderas, ciencias naturales, geografía específica)
- **Entrada**: Pregunta del usuario en texto plano
- **Salida**: Clasificación con tipo de pregunta y nivel de confianza
- **Prioridad**: Alta

**RF-002**: El sistema DEBE extraer entidades relevantes de las preguntas (países, conceptos científicos, ubicaciones)
- **Criterio de Aceptación**: Extracción correcta de entidades en >90% de casos
- **Entrada**: Pregunta clasificada como problemática
- **Salida**: Lista de entidades identificadas
- **Prioridad**: Alta

**RF-003**: El sistema DEBE calcular niveles de confianza para las clasificaciones
- **Criterio de Aceptación**: Niveles de confianza entre 0.0-1.0 con calibración precisa
- **Entrada**: Pregunta analizada
- **Salida**: Score de confianza numérico
- **Prioridad**: Media

### 1.2 Base de Datos de Hechos Offline

**RF-004**: El sistema DEBE mantener una base de datos offline de hechos críticos verificados
- **Criterio de Aceptación**: Base de datos accesible sin conexión a internet
- **Formato**: JSON estructurado con validación de esquema
- **Capacidad**: Mínimo 500 hechos críticos
- **Prioridad**: Alta

**RF-005**: El sistema DEBE permitir búsqueda eficiente de hechos por claves y patrones
- **Criterio de Aceptación**: Tiempo de búsqueda <100ms para 95% de consultas
- **Algoritmo**: Búsqueda por clave directa, patrones y aliases
- **Índices**: Por categoría y entidades principales
- **Prioridad**: Alta

**RF-006**: El sistema DEBE soportar hot-reload de la base de datos sin reiniciar BMO
- **Criterio de Aceptación**: Cambios en base de datos se reflejan en <5 segundos
- **Mecanismo**: Monitoreo de cambios en archivo
- **Fallback**: Mantener versión anterior si nueva es inválida
- **Prioridad**: Media

### 1.3 Generación de Respuestas Híbridas

**RF-007**: El sistema DEBE generar respuestas combinando información factual y LLM según sea necesario
- **Criterio de Aceptación**: Respuestas coherentes que mantienen personalidad de BMO
- **Estrategia**: Factual para datos críticos, LLM para contexto conversacional
- **Blending**: Integración natural de ambas fuentes
- **Prioridad**: Alta

**RF-008**: El sistema DEBE mantener la personalidad y tono natural de BMO en todas las respuestas
- **Criterio de Aceptación**: 100% de respuestas mantienen estilo amigable y directo
- **Características**: Español natural, tono amigable, respuestas concisas
- **Validación**: Revisión manual de muestras representativas
- **Prioridad**: Alta

**RF-009**: El sistema DEBE implementar fallback automático al LLM cuando la base de datos no tiene información
- **Criterio de Aceptación**: Transición transparente sin errores visibles al usuario
- **Condiciones**: Fact no encontrado, base de datos no disponible, error en búsqueda
- **Comportamiento**: Usar LLM normal con system prompt mejorado
- **Prioridad**: Alta

### 1.4 Integración con Arquitectura Existente

**RF-010**: El sistema DEBE integrarse transparentemente con brain.py existente
- **Criterio de Aceptación**: Sin cambios en API pública de brain.py
- **Compatibilidad**: Mantener todas las funciones existentes
- **Migración**: Activación/desactivación configurable
- **Prioridad**: Alta

**RF-011**: El sistema DEBE utilizar el config_manager existente para configuración
- **Criterio de Aceptación**: Configuración centralizada en config.json
- **Parámetros**: Umbrales, rutas, estrategias de fallback
- **Hot-reload**: Cambios sin reinicio del sistema
- **Prioridad**: Media

**RF-012**: El sistema DEBE mantener compatibilidad con persistent_memory
- **Criterio de Aceptación**: Historial conversacional se preserva correctamente
- **Integración**: Respuestas híbridas se almacenan como respuestas normales
- **Contexto**: Información de fuente disponible para debugging
- **Prioridad**: Media

## 2. Requisitos No Funcionales

### 2.1 Rendimiento

**RNF-001**: El sistema DEBE mantener tiempo de respuesta promedio <4 segundos
- **Medición**: Tiempo desde pregunta hasta inicio de audio
- **Objetivo**: 95% de respuestas en <4s, 99% en <8s
- **Baseline**: Tiempo actual de BMO sin sistema híbrido
- **Prioridad**: Alta

**RNF-002**: El sistema DEBE procesar mínimo 10 preguntas por minuto
- **Medición**: Throughput sostenido en hardware Raspberry Pi 5
- **Condiciones**: Mezcla de preguntas factuales y conversacionales
- **Degradación**: <10% degradación vs BMO base
- **Prioridad**: Media

**RNF-003**: El sistema DEBE usar <100MB de memoria adicional
- **Medición**: Memoria RAM adicional sobre BMO base
- **Incluye**: Base de datos, caches, estructuras de clasificación
- **Monitoreo**: Métricas de uso continuo
- **Prioridad**: Media

### 2.2 Precisión

**RNF-004**: El sistema DEBE alcanzar >90% precisión en categorías problemáticas
- **Medición**: Evaluación con conjunto de pruebas de 100+ preguntas
- **Categorías**: Banderas (objetivo >95%), ciencias naturales (objetivo >85%)
- **Baseline**: Precisión actual del 12.5% en banderas, 40% en ciencias
- **Prioridad**: Alta

**RNF-005**: El sistema DEBE mantener >95% precisión en categorías que funcionan bien
- **Medición**: No degradar categorías fuertes (entretenimiento, deportes, matemáticas)
- **Objetivo**: Mantener 100% actual en estas categorías
- **Validación**: Pruebas de regresión continuas
- **Prioridad**: Alta

**RNF-006**: El sistema DEBE lograr >90% precisión general
- **Medición**: Promedio ponderado de todas las categorías
- **Baseline**: 73.4% actual
- **Objetivo**: Mejora de +16.6 puntos porcentuales
- **Prioridad**: Alta

### 2.3 Disponibilidad

**RNF-007**: El sistema DEBE funcionar 100% offline
- **Requisito**: Sin dependencias de internet o servicios externos
- **Validación**: Funcionamiento completo sin conectividad
- **Filosofía**: Mantener principio offline-first de BMO
- **Prioridad**: Alta

**RNF-008**: El sistema DEBE tener disponibilidad >99.5%
- **Medición**: Tiempo operativo sin fallos críticos
- **Fallos**: Errores que impiden generar respuestas
- **Recuperación**: Fallback automático en <1 segundo
- **Prioridad**: Media

**RNF-009**: El sistema DEBE recuperarse automáticamente de errores
- **Comportamiento**: Nunca crashear BMO por errores del sistema híbrido
- **Estrategias**: Fallback a LLM, respuestas de error amigables
- **Logging**: Registro de errores para debugging
- **Prioridad**: Alta

### 2.4 Mantenibilidad

**RNF-010**: El sistema DEBE permitir agregar nuevos hechos sin programación
- **Interfaz**: Edición directa de archivo JSON
- **Validación**: Esquema automático y verificación de formato
- **Aplicación**: Hot-reload automático de cambios
- **Prioridad**: Media

**RNF-011**: El sistema DEBE proporcionar métricas de uso y efectividad
- **Métricas**: Uso por categoría, precisión por tipo, tiempos de respuesta
- **Formato**: Logs estructurados y estadísticas agregadas
- **Privacidad**: Sin datos personales o contenido de conversaciones
- **Prioridad**: Baja

**RNF-012**: El sistema DEBE tener configuración granular
- **Parámetros**: Umbrales de confianza, estrategias de fallback, categorías activas
- **Interfaz**: config.json con validación
- **Documentación**: Comentarios inline y documentación externa
- **Prioridad**: Media

### 2.5 Compatibilidad

**RNF-013**: El sistema DEBE ser compatible con Python 3.9+
- **Requisito**: Funcionar en versiones de Python soportadas por BMO
- **Dependencias**: Solo librerías compatibles con el ecosistema actual
- **Testing**: Validación en múltiples versiones de Python
- **Prioridad**: Media

**RNF-014**: El sistema DEBE funcionar en Raspberry Pi 5 con 8GB RAM
- **Hardware**: Optimizado para hardware objetivo de BMO
- **Recursos**: Uso eficiente de CPU y memoria limitados
- **Testing**: Validación en hardware real
- **Prioridad**: Alta

**RNF-015**: El sistema DEBE mantener compatibilidad con versiones futuras de Ollama
- **API**: Uso de APIs estables de Ollama
- **Versionado**: Manejo de cambios en versiones de Ollama
- **Fallback**: Degradación graceful si API cambia
- **Prioridad**: Baja

## 3. Requisitos de Datos

### 3.1 Base de Datos de Hechos

**RD-001**: La base de datos DEBE contener mínimo 50 hechos sobre banderas
- **Cobertura**: Países principales y casos problemáticos identificados
- **Formato**: Colores, orden, disposición de franjas
- **Fuentes**: Verificación con fuentes oficiales
- **Prioridad**: Alta

**RD-002**: La base de datos DEBE contener mínimo 100 hechos científicos básicos
- **Categorías**: Astronomía, biología, química, física
- **Nivel**: Conocimiento de educación secundaria
- **Precisión**: Información científicamente correcta
- **Prioridad**: Alta

**RD-003**: La base de datos DEBE incluir hechos geográficos críticos
- **Contenido**: Capitales, países más grandes, ríos, montañas
- **Cobertura**: Casos donde el LLM falla sistemáticamente
- **Actualización**: Datos actualizados a 2024
- **Prioridad**: Media

### 3.2 Patrones de Clasificación

**RD-004**: El sistema DEBE incluir patrones para detectar preguntas sobre banderas
- **Patrones**: Expresiones regulares y keywords
- **Idiomas**: Español con variaciones regionales
- **Cobertura**: >95% de formas naturales de preguntar
- **Prioridad**: Alta

**RD-005**: El sistema DEBE incluir patrones para preguntas científicas
- **Categorías**: Astronomía, biología, química, física básica
- **Variaciones**: Múltiples formas de formular la misma pregunta
- **Entidades**: Extracción de conceptos científicos clave
- **Prioridad**: Alta

**RD-006**: El sistema DEBE mantener aliases para entidades comunes
- **Ejemplos**: "Estados Unidos" = "USA" = "EEUU" = "América"
- **Cobertura**: Nombres alternativos comunes en español
- **Mantenimiento**: Actualización basada en uso real
- **Prioridad**: Media

## 4. Requisitos de Interfaz

### 4.1 API Interna

**RI-001**: El sistema DEBE exponer interfaz compatible con brain.py actual
- **Función**: `responder_con_tts()` sin cambios en signatura
- **Comportamiento**: Transparente para código cliente
- **Configuración**: Activación/desactivación sin cambios de código
- **Prioridad**: Alta

**RI-002**: El sistema DEBE proporcionar interfaz de configuración
- **Métodos**: Configuración via config_manager existente
- **Parámetros**: Todos los aspectos configurables del sistema
- **Validación**: Verificación automática de valores válidos
- **Prioridad**: Media

**RI-003**: El sistema DEBE exponer métricas para monitoreo
- **Interfaz**: Métodos para obtener estadísticas de uso
- **Datos**: Precisión, tiempos, uso por categoría
- **Formato**: Estructuras de datos estándar de Python
- **Prioridad**: Baja

### 4.2 Configuración

**RI-004**: El sistema DEBE usar config.json para toda la configuración
- **Integración**: Extensión del config_manager existente
- **Parámetros**: Umbrales, rutas, estrategias, categorías activas
- **Validación**: Esquema JSON y valores por defecto
- **Prioridad**: Media

**RI-005**: El sistema DEBE soportar configuración de umbrales por categoría
- **Granularidad**: Umbrales específicos para cada tipo de pregunta
- **Flexibilidad**: Ajuste fino del comportamiento del sistema
- **Documentación**: Explicación clara del impacto de cada parámetro
- **Prioridad**: Baja

## 5. Requisitos de Seguridad

### 5.1 Validación de Entrada

**RS-001**: El sistema DEBE validar y sanitizar todas las entradas
- **Validación**: Longitud, caracteres permitidos, formato
- **Sanitización**: Eliminación de caracteres potencialmente peligrosos
- **Límites**: Máximo 500 caracteres por pregunta
- **Prioridad**: Media

**RS-002**: El sistema DEBE implementar rate limiting básico
- **Límite**: Máximo 60 preguntas por minuto
- **Propósito**: Prevenir abuso y sobrecarga del sistema
- **Implementación**: Contador simple por sesión
- **Prioridad**: Baja

### 5.2 Protección de Datos

**RS-003**: El sistema DEBE mantener principio offline-first
- **Requisito**: Ningún dato sale del dispositivo local
- **Validación**: Sin conexiones de red desde el sistema híbrido
- **Auditoría**: Verificación de que no hay llamadas externas
- **Prioridad**: Alta

**RS-004**: El sistema DEBE proteger datos sensibles en memoria
- **Práctica**: Limpieza de datos sensibles después de uso
- **Alcance**: Preguntas del usuario y respuestas generadas
- **Implementación**: Sobrescritura explícita de variables
- **Prioridad**: Baja

## 6. Criterios de Aceptación del Sistema

### 6.1 Criterios de Precisión

**CA-001**: Mejora de precisión en banderas de 12.5% a >90%
- **Medición**: Conjunto de pruebas de 50 preguntas sobre banderas
- **Validación**: Evaluación automática de respuestas
- **Objetivo**: Incremento de 77.5 puntos porcentuales

**CA-002**: Mejora de precisión en ciencias de 40% a >80%
- **Medición**: Conjunto de pruebas de 100 preguntas científicas
- **Validación**: Verificación con fuentes científicas confiables
- **Objetivo**: Incremento de 40 puntos porcentuales

**CA-003**: Mantenimiento de precisión en categorías fuertes
- **Medición**: Sin degradación en entretenimiento, deportes, matemáticas
- **Validación**: Pruebas de regresión automáticas
- **Objetivo**: Mantener 100% actual

### 6.2 Criterios de Rendimiento

**CA-004**: Tiempo de respuesta promedio <4 segundos
- **Medición**: 1000 preguntas mixtas en hardware objetivo
- **Distribución**: 70% conversacionales, 30% factuales
- **Validación**: Medición automática de latencia

**CA-005**: Uso de memoria adicional <100MB
- **Medición**: Monitoreo continuo durante operación normal
- **Condiciones**: Base de datos completa cargada en memoria
- **Validación**: Herramientas de profiling de memoria

### 6.3 Criterios de Integración

**CA-006**: Integración transparente con BMO existente
- **Validación**: BMO funciona normalmente con sistema híbrido activado
- **Compatibilidad**: Todas las funciones existentes operativas
- **Configuración**: Activación/desactivación sin efectos secundarios

**CA-007**: Compatibilidad con persistent_memory
- **Validación**: Historial conversacional se mantiene correctamente
- **Integración**: Respuestas híbridas se almacenan apropiadamente
- **Funcionalidad**: Sin pérdida de contexto conversacional

### 6.4 Criterios de Mantenibilidad

**CA-008**: Adición de hechos sin programación
- **Validación**: Usuario no técnico puede agregar hechos editando JSON
- **Proceso**: Documentación clara del formato y proceso
- **Aplicación**: Cambios se reflejan automáticamente

**CA-009**: Configuración granular funcional
- **Validación**: Todos los parámetros configurables tienen efecto observable
- **Documentación**: Explicación clara del impacto de cada configuración
- **Validación**: Cambios se aplican sin reinicio

---

*Estos requisitos derivan directamente del diseño técnico y abordan los problemas críticos identificados en las pruebas exhaustivas de BMO. El sistema híbrido debe mantener la filosofía offline y la personalidad natural de BMO mientras resuelve los fallos sistemáticos en conocimiento factual.*