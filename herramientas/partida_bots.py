"""Partidas completas solo con bots, sin pantalla: de La Copa al informe final.

Usa la misma lógica autoritativa que el servidor (PartidaMovimiento) y el mismo
gestor de bots que las salas en línea, a 20 pasos por segundo simulados.
Cada partida termina cuando el cierre del final llega al informe (los bots no
pulsan "continuar" ahí), o al agotar el tiempo simulado.

Uso:
    python herramientas/partida_bots.py --semillas 1 2 3 4 5
"""
import argparse
import json
from pathlib import Path
import sys
import time

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from bots.gestor_bots import GestorBots  # noqa: E402
from multijugador.movimiento import PartidaMovimiento  # noqa: E402
from multijugador.protocolo import ROLES  # noqa: E402

PASO = .05  # s simulados por paso (20 Hz, como el servidor)


def jugar(semilla, dificultad="normal", limite=1200):
    """Devuelve un resumen con los hitos y el tiempo simulado y real."""
    jugadores = [{"id": "bot_" + rol, "nombre": rol, "rol": rol} for rol in ROLES]
    inicio = time.perf_counter()
    partida = PartidaMovimiento(jugadores, 0, semilla=semilla)
    gestor = GestorBots(partida, set(), dificultad)
    hitos, ahora = {}, 0.0
    peor_paso = 0.0
    while ahora < limite:
        ahora += PASO
        antes = time.perf_counter()
        partida.actualizar(ahora)
        gestor.actualizar(ahora, PASO)
        peor_paso = max(peor_paso, time.perf_counter() - antes)
        mision = partida.mision
        if "la_copa" not in hitos and mision.fase == "final":
            hitos["la_copa"] = round(ahora, 1)
        if "distrito_conecta" not in hitos and mision.presente is not None and mision.presente.fin:
            hitos["distrito_conecta"] = round(ahora, 1)
        futuro = mision.futuro
        if futuro is not None:
            if "ciudad_nucleo" not in hitos and futuro.completada:
                hitos["ciudad_nucleo"] = round(ahora, 1)
            if "victoria" not in hitos and futuro.final.fase == "victoria":
                hitos["victoria"] = round(ahora, 1)
            if futuro.final.aventura.etapa == "informe":
                hitos["informe"] = round(ahora, 1)
                break
    expediente = partida.mision.expediente
    return {"semilla": semilla, "dificultad": dificultad, "completa": "informe" in hitos,
            "hitos_s_simulados": hitos, "segundos_reales": round(time.perf_counter() - inicio, 1),
            "peor_paso_ms": round(peor_paso * 1000, 1),
            "arbol_avl": len(expediente.arbol.casos), "pendientes_avl": len(expediente.pendientes)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--semillas", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    parser.add_argument("--dificultad", default="normal", choices=("facil", "normal", "dificil"))
    parser.add_argument("--limite", type=float, default=1200, help="segundos simulados máximos por partida")
    parser.add_argument("--salida")
    args = parser.parse_args()
    resultados = []
    for semilla in args.semillas:
        resultado = jugar(semilla, args.dificultad, args.limite)
        print(json.dumps(resultado, ensure_ascii=False), flush=True)
        resultados.append(resultado)
    if args.salida:
        Path(args.salida).write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(0 if all(r["completa"] for r in resultados) else 1)


if __name__ == "__main__":
    main()
