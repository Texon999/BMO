"""
Sistema de Verificación de Hechos para BMO
Detecta preguntas factuales y busca información actualizada automáticamente

Características:
- Detección automática de preguntas factuales
- Búsqueda web para datos específicos
- Respuestas precisas sin contaminar el system prompt
- Mantiene velocidad para preguntas conversacionales
"""
import logging
import re
from typing import Optional, Dict, Any
import requests
from ddgs import DDGS

log = logging.getLogger("BMO.FactChecker")

class FactChecker:
    """Verificador de hechos con búsqueda web automática"""
    
    def __init__(self):
        self.factual_patterns = [
            # Banderas
            r"colores?\s+de\s+la\s+bandera\s+de\s+(\w+)",
            r"bandera\s+de\s+(\w+).*colores?",
            r"qué\s+colores?\s+tiene\s+la\s+bandera\s+de\s+(\w+)",
            
            # Geografía
            r"capital\s+de\s+(\w+)",
            r"cuál\s+es\s+la\s+capital\s+de\s+(\w+)",
            
            # Población
            r"población\s+de\s+(\w+)",
            r"cuántos\s+habitantes\s+tiene\s+(\w+)",
            
            # Fechas históricas
            r"cuándo\s+se\s+fundó\s+(\w+)",
            r"independencia\s+de\s+(\w+)",
            
            # Datos generales
            r"qué\s+es\s+(\w+)",
            r"quién\s+es\s+(\w+)",
        ]
        
        # Cache simple para evitar búsquedas repetidas
        self.cache = {}
    
    def is_factual_question(self, text: str) -> Optional[Dict[str, str]]:
        """
        Detecta si una pregunta es factual y extrae información relevante
        
        Returns:
            Dict con 'type', 'entity', 'query' si es factual, None si no
        """
        text_lower = text.lower().strip()
        
        for pattern in self.factual_patterns:
            match = re.search(pattern, text_lower)
            if match:
                entity = match.group(1) if match.groups() else None
                
                # Determinar tipo de pregunta
                if "bandera" in text_lower or "colores" in text_lower:
                    return {
                        "type": "flag_colors",
                        "entity": entity,
                        "query": f"colores bandera {entity}" if entity else "bandera colores"
                    }
                elif "capital" in text_lower:
                    return {
                        "type": "capital",
                        "entity": entity,
                        "query": f"capital de {entity}" if entity else "capital"
                    }
                elif "población" in text_lower or "habitantes" in text_lower:
                    return {
                        "type": "population",
                        "entity": entity,
                        "query": f"población {entity}" if entity else "población"
                    }
                elif "fundó" in text_lower or "independencia" in text_lower:
                    return {
                        "type": "history",
                        "entity": entity,
                        "query": f"historia {entity}" if entity else "historia"
                    }
                else:
                    return {
                        "type": "general",
                        "entity": entity,
                        "query": f"qué es {entity}" if entity else text_lower
                    }
        
        return None
    
    def search_fact(self, query: str, max_results: int = 2) -> Optional[str]:
        """
        Busca información factual usando DuckDuckGo
        
        Args:
            query: Consulta de búsqueda
            max_results: Máximo número de resultados a considerar
            
        Returns:
            Información encontrada o None si no hay resultados
        """
        # Verificar cache
        cache_key = query.lower().strip()
        if cache_key in self.cache:
            log.debug(f"[FACT] Cache hit for: {query}")
            return self.cache[cache_key]
        
        try:
            log.info(f"[FACT] Searching for: {query}")
            
            # Mejorar query para búsquedas específicas
            enhanced_query = self._enhance_query(query)
            
            with DDGS() as ddgs:
                results = []
                
                # Intentar búsqueda de texto con query mejorada
                try:
                    results = list(ddgs.text(enhanced_query, region='es-es', max_results=max_results))
                except Exception as e:
                    log.warning(f"[FACT] Enhanced search failed: {e}")
                
                # Si no hay resultados, intentar query original
                if not results:
                    try:
                        results = list(ddgs.text(query, region='es-es', max_results=max_results))
                    except Exception as e:
                        log.warning(f"[FACT] Original search failed: {e}")
                
                # Si aún no hay resultados, intentar con región diferente
                if not results:
                    try:
                        results = list(ddgs.text(enhanced_query, region='us-en', max_results=max_results))
                    except Exception as e:
                        log.warning(f"[FACT] Fallback search failed: {e}")
                
                if results:
                    # Combinar información de los primeros resultados
                    combined_info = []
                    for result in results[:max_results]:
                        title = result.get('title', '')
                        body = result.get('body', result.get('snippet', ''))
                        
                        if title and body:
                            combined_info.append(f"{title}: {body[:200]}")
                    
                    if combined_info:
                        fact_info = " | ".join(combined_info)
                        
                        # Guardar en cache
                        self.cache[cache_key] = fact_info
                        
                        log.info(f"[FACT] Found information for: {query}")
                        return fact_info
                
                log.info(f"[FACT] No results found for: {query}")
                return None
                
        except Exception as e:
            log.error(f"[FACT] Search error for '{query}': {e}")
            return None
    
    def _enhance_query(self, query: str) -> str:
        """Mejora la query para búsquedas más específicas"""
        query_lower = query.lower()
        
        # Mejorar búsquedas de banderas
        if "bandera" in query_lower and "colores" in query_lower:
            # Extraer país
            for word in query.split():
                if len(word) > 3 and word.lower() not in ['bandera', 'colores', 'de', 'la', 'los']:
                    return f"bandera {word} colores franjas"
        
        # Mejorar búsquedas de capitales
        if "capital" in query_lower:
            for word in query.split():
                if len(word) > 3 and word.lower() not in ['capital', 'de', 'la', 'cual', 'es']:
                    return f"capital {word} ciudad"
        
        return query
    
    def get_factual_response(self, question: str) -> Optional[str]:
        """
        Obtiene una respuesta factual completa para una pregunta
        
        Args:
            question: Pregunta del usuario
            
        Returns:
            Respuesta factual o None si no se puede responder
        """
        fact_info = self.is_factual_question(question)
        if not fact_info:
            return None
        
        # Buscar información
        search_result = self.search_fact(fact_info["query"])
        if not search_result:
            return None
        
        # Formatear respuesta según el tipo
        entity = fact_info.get("entity", "").title()
        fact_type = fact_info["type"]
        
        if fact_type == "flag_colors" and entity:
            # Extraer colores específicos de la información
            colors_found = self._extract_flag_colors(search_result, entity)
            if colors_found:
                return f"La bandera de {entity} tiene los colores: {colors_found}."
        
        elif fact_type == "capital" and entity:
            capital = self._extract_capital(search_result, entity)
            if capital:
                return f"La capital de {entity} es {capital}."
        
        elif fact_type == "population" and entity:
            population = self._extract_population(search_result, entity)
            if population:
                return f"La población de {entity} es aproximadamente {population}."
        
        # Respuesta genérica basada en la búsqueda
        return f"Según la información encontrada: {search_result[:300]}..."
    
    def _extract_flag_colors(self, text: str, country: str) -> Optional[str]:
        """Extrae colores de bandera del texto de búsqueda"""
        text_lower = text.lower()
        
        # Patrones comunes para colores de banderas
        color_patterns = [
            r"colores?\s+([^.]+)",
            r"franjas?\s+([^.]+)",
            r"bandera.*?([a-záéíóúñ\s,y]+(?:amarillo|azul|rojo|verde|blanco|negro|naranja)[^.]*)",
        ]
        
        for pattern in color_patterns:
            match = re.search(pattern, text_lower)
            if match:
                colors_text = match.group(1).strip()
                # Limpiar y formatear
                colors_text = re.sub(r'\s+', ' ', colors_text)
                if len(colors_text) < 100:  # Evitar texto muy largo
                    return colors_text
        
        return None
    
    def _extract_capital(self, text: str, country: str) -> Optional[str]:
        """Extrae capital del texto de búsqueda"""
        text_lower = text.lower()
        
        patterns = [
            rf"capital\s+de\s+{country.lower()}\s+es\s+([^.,]+)",
            rf"{country.lower()}.*capital.*?([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
            r"capital[:\s]+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                capital = match.group(1).strip().title()
                if len(capital) < 50:  # Nombre razonable
                    return capital
        
        return None
    
    def _extract_population(self, text: str, country: str) -> Optional[str]:
        """Extrae población del texto de búsqueda"""
        text_lower = text.lower()
        
        patterns = [
            r"población.*?([0-9,.\s]+(?:millones?|habitantes?|personas?))",
            r"([0-9,.\s]+(?:millones?|habitantes?)).*población",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                population = match.group(1).strip()
                if len(population) < 50:
                    return population
        
        return None

# Instancia global
fact_checker = FactChecker()