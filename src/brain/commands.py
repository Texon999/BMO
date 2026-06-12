"""
Sistema de Comandos por Voz para BMO.
Permite ejecutar acciones locales (abrir juegos, programas, páginas)
mediante comandos de voz.

Uso:
  1. Configurar rutas en config.json → "comandos_voz" y "juegos"
  2. En main.py, llamar a ejecutar_comando() ANTES de responder_con_tts()
  3. Si hay match → BMO ejecuta la acción y responde sin pasar por el LLM
"""
import subprocess
import re
import logging
import webbrowser
from pathlib import Path
from typing import Callable

log = logging.getLogger("BMO.Commands")


class ComandoVoz:
    """Comando de voz individual con patrón regex y acción."""

    def __init__(self, nombre: str, patron: str, respuesta: str,
                 ejecutar: Callable[[], None]):
        self.nombre = nombre
        self.patron = re.compile(patron, re.IGNORECASE)
        self.respuesta = respuesta
        self.ejecutar = ejecutar

    def coincide(self, texto: str) -> bool:
        return bool(self.patron.search(texto.strip()))


def _abrir_programa(ruta: str) -> None:
    """Abre un programa o URL con subprocess."""
    try:
        if ruta.startswith("http://") or ruta.startswith("https://"):
            webbrowser.open(ruta)
            log.info("[COMANDO] URL abierta: %s", ruta)
        else:
            subprocess.Popen([ruta], shell=False)
            log.info("[COMANDO] Programa abierto: %s", ruta)
    except Exception as e:
        log.error("[COMANDO] Error al abrir %s: %s", ruta, e)


def construir_comandos(config: dict) -> list[ComandoVoz]:
    """
    Construye la lista de comandos desde config.json["comandos_voz"].

    Formato esperado en config.json:
    {
        "comandos_voz": {
            "minecraft": {
                "ruta": "C:/juegos/minecraft.exe",
                "patron": "\\\\babre\\\\s+(?:el\\\\s+)?minecraft\\\\b",
                "respuesta": "Abriendo Minecraft! Diviertete!"
            }
        }
    }

    Args:
        config: Diccionario de configuración (config_manager.config)

    Returns:
        Lista de objetos ComandoVoz listos para usar
    """
    comandos = []
    comandos_config = config.get("comandos_voz", {})

    for nombre, cfg in comandos_config.items():
        ruta = cfg.get("ruta", "")
        patron = cfg.get(
            "patron",
            rf"\babre\s+(?:el\s+)?{re.escape(nombre)}\b",
        )
        respuesta = cfg.get("respuesta", f"Abriendo {nombre}!")

        if not ruta:
            log.warning("[COMANDOS] '%s' no tiene ruta configurada, ignorando", nombre)
            continue

        cmd = ComandoVoz(
            nombre=nombre,
            patron=patron,
            respuesta=respuesta,
            ejecutar=lambda r=ruta: _abrir_programa(r),
        )
        comandos.append(cmd)
        log.info("[COMANDOS] Registrado: '%s' -> %s", nombre, ruta)

    if not comandos:
        log.info("[COMANDOS] Ningun comando configurado")

    return comandos


def ejecutar_comando(texto: str, comandos: list[ComandoVoz]) -> str | None:
    """
    Verifica si el texto coincide con algun comando registrado.

    Args:
        texto: Texto transcrito por STT
        comandos: Lista de ComandoVoz registrados

    Returns:
        Respuesta a hablar si hay match, None si no hay comando
    """
    texto_clean = texto.lower().strip()

    for cmd in comandos:
        if cmd.coincide(texto_clean):
            log.info("[COMANDOS] Ejecutando: '%s' (trigger: '%s')", cmd.nombre, texto)
            try:
                cmd.ejecutar()
            except Exception as e:
                log.error("[COMANDOS] Error ejecutando '%s': %s", cmd.nombre, e)
                return f"Lo siento, no pude abrir {cmd.nombre}."
            return cmd.respuesta

    return None


# ══════════════════════════════════════════════════════════════════════════════
# SISTEMA DE JUEGOS — "BMO quiero jugar Hollow Knight"
# ══════════════════════════════════════════════════════════════════════════════

