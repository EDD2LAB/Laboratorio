"""Servidor multijugador real (aiohttp + WebSocket) corriendo en un hilo local.

Lo usan "Jugar con bots", el benchmark y las pruebas: es la MISMA aplicación
que se despliega en Render (``tiempo_real.crear_app``), escuchando en
127.0.0.1. No existe un camino especial para bots ni para pruebas.
"""
import asyncio
import threading

from aiohttp import web

from .tiempo_real import crear_app


class ServidorLocal:
    def __init__(self, host="127.0.0.1", puerto=0):
        self.host = host
        self.puerto_pedido = puerto
        self.preparado = threading.Event()
        self.error = None
        self.app = None
        self.loop = None
        self.server_port = None
        self.hilo = threading.Thread(target=self._hilo, name="servidor-local", daemon=True)
        self.hilo.start()
        if not self.preparado.wait(10):
            raise RuntimeError("El servidor local no inició.")
        if self.error:
            raise self.error

    @property
    def url(self):
        return f"http://{self.host}:{self.server_port}"

    def _hilo(self):
        try:
            asyncio.run(self._ejecutar())
        except Exception as error:  # se informa al hilo que lo creó
            self.error = error
            self.preparado.set()

    async def _ejecutar(self):
        self.loop = asyncio.get_running_loop()
        self.parar = asyncio.Event()
        self.app = crear_app()
        runner = web.AppRunner(self.app, shutdown_timeout=1, access_log=None)
        await runner.setup()
        sitio = web.TCPSite(runner, self.host, self.puerto_pedido)
        await sitio.start()
        self.server_port = runner.addresses[0][1]
        self.preparado.set()
        await self.parar.wait()
        await runner.cleanup()

    def cerrar(self):
        if self.loop and not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.parar.set)
        self.hilo.join(5)

    # Compatibilidad con tests/soporte_servidor.py
    def shutdown(self):
        self.cerrar()

    def server_close(self):
        pass
