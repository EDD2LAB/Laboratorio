"""Portapapeles del sistema, con pygame-ce y con pygame (API distinta).

Sin portapapeles disponible (pruebas sin pantalla) copia y pega dentro del juego.
"""
import pygame

_memoria = ""


def _scrap():
    try:
        # pygame-ce no necesita init (y lo marca obsoleto); pygame sí.
        if not hasattr(pygame.scrap, "put_text") and not pygame.scrap.get_init():
            pygame.scrap.init()
        return pygame.scrap
    except (pygame.error, AttributeError, NotImplementedError):
        return None


def copiar(texto):
    global _memoria
    _memoria = texto
    scrap = _scrap()
    if scrap is None:
        return
    try:
        if hasattr(scrap, "put_text"):
            scrap.put_text(texto)
        else:
            scrap.put(pygame.SCRAP_TEXT, texto.encode("utf-8"))
    except (pygame.error, NotImplementedError):
        pass


def pegar():
    scrap = _scrap()
    texto = ""
    if scrap is not None:
        try:
            if hasattr(scrap, "get_text"):
                texto = scrap.get_text() or ""
            else:
                datos = scrap.get(pygame.SCRAP_TEXT)
                texto = datos.decode("utf-8", "ignore") if datos else ""
        except (pygame.error, NotImplementedError):
            texto = ""
    return texto.replace("\x00", "") or _memoria
