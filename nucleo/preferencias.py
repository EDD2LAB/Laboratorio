"""Preferencias del jugador (modo de pantalla) guardadas en la raíz del juego.

Se leen y escriben solo cuando se piden; importar el módulo no toca disco.
"""
import json

from nucleo.rutas import RAIZ

ARCHIVO = RAIZ / "preferencias_usuario.json"
MODOS_PANTALLA = ("maximizada", "ventana", "completa")
PREDETERMINADAS = {"modo_pantalla": "maximizada"}
# Volúmenes (0..1) del multijugador y la campaña con bots.
VOLUMENES = {"volumen_general": 1.0, "volumen_musica": 0.45, "volumen_ambiente": 0.45, "volumen_efectos": 0.70}
PREDETERMINADAS.update(VOLUMENES)
# Interruptores de ambiente y accesibilidad.
INTERRUPTORES = {"niebla": True, "alto_contraste": False, "narracion": False}
PREDETERMINADAS.update(INTERRUPTORES)
# Variante del personaje por rol (solo estos roles tienen las dos).
APARIENCIAS = {"apariencia_aspirante": "hombre", "apariencia_habitante": "hombre"}
PREDETERMINADAS.update(APARIENCIAS)


def cargar():
    preferencias = dict(PREDETERMINADAS)
    try:
        datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return preferencias
    if not isinstance(datos, dict):
        return preferencias
    if datos.get("modo_pantalla") in MODOS_PANTALLA:
        preferencias["modo_pantalla"] = datos["modo_pantalla"]
    for clave in VOLUMENES:
        valor = datos.get(clave)
        if isinstance(valor, (int, float)) and not isinstance(valor, bool) and 0 <= valor <= 1:
            preferencias[clave] = float(valor)
    for clave in INTERRUPTORES:
        if isinstance(datos.get(clave), bool):
            preferencias[clave] = datos[clave]
    for clave in APARIENCIAS:
        if datos.get(clave) in ("hombre", "mujer"):
            preferencias[clave] = datos[clave]
    return preferencias


def guardar(preferencias):
    try:
        ARCHIVO.write_text(json.dumps(preferencias, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as error:  # carpeta de solo lectura: se usa solo en esta sesión
        print("[Preferencias] No se pudieron guardar:", error)
