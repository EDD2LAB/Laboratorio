"""Registro de errores: que un fallo nunca cierre el juego delante del público sin dejar rastro.

La carpeta se elige al primer uso (importar el módulo no toca disco):
- en el ``.exe``: ``logs/`` junto a ``TimelessGlitch.exe``;
- desde el código: ``logs/`` en la raíz del proyecto;
- si no se puede escribir ahí: ``%LOCALAPPDATA%\\TimelessGlitch\\logs`` y, en último caso, la
  carpeta temporal.
"""
from datetime import datetime
import faulthandler
import os
from pathlib import Path
import sys
import tempfile
import threading
import traceback

from nucleo.rutas import RAIZ

ARCHIVO_ERRORES = "errores.log"
ARCHIVO_SALIDA = "juego.log"
TAMANO_MAXIMO = 1_000_000  # bytes; al pasarlo, el archivo se renombra a .1 y se empieza otro
_carpeta = None
_bloqueo = threading.Lock()
_fallos_nativos = None  # archivo abierto para faulthandler (debe seguir abierto)


def _candidatas():
    if getattr(sys, "frozen", False):
        yield Path(sys.executable).resolve().parent / "logs"
    else:
        yield RAIZ / "logs"
    local = os.environ.get("LOCALAPPDATA")
    if local:
        yield Path(local) / "TimelessGlitch" / "logs"
    yield Path(tempfile.gettempdir()) / "TimelessGlitch" / "logs"


def carpeta():
    """Primera carpeta de registros en la que se puede escribir."""
    global _carpeta
    if _carpeta is None:
        for candidata in _candidatas():
            try:
                candidata.mkdir(parents=True, exist_ok=True)
                prueba = candidata / ".escritura"
                prueba.write_text("", encoding="utf-8")
                prueba.unlink()
            except OSError:
                continue
            _carpeta = candidata
            break
    return _carpeta


def _rotar(ruta):
    try:
        if ruta.stat().st_size > TAMANO_MAXIMO:
            os.replace(ruta, ruta.with_suffix(ruta.suffix + ".1"))
    except OSError:
        pass


def escribir(texto, archivo=ARCHIVO_ERRORES):
    """Añade ``texto`` con fecha al registro; nunca lanza excepciones."""
    destino = carpeta()
    if destino is None:
        return None
    ruta = destino / archivo
    try:
        with _bloqueo:
            _rotar(ruta)
            with ruta.open("a", encoding="utf-8") as salida:
                salida.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {texto.rstrip()}\n")
    except OSError:
        return None
    return ruta


def registrar_error(contexto, error=None):
    """Guarda el traceback de ``error`` (o de la excepción en curso) con su contexto."""
    if error is None:
        detalle = traceback.format_exc()
    else:
        detalle = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    return escribir(f"{contexto}\n{detalle}")


class _SalidaRegistro:
    """Sustituye a sys.stdout/sys.stderr cuando el .exe no tiene consola (son None)."""

    encoding = "utf-8"

    def write(self, texto):
        if texto and texto.strip():
            escribir(texto, ARCHIVO_SALIDA)
        return len(texto or "")

    def flush(self):
        pass

    def isatty(self):
        return False


def iniciar():
    """Redirige la salida sin consola y registra los errores no capturados."""
    global _fallos_nativos
    if sys.stdout is None:
        sys.stdout = _SalidaRegistro()
    if sys.stderr is None:
        sys.stderr = _SalidaRegistro()

    def excepcion_no_capturada(tipo, valor, rastro):
        escribir("Error no capturado\n" + "".join(traceback.format_exception(tipo, valor, rastro)))

    def excepcion_en_hilo(argumentos):
        if argumentos.exc_type is SystemExit:
            return
        nombre = getattr(argumentos.thread, "name", "?")
        escribir(f"Error en el hilo {nombre}\n" + "".join(
            traceback.format_exception(argumentos.exc_type, argumentos.exc_value, argumentos.exc_traceback)))

    sys.excepthook = excepcion_no_capturada
    threading.excepthook = excepcion_en_hilo
    destino = carpeta()
    if destino is not None and _fallos_nativos is None:
        try:  # cuelgues y fallos de C (SDL, drivers) quedan en este archivo
            _fallos_nativos = (destino / "fallos_nativos.log").open("a", encoding="utf-8")
            faulthandler.enable(_fallos_nativos)
        except (OSError, ValueError, RuntimeError):
            _fallos_nativos = None
