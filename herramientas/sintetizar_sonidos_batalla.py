"""Sintetiza los efectos de sonido del combate final en ``Audios/Batalla/``.

Sonidos retro de 8 bits hechos con ondas, ruido y envolventes, solo con la
biblioteca estándar. Son provisionales: si el equipo deja un ``.wav`` propio
con el mismo nombre, este script no lo sobrescribe (salvo con ``--forzar``).

Uso: .venv\\Scripts\\python.exe herramientas/sintetizar_sonidos_batalla.py [--forzar]
"""
import argparse
import math
import random
import struct
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nucleo.rutas import RAIZ  # noqa: E402

FRECUENCIA = 22050
CARPETA = RAIZ / "Audios" / "Batalla"


# --- Piezas básicas ---------------------------------------------------------
def muestras(segundos):
    return int(segundos * FRECUENCIA)


def barrido(segundos, inicio, fin, forma="cuadrada", curva=1.0):
    """Tono cuya frecuencia va de ``inicio`` a ``fin`` (Hz)."""
    total, fase, salida = muestras(segundos), 0.0, []
    for i in range(total):
        avance = (i / total) ** curva
        frecuencia = inicio + (fin - inicio) * avance
        fase = (fase + frecuencia / FRECUENCIA) % 1.0
        salida.append(onda(forma, fase))
    return salida


def onda(forma, fase):
    if forma == "cuadrada":
        return 1.0 if fase < .5 else -1.0
    if forma == "triangular":
        return 4 * fase - 1 if fase < .5 else 3 - 4 * fase
    if forma == "sierra":
        return 2 * fase - 1
    return math.sin(math.tau * fase)


def ruido(segundos, azar, suavizado=0.0):
    """Ruido blanco; ``suavizado`` cerca de 1 lo vuelve grave (filtro de un polo)."""
    valor, salida = 0.0, []
    for _ in range(muestras(segundos)):
        valor = valor * suavizado + azar.uniform(-1, 1) * (1 - suavizado)
        salida.append(valor)
    return salida


def envolvente(senal, ataque=.005, caida=6.0):
    """Subida breve y caída exponencial (``caida`` mayor = más corta)."""
    total = len(senal)
    subida = max(1, muestras(ataque))
    return [v * min(1.0, i / subida) * math.exp(-caida * i / total) for i, v in enumerate(senal)]


def tremolo(senal, hz, profundidad=.5):
    return [v * (1 - profundidad + profundidad * (math.sin(math.tau * hz * i / FRECUENCIA) + 1) / 2)
            for i, v in enumerate(senal)]


def mezclar(*capas):
    """Suma capas ``(señal, volumen, retraso_s)``."""
    total = max(len(s) + muestras(r) for s, _, r in capas)
    salida = [0.0] * total
    for senal, volumen, retraso in capas:
        inicio = muestras(retraso)
        for i, v in enumerate(senal):
            salida[inicio + i] += v * volumen
    return salida


def notas(frecuencias, duracion, forma="cuadrada", caida=5.0, separacion=None):
    separacion = duracion if separacion is None else separacion
    return mezclar(*((envolvente(barrido(duracion, f, f, forma), caida=caida), 1.0, i * separacion)
                     for i, f in enumerate(frecuencias)))


def silencio_final(senal, segundos=.02):
    return senal + [0.0] * muestras(segundos)


