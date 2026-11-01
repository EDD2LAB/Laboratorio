"""Servicio de salas HTTP detrás del HTTPS del alojamiento; no requiere Pygame.

Ejecutar: python -m multijugador.servicio_internet
Una instancia/proceso mantiene todas las salas de esta primera versión.
"""
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import queue
import secrets
import threading
import time

from .servidor import ServidorSala
from .movimiento import PartidaMovimiento
from .protocolo import VERSION


class SalaInternet(ServidorSala):
    def __init__(self, reloj=time.monotonic):
        super().__init__()
        self.reloj = reloj
        self.partida = None

    def _accion(self, identificador, mensaje):
        super()._accion(identificador, mensaje)
        if mensaje.get("tipo") == "iniciar":
            try:
                self.partida = PartidaMovimiento(
                    [s["jugador"] for s in self._sesiones.values()], self.reloj())
            except (OSError, ValueError):
                self._iniciada = False
                self._publicar()
                raise ValueError("No se pudo preparar el mapa del servidor.")

    def _estado(self):
        estado = super()._estado()
        estado["protocolo"] = VERSION
        estado["fase"] = "partida" if self.partida and self._iniciada else "sala"
        if self.partida:
            estado["mundo"] = self.partida.estado()
        return estado

    def _publicar(self):
        # Los clientes consultan el estado; no acumular copias en colas TCP.
        self._revision += 1


class ServicioSalas:
    def __init__(self, reloj=time.monotonic):
        self.reloj = reloj
        self.lock = threading.RLock()
        self.salas = {}
        self.sesiones = {}
        self.peticiones = defaultdict(deque)

    def _eliminar_sala(self, codigo):
        sala = self.salas.pop(codigo, None)
        if sala:
            sala.cerrar()
        self.sesiones = {t: s for t, s in self.sesiones.items() if s["codigo"] != codigo}

    def limpiar(self):
        ahora = self.reloj()
        for token, sesion in list(self.sesiones.items()):
            if token not in self.sesiones or ahora - sesion["ultima"] <= 45:
                continue
            self._salir(token)
        for ip, cola in list(self.peticiones.items()):
            while cola and ahora - cola[0] >= 60:
                cola.popleft()
            if not cola:
                self.peticiones.pop(ip, None)

    def limitar(self, ip):
        ahora = self.reloj()
        cola = self.peticiones[ip]
        while cola and ahora - cola[0] >= 60:
            cola.popleft()
        # Admite cuatro clientes detrás de una misma IP.
        if len(cola) >= 1200:
            raise ValueError("Demasiadas solicitudes. Espera un minuto.")
        cola.append(ahora)

    def _sesion(self, token):
        sesion = self.sesiones.get(token)
        if not sesion:
            raise PermissionError("La sala se cerró o tu sesión caducó. Vuelve a entrar.")
        sesion["ultima"] = self.reloj()
        return sesion, self.salas[sesion["codigo"]]

    def _salir(self, token):
        sesion = self.sesiones.pop(token, None)
        if not sesion:
            return
        codigo = sesion["codigo"]
        sala = self.salas.get(codigo)
        if not sala:
            return
        jugador = sala._sesiones.pop(sesion["id"], None)
        if jugador and jugador["jugador"]["anfitrion"]:
            self._eliminar_sala(codigo)
        else:
            if sala.partida:
                sala.partida.quitar(sesion["id"])
            else:
                sala._iniciada = False
            sala._publicar()

    def ejecutar(self, metodo, ruta, datos, token="", ip="local"):
        with self.lock:
            self.limpiar()
            self.limitar(ip)
            if metodo == "GET" and ruta == "/health":
                return {"ok": True, "protocolo": VERSION, "movimiento": True}
            if metodo == "POST" and ruta in ("/v1/crear", "/v1/unirse"):
                crear = ruta == "/v1/crear"
                if crear:
                    if len(self.salas) >= 100:
                        raise ValueError("El servicio está lleno. Intenta más tarde.")
                    # No asignar una sala hasta validar el saludo.
                    sala = SalaInternet(self.reloj)
                    codigo = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
                    while codigo in self.salas:
                        codigo = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
                else:
                    codigo = datos.get("codigo", "")
                    if not isinstance(codigo, str):
                        raise ValueError("Código de sala inválido.")
                    codigo = codigo.strip().upper()
                    sala = self.salas.get(codigo)
                    if sala is None:
                        raise ValueError("No encontramos esa sala. Comprueba el código.")
                salida = queue.Queue(maxsize=4)
                identificador = sala._registrar({
                    "tipo": "hola", "version": datos.get("version"),
                    "nombre": datos.get("nombre"),
                    "clave_host": sala.clave_host if crear else "",
                }, salida, threading.Event())
                if crear:
                    self.salas[codigo] = sala
                token = secrets.token_urlsafe(32)
                self.sesiones[token] = {"id": identificador, "codigo": codigo, "ultima": self.reloj()}
                return {"id": identificador, "codigo": codigo, "token": token, "estado": sala._estado()}
            sesion, sala = self._sesion(token)
            if metodo == "GET" and ruta == "/v1/estado":
                return sala._estado()
            if metodo == "POST" and ruta == "/v1/accion":
                if datos.get("tipo") not in ("rol", "listo", "iniciar"):
                    raise ValueError("Acción no permitida.")
                sala._accion(sesion["id"], datos)
                return sala._estado()
            if metodo == "POST" and ruta == "/v1/salir":
                self._salir(token)
                return {"ok": True}
            raise ValueError("Ruta desconocida.")


class ServidorHTTP(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, direccion, servicio=None):
        self.servicio = servicio or ServicioSalas()
        super().__init__(direccion, Manejador)


class Manejador(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(8)

    def do_GET(self):
        self._responder()

    def do_POST(self):
        self._responder()

    def _responder(self):
        estado = 200
        try:
            largo = int(self.headers.get("Content-Length", "0"))
            if not 0 <= largo <= 4096 or self.headers.get("Transfer-Encoding"):
                raise ValueError("Solicitud demasiado grande o inválida.")
            cuerpo = self.rfile.read(largo) if largo else b"{}"
            datos = json.loads(cuerpo)
            if not isinstance(datos, dict):
                raise ValueError("Solicitud inválida.")
            token = self.headers.get("Authorization", "").removeprefix("Bearer ")
            respuesta = self.server.servicio.ejecutar(self.command, self.path, datos, token, self.client_address[0])
        except PermissionError as error:
            estado, respuesta = 401, {"error": str(error)}
        except (ValueError, UnicodeError) as error:
            estado, respuesta = 400, {"error": str(error)}
        except OSError:
            return
        datos = json.dumps(respuesta, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(estado)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(datos)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(datos)
        except OSError:
            pass

    def log_message(self, *_):
        # No registrar cuerpos, nombres, tokens ni códigos de sala.
        pass


def main():
    from aiohttp import web
    from .tiempo_real import crear_app
    web.run_app(crear_app(), host="0.0.0.0", port=int(os.environ.get("PORT", "10000")), access_log=None)


if __name__ == "__main__":
    main()
