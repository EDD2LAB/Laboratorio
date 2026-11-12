"""Mensajes JSON delimitados por nueva línea; sin dependencias externas."""
import json

VERSION = 19  # Pies y bordes del exterior del Futuro: cliente y servidor deben coincidir.
# 14: exploración e interiores del Futuro, Elia y Arel.
# 13: ping/pong de aplicación, métricas de red y recuperación.
# 12: resultado con campos legales (norma, pena, cita_corta, conducta, nota, con_delito). 11: estado por diferencias (mensaje "delta", control "pedir_snapshot") y acciones habilidad
# en el futuro y pedir_informe. Ver multijugador/delta.py
# 10: eventos manipulados, Ciudad Núcleo y edificios (presente_analizar, presente_marcar,
# presente_siguiente, futuro_resolver, entrar_edificio, salir_edificio)
# 9: separación autoritativa entre bots (Kael y Mira se eligen: ver apariencia)
# 8: expediente AVL compartido y sorteo privado por partida
# 6: pociones, clasificación, puente 1, portal y Distrito Conecta
PUERTO = 45871
ROLES = ("guardian", "mensajero", "habitante", "aspirante")
NOMBRES_ROLES = ("Guardián", "Mensajero", "Habitante", "Aspirante")
MAX_MENSAJE = 32768  # Estados completos, incluidos expediente resumido y batalla.


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
