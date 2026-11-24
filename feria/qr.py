"""QR de la sesión como superficie de pygame (módulos nítidos, sin suavizado)."""
import importlib.util
import sys

import pygame

ZONA_SILENCIO = 4  # módulos blancos alrededor: los lectores la necesitan


def segno_disponible():
    """True si se puede importar segno.

    Si el juego se abrió con otro Python (p. ej. el botón ▶ de VS Code con el
    Python del sistema), se busca en el ``.venv`` del proyecto: segno es Python
    puro, así que sirve igual. Solo se añade esa carpeta si allí está segno."""
    if importlib.util.find_spec("segno") is not None:
        return True
    from nucleo.rutas import RAIZ
    paquetes = RAIZ / ".venv" / "Lib" / "site-packages"
    if (paquetes / "segno").is_dir():
        sys.path.append(str(paquetes))
        importlib.invalidate_caches()
    return importlib.util.find_spec("segno") is not None


def superficie_qr(texto, lado_max):
    """QR de ``texto`` que cabe en ``lado_max`` px, con módulos de tamaño entero."""
    segno_disponible()
    import segno  # solo al dibujar: el módulo se puede importar sin la librería
    qr = segno.make(texto, error="m", micro=False)
    filas = [list(fila) for fila in qr.matrix]
    modulos = len(filas) + 2 * ZONA_SILENCIO
    tam = max(1, lado_max // modulos)
    superficie = pygame.Surface((modulos * tam, modulos * tam))
    superficie.fill((255, 255, 255))
    for y, fila in enumerate(filas):
        for x, oscuro in enumerate(fila):
            if oscuro:
                superficie.fill((0, 0, 0), ((x + ZONA_SILENCIO) * tam, (y + ZONA_SILENCIO) * tam, tam, tam))
    return superficie
