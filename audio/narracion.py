"""Narración opcional de los mensajes con pyttsx3, en un hilo con cola.

pyttsx3 no es una dependencia obligatoria: sin él, la opción avisa y no hace nada.
"""
import importlib.util
import queue
import threading


def disponible():
    return importlib.util.find_spec("pyttsx3") is not None


class Narrador:
    MAX_PENDIENTES = 3

    def __init__(self):
        self.activo = False
        self.cola = queue.Queue(self.MAX_PENDIENTES)
        self._hilo = None
        self.fallo = False

    def decir(self, texto):
        if not self.activo or self.fallo or not texto or not disponible():
            return
        if self._hilo is None:
            self._hilo = threading.Thread(target=self._trabajar, daemon=True)
            self._hilo.start()
        try:
            self.cola.put_nowait(texto)
        except queue.Full:
            pass  # si va atrasado, se salta mensajes en vez de acumularlos

    def _trabajar(self):
        try:
            import pyttsx3
            motor = pyttsx3.init()
            while True:
                motor.say(self.cola.get())
                motor.runAndWait()
        except Exception as error:  # voz del sistema no disponible
            print("[Narración] Desactivada:", error)
            self.fallo = True
