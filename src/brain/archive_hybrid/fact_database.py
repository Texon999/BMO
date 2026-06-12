"""
Gestor de Base de Datos de Hechos Offline para el Sistema Híbrido.

Este módulo gestiona la base de datos offline de hechos críticos verificados,
proporcionando búsqueda eficiente, hot-reload y validación automática.

Características:
- Carga y validación de hechos desde archivos JSON
- Búsqueda por clave, patrones y aliases
- Hot-reload automático sin reiniciar BMO
- Índices para búsqueda O(1)
- Cache LRU para búsquedas frecuentes
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
from functools import lru_cache
from threading import Lock

from src.brain.models import FactEntry, QuestionType, DatabaseStats
from src.brain.hybrid_logger import hybrid_logger


class FactDatabaseManager:
    """
    Gestor de la base de datos offline de hechos críticos.
    
    Proporciona búsqueda eficiente, hot-reload y validación automática
    de hechos verificados para el sistema híbrido.
    """
    
    def __init__(self, database_path: str = "data/facts/"):
        self.database_path = Path(database_path)
        self.database_path.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("BMO.Hybrid.FactDB")
        
        # Almacenamiento principal
        self.facts: Dict[str, FactEntry] = {}
        
        # Índices para búsqueda eficiente
        self.category_index: Dict[str, Set[str]] = {}
        self.entity_index: Dict[str, Set[str]] = {}
        self.pattern_index: Dict[str, Set[str]] = {}
        
        # Control de hot-reload
        self.file_mtimes: Dict[str, float] = {}
        self.last_reload: Optional[datetime] = None
        self.lock = Lock()
        
        # Estadísticas
        self.total_searches = 0
        self.successful_searches = 0
        
        # Cargar base de datos inicial
        self.load_database()
    
    def load_database(self, force_reload: bool = False) -> bool:
        """
        Carga la base de datos de hechos desde archivos JSON.
        
        Args:
            force_reload: Forzar recarga incluso si no hay cambios
            
        Returns:
            True si se cargó exitosamente
        """
        with self.lock:
            try:
                # Buscar archivos JSON en el directorio
                json_files = list(self.database_path.glob("*.json"))
                
                if not json_files:
                    self.logger.warning(f"No fact database files found in {self.database_path}")
                    return False
                
                # Verificar si hay cambios
                if not force_reload and not self._has_changes(json_files):
                    return True
                
                # Limpiar datos anteriores
                new_facts = {}
                new_category_index = {}
                new_entity_index = {}
                new_pattern_index = {}
                
                # Cargar cada archivo
                for json_file in json_files:
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # Validar estructura
                        if not isinstance(data, dict) or 'facts' not in data:
                            self.logger.error(f"Invalid structure in {json_file.name}")
                            continue
                        
                        # Cargar hechos
                        for fact_data in data['facts']:
                            try:
                                fact = FactEntry(**fact_data)
                                
                                # Validar unicidad de key
                                if fact.key in new_facts:
                                    self.logger.warning(
                                        f"Duplicate fact key '{fact.key}' in {json_file.name}, skipping"
                                    )
                                    continue
                                
                                new_facts[fact.key] = fact
                                
                                # Actualizar índices
                                self._update_indices(
                                    fact, new_category_index, 
                                    new_entity_index, new_pattern_index
                                )
                                
                            except Exception as e:
                                self.logger.error(f"Error loading fact from {json_file.name}: {e}")
                                continue
                        
                        # Actualizar mtime
                        self.file_mtimes[str(json_file)] = json_file.stat().st_mtime
                        
                    except Exception as e:
                        self.logger.error(f"Error loading {json_file.name}: {e}")
                        continue
                
                # Actualizar base de datos
                self.facts = new_facts
                self.category_index = new_category_index
                self.entity_index = new_entity_index
                self.pattern_index = new_pattern_index
                self.last_reload = datetime.now()
                
                # Log resultado
                self.logger.info(
                    f"Loaded {len(self.facts)} facts from {len(json_files)} files"
                )
                
                hybrid_logger.log_database_operation("load", {
                    "total_facts": len(self.facts),
                    "files_loaded": len(json_files),
                    "categories": len(self.category_index)
                })
                
                return True
                
            except Exception as e:
                self.logger.error(f"Error loading fact database: {e}")
                return False
    
    def _has_changes(self, json_files: List[Path]) -> bool:
        """Verifica si hay cambios en los archivos de la base de datos."""
        for json_file in json_files:
            file_path = str(json_file)
            current_mtime = json_file.stat().st_mtime
            
            if file_path not in self.file_mtimes or self.file_mtimes[file_path] != current_mtime:
                return True
        
        return False
    
    def _update_indices(self, fact: FactEntry, category_index: Dict, 
                       entity_index: Dict, pattern_index: Dict):
        """Actualiza los índices con un nuevo hecho."""
        # Índice por categoría
        category = fact.category.value
        if category not in category_index:
            category_index[category] = set()
        category_index[category].add(fact.key)
        
        # Índice por entidades (aliases)
        for alias in fact.aliases:
            alias_lower = alias.lower()
            if alias_lower not in entity_index:
                entity_index[alias_lower] = set()
            entity_index[alias_lower].add(fact.key)
        
        # Índice por patrones
        for pattern in fact.question_patterns:
            pattern_lower = pattern.lower()
            if pattern_lower not in pattern_index:
                pattern_index[pattern_lower] = set()
            pattern_index[pattern_lower].add(fact.key)
    
    def get_fact(self, key: str) -> Optional[FactEntry]:
        """
        Obtiene un hecho por su clave.
        
        Args:
            key: Clave del hecho
            
        Returns:
            FactEntry si existe, None si no
        """
        with self.lock:
            fact = self.facts.get(key)
            
            if fact:
                # Incrementar contador de uso
                fact.usage_count += 1
            
            return fact
    
    def search_facts(self, query: str, entities: Optional[List[str]] = None,
                    category: Optional[QuestionType] = None) -> List[FactEntry]:
        """
        Busca hechos relevantes usando query, entidades y categoría.
        
        Args:
            query: Query de búsqueda normalizada
            entities: Lista de entidades extraídas
            category: Categoría de pregunta (opcional)
            
        Returns:
            Lista de hechos relevantes ordenados por relevancia
        """
        with self.lock:
            self.total_searches += 1
            
            candidates = []
            query_lower = query.lower()
            
            # 1. Búsqueda por categoría (filtro inicial)
            if category:
                category_facts = self.category_index.get(category.value, set())
            else:
                category_facts = set(self.facts.keys())
            
            # 2. Búsqueda directa por entidades
            if entities:
                for entity in entities:
                    entity_lower = entity.lower()
                    
                    # Buscar en índice de entidades
                    if entity_lower in self.entity_index:
                        for fact_key in self.entity_index[entity_lower]:
                            if fact_key in category_facts:
                                fact = self.facts[fact_key]
                                candidates.append((fact, 1.0, "entity_match"))
            
            # 3. Búsqueda por patrones
            for pattern, fact_keys in self.pattern_index.items():
                similarity = self._calculate_similarity(query_lower, pattern)
                
                if similarity > 0.7:
                    for fact_key in fact_keys:
                        if fact_key in category_facts:
                            fact = self.facts[fact_key]
                            # Evitar duplicados
                            if not any(c[0].key == fact.key for c in candidates):
                                candidates.append((fact, similarity, "pattern_match"))
            
            # 4. Búsqueda por palabras clave en query
            if entities and not candidates:
                for entity in entities:
                    entity_lower = entity.lower()
                    for fact_key in category_facts:
                        fact = self.facts[fact_key]
                        
                        # Buscar entidad en patrones del hecho
                        for pattern in fact.question_patterns:
                            if entity_lower in pattern.lower():
                                if not any(c[0].key == fact.key for c in candidates):
                                    candidates.append((fact, 0.8, "keyword_match"))
                                break
            
            # Ordenar por score de relevancia
            candidates.sort(key=lambda x: x[1], reverse=True)
            
            # Incrementar contadores de uso
            results = []
            for fact, score, match_type in candidates:
                fact.usage_count += 1
                results.append(fact)
            
            if results:
                self.successful_searches += 1
            
            return results
    
    @staticmethod
    @lru_cache(maxsize=1000)
    def _calculate_similarity(text1: str, text2: str) -> float:
        """
        Calcula similitud entre dos textos usando distancia de Levenshtein normalizada.
        
        Args:
            text1: Primer texto
            text2: Segundo texto
            
        Returns:
            Score de similitud entre 0.0 y 1.0
        """
        # Implementación simple de distancia de Levenshtein
        if text1 == text2:
            return 1.0
        
        if not text1 or not text2:
            return 0.0
        
        # Matriz de distancias
        len1, len2 = len(text1), len(text2)
        
        # Optimización: si la diferencia de longitud es muy grande, baja similitud
        if abs(len1 - len2) > max(len1, len2) * 0.5:
            return 0.0
        
        # Calcular distancia de Levenshtein
        if len1 < len2:
            text1, text2 = text2, text1
            len1, len2 = len2, len1
        
        current_row = range(len2 + 1)
        for i in range(1, len1 + 1):
            previous_row = current_row
            current_row = [i] + [0] * len2
            
            for j in range(1, len2 + 1):
                add = previous_row[j] + 1
                delete = current_row[j - 1] + 1
                change = previous_row[j - 1]
                
                if text1[i - 1] != text2[j - 1]:
                    change += 1
                
                current_row[j] = min(add, delete, change)
        
        # Normalizar a 0.0-1.0
        distance = current_row[len2]
        max_len = max(len1, len2)
        similarity = 1.0 - (distance / max_len)
        
        return max(0.0, similarity)
    
    def add_fact(self, fact: FactEntry) -> bool:
        """
        Agrega un nuevo hecho a la base de datos.
        
        Args:
            fact: Hecho a agregar
            
        Returns:
            True si se agregó exitosamente
        """
        with self.lock:
            if fact.key in self.facts:
                self.logger.warning(f"Fact with key '{fact.key}' already exists")
                return False
            
            self.facts[fact.key] = fact
            self._update_indices(fact, self.category_index, 
                               self.entity_index, self.pattern_index)
            
            self.logger.info(f"Added new fact: {fact.key}")
            return True
    
    def update_fact(self, key: str, fact: FactEntry) -> bool:
        """
        Actualiza un hecho existente.
        
        Args:
            key: Clave del hecho a actualizar
            fact: Nuevo hecho
            
        Returns:
            True si se actualizó exitosamente
        """
        with self.lock:
            if key not in self.facts:
                self.logger.warning(f"Fact with key '{key}' not found")
                return False
            
            # Actualizar hecho
            old_fact = self.facts[key]
            self.facts[key] = fact
            
            # Reconstruir índices (simplificado)
            self._rebuild_indices()
            
            self.logger.info(f"Updated fact: {key}")
            return True
    
    def _rebuild_indices(self):
        """Reconstruye todos los índices desde cero."""
        self.category_index.clear()
        self.entity_index.clear()
        self.pattern_index.clear()
        
        for fact in self.facts.values():
            self._update_indices(fact, self.category_index,
                               self.entity_index, self.pattern_index)
    
    def reload_database(self) -> bool:
        """
        Recarga la base de datos desde archivos (hot-reload).
        
        Returns:
            True si se recargó exitosamente
        """
        self.logger.info("Reloading fact database...")
        success = self.load_database(force_reload=True)
        
        if success:
            hybrid_logger.log_database_operation("reload", {
                "total_facts": len(self.facts),
                "timestamp": datetime.now().isoformat()
            })
        
        return success
    
    def get_database_stats(self) -> DatabaseStats:
        """
        Obtiene estadísticas de la base de datos.
        
        Returns:
            DatabaseStats con información de la base de datos
        """
        with self.lock:
            # Contar hechos por categoría
            facts_by_category = {}
            for category, fact_keys in self.category_index.items():
                facts_by_category[category] = len(fact_keys)
            
            # Obtener hechos más usados
            sorted_facts = sorted(
                self.facts.items(),
                key=lambda x: x[1].usage_count,
                reverse=True
            )
            most_used = [key for key, _ in sorted_facts[:10]]
            
            # Calcular tamaño aproximado
            import sys
            size_bytes = sys.getsizeof(self.facts)
            size_mb = size_bytes / (1024 * 1024)
            
            return DatabaseStats(
                total_facts=len(self.facts),
                facts_by_category=facts_by_category,
                most_used_facts=most_used,
                last_reload_time=self.last_reload,
                database_size_mb=round(size_mb, 2)
            )
    
    def get_fact_by_category(self, category: QuestionType) -> List[FactEntry]:
        """
        Obtiene todos los hechos de una categoría.
        
        Args:
            category: Categoría de pregunta
            
        Returns:
            Lista de hechos de esa categoría
        """
        with self.lock:
            fact_keys = self.category_index.get(category.value, set())
            return [self.facts[key] for key in fact_keys]
    
    def search_success_rate(self) -> float:
        """
        Calcula la tasa de éxito de búsquedas.
        
        Returns:
            Porcentaje de búsquedas exitosas
        """
        if self.total_searches == 0:
            return 0.0
        
        return (self.successful_searches / self.total_searches) * 100


# Instancia global del gestor de base de datos
fact_database_manager = FactDatabaseManager()