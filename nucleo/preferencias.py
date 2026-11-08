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
    return preferencias


def guardar(preferencias):
    try:
        ARCHIVO.write_text(json.dumps(preferencias, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as error:  # carpeta de solo lectura: se usa solo en esta sesión
        print("[Preferencias] No se pudieron guardar:", error)
