"""Estado por diferencias: snapshot al entrar o cambiar de lugar y, luego, solo lo que cambia.

El WebSocket es fiable y ordenado, así que el último estado enviado es el que el
cliente tiene. Cada delta indica sobre qué versión (``base``) se aplica: si no
coincide, el cliente pide un snapshot nuevo. Solo se resume el movimiento (enteros
y claves cortas); los eventos y demás mensajes conservan su formato.
"""
import json

BORRAR = "~"  # claves que desaparecen de un diccionario
CLAVES_CORTAS = {"animacion": "a", "direccion": "d", "orientacion": "o", "seq": "s", "corriendo": "c", "viaje": "v"}
CLAVES_LARGAS = {corta: larga for larga, corta in CLAVES_CORTAS.items()}
# Lo que un cliente necesita saber de quien está en otro lugar.
CAMPOS_DE_OTRO_LUGAR = ("id", "nombre", "rol", "apariencia", "dimension", "interior", "conectado", "controlador")
# Lo que necesita saber de una era en la que no está.
RESUMEN_DE_ERA = ("fin", "completada", "evento", "titulo", "resultado", "opciones")
ERAS_CON_MISION = ("presente", "futuro")


def preparar(estado, identificador):
    """Forma normal de lo que le interesa a este cliente, y dónde está."""
    mundo = estado["mundo"]
    yo = next((j for j in mundo["jugadores"] if j["id"] == identificador), {})
    lugar = (yo.get("dimension", "la_copa"), yo.get("interior"))
    jugadores = {}
    for jugador in mundo["jugadores"]:
        if (jugador.get("dimension", "la_copa"), jugador.get("interior")) == lugar:
            jugadores[jugador["id"]] = dict(jugador, x=round(jugador["x"]), y=round(jugador["y"]))
        else:
            jugadores[jugador["id"]] = {c: jugador[c] for c in CAMPOS_DE_OTRO_LUGAR if c in jugador}
    caso = dict(mundo["caso"])
    for era in ERAS_CON_MISION:
        if era != lugar[0] and caso.get(era):
            caso[era] = {c: caso[era][c] for c in RESUMEN_DE_ERA if c in caso[era]}
    caso["npcs"] = [n for n in caso.get("npcs", []) if n["dimension"] == lugar[0]]
    # La copia JSON evita que un objeto compartido cambie después de compararlo.
    return json.loads(json.dumps({**estado, "mundo": {**mundo, "jugadores": jugadores, "caso": caso}})), lugar


def exponer(forma):
    """Del formato interno (jugadores por id) al de siempre (lista de jugadores)."""
    mundo = forma["mundo"]
    return {**forma, "mundo": {**mundo, "jugadores": list(mundo["jugadores"].values())}}


def diferencia(antes, despues):
    cambios = {}
    for clave, valor in despues.items():
        if clave not in antes:
            cambios[clave] = valor
        elif antes[clave] != valor:
            if isinstance(valor, dict) and isinstance(antes[clave], dict):
                cambios[clave] = diferencia(antes[clave], valor)
            else:
                cambios[clave] = valor
    borradas = [clave for clave in antes if clave not in despues]
    if borradas:
        cambios[BORRAR] = borradas
    return cambios


def aplicar(base, cambios):
    """Devuelve un estado nuevo: lo que no cambió se comparte y nunca se modifica."""
    nuevo = dict(base)
    for clave in cambios.get(BORRAR, ()):
        nuevo.pop(clave, None)
    for clave, valor in cambios.items():
        if clave == BORRAR:
            continue
        nuevo[clave] = aplicar(nuevo[clave], valor) if isinstance(valor, dict) and isinstance(nuevo.get(clave), dict) else valor
    return nuevo


def _renombrar_movimiento(cambios, claves):
    jugadores = cambios.get("mundo", {}).get("jugadores")
    if not jugadores:
        return cambios
    renombrados = {i: {claves.get(c, c): v for c, v in datos.items()} if isinstance(datos, dict) else datos
                   for i, datos in jugadores.items()}
    return {**cambios, "mundo": {**cambios["mundo"], "jugadores": renombrados}}


class CodificadorEstado:
    """Lado servidor: uno por conexión, así reconectar siempre empieza con un snapshot."""

    def __init__(self, identificador):
        self.identificador = identificador
        self.base = None
        self.lugar = None
        self.seq = 0
        self.forzar_snapshot = False

    def codificar(self, estado):
        if "mundo" not in estado:
            return estado
        actual, lugar = preparar(estado, self.identificador)
        self.seq += 1
        if self.base is None or self.forzar_snapshot or lugar != self.lugar:
            self.base, self.lugar, self.forzar_snapshot = actual, lugar, False
            return dict(exponer(actual), seq=self.seq)
        cambios = diferencia(self.base, actual)
        self.base = actual
        return {"tipo": "delta", "seq": self.seq, "base": self.seq - 1, "c": _renombrar_movimiento(cambios, CLAVES_CORTAS)}


class DecodificadorEstado:
    """Lado cliente: reconstruye el estado completo con el formato de siempre."""

    def __init__(self):
        self.base = None
        self.seq = None
        self._pedir = False

    def recibir(self, mensaje):
        """El estado completo, el mensaje tal cual si no es de estado, o None si falta base."""
        if mensaje.get("tipo") == "estado" and "seq" in mensaje:
            mundo = mensaje["mundo"]
            self.base = {**mensaje, "mundo": {**mundo, "jugadores": {j["id"]: j for j in mundo["jugadores"]}}}
            self.seq = mensaje["seq"]
            self._pedir = False
            return mensaje
        if mensaje.get("tipo") != "delta":
            return mensaje
        if self.base is None or mensaje["base"] != self.seq:
            self._pedir = self.base is not None or self.seq is None
            self.base = None
            return None
        self.base = aplicar(self.base, _renombrar_movimiento(mensaje["c"], CLAVES_LARGAS))
        self.seq = mensaje["seq"]
        return exponer(self.base)

    def tomar_peticion(self):
        """True una sola vez por pérdida: hay que pedir un snapshot."""
        pedir, self._pedir = self._pedir, False
        return pedir
