"""La Copa: Voces en las Alturas — punto de entrada.

Ejecutar desde la raíz del proyecto:  python juego.py
El código del juego vive en los paquetes (ver CLAUDE.md).
"""
import pygame

from interfaz.inicio import mostrar_menu_inicio
from un_jugador.partida import main as jugar_un_jugador


def main():
    if mostrar_menu_inicio() == "individual":
        jugar_un_jugador()
    else:
        pygame.quit()


if __name__ == "__main__":
    main()
