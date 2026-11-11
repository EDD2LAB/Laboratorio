"""Benchmark headless de una partida multijugador real con 4 participantes.

Levanta el servidor de producción en local (multijugador.servidor_local),
conecta 4 clientes por WebSocket y dibuja la vista del cliente 0 con Pygame
en modo dummy. Mide:
- FPS medio y tiempo de frame p50/p95/p99 (trabajo de actualizar+dibujar),
- tiempo de tick del servidor (p50/p95/máx),
- mensajes/s y bytes/s recibidos por cada cliente.

Uso:
    python herramientas/benchmark.py --segundos 60 --salida docs/benchmark.json
    python herramientas/benchmark.py --segundos 30 --perfil   # cProfile del cliente
    python herramientas/benchmark.py --participantes clientes  # sin bots (clientes al azar)
"""
import argparse
import cProfile
import io
import json
import os
from pathlib import Path
import pstats
import queue
import random
import statistics
import sys
import time

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from multijugador.cliente_internet import ClienteInternet  # noqa: E402
from multijugador.servidor_local import ServidorLocal  # noqa: E402
from multijugador.tiempo_real import METRICAS  # noqa: E402

ROLES = ("guardian", "mensajero", "habitante", "aspirante")


def percentil(valores, p):
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    return ordenados[min(len(ordenados) - 1, round(p / 100 * (len(ordenados) - 1)))]


def esperar(cliente, predicado, limite=15):
    fin = time.monotonic() + limite
    while time.monotonic() < fin:
        try:
            evento = cliente.eventos.get(timeout=.1)
        except queue.Empty:
            continue
        if evento.get("tipo") in ("rechazado", "desconectado"):
            raise RuntimeError(evento.get("mensaje"))
        if predicado(evento):
            return evento
    raise RuntimeError("La sala no avanzó a tiempo.")


def preparar_sala(url, participantes):
    """Crea la sala con el cliente 0; el resto son clientes o bots."""
    humano = ClienteInternet(url, "Bench0", crear=True)
    codigo = esperar(humano, lambda e: e["tipo"] == "bienvenida")["codigo"]
    otros = []
    if participantes == "bots":
        from multijugador.bots import iniciar_bots
        otros = iniciar_bots(url, codigo, ROLES[1:], configuracion={"modo_rapido": False, "semilla": 7})
    else:
        for i in range(1, 4):
            cliente = ClienteInternet(url, "Bench" + str(i), codigo=codigo)
            esperar(cliente, lambda e: e["tipo"] == "bienvenida")
            otros.append(cliente)
    humano.enviar("rol", rol=ROLES[0])
    humano.enviar("listo", listo=True)
    if participantes != "bots":
        for cliente, rol in zip(otros, ROLES[1:]):
            cliente.enviar("rol", rol=rol)
            cliente.enviar("listo", listo=True)
    esperar(humano, lambda e: e["tipo"] == "estado" and len(e["jugadores"]) == 4 and all(j["listo"] for j in e["jugadores"]), 30)
    humano.enviar("iniciar")
    estado = esperar(humano, lambda e: e["tipo"] == "estado" and e.get("fase") == "partida", 30)
    return humano, otros, estado


