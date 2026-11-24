"""QR de la sesión como superficie de pygame (módulos nítidos, sin suavizado)."""
import importlib.util
import sys

import pygame

ZONA_SILENCIO = 4  # módulos blancos alrededor: los lectores la necesitan


def segno_disponible():
    """True si se puede importar segno.

    Orden: la instalada en el Python que abrió el juego; la del ``.venv`` del
    proyecto (si se abrió con el Python del sistema, p. ej. con ▶ de VS Code);
    y la copia incluida en ``feria/_vendor`` (BSD, Python puro), para que la
    feria funcione en cualquier computador sin instalar nada."""
    if importlib.util.find_spec("segno") is not None:
        return True
    from nucleo.rutas import RAIZ
    for carpeta in (RAIZ / ".venv" / "Lib" / "site-packages", RAIZ / "feria" / "_vendor"):
        if (carpeta / "segno" / "__init__.py").is_file():
            sys.path.append(str(carpeta))
            importlib.invalidate_caches()
            if importlib.util.find_spec("segno") is not None:
                return True
    return False


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
