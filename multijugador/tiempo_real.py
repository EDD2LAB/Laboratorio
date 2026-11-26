"""HTTP y WebSocket en el mismo puerto HTTPS del alojamiento."""
import asyncio
import contextlib
import json
import math
from collections import deque

from aiohttp import WSMsgType, web

from .movimiento import ColisionesMapa
from .servicio_internet import ServicioSalas, DemasiadasSolicitudes
from .delta import CodificadorEstado

SERVICIO = web.AppKey("servicio", ServicioSalas)
CONEXIONES = web.AppKey("conexiones", dict)
BUZONES = web.AppKey("buzones", dict)
# Métricas para herramientas/benchmark.py (no afectan al juego).
METRICAS = web.AppKey("metricas", dict)


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
        try:
            datos = await request.json() if request.method == "POST" else {}
        except ValueError as error:
            raise ValueError("Solicitud inválida.") from error
        if not isinstance(datos, dict):
            raise ValueError("Solicitud inválida.")
        token = request.headers.get("Authorization", "").removeprefix("Bearer ")
        respuesta = request.app[SERVICIO].ejecutar(request.method, request.path, datos, token, request.remote or "local")
        return web.json_response(respuesta, headers={"Cache-Control": "no-store"})
    except PermissionError as error:
        return web.json_response({"error": str(error)}, status=401)
    except DemasiadasSolicitudes as error:
        return web.json_response({"error": str(error), "reintentar_en": error.espera}, status=429,
                                 headers={"Retry-After": str(error.espera)})
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
    getattr(sala, "cortes", {}).pop(sesion["id"], None)  # volvió dentro del margen
    codificador = CodificadorEstado(sesion["id"])  # nueva conexión: empieza con un snapshot
    async def escribir():
        metricas = request.app[METRICAS]
        def medir(datos):
            texto = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
            metricas["mensajes"] += 1
            metricas["bytes"] += len(texto)
            return texto
        try:
            while not ws.closed:
                estado = await cola.siguiente()
                await asyncio.wait_for(ws.send_json(codificador.codificar(estado), dumps=medir), timeout=3)
                if estado.get("tipo") == "desconectado":
                    break
        except (OSError, TimeoutError, RuntimeError):
            pass
        finally:
            await ws.close()
    escritor = asyncio.create_task(escribir())
    ultimo_rechazo = 0
    ultimo_ping = -math.inf
    ventana, cantidad = servicio.reloj(), 0
    try:
        async for mensaje in ws:
            if mensaje.type != WSMsgType.TEXT:
                break
            ahora = servicio.reloj()
            try:
                datos = json.loads(mensaje.data)
                if isinstance(datos, dict) and datos.get("tipo") == "ping":
                    marca = datos.get("t")
                    if type(marca) not in (int, float) or not math.isfinite(marca):
                        raise ValueError("Ping inválido.")
                    # Límite independiente: el ping no consume controles de movimiento.
                    if ahora - ultimo_ping < 1:
                        continue
                    servicio._sesion(token)
                    ultimo_ping = ahora
                    cola.confirmar({"tipo": "pong", "t": marca})
                    continue
            except PermissionError:
                break
            except ValueError:
                datos = None  # el control inválido consume el límite habitual
            if ahora - ventana >= 1:
                ventana, cantidad = ahora, 0
            cantidad += 1
            if cantidad > 60:
                await ws.close(code=1008, message=b"Demasiados controles")
                break
            try:
                if not isinstance(datos, dict) or datos.get("tipo") not in ("mover", "accion", "pedir_snapshot"):
                    raise ValueError("Control inválido.")
                if datos["tipo"] == "pedir_snapshot":
                    codificador.forzar_snapshot = True
                    continue
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
        if request.app[CONEXIONES].get(token) is ws:
            request.app[CONEXIONES].pop(token, None)
        if request.app[BUZONES].get(token) is cola:
            request.app[BUZONES].pop(token, None)
        escritor.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await escritor
        # Un corte de Wi-Fi no elimina inmediatamente al jugador ni su rol.
        # Salir explícitamente usa /v1/salir; la partida tiene 120 s de gracia.
        actual = servicio.sesiones.get(token)
        if actual and token not in request.app[CONEXIONES]:
            sala = servicio.salas.get(actual["codigo"])
            if sala and sala.partida:
                if hasattr(sala, "marcar_corte"):
                    sala.marcar_corte(actual["id"], servicio.reloj())  # se suelta tras unos segundos
                else:
                    sala.partida.controles.pop(actual["id"], None)
                    sala.partida.conectados.discard(actual["id"])
    return ws


