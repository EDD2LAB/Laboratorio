"""Expediente ordenado por gravedad y orden de resolución; independiente de Pygame."""
from copy import deepcopy
from dataclasses import dataclass


@dataclass
class Caso:
    id: str
    titulo: str
    gravedad: int
    orden: int
    datos: dict

    @property
    def clave(self):
        return self.gravedad, self.orden, self.id

    def publico(self):
        return deepcopy(vars(self))


@dataclass
class Nodo:
    caso: Caso
    izquierda: object = None
    derecha: object = None
    altura: int = 1


class ExpedienteAVL:
    def __init__(self):
        self.raiz = None
        self.casos = {}
        self.rotaciones = []
        self.animacion = None
        self._giros = []

    @staticmethod
    def forma(nodo):
        if nodo is None:
            return None
        return {"id": nodo.caso.id, "i": ExpedienteAVL.forma(nodo.izquierda),
                "d": ExpedienteAVL.forma(nodo.derecha)}

    @staticmethod
    def altura(nodo):
        return nodo.altura if nodo else 0

    def _medir(self, nodo):
        nodo.altura = 1 + max(self.altura(nodo.izquierda), self.altura(nodo.derecha))

    def _rotar(self, nodo, izquierda):
        antes = self.forma(nodo)
        cima = nodo.derecha if izquierda else nodo.izquierda
        if izquierda:
            nodo.derecha, cima.izquierda = cima.izquierda, nodo
        else:
            nodo.izquierda, cima.derecha = cima.derecha, nodo
        self._medir(nodo)
        self._medir(cima)
        self.rotaciones.append({"nodo": nodo.caso.id, "direccion": "izquierda" if izquierda else "derecha"})
        self._giros.append((antes, self.forma(cima), "izquierda" if izquierda else "derecha"))
        return cima

    def ruta_insercion(self, caso):
        ruta, nodo = [], self.raiz
        while nodo:
            if caso.clave == nodo.caso.clave:
                break
            lado = "izquierda" if caso.clave < nodo.caso.clave else "derecha"
            ruta.append({"nodo": nodo.caso.id, "direccion": lado})
            nodo = getattr(nodo, lado)
        return ruta

    def insertar(self, caso):
        if not isinstance(caso.id, str) or not caso.id or type(caso.gravedad) is not int or not 1 <= caso.gravedad <= 9:
            raise ValueError("Caso o gravedad inválidos.")
        if type(caso.orden) is not int or caso.orden < 0:
            raise ValueError("Orden inválido.")
        if caso.id in self.casos:
            anterior = self.casos[caso.id]
            if anterior.clave != caso.clave:
                raise ValueError("No se puede cambiar la clave de un caso archivado.")
            anterior.datos = deepcopy(caso.datos)
            return False
        caso = deepcopy(caso)
        self.rotaciones = []
        self._giros = []
        antes = self.forma(self.raiz)

        def sin_equilibrar(forma):
            if forma is None:
                return {"id": caso.id, "i": None, "d": None}
            forma = deepcopy(forma)
            lado = "i" if caso.clave < self.casos[forma["id"]].clave else "d"
            forma[lado] = sin_equilibrar(forma[lado])
            return forma

        forma = sin_equilibrar(antes)

        def agregar(nodo):
            if nodo is None:
                return Nodo(caso)
            lado = "izquierda" if caso.clave < nodo.caso.clave else "derecha"
            setattr(nodo, lado, agregar(getattr(nodo, lado)))
            self._medir(nodo)
            balance = self.altura(nodo.izquierda) - self.altura(nodo.derecha)
            if balance > 1:
                if caso.clave > nodo.izquierda.caso.clave:
                    nodo.izquierda = self._rotar(nodo.izquierda, True)
                return self._rotar(nodo, False)
            if balance < -1:
                if caso.clave < nodo.derecha.caso.clave:
                    nodo.derecha = self._rotar(nodo.derecha, False)
                return self._rotar(nodo, True)
            return nodo

        self.raiz = agregar(self.raiz)
        self.casos[caso.id] = caso
        pasos = [{"tipo": "insertar", "forma": deepcopy(forma)}]

        def sustituir(arbol, viejo, nuevo):
            if arbol is None:
                return None
            if arbol["id"] == viejo:
                return deepcopy(nuevo)
            return dict(arbol, i=sustituir(arbol["i"], viejo, nuevo), d=sustituir(arbol["d"], viejo, nuevo))

        for previa, nueva, direccion in self._giros:
            forma = sustituir(forma, previa["id"], nueva)
            pasos.append({"tipo": "rotar", "direccion": direccion, "forma": deepcopy(forma)})
        self.animacion = {"caso": caso.id, "antes": antes, "pasos": pasos}
        return True

    def inorden(self):
        """Casos del árbol de menor a mayor clave."""
        orden = []

        def recorrer(nodo):
            if nodo is not None:
                recorrer(nodo.izquierda)
                orden.append(nodo.caso)
                recorrer(nodo.derecha)

        recorrer(self.raiz)
        return orden

    def publico(self):
        def recorrer(nodo):
            if nodo is None:
                return None
            return {"caso": nodo.caso.publico(), "altura": nodo.altura,
                    "izquierda": recorrer(nodo.izquierda), "derecha": recorrer(nodo.derecha)}
        return {"raiz": recorrer(self.raiz), "total": len(self.casos), "rotaciones": deepcopy(self.rotaciones)}
