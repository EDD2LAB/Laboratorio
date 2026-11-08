"""Rutas del proyecto, relativas a la raíz (funciona desde cualquier cwd)."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
IMAGENES = RAIZ / "Imagenes"
FUENTES = RAIZ / "Fuentes"
AUDIOS = RAIZ / "Audios"
HITBOXES = RAIZ / "Hitboxes"