# --- Sonidos -----------------------------------------------------------------
def sonidos(azar):
    return {
        # Las marcas aparecen: zumbido que sube y vibra.
        "rayo_aviso": envolvente(tremolo(barrido(.6, 260, 900, "sierra", .8), 14, .6), ataque=.08, caida=1.5),
        # Cae el rayo: estallido de ruido con golpe grave.
        "rayo_impacto": mezclar((envolvente(ruido(.45, azar, .35), caida=7), .8, 0),
                                (envolvente(barrido(.45, 90, 32, "seno"), caida=4), 1.0, 0),
                                (envolvente(barrido(.12, 1800, 300, "cuadrada"), caida=9), .25, 0)),
        # El bláster del jugador.
        "blaster_disparo": mezclar((envolvente(barrido(.16, 1500, 420, "cuadrada", .6), caida=7), .7, 0),
                                   (envolvente(ruido(.05, azar), caida=10), .2, 0)),
        # El disparo alcanza a un mini-núcleo: chasquido metálico.
        "mini_golpe": mezclar(*((envolvente(barrido(.14, f, f, "seno"), caida=14), .5, 0) for f in (930, 1370, 2110)),
                              (envolvente(ruido(.03, azar), caida=12), .5, 0)),
        # Explota un mini-núcleo.
        "mini_explosion": mezclar((envolvente(ruido(.75, azar, .55), caida=4), 1.0, 0),
                                  (envolvente(barrido(.5, 120, 40, "seno"), caida=5), .8, 0),
                                  (envolvente(ruido(.4, azar, .1), caida=9), .3, .05),
                                  (envolvente(barrido(.2, 600, 1200, "cuadrada"), caida=8), .15, .1)),
        # Pulso de un mini-núcleo.
        "mini_disparo": mezclar((envolvente(barrido(.35, 190, 65, "seno"), caida=4), 1.0, 0),
                                (envolvente(barrido(.35, 380, 130, "cuadrada"), caida=6), .25, 0)),
        # Aparece un mini-núcleo: arpegio inquietante.
        "mini_aparicion": notas((330, 392, 466, 554), .1, "cuadrada", caida=4),
        # Te derriban: tono que cae.
        "derribado": envolvente(tremolo(barrido(.6, 620, 140, "triangular", .7), 9, .4), caida=2.5),
        # Te levantan: arpegio que sube.
        "levantado": notas((523, 659, 784, 1047), .09, "triangular", caida=3),
        # Se pierde un corazón de señal: alarma corta.
        "senal_perdida": mezclar(*((envolvente(barrido(.09, f, f, "cuadrada"), ataque=.002, caida=1.5), .6, i * .1)
                                   for i, f in enumerate((880, 660, 880, 660)))),
        # Empiezan los rayos rojos: sirena.
        "cambio_fase": envolvente(mezclar((barrido(.5, 420, 980, "seno"), .7, 0), (barrido(.5, 980, 420, "seno"), .7, .5),
                                          (barrido(.5, 420, 980, "cuadrada"), .15, 0), (barrido(.5, 980, 420, "cuadrada"), .15, .5)),
                                  ataque=.04, caida=1.2),
        # Recoger o entregar una pieza.
        "recoger_material": notas((660, 990), .07, "cuadrada", caida=4),
        # Se fabrica el equipo: trinquete y acorde final.
        "fabricar": mezclar(*((envolvente(ruido(.025, azar), caida=10), .45, i * .07) for i in range(6)),
                            (notas((523, 784, 1047), .25, "triangular", caida=2.5, separacion=0), .5, .45)),
    }


def normalizar(senal, pico=.8):
    maximo = max(1e-9, max(abs(v) for v in senal))
    return [v / maximo * pico for v in senal]


def guardar(ruta, senal):
    datos = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, v)) * 32767)) for v in senal)
    with wave.open(str(ruta), "wb") as archivo:
        archivo.setnchannels(1)
        archivo.setsampwidth(2)
        archivo.setframerate(FRECUENCIA)
        archivo.writeframes(datos)


def generar(carpeta=CARPETA, forzar=False, semilla=7):
    """Escribe los ``.wav``; devuelve los nombres creados (no toca los existentes)."""
    carpeta.mkdir(parents=True, exist_ok=True)
    creados = []
    for nombre, senal in sonidos(random.Random(semilla)).items():
        ruta = carpeta / f"{nombre}.wav"
        if ruta.exists() and not forzar:
            continue
        guardar(ruta, silencio_final(normalizar(senal)))
        creados.append(nombre)
    return creados


if __name__ == "__main__":
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("--forzar", action="store_true", help="sobrescribe los .wav existentes")
    creados = generar(forzar=argumentos.parse_args().forzar)
    print("Creados:", ", ".join(creados) if creados else "ninguno (ya existían)")
