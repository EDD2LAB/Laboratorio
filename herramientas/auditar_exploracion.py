"""Auditoría reproducible de rutas y dimensiones; no modifica Hitboxes ni arte."""
import argparse
import json
import math
from pathlib import Path
import struct
import sys

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from bots.navegador_bot import NavegadorBot
from logica.dimensiones import EDIFICIOS_FUTURO
from multijugador.dimensiones_red import spawn_interior, rect_salida
from multijugador.movimiento import PartidaMovimiento


def dimensiones_png(ruta):
    with ruta.open("rb") as archivo:
        cabecera = archivo.read(24)
    if cabecera[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("El recurso no es PNG: " + str(ruta))
    return list(struct.unpack(">II", cabecera[16:24]))


def auditar():
    partida = PartidaMovimiento([dict(id="auditoria", nombre="Auditoría", rol="guardian")], 0)
    recorridos = []
    for punto in partida.mision.exploracion.objetivos:
        mapa = (partida.interiores_futuro if punto["dimension"] == "futuro" else partida.interiores)[punto["interior"]]
        origen = spawn_interior(mapa.datos)
        salida = rect_salida(mapa.datos)
        destinos = (("mesa", (punto["x"], punto["y"]), 40),
                    ("salida", (salida[0] + salida[2] / 2, salida[1] + salida[3] / 2), 58))
        for nombre, destino, radio in destinos:
            ruta = NavegadorBot(mapa).buscar_ruta(origen, destino, radio=radio)
            anterior, libre = origen, bool(ruta) or math.dist(origen, destino) <= radio
            for posicion in ruta:
                libre = libre and mapa.trayecto_libre(anterior, posicion)
                anterior = posicion
            recorridos.append(dict(dimension=punto["dimension"], edificio=punto["interior"],
                                   destino=nombre, transitable=libre))
    interiores = []
    for clave, edificio in EDIFICIOS_FUTURO.items():
        datos = json.loads((RAIZ / "Hitboxes" / edificio["interior_hitboxes"]).read_text(encoding="utf-8"))
        tamano = dimensiones_png(RAIZ / "Imagenes" / edificio["interior"])
        interiores.append(dict(edificio=clave, imagen=tamano, plantilla=datos["image_size"],
                               mismo_tamano=tamano == datos["image_size"]))
    return dict(ok=all(r["transitable"] for r in recorridos) and all(i["mismo_tamano"] for i in interiores),
                recorridos=recorridos, interiores=interiores,
                mapa_exterior=dict(nuevo=dimensiones_png(RAIZ / "Imagenes/Fondos/Mapas/Futuro/MapaFuturo.png"),
                                   activo=dimensiones_png(RAIZ / "Imagenes/Futuro/generado/MapaFuturo.png"),
                                   sustitucion_habilitada=False,
                                   pendiente="Revisión manual de paredes, escaleras, puertas y portal sobre el mapa nuevo."),
                limite="Las rutas y tamaños no certifican todos los muebles. Las plantillas de paredes siguen siendo las editadas por el equipo.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path)
    args = parser.parse_args()
    informe = auditar()
    texto = json.dumps(informe, ensure_ascii=False, indent=2)
    if args.salida:
        args.salida.write_text(texto + "\n", encoding="utf-8")
    print(texto)
    raise SystemExit(0 if informe["ok"] else 1)