# Patrones para detectar intención de jugar, en orden de prioridad.
# El grupo (1) captura el nombre del juego.
_PATRONES_JUEGO = [
    re.compile(r"quiero\s+jugar\s+(?:a\s+|al\s+)?(.+)", re.IGNORECASE),
    re.compile(r"juguemos\s+(?:a\s+|al\s+)?(.+)", re.IGNORECASE),
    re.compile(r"vamos\s+a\s+jugar\s+(?:a\s+|al\s+)?(.+)", re.IGNORECASE),
    re.compile(r"pon\s+(?:el\s+)?(?:juego\s+de\s+)?(.+)", re.IGNORECASE),
    re.compile(r"abre\s+(?:el\s+)?(?:juego\s+)?(.+)", re.IGNORECASE),
    re.compile(r"ejecuta\s+(?:el\s+)?(?:juego\s+)?(.+)", re.IGNORECASE),
]


def construir_juegos(config: dict) -> dict[str, str]:
    """
    Construye el mapeo nombre -> ruta desde config.json["juegos"].

    Formato esperado en config.json:
    {
        "juegos": {
            "hollow knight": "C:/juegos/Hollow Knight/hollow_knight.exe",
            "minecraft":     "C:/juegos/Minecraft/minecraft.exe"
        }
    }

    Args:
        config: Diccionario de configuración (config_manager.config)

    Returns:
        Dict {nombre_normalizado: ruta_al_ejecutable}
    """
    juegos_raw = config.get("juegos", {})
    juegos: dict[str, str] = {}
    for nombre, ruta in juegos_raw.items():
        nombre_key = nombre.strip().lower()
        path = Path(ruta)
        if not path.exists() and not path.is_absolute():
            log.warning("[JUEGOS] '%s' -> %s no encontrado, se intentara igual", nombre, ruta)
        juegos[nombre_key] = ruta
        log.info("[JUEGOS] Registrado: '%s' -> %s", nombre, ruta)
    if not juegos:
        log.info("[JUEGOS] Ningun juego configurado (agrega 'juegos' a config.json)")
    return juegos


def _extraer_nombre_juego(texto: str) -> str | None:
    """
    Extrae el nombre del juego del texto usando los patrones definidos.

    Ej: "quiero jugar hollow knight" -> "hollow knight"
        "juguemos minecraft" -> "minecraft"
        "abre el juego mario" -> "mario"
    """
    t = texto.lower().strip()
    for patron in _PATRONES_JUEGO:
        m = patron.search(t)
        if m:
            nombre = m.group(1).strip()
            # Limpiar artículos/palabras sobrantes al final
            nombre = re.sub(r"\s+(por favor|please|gracias|ok|ahi|ya)$", "", nombre)
            if nombre:
                return nombre
    return None


def _mejor_coincidencia_juego(texto_juego: str, juegos: dict[str, str]) -> str | None:
    """
    Busca la mejor coincidencia del nombre del juego en el diccionario de juegos.
    Primero busca coincidencia exacta, luego parcial.
    """
    tj = texto_juego.lower().strip()
    # Coincidencia exacta
    if tj in juegos:
        return tj
    # Coincidencia parcial: el texto contiene el nombre del juego
    for nombre_key in juegos:
        if nombre_key in tj or tj in nombre_key:
            return nombre_key
    # Coincidencia por palabras: todas las palabras del nombre aparecen en el texto
    palabras_juego = set(tj.split())
    for nombre_key in juegos:
        palabras_key = set(nombre_key.split())
        if palabras_key & palabras_juego:  # al menos una palabra coincide
            return nombre_key
    return None


def ejecutar_juego(texto: str, juegos: dict[str, str]) -> str | None:
    """
    Verifica si el texto es un comando para abrir un juego.

    Args:
        texto: Texto transcrito por STT
        juegos: Dict {nombre: ruta} de juegos configurados

    Returns:
        Mensaje a hablar si hay match, None si no es un comando de juego
    """
    if not juegos:
        return None

    texto_juego = _extraer_nombre_juego(texto)
    if not texto_juego:
        return None

    juego_key = _mejor_coincidencia_juego(texto_juego, juegos)
    if not juego_key:
        return None

    ruta = juegos[juego_key]
    nombre_mostrar = juego_key.title()

    log.info("[JUEGOS] Abriendo '%s' -> %s", juego_key, ruta)
    try:
        _abrir_programa(ruta)
    except Exception as e:
        log.error("[JUEGOS] Error abriendo '%s': %s", juego_key, e)
        return f"Lo siento, no pude abrir {nombre_mostrar}."

    return f"Abriendo {nombre_mostrar}! Que te diviertas!"
