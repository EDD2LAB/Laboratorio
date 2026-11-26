"""Benchmark headless del juego (sin pantalla real).

Escenario ``sala`` (el original): levanta el servidor de producción en local
(multijugador.servidor_local), conecta clientes por WebSocket y dibuja la vista
del cliente 0 con Pygame en modo dummy. Mide FPS, cuadro p50/p95/p99, tick del
servidor (p50/p95/máx) y mensajes/bytes por cliente.

Escenarios ``campana_*`` y ``final``: ejecutan el bucle REAL del menú
(``MenuInicio.ejecutar``) con la campaña local con bots, igual que la Demo
rápida, con entrada simulada (la persona camina al azar). Miden el cuadro tal
como lo vive el visitante (todo lo que pasa entre dos ``Clock.tick``), el paso
del servidor local con sus bots, los tirones de más de 50 ms, las pausas del
recolector de basura, el tiempo de carga y la memoria del proceso.

Uso:
    python herramientas/benchmark.py --segundos 60 --salida docs/benchmark.json
    python herramientas/benchmark.py --segundos 30 --perfil   # cProfile del cliente
    python herramientas/benchmark.py --participantes clientes  # sin bots (clientes al azar)
    python herramientas/benchmark.py --escenario campana_copa --segundos 60
    python herramientas/benchmark.py --escenario final --segundos 90 --tamano 1920x1080
    python herramientas/benchmark.py --escenario todos --segundos 60 --salida docs/revision_feria/benchmark.json
"""
import argparse
import cProfile
import gc
import io
import json
import os
from pathlib import Path
import pstats
import queue
import random
import statistics
import subprocess
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
    """Crea la sala con el cliente 0; el resto son clientes o bots.

    ``mixto``: dos personas por WebSocket y el servidor rellena los otros dos
    roles con sus bots (como una sala real con roles libres)."""
    humano = ClienteInternet(url, "Bench0", crear=True)
    codigo = esperar(humano, lambda e: e["tipo"] == "bienvenida")["codigo"]
    otros = []
    if participantes == "bots":
        from multijugador.bots import iniciar_bots
        otros = iniciar_bots(url, codigo, ROLES[1:], configuracion={"modo_rapido": False, "semilla": 7})
    else:
        for i in range(1, 2 if participantes == "mixto" else 4):
            cliente = ClienteInternet(url, "Bench" + str(i), codigo=codigo)
            esperar(cliente, lambda e: e["tipo"] == "bienvenida")
            otros.append(cliente)
    humano.enviar("rol", rol=ROLES[0])
    humano.enviar("listo", listo=True)
    if participantes != "bots":
        for cliente, rol in zip(otros, ROLES[1:]):
            cliente.enviar("rol", rol=rol)
            cliente.enviar("listo", listo=True)
    personas = 2 if participantes == "mixto" else 4
    esperar(humano, lambda e: e["tipo"] == "estado" and len(e["jugadores"]) == personas
            and all(j["listo"] for j in e["jugadores"]), 30)
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


