"""Rutas HTTP de la feria y servidor local en un hilo.

``registrar(app)`` añade solo rutas nuevas bajo ``/feria``: sirve igual en el
servidor local de la pantalla grande y, si se decide, en el de Render. No
modifica ninguna ruta ni mensaje del juego.
"""
import asyncio
import json
import re
import socket
import threading
import time

from aiohttp import web

from feria.movil import PAGINA
from feria.sesion import SesionFeria, VotoInvalido

CODIGO = re.compile(r"^[A-Z0-9]{6}$")
DURACION_SESION = 6 * 3600   # una jornada de feria
MAX_SESIONES = 20
PUERTOS = (8080, 8081, 8090, 8765)


class RegistroFerias:
    """Sesiones activas por código; caducan solas para no acumular memoria."""

    def __init__(self):
        self.sesiones = {}
        self._candado = threading.Lock()

    def crear(self):
        with self._candado:
            self._limpiar()
            if len(self.sesiones) >= MAX_SESIONES:
                raise RuntimeError("Hay demasiadas sesiones de feria abiertas.")
            sesion = SesionFeria()
            while sesion.codigo_sesion in self.sesiones:
                sesion = SesionFeria()
            self.sesiones[sesion.codigo_sesion] = (sesion, time.monotonic())
            return sesion

    def obtener(self, codigo):
        with self._candado:
            self._limpiar()
            entrada = self.sesiones.get(codigo)
            return entrada[0] if entrada else None

    def cerrar(self, codigo):
        with self._candado:
            self.sesiones.pop(codigo, None)

    def _limpiar(self):
        ahora = time.monotonic()
        for codigo, (_, inicio) in list(self.sesiones.items()):
            if ahora - inicio > DURACION_SESION:
                del self.sesiones[codigo]


REGISTRO = web.AppKey("registro_ferias", RegistroFerias)


def _sesion(request):
    codigo = request.match_info["codigo"].upper()
    sesion = request.app[REGISTRO].obtener(codigo) if CODIGO.match(codigo) else None
    if sesion is None:
        raise web.HTTPNotFound(text="Esta sesión de feria ya terminó.", content_type="text/plain")
    return sesion


async def pagina(request):
    _sesion(request)
    return web.Response(text=PAGINA, content_type="text/html", charset="utf-8",
                        headers={"Cache-Control": "no-store"})


async def ronda(request):
    return web.json_response(_sesion(request).para_celular(), headers={"Cache-Control": "no-store"})


async def voto(request):
    sesion = _sesion(request)
    try:
        datos = await request.json()
        if not isinstance(datos, dict):
            raise ValueError
    except (ValueError, json.JSONDecodeError):
        return web.json_response({"mensaje": "Solicitud inválida."}, status=400)
    try:
        sesion.votar(datos.get("dispositivo"), datos.get("ronda"), datos.get("decision"), datos.get("categoria"))
    except VotoInvalido as error:
        return web.json_response({"mensaje": str(error)}, status=409)
    return web.json_response({"ok": True})


def registrar(app, registro=None):
    app[REGISTRO] = registro or RegistroFerias()
    app.router.add_get("/feria/{codigo}", pagina)
    app.router.add_get("/feria/{codigo}/", pagina)
    app.router.add_get("/feria/{codigo}/ronda", ronda)
    app.router.add_post("/feria/{codigo}/voto", voto)
    return app[REGISTRO]


def ip_local():
    """IPv4 de la red local (sin enviar nada: UDP no conecta de verdad)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as prueba:
            prueba.connect(("10.255.255.255", 1))
            ip = prueba.getsockname()[0]
            if not ip.startswith("127."):
                return ip
    except OSError:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if not ip.startswith("127."):
                return ip
    except OSError:
        pass
    return "127.0.0.1"


class ServidorFeriaLocal:
    """aiohttp en un hilo propio: la pantalla grande no se bloquea esperando a la red."""

    def __init__(self, puertos=PUERTOS, host="0.0.0.0"):
        self.registro = RegistroFerias()
        self.puertos, self.host = puertos, host
        self.puerto = None
        self._bucle = None
        self._runner = None
        self._listo = threading.Event()
        self._error = None
        self._hilo = threading.Thread(target=self._ejecutar, name="feria-web", daemon=True)

    def iniciar(self, espera=5):
        self._hilo.start()
        if not self._listo.wait(espera) or self._error:
            raise RuntimeError(self._error or "El servidor de la feria no respondió.")
        return self

    def _ejecutar(self):
        self._bucle = asyncio.new_event_loop()
        asyncio.set_event_loop(self._bucle)
        try:
            self._bucle.run_until_complete(self._arrancar())
        except Exception as error:  # puerto ocupado, permisos…
            self._error = str(error)
            self._listo.set()
            return
        self._listo.set()
        self._bucle.run_forever()

    async def _arrancar(self):
        app = web.Application(client_max_size=4096)
        registrar(app, self.registro)
        self._runner = web.AppRunner(app, access_log=None)
        await self._runner.setup()
        ultimo = None
        for puerto in self.puertos:
            try:
                await web.TCPSite(self._runner, self.host, puerto).start()
                self.puerto = puerto
                return
            except OSError as error:
                ultimo = error
        raise RuntimeError(f"No hay un puerto libre para la feria ({ultimo}).")

    def url(self, codigo, ip=None):
        return f"http://{ip or ip_local()}:{self.puerto}/feria/{codigo}"

    def detener(self):
        if self._bucle is None or not self._bucle.is_running():
            return
        futuro = asyncio.run_coroutine_threadsafe(self._runner.cleanup(), self._bucle)
        try:
            futuro.result(5)
        except Exception:
            pass
        self._bucle.call_soon_threadsafe(self._bucle.stop)
        self._hilo.join(5)
