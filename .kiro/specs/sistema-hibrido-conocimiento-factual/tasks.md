# Tareas de Implementación: Sistema Híbrido de Conocimiento Factual

## Fase 1: Infraestructura Base (Semana 1)

### 1.1 Configuración del Sistema Híbrido

- [ ] **1.1.1** Extender config_manager para soportar configuraciones del sistema híbrido
  - Agregar parámetros: `hybrid_mode_enabled`, `fact_database_path`, `classification_thresholds`
  - Implementar validación de configuración híbrida
  - Agregar valores por defecto seguros
  - **Estimación**: 4 horas
  - **Dependencias**: Ninguna
  - **Archivos**: `src/config/config_manager.py`, `config.json`

- [ ] **1.1.2** Crear estructura de datos para FactEntry y modelos relacionados
  - Implementar dataclasses para FactEntry, QuestionType, ClassificationResult
  - Agregar validación con Pydantic
  - Crear enums para categorías de preguntas
  - **Estimación**: 3 horas
  - **Dependencias**: 1.1.1
  - **Archivos**: `src/brain/models.py`

- [ ] **1.1.3** Implementar sistema de logging específico para el sistema híbrido
  - Configurar logger separado para componentes híbridos
  - Implementar métricas de uso y rendimiento
  - Agregar logging de decisiones de clasificación
  - **Estimación**: 2 horas
  - **Dependencias**: 1.1.1
  - **Archivos**: `src/brain/hybrid_logger.py`

### 1.2 Base de Datos de Hechos

- [ ] **1.2.1** Crear FactDatabaseManager para gestión de hechos offline
  - Implementar carga y validación de base de datos JSON
  - Agregar búsqueda por clave, patrones y aliases
  - Implementar hot-reload con monitoreo de archivos
  - **Estimación**: 6 horas
  - **Dependencias**: 1.1.2
  - **Archivos**: `src/brain/fact_database.py`

- [ ] **1.2.2** Crear base de datos inicial con hechos críticos sobre banderas
  - Recopilar y verificar colores de 50 banderas principales
  - Incluir casos problemáticos identificados en pruebas (Colombia, México, España)
  - Formatear en estructura JSON con patrones de búsqueda
  - **Estimación**: 8 horas
  - **Dependencias**: 1.2.1
  - **Archivos**: `data/facts/flags.json`

- [ ] **1.2.3** Crear base de datos de hechos científicos básicos
  - Recopilar 100 hechos científicos verificados
  - Cubrir astronomía, biología, química, física básica
  - Incluir casos donde el LLM falla (planetas, animales, órganos)
  - **Estimación**: 10 horas
  - **Dependencias**: 1.2.1
  - **Archivos**: `data/facts/science.json`

- [ ] **1.2.4** Implementar sistema de índices para búsqueda eficiente
  - Crear índices por categoría y entidades
  - Implementar cache LRU para búsquedas frecuentes
  - Optimizar para búsquedas <100ms
  - **Estimación**: 4 horas
  - **Dependencias**: 1.2.1
  - **Archivos**: `src/brain/fact_indexer.py`

## Fase 2: Clasificación de Preguntas (Semana 2)

### 2.1 Question Classifier

- [ ] **2.1.1** Implementar QuestionClassifier para detección de preguntas problemáticas
  - Crear patrones regex para banderas, ciencias, geografía
  - Implementar extracción de entidades (países, conceptos)
  - Calcular niveles de confianza para clasificaciones
  - **Estimación**: 8 horas
  - **Dependencias**: 1.1.2, 1.1.3
  - **Archivos**: `src/brain/question_classifier.py`

- [ ] **2.1.2** Crear patrones de clasificación para preguntas sobre banderas
  - Patrones para "colores de la bandera de X"
  - Variaciones en español: "qué colores tiene", "de qué color es"
  - Extracción de nombres de países con aliases
  - **Estimación**: 4 horas
  - **Dependencias**: 2.1.1
  - **Archivos**: `src/brain/patterns/flag_patterns.py`

- [ ] **2.1.3** Crear patrones de clasificación para preguntas científicas
  - Patrones para astronomía (planetas, sistema solar)
  - Patrones para biología (animales, órganos, anatomía)
  - Patrones para química y física básica
  - **Estimación**: 6 horas
  - **Dependencias**: 2.1.1
  - **Archivos**: `src/brain/patterns/science_patterns.py`

