"""Timeless Glitch — punto de entrada.

Ejecutar desde la raíz del proyecto:  python juego.py
El código del juego vive en los paquetes (ver CLAUDE.md).
"""
import pygame

from interfaz.inicio import mostrar_menu_inicio


def main():
    mostrar_menu_inicio()
    pygame.quit()


if __name__ == "__main__":
    main()
