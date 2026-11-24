"""Pantalla grande conectada a una sesión de feria en el servidor de internet.

Así los celulares votan con sus datos móviles, sin entrar a la Wi-Fi del lugar
(que suele aislar a los dispositivos entre sí). ``SesionRemota`` imita lo que la
pantalla usa de ``SesionFeria``; toda la red ocurre en un hilo propio para que
el dibujo nunca espere. Solo viajan textos cortos en JSON, nunca imágenes.
"""
import json
import os
import queue
import threading
import time
import urllib.error
import urllib.request

INTERVALO = 1.5          # segundos entre consultas del estado
SIN_RESPUESTA = 6        # a partir de aquí se avisa en pantalla


def servidor_remoto():
    """URL base del servidor de internet ("" = solo red local).

    ``COPA_FERIA_SERVIDOR`` manda (vacía la desactiva); si no, la misma del
    multijugador: ``COPA_SERVIDOR_INTERNET`` o ``multijugador/configuracion.json``."""
    if "COPA_FERIA_SERVIDOR" in os.environ:
        return os.environ["COPA_FERIA_SERVIDOR"].strip().rstrip("/")
    if os.environ.get("COPA_SERVIDOR_INTERNET"):
        return os.environ["COPA_SERVIDOR_INTERNET"].strip().rstrip("/")
    from nucleo.rutas import RAIZ
    try:
        with open(RAIZ / "multijugador" / "configuracion.json", encoding="utf-8") as archivo:
            return str(json.load(archivo).get("servidor_internet", "")).strip().rstrip("/")
    except (OSError, ValueError, AttributeError):
        return ""


def _pedir(url, datos=None, token=None, timeout=8):
    cabeceras = {"Content-Type": "application/json", "User-Agent": "TimelessGlitch-Feria"}
    if token:
        cabeceras["Authorization"] = "Bearer " + token
    cuerpo = None if datos is None else json.dumps(datos).encode()
    peticion = urllib.request.Request(url, cuerpo, cabeceras, method="GET" if datos is None else "POST")
    with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
        return json.load(respuesta)


class SesionRemota:
    def __init__(self, base, codigo, token, estado):
        self.base, self.codigo_sesion, self._token = base, codigo, token
        self._estado = estado
        self._candado = threading.Lock()
        self._ordenes = queue.Queue()
        self._pendientes = 0       # órdenes sin respuesta: mientras haya, no se pisa el estado
        self.ultimo_ok = time.monotonic()
        self.perdida = False
        self._vivo = True
        self._hilo = threading.Thread(target=self._trabajar, name="feria-remota", daemon=True)
        self._hilo.start()

    @classmethod
    def crear(cls, base, timeout=20):
        datos = _pedir(base + "/feria/nueva", {}, timeout=timeout)
        return cls(base, datos["codigo"], datos["token"], datos["estado"])

    @property
    def url(self):
        return f"{self.base}/feria/{self.codigo_sesion}"

    # --- Lo que usa la pantalla (igual que SesionFeria) -----------------------
    def para_pantalla(self):
        with self._candado:
            return dict(self._estado)

    @property
    def ronda_actual(self):
        with self._candado:
            return self._estado["ronda"]

    @property
    def abierta(self):
        with self._candado:
            return self._estado["abierta"]

    def abrir_ronda(self):
        self._ordenar("control", {"accion": "abrir"}, abierta=True)

    def cerrar_ronda(self):
        self._ordenar("control", {"accion": "cerrar"}, abierta=False)

    def votar(self, dispositivo, ronda, decision, categoria):
        self._ordenar("voto", {"dispositivo": dispositivo, "ronda": ronda, "decision": decision, "categoria": categoria})

    @property
    def problema(self):
        """Aviso para la pantalla grande ("" si todo va bien)."""
        if self.perdida:
            return "El servidor de internet se reinició: sal con Esc y vuelve a entrar a la feria."
        if time.monotonic() - self.ultimo_ok > SIN_RESPUESTA:
            return "Sin conexión con el servidor de internet: reintentando…"
        return ""

    def terminar(self, espera=4):
        """Borra la sesión del servidor (si responde) y detiene el hilo."""
        self._ordenar("control", {"accion": "terminar"})
        self._vivo = False
        self._hilo.join(espera)

    # --- Hilo de red ----------------------------------------------------------
    def _ordenar(self, ruta, datos, **optimista):
        with self._candado:
            self._pendientes += 1
            self._estado.update(optimista)   # la pantalla reacciona al instante
        self._ordenes.put((ruta, datos))

    def _trabajar(self):
        while True:
            try:
                orden = self._ordenes.get(timeout=INTERVALO)
            except queue.Empty:
                if not self._vivo:
                    return
                orden = None
            if orden is None:
                self._consultar()
                continue
            ruta, datos = orden
            try:
                respuesta = self._pedir_sesion(ruta, datos)
                if ruta == "control" and datos["accion"] != "terminar":
                    with self._candado:
                        self._estado = respuesta
            except urllib.error.HTTPError as error:
                self._fallo_http(error, ruta)
            except (OSError, ValueError):
                pass
            finally:
                with self._candado:
                    self._pendientes -= 1
            if datos.get("accion") == "terminar":
                return

    def _consultar(self):
        with self._candado:
            antes = self._pendientes
        try:
            estado = self._pedir_sesion("estado")
        except urllib.error.HTTPError as error:
            self._fallo_http(error, "estado")
            return
        except (OSError, ValueError):
            return
        with self._candado:
            if antes == 0 and self._pendientes == 0:
                self._estado = estado

    def _pedir_sesion(self, ruta, datos=None):
        respuesta = _pedir(f"{self.url}/{ruta}", datos, self._token)
        self.ultimo_ok = time.monotonic()
        return respuesta

    def _fallo_http(self, error, ruta):
        self.ultimo_ok = time.monotonic()   # el servidor sí respondió
        if error.code == 403 and ruta != "voto":
            self.perdida = True              # reinició y olvidó la sesión
