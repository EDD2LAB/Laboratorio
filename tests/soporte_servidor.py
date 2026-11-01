"""Servidor de prueba en un hilo, usando la aplicación real de producción."""
import asyncio
import threading

from aiohttp import web
from multijugador.tiempo_real import crear_app


class ServidorPrueba:
    def __init__(self):
        self.preparado = threading.Event()
        self.error = None
        self.hilo = threading.Thread(target=self._hilo, daemon=True)
        self.hilo.start()
        if not self.preparado.wait(5):
            raise RuntimeError("El servidor de prueba no inició.")
        if self.error:
            raise self.error

    def _hilo(self):
        try:
            asyncio.run(self._ejecutar())
        except Exception as error:
            self.error = error
            self.preparado.set()

    async def _ejecutar(self):
        self.loop = asyncio.get_running_loop()
        self.parar = asyncio.Event()
        runner = web.AppRunner(crear_app(), shutdown_timeout=1, access_log=None)
        await runner.setup()
        sitio = web.TCPSite(runner, "127.0.0.1", 0)
        await sitio.start()
        self.server_port = runner.addresses[0][1]
        self.preparado.set()
        await self.parar.wait()
        await runner.cleanup()

    def shutdown(self):
        self.loop.call_soon_threadsafe(self.parar.set)
        self.hilo.join(5)

    def server_close(self):
        pass
