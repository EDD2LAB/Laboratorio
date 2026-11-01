"""Prueba prolongada opcional. No forma parte de unittest discover."""
import argparse
import asyncio
import json
from pathlib import Path
import queue
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from soporte_servidor import ServidorPrueba
from multijugador.cliente_internet import ClienteInternet
from multijugador.movimiento import ColisionesMapa
from multijugador.tiempo_real import CONEXIONES


def ejecutar(segundos, salida):
    servidor = ServidorPrueba()
    clientes = []
    def esperar(c, predicado):
        fin = time.monotonic() + 8
        while time.monotonic() < fin:
            try:
                e = c.eventos.get(timeout=.1)
            except queue.Empty:
                continue
            if e["tipo"] in ("rechazado", "desconectado"):
                raise AssertionError(e.get("mensaje"))
            if predicado(e):
                return e
        raise AssertionError("La sesión no avanzó a tiempo.")
    try:
        url = "http://127.0.0.1:" + str(servidor.server_port)
        for i in range(4):
            c = ClienteInternet(url, "Prueba" + str(i), crear=i == 0, codigo=codigo if i else "")
            clientes.append(c)
            codigo = esperar(c, lambda e: e["tipo"] == "bienvenida")["codigo"]
        for c, rol in zip(clientes, ("guardian", "mensajero", "habitante", "aspirante")):
            c.enviar("rol", rol=rol)
            c.enviar("listo", listo=True)
        esperar(clientes[0], lambda e: e["tipo"] == "estado" and len(e["jugadores"]) == 4 and all(j["listo"] for j in e["jugadores"]))
        clientes[0].enviar("iniciar")
        for c in clientes:
            esperar(c, lambda e: e["tipo"] == "estado" and e.get("fase") == "partida")
        inicio = time.monotonic()
        estados = acuses = reconexiones = 0
        ultimo = [inicio] * 4
        cortes = [x for x in (120, 300, 480) if x < segundos - 10]
        siguiente_corte, siguiente_informe, siguiente_accion = 0, 30, 10
        colisiones = ColisionesMapa()
        while time.monotonic() - inicio < segundos:
            duracion = time.monotonic() - inicio
            if siguiente_corte < len(cortes) and duracion >= cortes[siguiente_corte]:
                c = clientes[(siguiente_corte + 1) % 4]
                async def cortar(token=c._token):
                    await servidor.app[CONEXIONES][token].close(code=1001)
                asyncio.run_coroutine_threadsafe(cortar(), servidor.loop).result(timeout=4)
                siguiente_corte += 1
            if duracion >= siguiente_accion:
                clientes[0].actuar("interactuar", objetivo="objetivo_inexistente")
                siguiente_accion += 30
            for i, c in enumerate(clientes):
                c.mover(1 if int(duracion // 10 + i) % 2 else -1, 0)
                while True:
                    try:
                        e = c.eventos.get_nowait()
                    except queue.Empty:
                        break
                    if e["tipo"] in ("desconectado", "rechazado", "error"):
                        raise AssertionError(e.get("mensaje"))
                    if e["tipo"] == "reconectando":
                        reconexiones += 1
                    elif e["tipo"] == "acuse":
                        acuses += 1
                    elif e["tipo"] == "estado":
                        ultimo[i] = time.monotonic()
                        estados += 1
                        assert len(e["mundo"]["jugadores"]) == 4
                        assert all(not colisiones.bloqueado(j["x"], j["y"]) for j in e["mundo"]["jugadores"])
                assert time.monotonic() - ultimo[i] < 15, "Un cliente dejó de recibir estados."
            if duracion >= siguiente_informe:
                print(f"Estabilidad: {int(duracion)} s; estados={estados}; recuperaciones={reconexiones}", flush=True)
                siguiente_informe += 30
            time.sleep(.02)
        resultado = {"ok": True, "segundos": round(time.monotonic() - inicio), "clientes": 4,
                     "estados": estados, "acuses": acuses, "cortes_simulados": len(cortes),
                     "reconexiones": reconexiones, "entorno": "servidor y clientes locales, WebSocket real"}
        Path(salida).write_text(json.dumps(resultado, indent=2), encoding="utf-8")
        print(json.dumps(resultado), flush=True)
    finally:
        for c in clientes:
            c.cerrar()
        time.sleep(.3)
        servidor.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--segundos", type=int, default=600)
    parser.add_argument("--salida", required=True)
    args = parser.parse_args()
    ejecutar(args.segundos, args.salida)
