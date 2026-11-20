"""Diagnóstico del ejecutable (build con consola, sin --windowed).

Recorre, dentro del entorno empaquetado y sin pantalla (SDL_VIDEODRIVER=dummy):
menú de inicio -> campaña local con bots -> primer caso de La Copa -> portal a
Distrito Conecta -> portal a Ciudad Núcleo -> vuelta al menú. Dibuja cada era
con la vista real del juego, así que comprueba que imágenes, mapas, hitboxes,
datos y audio se encuentran en _internal. Imprime cada paso; sale con código 1
si algo falla.
"""
import os
import sys
import time
import traceback

if not getattr(sys, "frozen", False):  # también se puede correr desde el código fuente
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def paso(texto):
    print("[diagnóstico]", texto, flush=True)


def llevar_al_portal(partida, identificador):
    """Pone a la persona junto al portal de su dimensión (como si caminara hasta él)."""
    from multijugador.dimensiones_red import rect_portal
    jugador = partida.jugadores[identificador]
    dimension = jugador["dimension"]
    x, y, w, h = rect_portal(dimension, partida.colisiones_de(dimension).datos)
    jugador.update(x=x + w / 2, y=y + h + 10, interior=None)


def main():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    import pygame
    from nucleo.rutas import RAIZ
    paso(f"frozen={getattr(sys, 'frozen', False)}  RAIZ={RAIZ}")
    for carpeta in ("Imagenes", "Audios", "Fuentes", "Hitboxes", "datos"):
        if not (RAIZ / carpeta).is_dir():
            raise RuntimeError("Falta la carpeta " + carpeta)
    if not (RAIZ / "multijugador" / "configuracion.json").is_file():
        raise RuntimeError("Falta multijugador/configuracion.json")
    pygame.init()
    from interfaz.inicio import MenuInicio
    menu = MenuInicio()
    menu.dibujar()
    paso("menú de inicio abierto: " + ", ".join(sorted(menu.botones)))
    menu.campos["nombre"] = "Diagnóstico"
    inicio = time.monotonic()
    menu.accionar("iniciar_campana_solo:la_copa")
    if menu.vista != "partida":
        raise RuntimeError("No se creó la campaña local: " + menu.mensaje)
    paso(f"campaña local creada en {time.monotonic() - inicio:.1f} s; caso: {menu.estado['mundo']['caso']['titulo']}")
    partida = menu.cliente._partida
    for destino in ("presente", "futuro"):
        for _ in range(20):  # unos cuadros de juego reales en la era actual
            menu.partida.actualizar(1 / 30, menu.cliente)
            menu.cliente.actualizar(1 / 30)
            menu.recibir()
            menu.dibujar()
        llevar_al_portal(partida, menu.identificador)
        menu.cliente.actuar("usar_portal", destino=destino)
        for _ in range(30):
            menu.cliente.actualizar(1 / 30)
            menu.recibir()
            menu.partida.actualizar(1 / 30, menu.cliente)
            menu.dibujar()
        llegada = partida.jugadores[menu.identificador]["dimension"]
        if llegada != destino or menu.partida.dimension != destino:
            raise RuntimeError(f"El portal no llevó a {destino} (servidor: {llegada}, vista: {menu.partida.dimension})")
        paso(f"portal: el equipo llegó a {destino} y la vista dibujó la era")
    menu.limpiar_conexion()
    menu.vista = "principal"
    menu.dibujar()
    paso("vuelta al menú de inicio")
    pygame.quit()
    paso("OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
