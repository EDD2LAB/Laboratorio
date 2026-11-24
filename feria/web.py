"""Rutas HTTP de la feria y servidor local en un hilo.

``registrar(app)`` añade solo rutas nuevas bajo ``/feria``: sirve igual en el
servidor local de la pantalla grande y, si se decide, en el de Render. No
modifica ninguna ruta ni mensaje del juego.
"""
import asyncio
import json
import secrets
import re
import socket
import threading
import time

from aiohttp import web

from feria.movil import PAGINA
from feria.sesion import SesionFeria, VotoInvalido

CODIGO = re.compile(r"^[A-Z0-9]{6}$")
DURACION_SESION = 6 * 3600   # una jornada de feria
MAX_SESIONES = 40
SIN_ANFITRION = 10 * 60      # una sesión creada por internet muere si su pantalla deja de preguntar
PUERTOS = (8080, 8081, 8090, 8765)


class RegistroFerias:
    """Sesiones activas por código; caducan solas para no acumular memoria.

    Cada entrada guarda ``[sesion, inicio, visto, remota]``. Las sesiones
    ``remota`` (creadas por internet desde una pantalla grande) además mueren si
    su pantalla lleva ``SIN_ANFITRION`` segundos sin preguntar por el estado."""

    def __init__(self):
        self.sesiones = {}
        self._candado = threading.Lock()

    def crear(self, remota=False):
        with self._candado:
            self._limpiar()
            if len(self.sesiones) >= MAX_SESIONES:
                raise RuntimeError("Hay demasiadas sesiones de feria abiertas.")
            sesion = SesionFeria()
            while sesion.codigo_sesion in self.sesiones:
                sesion = SesionFeria()
            ahora = time.monotonic()
            self.sesiones[sesion.codigo_sesion] = [sesion, ahora, ahora, remota]
            return sesion

    def obtener(self, codigo):
        with self._candado:
            self._limpiar()
            entrada = self.sesiones.get(codigo)
            return entrada[0] if entrada else None

    def anfitrion(self, codigo, token):
        """La sesión si ``token`` es el de su pantalla grande (y la marca como viva)."""
        with self._candado:
            self._limpiar()
            entrada = self.sesiones.get(codigo)
            if entrada is None or type(token) is not str or                     not secrets.compare_digest(token.encode(), entrada[0].token_anfitrion.encode()):
                return None
            entrada[2] = time.monotonic()
            return entrada[0]

    def cerrar(self, codigo):
        with self._candado:
            self.sesiones.pop(codigo, None)

    def _limpiar(self):
        ahora = time.monotonic()
        for codigo, (_, inicio, visto, remota) in list(self.sesiones.items()):
            if ahora - inicio > DURACION_SESION or (remota and ahora - visto > SIN_ANFITRION):
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


# --- Pantalla grande por internet ---------------------------------------------
# La pantalla crea su sesión y la controla con el token secreto que recibe al
# crearla; los celulares nunca lo ven (solo usan /ronda y /voto).
def _token(request):
    return request.headers.get("Authorization", "").removeprefix("Bearer ")


def _anfitrion(request):
    codigo = request.match_info["codigo"].upper()
    sesion = request.app[REGISTRO].anfitrion(codigo, _token(request)) if CODIGO.match(codigo) else None
    if sesion is None:
        raise web.HTTPForbidden(text="Sesión terminada o clave de anfitrión incorrecta.", content_type="text/plain")
    return sesion


async def nueva(request):
    try:
        sesion = request.app[REGISTRO].crear(remota=True)
    except RuntimeError as error:
        return web.json_response({"mensaje": str(error)}, status=503)
    return web.json_response({"codigo": sesion.codigo_sesion, "token": sesion.token_anfitrion,
                              "estado": sesion.para_pantalla()}, headers={"Cache-Control": "no-store"})


async def estado(request):
    return web.json_response(_anfitrion(request).para_pantalla(), headers={"Cache-Control": "no-store"})


async def control(request):
    sesion = _anfitrion(request)
    try:
        datos = await request.json()
        accion = datos.get("accion") if isinstance(datos, dict) else None
    except (ValueError, json.JSONDecodeError):
        accion = None
    if accion == "cerrar":
        sesion.cerrar_ronda()
    elif accion == "abrir":
        sesion.abrir_ronda()
    elif accion == "terminar":
        request.app[REGISTRO].cerrar(sesion.codigo_sesion)
        return web.json_response({"ok": True})
    else:
        return web.json_response({"mensaje": "Acción desconocida."}, status=400)
    return web.json_response(sesion.para_pantalla(), headers={"Cache-Control": "no-store"})


def registrar(app, registro=None):
    app[REGISTRO] = registro or RegistroFerias()
    app.router.add_post("/feria/nueva", nueva)
    app.router.add_get("/feria/{codigo}", pagina)
    app.router.add_get("/feria/{codigo}/", pagina)
    app.router.add_get("/feria/{codigo}/ronda", ronda)
    app.router.add_post("/feria/{codigo}/voto", voto)
    app.router.add_get("/feria/{codigo}/estado", estado)
    app.router.add_post("/feria/{codigo}/control", control)
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


def ips_locales():
    """IPv4 donde los celulares pueden encontrar este computador, la mejor primero.

    Primero la zona con cobertura móvil de Windows (192.168.137.x): si el
    computador comparte su propia Wi-Fi, los celulares se conectan a ella y no
    dependen de una red que aísle a los dispositivos. Luego la red con salida.
    Se descartan 127.x y 169.254.x (sin red real)."""
    candidatas = []
    try:
        candidatas += [info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)]
    except OSError:
        pass
    principal = ip_local()
    candidatas.append(principal)
    validas = list(dict.fromkeys(ip for ip in candidatas if not ip.startswith(("127.", "169.254."))))
    validas.sort(key=lambda ip: (not ip.startswith("192.168.137."), ip != principal))
    return validas or ["127.0.0.1"]


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
        self._bucle.close()

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