- [ ] **2.1.4** Implementar sistema de aliases para entidades comunes
  - Aliases para países: "Estados Unidos" = "USA" = "EEUU"
  - Aliases para conceptos científicos
  - Sistema de normalización de entidades
  - **Estimación**: 3 horas
  - **Dependencias**: 2.1.1
  - **Archivos**: `src/brain/entity_aliases.py`

### 2.2 Algoritmos de Similitud

- [ ] **2.2.1** Implementar cálculo de similitud entre preguntas y patrones
  - Algoritmo de distancia de Levenshtein normalizada
  - Similitud semántica básica con keywords
  - Optimización para velocidad <10ms por comparación
  - **Estimación**: 4 horas
  - **Dependencias**: 2.1.1
  - **Archivos**: `src/brain/similarity.py`

- [ ] **2.2.2** Crear sistema de normalización de preguntas
  - Conversión a minúsculas y eliminación de acentos
  - Eliminación de caracteres especiales
  - Normalización de espacios múltiples
  - **Estimación**: 2 horas
  - **Dependencias**: 2.2.1
  - **Archivos**: `src/brain/text_normalizer.py`

## Fase 3: Generación de Respuestas Híbridas (Semana 3)

### 3.1 Hybrid Response Generator

- [ ] **3.1.1** Implementar HybridResponseGenerator como coordinador principal
  - Lógica de decisión entre fuentes (factual vs LLM)
  - Integración con QuestionClassifier y FactDatabaseManager
  - Manejo de fallbacks automáticos
  - **Estimación**: 6 horas
  - **Dependencias**: 2.1.1, 1.2.1
  - **Archivos**: `src/brain/hybrid_response_generator.py`

- [ ] **3.1.2** Crear formateador de respuestas factuales con personalidad BMO
  - Templates para diferentes tipos de hechos
  - Mantenimiento de tono amigable y natural
  - Integración de información factual en contexto conversacional
  - **Estimación**: 4 horas
  - **Dependencias**: 3.1.1
  - **Archivos**: `src/brain/response_formatter.py`

- [ ] **3.1.3** Implementar sistema de blending para respuestas mixtas
  - Combinación de información factual con contexto LLM
  - Detección de cuándo se necesita información adicional
  - Generación de contexto enriquecido para el LLM
  - **Estimación**: 5 horas
  - **Dependencias**: 3.1.1, 3.1.2
  - **Archivos**: `src/brain/response_blender.py`

- [ ] **3.1.4** Crear sistema de fallback robusto
  - Fallback automático cuando base de datos no está disponible
  - Manejo de errores en clasificación o búsqueda
  - Respuestas de error amigables manteniendo personalidad BMO
  - **Estimación**: 3 horas
  - **Dependencias**: 3.1.1
  - **Archivos**: `src/brain/fallback_handler.py`

### 3.2 Integración con Brain.py

- [ ] **3.2.1** Modificar brain.py para integrar sistema híbrido
  - Integrar HybridResponseGenerator en `responder_con_tts()`
  - Mantener compatibilidad con API existente
  - Agregar configuración para activar/desactivar modo híbrido
  - **Estimación**: 4 horas
  - **Dependencias**: 3.1.1, 1.1.1
  - **Archivos**: `src/brain/brain.py`

- [ ] **3.2.2** Asegurar compatibilidad con persistent_memory
  - Verificar que respuestas híbridas se almacenan correctamente
  - Mantener contexto conversacional entre respuestas
  - Agregar metadatos de fuente para debugging
  - **Estimación**: 2 horas
  - **Dependencias**: 3.2.1
  - **Archivos**: `src/brain/brain.py`, `src/memory/persistent_memory.py`

- [ ] **3.2.3** Implementar métricas y logging de uso
  - Tracking de uso por categoría de pregunta
  - Métricas de precisión y tiempos de respuesta
  - Logging de decisiones de clasificación para debugging
  - **Estimación**: 3 horas
  - **Dependencias**: 3.2.1, 1.1.3
  - **Archivos**: `src/brain/metrics_collector.py`

## Fase 4: Testing y Validación (Semana 4)

### 4.1 Testing Unitario

