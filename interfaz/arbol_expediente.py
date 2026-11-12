"""Distribución y animación visual del AVL; nunca decide una inserción."""

AREA = (60, 155, 390, 245)
RADIO = 18


def forma_publica(nodo):
    if not nodo:
        return None
    return dict(id=nodo["caso"]["id"], i=forma_publica(nodo["izquierda"]), d=forma_publica(nodo["derecha"]))


def posiciones(forma):
    orden = []
    def recorrer(nodo, nivel=0):
        if nodo:
            recorrer(nodo["i"], nivel + 1)
            orden.append((nodo["id"], nivel))
            recorrer(nodo["d"], nivel + 1)
    recorrer(forma)
    x, y, ancho, alto = AREA
    niveles = max((n for _, n in orden), default=0)
    paso_y = min(76, (alto - 48) / max(1, niveles))
    return {clave: (x + (i + .5) * ancho / max(1, len(orden)), y + 20 + nivel * paso_y)
            for i, (clave, nivel) in enumerate(orden)}


class AnimacionAVL:
    DURACION = 850

    def __init__(self):
        self.revision = None
        self.inicio = None
        self.datos = None

    def actualizar(self, estado, ahora, repetir=False):
        actual = forma_publica(estado.get("raiz"))
        datos = estado.get("animacion")
        revision = estado.get("revision", 0)
        cambio = self.revision is not None and revision != self.revision
        self.revision = revision
        # Al abrir el libro se muestra el árbol actual. Repetir permite ver
        # lo que ocurrió mientras estaba cerrado, sin volver a enviarlo al servidor.
        if datos and datos.get("pasos") and (cambio or repetir):
            if datos["pasos"][-1]["forma"] == actual:
                self.datos, self.inicio = datos, ahora
        if self.inicio is None or not self.datos:
            return actual, posiciones(actual), "", False
        indice = int(max(0, ahora - self.inicio) // self.DURACION)
        pasos = self.datos["pasos"]
        if indice >= len(pasos):
            self.inicio = None
            return actual, posiciones(actual), "", False
        paso = pasos[indice]
        anterior = pasos[indice - 1]["forma"] if indice else self.datos["antes"]
        destino = paso["forma"]
        origenes, finales = posiciones(anterior), posiciones(destino)
        t = min(1, max(0, (ahora - self.inicio - indice * self.DURACION) / self.DURACION))
        t = t * t * (3 - 2 * t)
        puntos = {}
        for clave, fin in finales.items():
            inicio = origenes.get(clave, (fin[0], AREA[1]))
            puntos[clave] = tuple(a + (b - a) * t for a, b in zip(inicio, fin))
        texto = ("Guardamos el caso en su lugar." if paso["tipo"] == "insertar" else
                 "Giro a la " + paso["direccion"] + ": repartimos las ramas.")
        return destino, puntos, texto, True


def dimension_caso(caso):
    return caso.get("datos", {}).get("dimension") or (
        "futuro" if caso["id"] == "nucleo_control" else "presente" if caso["id"].startswith("presente_") else "la_copa")


def etiqueta_decision(caso, contexto):
    era = dimension_caso(caso)
    from multijugador.mision import OPCIONES as COPA
    from multijugador.presente import OPCIONES as PRESENTE
    from multijugador.nucleo import OPCIONES as FUTURO
    opciones = {"la_copa": COPA, "presente": PRESENTE, "futuro": FUTURO}[era]
    opcion = caso["datos"]["resultado"].get("opcion", "")
    propias = contexto if era == "la_copa" else contexto.get(era) or {}
    return propias.get("opciones", {}).get(opcion, opciones.get(opcion, opcion))


def aprendizaje(caso):
    era = dimension_caso(caso)
    return {
        "la_copa": "Antes de repetir un aviso, compara quién lo cuenta, la fecha y sus pruebas.",
        "presente": "Una foto, una voz o un video pueden alterarse. Busca el original y contrasta sus fuentes.",
        "futuro": "Una herramienta puede ayudar, pero las personas deben poder revisar sus decisiones.",
    }[era]