def memoria_mb():
    """Memoria del proceso en MB: conjunto de trabajo y bytes privados (solo Windows)."""
    try:
        import ctypes
        from ctypes import wintypes

        class Contadores(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        contadores = Contadores()
        contadores.cb = ctypes.sizeof(Contadores)
        proceso = ctypes.windll.kernel32.GetCurrentProcess
        proceso.restype = wintypes.HANDLE
        leer = ctypes.windll.psapi.GetProcessMemoryInfo
        leer.argtypes = (wintypes.HANDLE, ctypes.POINTER(Contadores), wintypes.DWORD)
        if not leer(proceso(), ctypes.byref(contadores), contadores.cb):
            return None
        return {"trabajo": round(contadores.WorkingSetSize / 2 ** 20, 1),
                "privada": round(contadores.PagefileUsage / 2 ** 20, 1)}
    except (AttributeError, OSError):
        return None


def resumen_cuadros(cuadros):
    """p50/p95/p99/máx en ms y tirones (> 50 ms) de una lista de segundos."""
    if not cuadros:
        return {}
    return {"p50": round(percentil(cuadros, 50) * 1000, 2), "p95": round(percentil(cuadros, 95) * 1000, 2),
            "p99": round(percentil(cuadros, 99) * 1000, 2), "max": round(max(cuadros) * 1000, 2),
            "medio": round(statistics.fmean(cuadros) * 1000, 2), "cuadros": len(cuadros),
            "tirones_50ms": sum(1 for c in cuadros if c > .05)}


class RelojMedido:
    """``pygame.time.Clock`` que anota el trabajo de cada cuadro (de un tick al siguiente)."""

    def __init__(self, registro, original):
        self._reloj = original()
        self._registro = registro
        self._fin = None

    def tick(self, fps=0):
        ahora = time.perf_counter()
        if self._fin is not None:
            self._registro.append(ahora - self._fin)
        resultado = self._reloj.tick(fps)
        self._fin = time.perf_counter()
        return resultado

    def __getattr__(self, nombre):
        return getattr(self._reloj, nombre)


class EntradaSimulada:
    """La persona camina al azar; al acabar el tiempo cierra la ventana (QUIT)."""

    def __init__(self, segundos, semilla, etiquetar=None, al_cuadro=None):
        self.fin = time.perf_counter() + segundos
        self.azar = random.Random(semilla)
        self.teclas = set()
        self.cambio = 0.0
        self.etiquetar = etiquetar
        self.al_cuadro = al_cuadro
        self.etiquetas = []

    def eventos(self, *_args, **_kwargs):
        ahora = time.perf_counter()
        if self.etiquetar:
            self.etiquetas.append(self.etiquetar())
        if self.al_cuadro:
            self.al_cuadro(ahora)
        if ahora >= self.fin:
            return [pygame.event.Event(pygame.QUIT)]
        if ahora >= self.cambio:
            dx, dy = self.azar.choice((-1, 0, 1)), self.azar.choice((-1, 0, 1))
            self.teclas = ({pygame.K_RIGHT} if dx > 0 else {pygame.K_LEFT} if dx < 0 else set()) | (
                {pygame.K_DOWN} if dy > 0 else {pygame.K_UP} if dy < 0 else set())
            self.cambio = ahora + self.azar.uniform(.4, 1.5)
        return []

    def tecla_activa(self, _teclas, *codigos):
        return any(codigo in self.teclas for codigo in codigos)


def fase_final(menu):
    """Etiqueta del cuadro: fase del final cooperativo (o la era si aún no empezó)."""
    partida = menu.partida
    if partida is None:
        return "menu"
    final = partida.contexto().get("desafio_final") or {}
    fase = final.get("fase")
    if not fase or fase == "bloqueado":
        return partida.dimension
    turno = final.get("batalla", {}).get("turno")
    return "batalla" if fase == "activo" else fase if not turno else fase


def ejecutar_campana(segundos, era, saltar_final=False, tamano=(960, 720), semilla=7):
    """Bucle real del menú con la campaña local con bots (como la Demo rápida)."""
    pausas_gc = []
    inicio_gc = [0.0]

    def medir_gc(fase, _info):
        if fase == "start":
            inicio_gc[0] = time.perf_counter()
        else:
            pausas_gc.append(time.perf_counter() - inicio_gc[0])

    t0 = time.perf_counter()
    import interfaz.inicio as inicio
    import interfaz.partida_multijugador as vista_partida
    from multijugador.partida_local import ClienteCampanaLocal
    t_import = time.perf_counter() - t0
    pygame.init()
    t1 = time.perf_counter()
    menu = inicio.MenuInicio()
    t_menu = time.perf_counter() - t1
    menu.pantalla = pygame.display.set_mode(tamano)
    memoria_menu = memoria_mb()
    pasos = []
    actualizar_original = ClienteCampanaLocal.actualizar

    def actualizar_medido(cliente, segundos_paso):
        antes = time.perf_counter()
        actualizar_original(cliente, segundos_paso)
        pasos.append(time.perf_counter() - antes)

    ClienteCampanaLocal.actualizar = actualizar_medido
    t2 = time.perf_counter()
    menu.iniciar_campana("Visitante", "guardian", "normal", era, "principal")
    t_campana = time.perf_counter() - t2
    if menu.partida is None:
        raise RuntimeError("No se pudo iniciar la campaña: " + menu.mensaje)
    menu.intro = None  # la intro espera a la persona; el benchmark mide la partida
    if saltar_final:
        menu.cliente.actuar("saltar_al_final")
    memoria_inicio = memoria_mb()
    cuadros = []
    entrada = EntradaSimulada(segundos, semilla, etiquetar=lambda: fase_final(menu))
    reloj_original, eventos_original = pygame.time.Clock, pygame.event.get
    tecla_original, foco_original = vista_partida.tecla_activa, pygame.key.get_focused
    pygame.time.Clock = lambda: RelojMedido(cuadros, reloj_original)
    pygame.event.get = entrada.eventos
    vista_partida.tecla_activa = entrada.tecla_activa
    pygame.key.get_focused = lambda: True
    gc.callbacks.append(medir_gc)
    inicio_bucle = time.perf_counter()
    try:
        menu.ejecutar()
    finally:
        gc.callbacks.remove(medir_gc)
        pygame.time.Clock, pygame.event.get = reloj_original, eventos_original
        vista_partida.tecla_activa, pygame.key.get_focused = tecla_original, foco_original
        ClienteCampanaLocal.actualizar = actualizar_original
    duracion = time.perf_counter() - inicio_bucle
    memoria_fin = memoria_mb()
    # Cuadro k: etiqueta tomada durante ese cuadro; su duración se anota en el tick siguiente.
    por_fase = {}
    for etiqueta, cuadro in zip(entrada.etiquetas, cuadros):
        por_fase.setdefault(etiqueta, []).append(cuadro)
    resultado = {
        "escenario": "final" if saltar_final else "campana_" + era,
        "tamano_pantalla": list(tamano),
        "segundos": round(duracion, 1),
        "fps_medio": round(len(cuadros) / duracion, 1),
        "cuadro_ms": resumen_cuadros(cuadros),
        "cuadro_por_fase_ms": {fase: resumen_cuadros(valores) for fase, valores in por_fase.items()},
        "paso_servidor_local_ms": resumen_cuadros(pasos),
        "gc_pausas_ms": {"cantidad": len(pausas_gc), "max": round(max(pausas_gc, default=0) * 1000, 2),
                         "mas_de_5ms": sum(1 for p in pausas_gc if p > .005)},
        "carga_s": {"imports": round(t_import, 2), "menu": round(t_menu, 2), "campana": round(t_campana, 2)},
        "memoria_mb": {"menu": memoria_menu, "inicio_partida": memoria_inicio, "fin": memoria_fin},
    }
    pygame.quit()
    return resultado


ESCENARIOS = ("sala", "sala_mixta", "campana_la_copa", "campana_presente", "campana_futuro", "final")


def ejecutar_escenario(escenario, segundos, tamano, perfil=False):
    if escenario == "sala":
        return ejecutar(segundos, "clientes", perfil)
    if escenario == "sala_mixta":
        return ejecutar(segundos, "mixto", perfil)
    if escenario == "final":
        return ejecutar_campana(segundos, "futuro", saltar_final=True, tamano=tamano)
    return ejecutar_campana(segundos, escenario.removeprefix("campana_"), tamano=tamano)


def todos(segundos, tamanos):
    """Cada escenario en su propio proceso: memoria y cachés sin arrastre."""
    resultados = []
    for escenario in ESCENARIOS:
        for tamano in (tamanos if escenario.startswith(("campana", "final")) else tamanos[:1]):
            orden = [sys.executable, str(Path(__file__).resolve()), "--escenario", escenario,
                     "--segundos", str(segundos * (1.5 if escenario == "final" else 1)),
                     "--tamano", "x".join(map(str, tamano)), "--json"]
            print("·", escenario, tamano, flush=True)
            salida = subprocess.run(orden, capture_output=True, text=True, encoding="utf-8", cwd=str(RAIZ))
            if salida.returncode != 0:
                resultados.append({"escenario": escenario, "error": salida.stderr[-2000:]})
                continue
            resultados.append(json.loads(salida.stdout.strip().splitlines()[-1]))
    return {"fecha": time.strftime("%Y-%m-%d %H:%M"), "python": sys.version.split()[0],
            "pygame": pygame.version.ver, "resultados": resultados}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--segundos", type=float, default=60)
    parser.add_argument("--participantes", choices=("bots", "clientes", "mixto"), default="bots")
    parser.add_argument("--escenario", choices=ESCENARIOS + ("todos",))
    parser.add_argument("--tamano", default="960x720", help="tamaño de la ventana simulada, p. ej. 1920x1080")
    parser.add_argument("--perfil", action="store_true")
    parser.add_argument("--json", action="store_true", help="una sola línea JSON en la salida (uso interno)")
    parser.add_argument("--salida")
    args = parser.parse_args()
    tamano = tuple(int(v) for v in args.tamano.lower().split("x"))
    if args.escenario == "todos":
        resultado = todos(args.segundos, [tamano, (1920, 1080)] if tamano != (1920, 1080) else [tamano])
        texto = json.dumps(resultado, ensure_ascii=False, indent=2)
        print(texto)
        if args.salida:
            Path(args.salida).write_text(texto, encoding="utf-8")
        return
    if args.escenario:
        resultado = ejecutar_escenario(args.escenario, args.segundos, tamano, args.perfil)
        if args.json:
            print(json.dumps(resultado, ensure_ascii=False))
            return
    else:
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
