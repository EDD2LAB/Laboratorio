"""Prepara el arte esencial a partir de los originales de Gemini.

Ejecutar desde la raíz:  .venv\\Scripts\\python.exe herramientas/preparar_arte_esencial.py

Lee de ``Imagenes/assets finales/`` (no los modifica ni los borra) y escribe:

- ``Indicadores Puente/Indicador_base.png``: medidor sin magenta, recortado en un
  lienzo cuadrado centrado en la cara del medidor y reducido al tamaño del juego.
  Junto a él, ``Indicador_base.json`` guarda el radio de la cara (para el arco verde).
- ``Indicadores Puente/Aguja_base.png``: aguja sin magenta, con el centro del remache
  exactamente en el centro del lienzo y un largo de 0,8 del radio de la cara.
- ``Intro/vineta1.png`` (960×720), ``Intro/vineta2.png`` (960×536, sin recortar),
  ``Finales/Final_tres_eras.png`` y ``Finales/Final_humo_tres_eras.png`` (960×720).

Estas ilustraciones no son pixel art en cuadrícula: se reducen aquí UNA sola vez con
Pillow y LANCZOS, y el juego las carga ya al tamaño final. Si cambia un original,
basta con volver a correr el script.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nucleo.rutas import IMAGENES  # noqa: E402

ORIGEN = IMAGENES / "assets finales"
LADO_MEDIDOR = 220          # mismo tamaño que dibuja el minijuego del puente
LARGO_AGUJA_RELATIVO = 0.8  # largo de la aguja respecto al radio de la cara
ILUSTRACIONES = (
    ("vineta1.png", "Intro/vineta1.png", (960, 720)),
    ("vineta2.png", "Intro/vineta2.png", (960, 536)),
    ("Final_tres_eras.png", "Finales/Final_tres_eras.png", (960, 720)),
    ("Final_humo_tres_eras.png", "Finales/Final_humo_tres_eras.png", (960, 720)),
)
MAGENTA_FONDO = 110  # min(R, B) - G desde el que un píxel es fondo
MAGENTA_BORDE = 30   # en el contorno, desde aquí el píxel conserva un halo rosa
MAGENTA_VISIBLE = 60  # comprobación final: ningún píxel visible por encima de esto


def tono_magenta(r, g, b):
    """Cuánto se acerca un color al magenta del fondo (≈ #FE01FA)."""
    return min(r, b) - g


def datos(imagen):
    """Píxeles como lista (Pillow 13 renombró getdata a get_flattened_data)."""
    return list(getattr(imagen, "get_flattened_data", imagen.getdata)())


def quitar_magenta(imagen):
    """RGBA con el fondo magenta transparente y el halo rosa del contorno eliminado."""
    imagen = imagen.convert("RGBA")
    ancho, alto = imagen.size
    pixeles = datos(imagen)
    transparente = [tono_magenta(r, g, b) >= MAGENTA_FONDO or (r > 200 and g < 70 and b > 200)
                    for r, g, b, _ in pixeles]
    # El borde antialiasado mezcla el dibujo con el magenta: se pela por capas.
    for _ in range(3):
        quitar = []
        for indice, (r, g, b, _) in enumerate(pixeles):
            if transparente[indice] or tono_magenta(r, g, b) < MAGENTA_BORDE:
                continue
            x, y = indice % ancho, indice // ancho
            if ((x > 0 and transparente[indice - 1]) or (x < ancho - 1 and transparente[indice + 1])
                    or (y > 0 and transparente[indice - ancho]) or (y < alto - 1 and transparente[indice + ancho])):
                quitar.append(indice)
        if not quitar:
            break
        for indice in quitar:
            transparente[indice] = True
    imagen.putdata([(0, 0, 0, 0) if transparente[i] else (r, g, b, 255) for i, (r, g, b, _) in enumerate(pixeles)])
    return imagen


def reducir(imagen, tamano):
    """LANCZOS con alfa premultiplicado: el borde no arrastra color de píxeles transparentes."""
    if imagen.mode == "RGBA":
        return imagen.convert("RGBa").resize(tamano, Image.LANCZOS).convert("RGBA")
    return imagen.convert("RGB").resize(tamano, Image.LANCZOS)


def cara_del_medidor(imagen):
    """Centro y radio de la cara clara del medidor (relleno desde el centro del dibujo)."""
    escala = 4
    chica = imagen.resize((imagen.width // escala, imagen.height // escala), Image.NEAREST)
    ancho, alto = chica.size
    datos = chica.load()

    def clara(x, y):
        r, g, b, a = datos[x, y]
        return a and r > 200 and g > 160 and b > 110 and r - b < 120

    caja = chica.getbbox()
    inicio = ((caja[0] + caja[2]) // 2, (caja[1] + caja[3]) // 2)
    if not clara(*inicio):
        raise ValueError("El centro del medidor no es la cara clara; revisa indicador_base.png")
    vistos, pila = {inicio}, [inicio]
    while pila:
        x, y = pila.pop()
        for vecino in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if vecino not in vistos and 0 <= vecino[0] < ancho and 0 <= vecino[1] < alto and clara(*vecino):
                vistos.add(vecino)
                pila.append(vecino)
    xs = [x for x, _ in vistos]
    ys = [y for _, y in vistos]
    izquierda, derecha = min(xs) * escala, (max(xs) + 1) * escala
    arriba, abajo = min(ys) * escala, (max(ys) + 1) * escala
    centro = ((izquierda + derecha) / 2, (arriba + abajo) / 2)
    radio = ((derecha - izquierda) + (abajo - arriba)) / 4
    return centro, radio


def preparar_medidor(origen):
    imagen = quitar_magenta(Image.open(origen))
    (cx, cy), radio = cara_del_medidor(imagen)
    izquierda, arriba, derecha, abajo = imagen.getbbox()
    mitad = max(cx - izquierda, derecha - cx, cy - arriba, abajo - cy)
    caja = tuple(round(v) for v in (cx - mitad, cy - mitad, cx + mitad, cy + mitad))
    cuadrado = imagen.crop(caja)  # lo que sale del original queda transparente
    factor = LADO_MEDIDOR / cuadrado.width
    return reducir(cuadrado, (LADO_MEDIDOR, LADO_MEDIDOR)), round(radio * factor, 2)


def remache_de_la_aguja(imagen):
    """Centro del remache: las filas anchas de la mitad inferior de la aguja."""
    alfa = imagen.getchannel("A").load()
    izquierda, arriba, derecha, abajo = imagen.getbbox()
    filas = {}
    for y in range(arriba, abajo):
        xs = [x for x in range(izquierda, derecha) if alfa[x, y]]
        if xs:
            filas[y] = xs
    medio = (arriba + abajo) // 2
    anchos_eje = sorted(len(xs) for y, xs in filas.items() if y >= medio)
    eje = anchos_eje[len(anchos_eje) // 4]  # el vástago es la parte más delgada
    remache = [y for y, xs in filas.items() if y >= medio and len(xs) > eje * 1.6]
    if not remache:
        raise ValueError("No se encontró el remache en aguja_base.png")
    ys = range(min(remache), max(remache) + 1)
    puntos = [(x, y) for y in ys for x in filas.get(y, ())]
    cx = round(sum(x for x, _ in puntos) / len(puntos))
    cy = round((min(remache) + max(remache)) / 2)
    return cx, cy


def preparar_aguja(origen, radio_cara):
    imagen = quitar_magenta(Image.open(origen))
    cx, cy = remache_de_la_aguja(imagen)
    izquierda, arriba, derecha, abajo = imagen.getbbox()
    # Lienzo de lado impar con el píxel del remache justo en el centro.
    mitad = max(cx - izquierda, derecha - 1 - cx, cy - arriba, abajo - 1 - cy)
    cuadrado = imagen.crop((cx - mitad, cy - mitad, cx + mitad + 1, cy + mitad + 1))
    largo = max(8, round(radio_cara * LARGO_AGUJA_RELATIVO))
    lado = 2 * largo + 1
    return reducir(cuadrado, (lado, lado)), (cx, cy)


def pixeles_magenta_visibles(imagen):
    """Cuenta los píxeles visibles (alfa ≥ 16) que aún tienen tono magenta."""
    return sum(1 for r, g, b, a in datos(imagen.convert("RGBA"))
               if a >= 16 and tono_magenta(r, g, b) > MAGENTA_VISIBLE)


def preparar(origen=ORIGEN, destino=IMAGENES, informar=print):
    """Escribe los seis archivos finales; devuelve sus rutas."""
    origen, destino = Path(origen), Path(destino)
    faltan = [nombre for nombre in ("indicador_base.png", "aguja_base.png", *(i[0] for i in ILUSTRACIONES))
              if not (origen / nombre).is_file()]
    if faltan:
        raise FileNotFoundError("Faltan originales en " + str(origen) + ": " + ", ".join(faltan))
    escritos = []
    carpeta = destino / "Indicadores Puente"
    carpeta.mkdir(parents=True, exist_ok=True)
    medidor, radio = preparar_medidor(origen / "indicador_base.png")
    aguja, remache = preparar_aguja(origen / "aguja_base.png", radio)
    for nombre, imagen in (("Indicador_base.png", medidor), ("Aguja_base.png", aguja)):
        restantes = pixeles_magenta_visibles(imagen)
        if restantes:
            raise ValueError(f"{nombre}: quedan {restantes} píxeles magenta visibles")
        imagen.save(carpeta / nombre)
        escritos.append(carpeta / nombre)
    (carpeta / "Indicador_base.json").write_text(
        json.dumps({"lado": LADO_MEDIDOR, "radio_cara": radio}, indent=2) + "\n", encoding="utf-8")
    informar(f"Medidor {medidor.size}, radio de la cara {radio}px; aguja {aguja.size} (remache original en {remache})")
    for nombre, salida, tamano in ILUSTRACIONES:
        ruta = destino / salida
        ruta.parent.mkdir(parents=True, exist_ok=True)
        reducir(Image.open(origen / nombre), tamano).save(ruta)
        escritos.append(ruta)
        informar(f"{salida}: {tamano[0]}x{tamano[1]}")
    return escritos


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--origen", default=str(ORIGEN))
    parser.add_argument("--destino", default=str(IMAGENES))
    argumentos = parser.parse_args()
    preparar(argumentos.origen, argumentos.destino)


if __name__ == "__main__":
    main()
