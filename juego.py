"""Timeless Glitch — punto de entrada.

Ejecutar desde la raíz del proyecto:  python juego.py
El código del juego vive en los paquetes (ver CLAUDE.md).
"""
import os
import sys

# Antes de iniciar SDL: nitidez con el escalado de Windows (125 %, 150 %) y la pantalla
# completa no se minimiza al perder el foco (Alt+Tab, notificaciones).
os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitorv2")
os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")

import pygame  # noqa: E402

from nucleo import registro  # noqa: E402


def main():
    registro.iniciar()
    try:
        from interfaz.inicio import mostrar_menu_inicio
        mostrar_menu_inicio()
    except Exception:  # noqa: BLE001 - nada debe abrir el diálogo de error de PyInstaller
        # Se registra y se sale con código 1: en la feria, Feria.bat reabre el juego.
        registro.registrar_error("El juego se cerró por un error")
        pygame.quit()
        sys.exit(1)
    pygame.quit()


if __name__ == "__main__":
    main()
