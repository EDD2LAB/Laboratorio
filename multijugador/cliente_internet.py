"""Cliente HTTPS de la sala central; todas las peticiones salen de la PC."""
import json
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

    def _ejecutar(self):
        try:
            respuesta = self._peticion("/v1/crear" if self._crear else "/v1/unirse", self._datos, timeout=60)
            self._token = respuesta["token"]
            self._evento({"tipo": "bienvenida", "id": respuesta["id"], "codigo": respuesta["codigo"]})
            self._evento(respuesta["estado"])
            revision = respuesta["estado"]["revision"]
            siguiente = 0
            while not self._cerrado.is_set():
                try:
                    accion = self._salida.get(timeout=0.1)
                except queue.Empty:
                    accion = None
                if accion:
                    try:
                        estado = self._peticion("/v1/accion", accion)
                        self._evento(estado)
                        revision = estado["revision"]
                    except ValueError as error:
                        self._evento({"tipo": "error", "mensaje": str(error)})
                if time.monotonic() >= siguiente:
                    estado = self._peticion("/v1/estado")
                    if estado["revision"] != revision:
                        self._evento(estado)
                        revision = estado["revision"]
                    siguiente = time.monotonic() + 0.6
        except ValueError as error:
            self._evento({"tipo": "rechazado", "mensaje": str(error)})
        except (OSError, KeyError) as error:
            mensaje = str(error) if isinstance(error, PermissionError) else "No se pudo conectar con el servidor de Internet. Comprueba la dirección y tu conexión."
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