- [ ] **4.1.1** Crear tests unitarios para QuestionClassifier
  - Test de precisión de clasificación >95%
  - Test de extracción de entidades
  - Test de cálculo de niveles de confianza
  - **Estimación**: 4 horas
  - **Dependencias**: 2.1.1
  - **Archivos**: `tests/test_question_classifier.py`

- [ ] **4.1.2** Crear tests unitarios para FactDatabaseManager
  - Test de carga y validación de base de datos
  - Test de búsqueda por claves, patrones y aliases
  - Test de hot-reload y manejo de errores
  - **Estimación**: 4 horas
  - **Dependencias**: 1.2.1
  - **Archivos**: `tests/test_fact_database.py`

- [ ] **4.1.3** Crear tests unitarios para HybridResponseGenerator
  - Test de generación de respuestas factuales
  - Test de fallback automático
  - Test de blending de respuestas
  - **Estimación**: 4 horas
  - **Dependencias**: 3.1.1
  - **Archivos**: `tests/test_hybrid_response_generator.py`

- [ ] **4.1.4** Crear tests de integración con brain.py
  - Test de integración transparente
  - Test de compatibilidad con persistent_memory
  - Test de activación/desactivación del modo híbrido
  - **Estimación**: 3 horas
  - **Dependencias**: 3.2.1
  - **Archivos**: `tests/test_brain_integration.py`

### 4.2 Testing de Propiedades

- [ ] **4.2.1** Implementar property-based tests con Hypothesis
  - Propiedad: Todas las respuestas se generan en <10 segundos
  - Propiedad: Todas las respuestas son strings válidos en español
  - Propiedad: Sistema nunca crashea, siempre produce respuesta
  - **Estimación**: 6 horas
  - **Dependencias**: 3.2.1
  - **Archivos**: `tests/test_properties.py`

- [ ] **4.2.2** Crear tests de precisión con conjunto de pruebas conocido
  - Test con 50 preguntas sobre banderas (objetivo >90% precisión)
  - Test con 100 preguntas científicas (objetivo >80% precisión)
  - Test de regresión para categorías que funcionan bien
  - **Estimación**: 4 horas
  - **Dependencias**: 4.2.1
  - **Archivos**: `tests/test_accuracy.py`, `tests/data/test_questions.json`

### 4.3 Testing de Rendimiento

- [ ] **4.3.1** Crear benchmarks de rendimiento
  - Benchmark de tiempo de respuesta (<4s promedio)
  - Benchmark de throughput (>10 preguntas/minuto)
  - Benchmark de uso de memoria (<100MB adicional)
  - **Estimación**: 4 horas
  - **Dependencias**: 3.2.1
  - **Archivos**: `tests/test_performance.py`

- [ ] **4.3.2** Validar rendimiento en hardware objetivo (Raspberry Pi 5)
  - Ejecutar benchmarks en hardware real
  - Validar que se cumplen objetivos de rendimiento
  - Identificar y optimizar cuellos de botella
  - **Estimación**: 6 horas
  - **Dependencias**: 4.3.1
  - **Archivos**: `tests/hardware_validation.py`

## Fase 5: Documentación y Despliegue (Semana 5)

### 5.1 Documentación

- [ ] **5.1.1** Crear documentación de usuario para el sistema híbrido
  - Guía de configuración y activación
  - Explicación de cómo agregar nuevos hechos
  - Troubleshooting de problemas comunes
  - **Estimación**: 4 horas
  - **Dependencias**: Todas las fases anteriores
  - **Archivos**: `docs/SISTEMA_HIBRIDO_USUARIO.md`

- [ ] **5.1.2** Crear documentación técnica para desarrolladores
  - Arquitectura del sistema y componentes
  - API interna y puntos de extensión
  - Guía de contribución y mantenimiento
  - **Estimación**: 4 horas
  - **Dependencias**: Todas las fases anteriores
  - **Archivos**: `docs/SISTEMA_HIBRIDO_TECNICO.md`

- [ ] **5.1.3** Actualizar README.md con información del sistema híbrido
  - Descripción de la nueva funcionalidad
  - Instrucciones de instalación y configuración
  - Ejemplos de uso y beneficios
  - **Estimación**: 2 horas
  - **Dependencias**: 5.1.1, 5.1.2
  - **Archivos**: `README.md`

### 5.2 Scripts de Utilidad

