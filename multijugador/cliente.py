"""E/S de red en segundo plano; Pygame consume una cola de eventos."""
import queue
import socket
import threading
import time

from .protocolo import VERSION, codificar, extraer
from .metricas_red import SondaPing


class ClienteSala:
    def __init__(self, ip, puerto, nombre, clave_host=""):
        self.eventos = queue.Queue(maxsize=128)
        self._salida = queue.Queue(maxsize=64)
        self._cerrado = threading.Event()
        self._socket = None
        self._argumentos = ip, puerto, nombre, clave_host
        self.metricas = {"mensajes": 0, "bytes": 0, "ping_ms": None}
        threading.Thread(target=self._ejecutar, daemon=True).start()

    def enviar(self, tipo, **datos):
        if not self._cerrado.is_set():
            try:
                self._salida.put_nowait({"tipo": tipo, **datos})
            except queue.Full:
                self._evento({"tipo": "error", "mensaje": "Espera a que se procesen las acciones anteriores."})

    def _evento(self, evento):
        try:
            self.eventos.put_nowait(evento)
        except queue.Full:
            self.cerrar()

    def _ejecutar(self):
        ip, puerto, nombre, clave = self._argumentos
        try:
            conexion = socket.create_connection((ip, puerto), timeout=4)
            self._socket = conexion
            conexion.settimeout(0.1)
            conexion.sendall(codificar({"tipo": "hola", "version": VERSION, "nombre": nombre, "clave_host": clave}))
            buffer = b""
            sonda = SondaPing(self.metricas)
            ultimo_dato = time.monotonic()
            while not self._cerrado.is_set():
                ping = sonda.siguiente()
                if ping is not None:
                    conexion.sendall(codificar(ping))
                while not self._salida.empty():
                    conexion.sendall(codificar(self._salida.get_nowait()))
                try:
                    datos = conexion.recv(4096)
                    if not datos:
                        raise ConnectionError("La sala se cerró o se perdió la conexión con el anfitrión.")
                    ultimo_dato = time.monotonic()
                    self.metricas["bytes"] += len(datos)
                    mensajes, buffer = extraer(buffer + datos)
                    for mensaje in mensajes:
                        self.metricas["mensajes"] += 1
                        if mensaje.get("tipo") == "pong":
                            sonda.recibir(mensaje)
                        if mensaje.get("tipo") != "pong":
                            self._evento(mensaje)
                        if mensaje.get("tipo") == "rechazado":
                            return
                except socket.timeout:
                    if time.monotonic() - ultimo_dato > 15:
                        raise ConnectionError("El anfitrión dejó de responder.")
        except (OSError, ValueError) as error:
            if not self._cerrado.is_set():
                self._evento({"tipo": "desconectado", "mensaje": str(error)})
        finally:
            if self._socket:
                self._socket.close()

    def cerrar(self):
        self._cerrado.set()
        if self._socket:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
