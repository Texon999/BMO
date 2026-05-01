# Base de Datos de Hechos - Sistema Híbrido BMO

Este directorio contiene la base de datos offline de hechos críticos para el Sistema Híbrido de Conocimiento Factual de BMO.

## Estructura

- `flags.json` - Hechos sobre banderas de países
- `science.json` - Hechos científicos básicos
- `geography.json` - Hechos geográficos específicos
- `history.json` - Fechas históricas importantes

## Configuración

Las configuraciones del sistema híbrido se encuentran en `config.json`:

```json
{
  "hybrid_mode_enabled": false,
  "fact_database_path": "data/facts/",
  "classification_thresholds": {
    "flag_colors": 0.8,
    "natural_sciences": 0.75,
    "specific_geography": 0.7,
    "historical_dates": 0.7,
    "default": 0.6
  },
  "hybrid_fallback_strategy": "llm_normal",
  "hybrid_response_blending": true,
  "hybrid_cache_enabled": true,
  "hybrid_cache_size": 100
}
```

## Parámetros de Configuración

### `hybrid_mode_enabled`
- **Tipo**: Boolean
- **Defecto**: `false`
- **Descripción**: Activa o desactiva el sistema híbrido completo

### `fact_database_path`
- **Tipo**: String
- **Defecto**: `"data/facts/"`
- **Descripción**: Ruta al directorio que contiene los archivos de hechos

### `classification_thresholds`
- **Tipo**: Object
- **Descripción**: Umbrales de confianza para cada categoría de pregunta
- **Valores**: Entre 0.0 y 1.0 (mayor = más estricto)

### `hybrid_fallback_strategy`
- **Tipo**: String
- **Opciones**: `"llm_normal"`, `"llm_enhanced"`, `"error_response"`
- **Defecto**: `"llm_normal"`
- **Descripción**: Estrategia cuando no se encuentra información factual

### `hybrid_response_blending`
- **Tipo**: Boolean
- **Defecto**: `true`
- **Descripción**: Permite combinar respuestas factuales con información del LLM

### `hybrid_cache_enabled`
- **Tipo**: Boolean
- **Defecto**: `true`
- **Descripción**: Habilita cache de clasificaciones para mejor rendimiento

### `hybrid_cache_size`
- **Tipo**: Integer
- **Rango**: 10-1000
- **Defecto**: `100`
- **Descripción**: Número máximo de clasificaciones en cache

## Uso Programático

```python
from src.config.config_manager import config_manager

# Verificar si el modo híbrido está habilitado
if config_manager.is_hybrid_mode_enabled():
    print("Sistema híbrido activo")

# Obtener ruta de la base de datos
db_path = config_manager.get_fact_database_path()

# Obtener umbral para una categoría específica
threshold = config_manager.get_classification_threshold('flag_colors')

# Activar modo híbrido
config_manager.set_hybrid_mode(True)

# Actualizar umbral de clasificación
config_manager.update_classification_threshold('flag_colors', 0.9)

# Obtener resumen de configuración híbrida
summary = config_manager.get_hybrid_config_summary()
```

## Notas

- Los cambios en la configuración se aplican automáticamente con hot-reload
- Los valores inválidos se corrigen automáticamente a valores por defecto seguros
- El directorio de hechos se crea automáticamente si no existe