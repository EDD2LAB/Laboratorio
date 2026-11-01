"""Mensajes JSON delimitados por nueva línea; sin dependencias externas."""
import json

VERSION = 3
PUERTO = 45871
ROLES = ("guardian", "mensajero", "habitante", "aspirante")
NOMBRES_ROLES = ("Guardián", "Mensajero", "Habitante", "Aspirante")
MAX_MENSAJE = 16384


def codificar(mensaje):
    return (json.dumps(mensaje, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def extraer(buffer):
    mensajes = []
    while b"\n" in buffer:
        linea, buffer = buffer.split(b"\n", 1)
        if len(linea) > MAX_MENSAJE:
            raise ValueError("Mensaje demasiado largo.")
        valor = json.loads(linea.decode("utf-8"))
        if not isinstance(valor, dict):
            raise ValueError("Mensaje inválido.")
        mensajes.append(valor)
    if len(buffer) > MAX_MENSAJE:
        raise ValueError("Mensaje demasiado largo.")
    return mensajes, buffer
