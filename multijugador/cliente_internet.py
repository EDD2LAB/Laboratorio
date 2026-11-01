"""Cliente HTTPS de la sala central; todas las peticiones salen de la PC."""
import json
import asyncio
import queue
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from .protocolo import VERSION


class SinRedirecciones(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validar_url(url):
    url = url.strip().rstrip("/")
    partes = urllib.parse.urlsplit(url)
    local = partes.hostname in ("localhost", "127.0.0.1", "::1")
    if (not partes.hostname or partes.username or partes.password or partes.query or partes.fragment
            or partes.path not in ("", "/")
            or (partes.scheme != "https" and not (local and partes.scheme == "http"))):
        raise ValueError("Usa la dirección HTTPS del servidor, sin rutas ni contraseñas.")
    # Validar también el formato/rango del puerto.
    _ = partes.port
    return url


class ClienteInternet:
    def __init__(self, url, nombre, crear=False, codigo=""):
        self.url = validar_url(url)
        self.eventos = queue.Queue(maxsize=128)
        self._salida = queue.Queue(maxsize=32)
        self._cerrado = threading.Event()
        self._token = ""
        self._datos = {"nombre": nombre, "version": VERSION, "codigo": codigo}
        self._crear = crear
        self._movimiento = (0, 0)
        self._ultimo_estado = 0
        self._http = urllib.request.build_opener(SinRedirecciones())
        threading.Thread(target=self._ejecutar, daemon=True).start()

    def _peticion(self, ruta, datos=None, timeout=8):
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = "Bearer " + self._token
        cuerpo = json.dumps(datos).encode("utf-8") if datos is not None else None
        solicitud = urllib.request.Request(self.url + ruta, data=cuerpo, headers=headers)
        try:
            with self._http.open(solicitud, timeout=timeout) as respuesta:
                cuerpo = respuesta.read(65537)
        except urllib.error.HTTPError as error:
            try:
                mensaje = json.loads(error.read(4096)).get("error", "El servidor rechazó la solicitud.")
            except (ValueError, AttributeError):
                mensaje = "El servidor no pudo atender la solicitud."
            if error.code == 401:
                raise PermissionError(mensaje) from error
            raise ValueError(mensaje) from error
        if len(cuerpo) > 65536:
            raise ValueError("Respuesta del servidor demasiado grande.")
        valor = json.loads(cuerpo)
        if not isinstance(valor, dict):
            raise ValueError("Respuesta del servidor inválida.")
        return valor

    def _evento(self, evento):
        try:
            self.eventos.put_nowait(evento)
        except queue.Full:
            self._cerrado.set()

    def enviar(self, tipo, **datos):
        if not self._cerrado.is_set():
            try:
                self._salida.put_nowait({"tipo": tipo, **datos})
            except queue.Full:
                self._evento({"tipo": "error", "mensaje": "Espera antes de enviar otra acción."})

    def mover(self, dx, dy):
        self._movimiento = (dx, dy)

    def _abrir_juego(self):
        try:
            asyncio.run(self._jugar())
        except ValueError:
            raise
        except Exception as error:
            raise ConnectionError("No se pudo mantener la conexión de movimiento. Comprueba la red y actualiza el servidor en Render.") from error

    async def _jugar(self):
        try:
            import aiohttp
        except ImportError as error:
            raise ValueError("Instala las dependencias: python -m pip install -r multijugador/requirements.txt") from error
        url = self.url.replace("https://", "wss://", 1).replace("http://", "ws://", 1) + "/v1/juego"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None, connect=10)) as sesion:
            async with sesion.ws_connect(url, headers={"Authorization": "Bearer " + self._token},
                                         heartbeat=8, max_msg_size=65536, compress=0) as ws:
                async def controles():
                    seq = 0
                    while not self._cerrado.is_set():
                        dx, dy = self._movimiento
                        await ws.send_json({"tipo": "mover", "dx": dx, "dy": dy, "seq": seq})
                        seq += 1
                        await asyncio.sleep(.05)
                    await ws.close()
                envio = asyncio.create_task(controles())
                try:
                    while not self._cerrado.is_set():
                        mensaje = await asyncio.wait_for(ws.receive(), timeout=12)
                        if mensaje.type == aiohttp.WSMsgType.TEXT:
                            estado = mensaje.json()
                            if isinstance(estado, dict):
                                self._evento(estado)
                                if estado.get("tipo") == "desconectado":
                                    return
                        else:
                            break
                finally:
                    envio.cancel()
                    try:
                        await envio
                    except asyncio.CancelledError:
                        pass
                if not self._cerrado.is_set():
                    raise ConnectionError("Se perdió la conexión con el mapa compartido.")

    def _ejecutar(self):
        try:
            respuesta = self._peticion("/v1/crear" if self._crear else "/v1/unirse", self._datos, timeout=60)
            self._token = respuesta["token"]
            self._evento({"tipo": "bienvenida", "id": respuesta["id"], "codigo": respuesta["codigo"]})
            self._evento(respuesta["estado"])
            revision = respuesta["estado"]["revision"]
            siguiente = 0
            while not self._cerrado.is_set():
                if respuesta.get("estado", {}).get("fase") == "partida":
                    self._abrir_juego()
                    return
                try:
                    accion = self._salida.get(timeout=0.1)
                except queue.Empty:
                    accion = None
                if accion:
                    try:
                        estado = self._peticion("/v1/accion", accion)
                        self._evento(estado)
                        revision = estado["revision"]
                        if estado.get("fase") == "partida":
                            self._abrir_juego()
                            return
                    except ValueError as error:
                        self._evento({"tipo": "error", "mensaje": str(error)})
                if time.monotonic() >= siguiente:
                    estado = self._peticion("/v1/estado")
                    if estado["revision"] != revision:
                        self._evento(estado)
                        revision = estado["revision"]
                    if estado.get("fase") == "partida":
                        self._abrir_juego()
                        return
                    siguiente = time.monotonic() + 0.6
        except ValueError as error:
            self._evento({"tipo": "rechazado", "mensaje": str(error)})
        except (OSError, KeyError) as error:
            mensaje = str(error) if isinstance(error, (PermissionError, ConnectionError)) else "No se pudo conectar con el servidor de Internet. Comprueba la dirección y tu conexión."
            if not self._cerrado.is_set():
                self._evento({"tipo": "desconectado", "mensaje": mensaje})
        finally:
            if self._token:
                try:
                    self._peticion("/v1/salir", {})
                except (OSError, ValueError):
                    pass

    def cerrar(self):
        self._cerrado.set()
