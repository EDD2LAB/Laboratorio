"""HTTP y WebSocket en el mismo puerto HTTPS del alojamiento."""
import asyncio
import contextlib
import json
from collections import deque

from aiohttp import WSMsgType, web

from .movimiento import ColisionesMapa
from .servicio_internet import ServicioSalas

SERVICIO = web.AppKey("servicio", ServicioSalas)
CONEXIONES = web.AppKey("conexiones", dict)
BUZONES = web.AppKey("buzones", dict)


class Buzon:
    """Estados reemplazables y acuses fiables, sin bloquear la simulación."""
    def __init__(self):
        self.estado = None
        self.acuses = deque()
        self.nuevo = asyncio.Event()

    def publicar(self, estado):
        self.estado = estado
        self.nuevo.set()

    def confirmar(self, acuse):
        if len(self.acuses) >= 32:
            raise ValueError("Demasiadas acciones pendientes.")
        self.acuses.append(acuse)
        self.nuevo.set()

    async def siguiente(self):
        while True:
            if self.acuses:
                return self.acuses.popleft()
            if self.estado is not None:
                estado, self.estado = self.estado, None
                return estado
            self.nuevo.clear()
            await self.nuevo.wait()


async def http(request):
    try:
        datos = await request.json() if request.method == "POST" else {}
        if not isinstance(datos, dict):
            raise ValueError("Solicitud inválida.")
        token = request.headers.get("Authorization", "").removeprefix("Bearer ")
        respuesta = request.app[SERVICIO].ejecutar(request.method, request.path, datos, token, request.remote or "local")
        return web.json_response(respuesta, headers={"Cache-Control": "no-store"})
    except PermissionError as error:
        return web.json_response({"error": str(error)}, status=401)
    except (ValueError, UnicodeError) as error:
        return web.json_response({"error": str(error)}, status=400)


async def websocket(request):
    servicio = request.app[SERVICIO]
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    try:
        sesion, sala = servicio._sesion(token)
        if not sala.partida:
            raise ValueError("La partida todavía no ha comenzado.")
    except (PermissionError, ValueError) as error:
        return web.json_response({"error": str(error)}, status=401)
    if token in request.app[CONEXIONES]:
        return web.json_response({"error": "Tu sesión ya está conectada al mapa."}, status=409)
    ws = web.WebSocketResponse(heartbeat=8, timeout=2, max_msg_size=2048, compress=False)
    await ws.prepare(request)
    request.app[CONEXIONES][token] = ws
    cola = Buzon()
    request.app[BUZONES][token] = cola
    sala.partida.conectados.add(sesion["id"])
    async def escribir():
        try:
            while not ws.closed:
                estado = await cola.siguiente()
                await asyncio.wait_for(ws.send_json(estado), timeout=3)
                if estado.get("tipo") == "desconectado":
                    break
        except (OSError, TimeoutError, RuntimeError):
            pass
        finally:
            await ws.close()
    escritor = asyncio.create_task(escribir())
    ultimo_rechazo = 0
    ventana, cantidad = servicio.reloj(), 0
    try:
        async for mensaje in ws:
            if mensaje.type != WSMsgType.TEXT:
                break
            ahora = servicio.reloj()
            if ahora - ventana >= 1:
                ventana, cantidad = ahora, 0
            cantidad += 1
            if cantidad > 60:
                await ws.close(code=1008, message=b"Demasiados controles")
                break
            try:
                datos = json.loads(mensaje.data)
                if not isinstance(datos, dict) or datos.get("tipo") not in ("mover", "accion"):
                    raise ValueError("Control inválido.")
                actual, sala = servicio._sesion(token)
                if datos["tipo"] == "mover":
                    sala.partida.recibir(actual["id"], datos, ahora)
                else:
                    cola.confirmar(sala.partida.actuar(actual["id"], datos, ahora))
                    sala._publicar()
            except PermissionError:
                break
            except ValueError as error:
                if ahora - ultimo_rechazo > 1:
                    await ws.send_json({"tipo": "error", "mensaje": str(error)})
                    ultimo_rechazo = ahora
    finally:
        request.app[CONEXIONES].pop(token, None)
        request.app[BUZONES].pop(token, None)
        escritor.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await escritor
        # Un corte de Wi-Fi no elimina inmediatamente al jugador ni su rol.
        # Salir explícitamente usa /v1/salir; una ausencia caduca a los 45 s.
        actual = servicio.sesiones.get(token)
        if actual:
            sala = servicio.salas.get(actual["codigo"])
            if sala and sala.partida:
                sala.partida.controles.pop(actual["id"], None)
                sala.partida.conectados.discard(actual["id"])
    return ws


async def simulacion(app):
    servicio = app[SERVICIO]
    async def paso():
        while True:
            inicio = asyncio.get_running_loop().time()
            servicio.limpiar()
            ahora = servicio.reloj()
            for sala in list(servicio.salas.values()):
                if sala.partida:
                    sala.partida.actualizar(ahora)
                    sala._publicar()
            # No esperar a la red dentro del reloj de simulación. Cada cliente
            # tiene un escritor independiente y conserva solo el estado nuevo.
            estados = {codigo: sala._estado() for codigo, sala in servicio.salas.items() if sala.partida}
            for token, cola in list(app[BUZONES].items()):
                sesion = servicio.sesiones.get(token)
                estado = estados.get(sesion["codigo"]) if sesion else None
                if estado is None:
                    estado = {"tipo": "desconectado", "mensaje": "El anfitrión cerró la sala."}
                else:
                    sala = servicio.salas[sesion["codigo"]]
                    estado = {**estado, "mundo": {**estado["mundo"], "privado": sala.partida.mision.privado(sesion["id"])}}
                cola.publicar(estado)
            await asyncio.sleep(max(.001, .05 - (asyncio.get_running_loop().time() - inicio)))
    tarea = asyncio.create_task(paso())
    yield
    tarea.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await tarea
    for ws in list(app[CONEXIONES].values()):
        await ws.close(code=1001, message=b"Servidor reiniciado")


def crear_app(servicio=None):
    ColisionesMapa()
    app = web.Application(client_max_size=4096)
    app[SERVICIO] = servicio or ServicioSalas()
    app[CONEXIONES] = {}
    app[BUZONES] = {}
    app.router.add_get("/v1/juego", websocket)
    app.router.add_get("/health", http)
    app.router.add_get("/v1/estado", http)
    for ruta in ("crear", "unirse", "accion", "salir"):
        app.router.add_post("/v1/" + ruta, http)
    app.cleanup_ctx.append(simulacion)
    return app
