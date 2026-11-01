"""Cliente HTTPS de la sala central; todas las peticiones salen de la PC."""
import json
import asyncio
import queue
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from .protocolo import VERSION


class CorteMovimiento(ConnectionError):
    def __init__(self, codigo_ws=None):
        super().__init__("Se interrumpió la conexión con el mapa compartido.")
        self.codigo_ws = codigo_ws


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
        self._secuencia = 0
        self._pendientes = {}
        self._lock_acciones = threading.Lock()
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

    def actuar(self, accion, **datos):
        solicitud = {"tipo": "accion", "accion": accion, "id_solicitud": uuid.uuid4().hex, **datos}
        with self._lock_acciones:
            if len(self._pendientes) >= 16:
                self._evento({"tipo": "error", "mensaje": "Espera a que el servidor confirme tus acciones."})
                return
            self._pendientes[solicitud["id_solicitud"]] = solicitud

    def _abrir_juego(self):
        intento = 0
        while not self._cerrado.is_set():
            inicio = time.monotonic()
            try:
                asyncio.run(self._jugar())
                return
            except ValueError:
                raise
            except Exception as error:
                if self._cerrado.is_set():
                    return
                nombre = type(error).__name__
                estado = getattr(error, "status", None)
                codigo = getattr(error, "winerror", None) or getattr(error, "errno", None)
                codigo_ws = getattr(error, "codigo_ws", None)
                # Diagnóstico sin tokens, cabeceras, nombres ni código de sala.
                print(f"[Red] WebSocket: {nombre}; HTTP={estado}; WS={codigo_ws}; codigo={codigo}", flush=True)
                if estado in (401, 403):
                    raise PermissionError("La sala se cerró o tu sesión caducó. Pide al anfitrión crear una sala nueva.") from error
                if estado == 404:
                    raise ValueError("Render todavía no tiene la conexión de movimiento. Despliega el último commit del servidor.") from error
                if "Certificate" in nombre:
                    raise ValueError("No se pudo validar el certificado del servidor. Comprueba la fecha y hora de esta PC.") from error
                if time.monotonic() - inicio >= 10:
                    intento = 0  # Los cortes separados por una sesión sana no agotan el contador.
                if intento == 3:
                    detalle = f"HTTP {estado}" if estado else f"WS {codigo_ws}" if codigo_ws else f"{nombre}" + (f", código {codigo}" if codigo else "")
                    raise ConnectionError(f"Se perdió la conexión tras 3 reintentos ({detalle}). Vuelve a entrar a la sala.") from error
                self._evento({"tipo": "reconectando", "mensaje": f"Conexión interrumpida. Reconectando ({intento + 1}/3)…"})
                self._cerrado.wait(min(2 ** intento, 4))
                intento += 1

    async def _jugar(self):
        try:
            import aiohttp
        except ImportError as error:
            raise ValueError("Instala las dependencias: python -m pip install -r multijugador/requirements.txt") from error
        url = self.url.replace("https://", "wss://", 1).replace("http://", "ws://", 1) + "/v1/juego"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None, connect=10), trust_env=True) as sesion:
            async with sesion.ws_connect(url, headers={"Authorization": "Bearer " + self._token},
                                         heartbeat=8, max_msg_size=65536, compress=0) as ws:
                async def controles():
                    enviadas = {}
                    while not self._cerrado.is_set():
                        dx, dy = self._movimiento
                        seq = self._secuencia
                        self._secuencia += 1
                        await ws.send_json({"tipo": "mover", "dx": dx, "dy": dy, "seq": seq})
                        with self._lock_acciones:
                            pendientes = list(self._pendientes.values())
                        enviadas = {clave: fecha for clave, fecha in enviadas.items() if any(p["id_solicitud"] == clave for p in pendientes)}
                        for solicitud in pendientes:
                            clave = solicitud["id_solicitud"]
                            if time.monotonic() - enviadas.get(clave, -10) >= 1:
                                await ws.send_json(solicitud)
                                enviadas[clave] = time.monotonic()
                        await asyncio.sleep(.05)
                    await ws.close()
                envio = asyncio.create_task(controles())
                try:
                    while not self._cerrado.is_set():
                        mensaje = await asyncio.wait_for(ws.receive(), timeout=12)
                        if mensaje.type == aiohttp.WSMsgType.TEXT:
                            estado = mensaje.json()
                            if isinstance(estado, dict):
                                if estado.get("tipo") == "acuse":
                                    with self._lock_acciones:
                                        self._pendientes.pop(estado.get("id_solicitud"), None)
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
                    raise CorteMovimiento(ws.close_code)

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