def ejecutar(segundos, participantes, perfil):
    pygame.init()
    pygame.display.set_mode((960, 720))
    servidor = ServidorLocal()
    humano, otros, estado = preparar_sala(servidor.url, participantes)
    from interfaz.partida_multijugador import VistaPartida
    identificador = next(j["id"] for j in estado["jugadores"] if j["nombre"] == "Bench0")
    vista = VistaPartida(identificador, estado)
    lienzo = pygame.Surface((960, 720))
    reloj = pygame.time.Clock()
    azar = random.Random(3)
    direccion, cambio = (0, 0), 0.0
    frames, cuadros = [], 0
    for cliente in [humano] + [getattr(o, "cliente", o) for o in otros]:
        cliente.metricas.update(mensajes=0, bytes=0)
    servidor.app[METRICAS]["ticks"].clear()
    perfilador = cProfile.Profile() if perfil else None
    inicio = time.perf_counter()
    if perfilador:
        perfilador.enable()
    while time.perf_counter() - inicio < segundos:
        segundos_frame = reloj.tick(60) / 1000
        trabajo = time.perf_counter()
        while True:
            try:
                evento = humano.eventos.get_nowait()
            except queue.Empty:
                break
            if evento.get("tipo") == "estado" and evento.get("fase") == "partida":
                vista.recibir(evento)
            elif evento.get("tipo") == "acuse":
                vista.panel.recibir(evento)
        cambio -= segundos_frame
        if cambio <= 0:  # el "humano" camina al azar para mover cámara y animaciones
            direccion = (azar.choice((-1, 0, 1)), azar.choice((-1, 0, 1)))
            cambio = azar.uniform(.4, 1.5)
        vista.panel.modo = None
        vista.actualizar(segundos_frame, humano)
        humano.mover(*direccion)
        if participantes != "bots":
            for cliente in otros:
                while True:  # un cliente real siempre consume sus eventos
                    try:
                        cliente.eventos.get_nowait()
                    except queue.Empty:
                        break
                if azar.random() < .02:
                    cliente.mover(azar.choice((-1, 0, 1)), azar.choice((-1, 0, 1)))
        vista.dibujar(lienzo, "BENCH", (-1, -1))
        pygame.display.get_surface().blit(lienzo, (0, 0))
        pygame.display.flip()
        frames.append(time.perf_counter() - trabajo)
        cuadros += 1
    if perfilador:
        perfilador.disable()
    duracion = time.perf_counter() - inicio
    ticks = list(servidor.app[METRICAS]["ticks"])
    clientes = [humano] + [getattr(o, "cliente", o) for o in otros]
    resultado = {
        "segundos": round(duracion, 1),
        "participantes": participantes,
        "fps_medio": round(cuadros / duracion, 1),
        "frame_ms": {"p50": round(percentil(frames, 50) * 1000, 2), "p95": round(percentil(frames, 95) * 1000, 2),
                     "p99": round(percentil(frames, 99) * 1000, 2), "medio": round(statistics.fmean(frames) * 1000, 2)},
        "tick_servidor_ms": {"p50": round(percentil(ticks, 50) * 1000, 2), "p95": round(percentil(ticks, 95) * 1000, 2),
                             "max": round(max(ticks, default=0) * 1000, 2), "ticks": len(ticks)},
        "por_cliente": [{"mensajes_s": round(c.metricas["mensajes"] / duracion, 1),
                         "bytes_s": round(c.metricas["bytes"] / duracion)} for c in clientes],
        "ping_ms": round(humano.metricas["ping_ms"], 1) if humano.metricas.get("ping_ms") is not None else None,
    }
    if perfilador:
        texto = io.StringIO()
        pstats.Stats(perfilador, stream=texto).sort_stats("cumulative").print_stats(25)
        resultado["perfil_cumulativo"] = texto.getvalue()
        texto = io.StringIO()
        pstats.Stats(perfilador, stream=texto).sort_stats("tottime").print_stats(15)
        resultado["perfil_propio"] = texto.getvalue()
    for cliente in [humano] + list(otros):
        cliente.cerrar()
    servidor.cerrar()
    pygame.quit()
    return resultado


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--segundos", type=float, default=60)
    parser.add_argument("--participantes", choices=("bots", "clientes"), default="bots")
    parser.add_argument("--perfil", action="store_true")
    parser.add_argument("--salida")
    args = parser.parse_args()
    participantes = args.participantes
    if participantes == "bots":
        try:
            import multijugador.bots  # noqa: F401
        except ImportError:
            participantes = "clientes"
    resultado = ejecutar(args.segundos, participantes, args.perfil)
    perfiles = {k: resultado.pop(k) for k in ("perfil_cumulativo", "perfil_propio") if k in resultado}
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    for texto in perfiles.values():
        print(texto)
    if args.salida:
        Path(args.salida).write_text(json.dumps(dict(resultado, **perfiles), ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