- [ ] **5.2.1** Crear script de migración para activar sistema híbrido
  - Script para actualizar config.json con configuraciones híbridas
  - Validación de configuración existente
  - Backup automático antes de cambios
  - **Estimación**: 3 horas
  - **Dependencias**: 1.1.1
  - **Archivos**: `scripts/enable_hybrid_system.py`

- [ ] **5.2.2** Crear script de validación de base de datos de hechos
  - Validación de formato JSON y esquema
  - Verificación de integridad de datos
  - Reporte de estadísticas de la base de datos
  - **Estimación**: 3 horas
  - **Dependencias**: 1.2.1
  - **Archivos**: `scripts/validate_fact_database.py`

- [ ] **5.2.3** Crear script de testing integral del sistema híbrido
  - Ejecución de todas las pruebas de precisión
  - Generación de reporte de rendimiento
  - Comparación con baseline de BMO original
  - **Estimación**: 4 horas
  - **Dependencias**: 4.2.2, 4.3.1
  - **Archivos**: `scripts/test_hybrid_system.py`

### 5.3 Configuración de Producción

- [ ] **5.3.1** Crear configuración por defecto optimizada
  - Umbrales de confianza calibrados
  - Configuración de rendimiento para Raspberry Pi 5
  - Valores por defecto seguros y conservadores
  - **Estimación**: 2 horas
  - **Dependencias**: 4.3.2
  - **Archivos**: `config/hybrid_defaults.json`

- [ ] **5.3.2** Implementar sistema de monitoreo básico
  - Logging de métricas de uso
  - Alertas para errores críticos
  - Dashboard básico de estadísticas
  - **Estimación**: 4 horas
  - **Dependencias**: 3.2.3
  - **Archivos**: `src/brain/monitoring.py`

## Tareas Opcionales (Mejoras Futuras)

### Mejoras de Precisión

- [ ] **O.1** Implementar aprendizaje de patrones basado en uso
  - Análisis de preguntas mal clasificadas
  - Mejora automática de patrones de clasificación
  - **Estimación**: 8 horas
  - **Prioridad**: Baja

- [ ] **O.2** Agregar más categorías de hechos (historia, cultura)
  - Expandir base de datos con hechos históricos
  - Agregar patrones para preguntas culturales
  - **Estimación**: 12 horas
  - **Prioridad**: Media

### Mejoras de Rendimiento

- [ ] **O.3** Implementar cache persistente para clasificaciones
  - Cache en disco para clasificaciones frecuentes
  - Reducir tiempo de respuesta para preguntas repetidas
  - **Estimación**: 4 horas
  - **Prioridad**: Baja

- [ ] **O.4** Optimizar búsqueda con índices avanzados
  - Índices invertidos para búsqueda de texto completo
  - Búsqueda aproximada con tolerancia a errores
  - **Estimación**: 6 horas
  - **Prioridad**: Baja

### Mejoras de Usabilidad

- [ ] **O.5** Crear interfaz web para gestión de hechos
  - Interfaz gráfica para agregar/editar hechos
  - Validación en tiempo real
  - **Estimación**: 16 horas
  - **Prioridad**: Baja

- [ ] **O.6** Implementar sistema de feedback de usuarios
  - Mecanismo para reportar respuestas incorrectas
  - Mejora iterativa basada en feedback
  - **Estimación**: 8 horas
  - **Prioridad**: Baja

---

## Resumen de Estimaciones

**Tiempo Total Estimado**: 140 horas (5 semanas de trabajo)

**Distribución por Fase**:
- Fase 1 (Infraestructura): 37 horas
- Fase 2 (Clasificación): 25 horas  
- Fase 3 (Respuestas Híbridas): 27 horas
- Fase 4 (Testing): 31 horas
- Fase 5 (Documentación): 20 horas

**Tareas Críticas** (bloquean otras tareas):
- 1.1.1 (Config Manager)
- 1.1.2 (Modelos de Datos)
- 1.2.1 (Fact Database Manager)
- 2.1.1 (Question Classifier)
- 3.1.1 (Hybrid Response Generator)

**Ruta Crítica**: 1.1.1 → 1.1.2 → 1.2.1 → 2.1.1 → 3.1.1 → 3.2.1 → Testing → Despliegue

---

*Estas tareas implementan completamente el sistema híbrido diseñado para resolver los problemas críticos de precisión identificados en BMO, manteniendo la filosofía offline y la experiencia de usuario natural.*