SALA_AVERIADA = "La sala tuvo un problema y se cerró. Creen una sala nueva para seguir jugando."


def _cerrar_sala_averiada(servicio, codigo, averiadas):
    """Registra el error de una sala y la cierra solo a ella (las demás siguen)."""
    import traceback
    print("[Servidor] Sala", codigo, "cerrada por un error:\n" + traceback.format_exc(), flush=True)
    for token, sesion in list(servicio.sesiones.items()):
        if sesion.get("codigo") == codigo:
            averiadas[token] = SALA_AVERIADA
    try:
        with servicio.lock:
            servicio._eliminar_sala(codigo)
    except Exception:  # noqa: BLE001
        print("[Servidor] No se pudo cerrar la sala", codigo, flush=True)


async def simulacion(app):
    servicio = app[SERVICIO]
    async def paso():
        while True:
            inicio = asyncio.get_running_loop().time()
            servicio.limpiar()
            ahora = servicio.reloj()
            estados, averiadas = {}, {}
            for codigo, sala in list(servicio.salas.items()):
                if not sala.partida:
                    continue
                try:
                    if hasattr(sala, "revisar_cortes"):
                        sala.revisar_cortes(ahora)
                    sala.partida.actualizar(ahora)
                    sala.actualizar_bots(ahora)
                    sala._publicar()
                    # No esperar a la red dentro del reloj de simulación. Cada cliente
                    # tiene un escritor independiente y conserva solo el estado nuevo.
                    estados[codigo] = sala._estado()
                except Exception:  # noqa: BLE001 - una sala averiada no congela a las demás
                    _cerrar_sala_averiada(servicio, codigo, averiadas)
            for token, cola in list(app[BUZONES].items()):
                sesion = servicio.sesiones.get(token)
                estado = estados.get(sesion["codigo"]) if sesion else None
                if estado is None:
                    estado = {"tipo": "desconectado", "mensaje": averiadas.get(token, "El anfitrión cerró la sala.")}
                else:
                    try:
                        sala = servicio.salas[sesion["codigo"]]
                        estado = {**estado, "mundo": {**estado["mundo"], "privado": sala.partida.mision.privado(sesion["id"])}}
                    except Exception:  # noqa: BLE001
                        _cerrar_sala_averiada(servicio, sesion["codigo"], averiadas)
                        estado = {"tipo": "desconectado", "mensaje": averiadas.get(token, SALA_AVERIADA)}
                cola.publicar(estado)
            duracion = asyncio.get_running_loop().time() - inicio
            app[METRICAS]["ticks"].append(duracion)
            await asyncio.sleep(max(.001, .05 - duracion))
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
    from collections import deque
    app[METRICAS] = {"ticks": deque(maxlen=20000), "mensajes": 0, "bytes": 0}
    app.router.add_get("/v1/juego", websocket)
    app.router.add_get("/health", http)
    app.router.add_get("/v1/estado", http)
    for ruta in ("crear", "unirse", "accion", "salir"):
        app.router.add_post("/v1/" + ruta, http)
    # Feria de los Ecos QR: rutas aparte bajo /feria (no tocan salas ni protocolo).
    from feria.web import registrar as registrar_feria
    registrar_feria(app)
    app.cleanup_ctx.append(simulacion)
    return app
