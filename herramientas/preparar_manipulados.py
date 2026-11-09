"""Prepara una sola vez el material manipulado y mide los audios.

Ejecutar desde la raíz:  .venv\\Scripts\\python.exe herramientas/preparar_manipulados.py

Usa pygame-ce porque el entorno del proyecto no incluye Pillow. Deja la salida en
Imagenes/Manipulado/procesado/; el juego solo carga esos archivos.
"""
import array
import os
import sys
import wave
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

from nucleo.rutas import RAIZ  # noqa: E402

ORIGEN = RAIZ / "Imagenes" / "Manipulado"
SALIDA = ORIGEN / "procesado"
AUDIOS = RAIZ / "Audios" / "Presente"
RECORTE_FOTO = pygame.Rect(104, 104, 1840, 1840)
LADO_FOTO = 384
TAMANO_CUADRO = (296, 288)  # los dos videos se muestran al mismo tamaño
CUADROS = 8
VENTANA_AUDIO = .05


def es_magenta(color):
    """Fondo y halo: el borde de la tira original es un morado más oscuro."""
    return min(color[0], color[2]) > 90 and color[1] < min(color[0], color[2]) * .55


def quitar_magenta(superficie):
    """Vuelve transparente el fondo y un borde de 1 px, donde queda el halo rosa."""
    ancho, alto = superficie.get_size()
    fondo = {(x, y) for x in range(ancho) for y in range(alto) if es_magenta(superficie.get_at((x, y)))}
    for x, y in fondo:
        for vx, vy in ((x, y), (x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= vx < ancho and 0 <= vy < alto:
                superficie.set_at((vx, vy), (0, 0, 0, 0))


def preparar_video(archivo, destino):
    hoja = pygame.image.load(str(ORIGEN / archivo)).convert_alpha()
    celda = hoja.get_width() // CUADROS
    tira = pygame.Surface((TAMANO_CUADRO[0] * CUADROS, TAMANO_CUADRO[1]), pygame.SRCALPHA)
    for i in range(CUADROS):
        # Primero se limpia, a su resolución real: al ampliar, el halo se haría más grueso.
        cuadro = hoja.subsurface((i * celda, 0, celda, hoja.get_height())).copy()
        quitar_magenta(cuadro)
        tira.blit(pygame.transform.scale(cuadro, TAMANO_CUADRO), (i * TAMANO_CUADRO[0], 0))
    pygame.image.save(tira, str(SALIDA / destino))


def preparar_foto(archivo, destino):
    foto = pygame.image.load(str(ORIGEN / archivo)).convert_alpha()
    pygame.image.save(pygame.transform.scale(foto.subsurface(RECORTE_FOTO), (LADO_FOTO, LADO_FOTO)), str(SALIDA / destino))


def medir_audio(archivo):
    """(duración, pico, tramos de silencio en segundos) para comprobar las marcas."""
    with wave.open(str(AUDIOS / archivo), "rb") as audio:
        tasa = audio.getframerate()
        muestras = array.array("h", audio.readframes(audio.getnframes()))
    pico = max(abs(m) for m in muestras)
    paso = int(tasa * VENTANA_AUDIO)
    silencio = [i * VENTANA_AUDIO for i in range(0, len(muestras) // paso + 1)
                if max((abs(m) for m in muestras[i * paso:(i + 1) * paso]), default=0) < pico * .05]
    tramos = []
    for instante in silencio:
        if tramos and instante - tramos[-1][1] < VENTANA_AUDIO * 1.5:
            tramos[-1][1] = instante
        else:
            tramos.append([instante, instante])
    return len(muestras) / tasa, pico, [(round(a, 2), round(b + VENTANA_AUDIO, 2)) for a, b in tramos]


def main():
    pygame.init()
    pygame.display.set_mode((10, 10))
    SALIDA.mkdir(exist_ok=True)
    preparar_video("video_original_8f.png", "video_original.png")
    preparar_video("video_manipulado_8f.png", "video_manipulado.png")
    preparar_foto("foto_original.jpg", "foto_original.png")
    preparar_foto("foto_manipulada.jpg", "foto_manipulada.png")
    for archivo in ("audio_original.wav", "audio_suplantado.wav"):
        print(archivo, *medir_audio(archivo))
    pygame.quit()


if __name__ == "__main__":
    main()
