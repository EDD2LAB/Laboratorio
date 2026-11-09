"""Registro autoritativo de casos e inserción guiada, sin datos de casos futuros."""
import json
from copy import deepcopy
from pathlib import Path

from logica.expediente_avl import Caso, ExpedienteAVL

CATALOGO = json.loads((Path(__file__).resolve().parents[1] / "datos" / "casos_expediente.json").read_text(encoding="utf-8"))


class ExpedientePartida:
    def __init__(self):
        self.arbol = ExpedienteAVL()
        self.pendientes = []
        self.revision = 0
        self.paso = 0
        self.eventos = {}

    def registrar(self, evento, titulo, resultado, pruebas):
        if self.eventos.get(evento) == resultado.get("evento_id") and evento in self.eventos:
            return
        self.eventos[evento] = resultado.get("evento_id")
        datos = {"resultado": deepcopy(resultado), "pruebas": deepcopy(pruebas),
                 "tipo": CATALOGO[evento]["tipo"], "ley": None, "sancion": None,
                 "estado_normativo": "pendiente_profesor"}
        if evento in self.arbol.casos:
            self.arbol.casos[evento].datos = datos
            return
        for caso in self.pendientes:
            if caso.id == evento:
                caso.datos = datos
                return
        caso = Caso(evento, titulo, CATALOGO[evento]["gravedad"],
                    len(self.arbol.casos) + len(self.pendientes), datos)
        if self.arbol.raiz is None:
            self.arbol.insertar(caso)
            self.revision += 1
        else:
            self.pendientes.append(caso)

    def paso_insercion(self, solicitud):
        if (type(solicitud.get("revision")) is not int or type(solicitud.get("paso")) is not int
                or not self.pendientes or solicitud.get("revision") != self.revision or solicitud.get("paso") != self.paso):
            raise ValueError("El expediente cambió. Revisa el paso actual.")
        caso = self.pendientes[0]
        if solicitud.get("caso") != caso.id:
            raise ValueError("Ese caso no está en turno.")
        ruta = self.arbol.ruta_insercion(caso)
        if solicitud.get("direccion") != ruta[self.paso]["direccion"]:
            raise ValueError("Compara la gravedad. Si es igual, el caso más reciente va a la derecha.")
        self.paso += 1
        if self.paso == len(ruta):
            self.arbol.insertar(self.pendientes.pop(0))
            self.paso = 0
            self.revision += 1
            return {"mensaje": "¡Caso guardado! El árbol se equilibra para encontrarlo fácilmente."}
        return {"mensaje": "¡Bien! Ahora compara con el siguiente caso."}

    def publico(self):
        estado = self.arbol.publico()
        pendiente = self.pendientes[0] if self.pendientes else None
        ruta = self.arbol.ruta_insercion(pendiente) if pendiente else []
        estado.update(revision=self.revision, paso=self.paso, pendientes=len(self.pendientes),
                      pendiente=pendiente.publico() if pendiente else None,
                      comparar_con=ruta[self.paso]["nodo"] if ruta else None)
        return estado
