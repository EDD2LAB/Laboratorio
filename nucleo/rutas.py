"""Rutas del proyecto, relativas a la raíz (funciona desde cualquier cwd)."""
import sys
from pathlib import Path

# En el ejecutable (PyInstaller) los datos viven en la carpeta _internal.
RAIZ = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
IMAGENES = RAIZ / "Imagenes"
FUENTES = RAIZ / "Fuentes"
AUDIOS = RAIZ / "Audios"
HITBOXES = RAIZ / "Hitboxes"
