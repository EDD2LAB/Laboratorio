"""Servidor autoritativo de la sala. El anfitrión también usa un cliente."""
import queue
import secrets
import socket
import threading
import time

from .protocolo import VERSION, PUERTO, ROLES, codificar, extraer


class ServidorSala:
    def __init__(self, puerto=PUERTO):
        self.puerto = puerto
        self._clave_host = secrets.token_urlsafe(24)
        self._lock = threading.RLock()
        self._sesiones = {}
        self._revision = 0
        self._iniciada = False
        self._cerrado = threading.Event()
        self._socket = None

    def iniciar(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self._socket.bind(("0.0.0.0", self.puerto))
            self._socket.listen(8)
            self._socket.settimeout(0.25)
            self.puerto = self._socket.getsockname()[1]
        except OSError:
            self._socket.close()
            raise
        threading.Thread(target=self._aceptar, daemon=True).start()

    @property
    def clave_host(self):
        return self._clave_host

    def _aceptar(self):
        while not self._cerrado.is_set():
            try:
                conexion, _ = self._socket.accept()
                conexion.settimeout(0.1)
                threading.Thread(target=self._atender, args=(conexion,), daemon=True).start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _estado(self):
        return {
            "tipo": "estado", "revision": self._revision,
            "iniciada": self._iniciada,
            "jugadores": [dict(s["jugador"]) for s in self._sesiones.values()],
        }

    def _publicar(self):
        self._revision += 1
        estado = self._estado()
        for sesion in self._sesiones.values():
            try:
                sesion["salida"].put_nowait(estado)
            except queue.Full:
                # Un cliente que no lee no puede bloquear al resto de la sala.
                sesion["cerrar"].set()

    def _registrar(self, mensaje, salida, cerrar):
        if mensaje.get("tipo") != "hola" or mensaje.get("version") != VERSION:
            raise ValueError("Versión incompatible. Todos deben usar la misma versión del juego.")
        nombre = mensaje.get("nombre")
        if not isinstance(nombre, str) or not nombre.strip() or len(nombre.strip()) > 20:
            raise ValueError("Escribe un nombre de entre 1 y 20 caracteres.")
        nombre = nombre.strip()
        if any(ord(c) < 32 for c in nombre):
            raise ValueError("Nombre inválido.")
        with self._lock:
            if self._iniciada:
                raise ValueError("La sala ya se inició.")
            if len(self._sesiones) >= 4:
                raise ValueError("La sala está llena (4 jugadores).")
            if any(s["jugador"]["nombre"].casefold() == nombre.casefold() for s in self._sesiones.values()):
                raise ValueError("Ese nombre ya está en la sala.")
            es_host = secrets.compare_digest(str(mensaje.get("clave_host", "")), self._clave_host)
            if es_host and any(s["jugador"]["anfitrion"] for s in self._sesiones.values()):
                raise ValueError("El anfitrión ya está conectado.")
            identificador = secrets.token_hex(8)
            self._sesiones[identificador] = {
                "jugador": {"id": identificador, "nombre": nombre, "rol": None,
                            "listo": False, "anfitrion": es_host},
                "salida": salida, "cerrar": cerrar,
            }
            salida.put_nowait({"tipo": "bienvenida", "id": identificador})
            self._publicar()
            return identificador

    def _accion(self, identificador, mensaje):
        with self._lock:
            sesion = self._sesiones[identificador]
            jugador = sesion["jugador"]
            tipo = mensaje.get("tipo")
            if tipo == "ping":
                sesion["salida"].put_nowait({"tipo": "pong"})
                return
            if self._iniciada:
                raise ValueError("El equipo ya está confirmado.")
            if tipo == "rol":
                rol = mensaje.get("rol")
                if rol is not None and rol not in ROLES:
                    raise ValueError("Rol inválido.")
                if rol is not None and any(s["jugador"]["rol"] == rol and clave != identificador
                       for clave, s in self._sesiones.items()):
                    raise ValueError("Otro jugador acaba de elegir ese rol.")
                jugador.update(rol=rol, listo=False)
            elif tipo == "listo":
                if not jugador["rol"]:
                    raise ValueError("Elige un rol antes de marcarte como listo.")
                if type(mensaje.get("listo")) is not bool:
                    raise ValueError("Estado de preparación inválido.")
                jugador["listo"] = mensaje["listo"]
            elif tipo == "iniciar":
                if not jugador["anfitrion"]:
                    raise ValueError("Solo el anfitrión puede iniciar.")
                if len(self._sesiones) < 2 or not all(s["jugador"]["listo"] for s in self._sesiones.values()):
                    raise ValueError("Se necesitan entre 2 y 4 jugadores con rol y listos.")
                self._iniciada = True
            else:
                raise ValueError("Acción desconocida.")
            self._publicar()

    def _atender(self, conexion):
        identificador = None
        salida = queue.Queue(maxsize=64)
        cerrar = threading.Event()
        buffer = b""
        ultimo = time.monotonic()
        limite_saludo = ultimo + 5
        try:
            while not self._cerrado.is_set() and not cerrar.is_set():
                while not salida.empty():
                    conexion.sendall(codificar(salida.get_nowait()))
                try:
                    datos = conexion.recv(4096)
                    if not datos:
                        break
                    ultimo = time.monotonic()
                    mensajes, buffer = extraer(buffer + datos)
                    for mensaje in mensajes:
                        if identificador is None:
                            identificador = self._registrar(mensaje, salida, cerrar)
                        else:
                            try:
                                self._accion(identificador, mensaje)
                            except ValueError as error:
                                salida.put_nowait({"tipo": "error", "mensaje": str(error)})
                except socket.timeout:
                    pass
                if (identificador is None and time.monotonic() > limite_saludo) or time.monotonic() - ultimo > 15:
                    break
        except ValueError as error:
            try:
                conexion.sendall(codificar({"tipo": "rechazado", "mensaje": str(error)}))
                conexion.shutdown(socket.SHUT_WR)
                # Consumir el ping que puede acompañar al saludo evita que
                # Windows cierre con RST y descarte el motivo de rechazo.
                for _ in range(2):
                    if not conexion.recv(4096):
                        break
            except OSError:
                pass
        except (OSError, queue.Full):
            pass
        finally:
            conexion.close()
            with self._lock:
                sesion = self._sesiones.pop(identificador, None)
                if sesion and sesion["jugador"]["anfitrion"]:
                    self.cerrar()
                elif sesion:
                    self._iniciada = False
                    self._publicar()

    def cerrar(self):
        self._cerrado.set()
        if self._socket:
            self._socket.close()
        with self._lock:
            for sesion in self._sesiones.values():
                sesion["cerrar"].set()
