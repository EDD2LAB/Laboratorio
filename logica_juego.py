"""
Alcalde Digital - La Copa
Logica del juego: mantiene el estado de la partida (indicadores,
tablilla actual, nodo actual del arbol) y expone funciones simples
para que la interfaz grafica (botones) las use, sin necesitar saber
como funciona el arbol por dentro.

Este modulo depende de arboles.py (NodoDecision, construir_tablilla_*).
"""

import copy

from Arboles import (
    construir_tablilla_rumor_politico,
    construir_tablilla_suceso_natural,
    construir_tablilla_dia_tres,
)
from propagacion_informacion import PropagacionInformacion
from dimensiones import (
    DIMENSION_LA_COPA,
    DIMENSION_PRESENTE,
    GestorDimensiones,
)


OPCIONES_CLASIFICACION = {
    "Rumor Político": "Rumor Politico",
    "Suceso Natural": "Suceso Natural",
    "Acusación Personal": "Acusacion Personal",
}


class EstadoJuego:
    """
    Guarda todo lo que cambia durante una partida:
    - los indicadores de la aldea
    - la lista de tablillas pendientes (arboles de decision)
    - el nodo actual dentro de la tablilla que se esta jugando
    """

    PISTAS_PARA_VERIFICAR = (
        "fuente_ausente",
        "testimonio_y_contexto",
        "respuesta_kael",
    )

    def __init__(self):
        self.gestor_dimensiones = GestorDimensiones()
        self.indicadores = {
            "sabiduria": 50,
            "confianza_consejo": 50,
            "armonia": 50,
            "susurros_falsos": 0,
            "desinformación": 0,
        }

        # Cola de tablillas pendientes. Cada elemento es la raiz
        # de un arbol de decisiones (NodoDecision).
        self.tablillas_pendientes = [
            construir_tablilla_rumor_politico(),
            construir_tablilla_suceso_natural(),
        ]
        self.categorias_clasificadas = [
            tablilla.categoria for tablilla in self.tablillas_pendientes
        ]

        self.tablillas_resueltas = 0
        self.dia = 0
        self.nodo_actual = None
        self.categoria_tablilla_actual = None
        self.camino_decision_actual = []
        self.historial_decisiones = []
        self.propagaciones_informacion = []
        self.propagacion_actual = None
        # La clasificación se guarda como resultado: no se revela mientras
        # el jugador todavía está tomando decisiones sobre la tablilla.
        self.resultado_evento = None
        self.terminado = False
        self.puntuacion = 0
        self.historial_evidencias = []
        self.mensajes_verificados = []
        self.reputacion = 0
        self.rol_jugador = "periodista"
        self.mision_actual = "tablillas_iniciales"
        self.mision_presente = {
            "id": "contenido_sospechoso",
            "estado": "bloqueada",
            "pistas": [],
            "decision": None,
            "correccion_difundida": False,
        }
        self.progreso_guardado = {}

        self._cargar_siguiente_tablilla()

    @property
    def dimension_actual(self):
        return self.gestor_dimensiones.dimension_actual

    @dimension_actual.setter
    def dimension_actual(self, dimension):
        self.gestor_dimensiones.dimension_actual = dimension

    @property
    def dimensiones_desbloqueadas(self):
        return self.gestor_dimensiones.desbloqueadas

    @property
    def progreso_dimensiones(self):
        return self.gestor_dimensiones.progreso_dimensiones

    def guardar_progreso_dimension(self):
        """Toma una copia del progreso sin reiniciar el estado compartido."""
        if self.dimension_actual == DIMENSION_LA_COPA:
            self.gestor_dimensiones.registrar_completada(
                DIMENSION_LA_COPA,
                self.tablillas_resueltas,
            )
        self.progreso_guardado[self.dimension_actual] = {
            "indicadores": copy.deepcopy(self.indicadores),
            "puntuacion": self.puntuacion,
            "historial_decisiones": copy.deepcopy(self.historial_decisiones),
            "historial_evidencias": copy.deepcopy(self.historial_evidencias),
            "mensajes_verificados": copy.deepcopy(self.mensajes_verificados),
            "reputacion": self.reputacion,
            "rol_jugador": self.rol_jugador,
            "mision_actual": self.mision_actual,
            "mision_presente": copy.deepcopy(self.mision_presente),
            "dimensiones": self.gestor_dimensiones.snapshot(),
        }
        return self.progreso_guardado[self.dimension_actual]

    def iniciar_mision_presente(self):
        self.mision_actual = "contenido_sospechoso"
        self.mision_presente["estado"] = "activa"

    def registrar_pista_presente(self, pista):
        if pista not in self.mision_presente["pistas"]:
            self.mision_presente["pistas"].append(pista)
            self.historial_evidencias.append(pista)
            return True
        return False

    def resolver_mision_presente(self, decision):
        """Aplica una decisión de la primera publicación al estado compartido."""
        if self.dimension_actual != DIMENSION_PRESENTE:
            return False
        if self.mision_presente["estado"] == "completada":
            return False

        if decision == "revisar_fuente":
            self.registrar_pista_presente("fuente_ausente")
            self.guardar_progreso_dimension()
            return True
        if decision == "comparar_evidencia":
            self.registrar_pista_presente("testimonio_y_contexto")
            self.guardar_progreso_dimension()
            return True
        if decision == "dejar_pendiente":
            self.mision_presente["estado"] = "pendiente"
            self._aplicar_efecto({"sabiduria": 2})
            self.mision_presente["decision"] = decision
            self.guardar_progreso_dimension()
            return True
        if decision == "verificar" and any(
            pista not in self.mision_presente["pistas"]
            for pista in self.PISTAS_PARA_VERIFICAR
        ):
            return False
        if decision == "reportar":
            self._aplicar_efecto({
                "confianza_consejo": -2,
                "desinformación": -3,
            })
        elif decision == "verificar":
            self._aplicar_efecto({
                "sabiduria": 5,
                "confianza_consejo": 3,
                "armonia": 2,
                "susurros_falsos": -3,
                "desinformación": -5,
            })
            self.mensajes_verificados.append("publicacion_aspirante")
        else:
            raise ValueError(f"Decisión de misión inválida: {decision}")

        self.mision_presente["estado"] = "completada"
        self.mision_presente["decision"] = decision
        self.gestor_dimensiones.registrar_completada(
            DIMENSION_PRESENTE,
            eventos_resueltos=1,
        )
        self.guardar_progreso_dimension()
        return True

    # -----------------------------------------------------------------
    # Funciones que la interfaz grafica (botones) puede llamar
    # -----------------------------------------------------------------

    def texto_actual(self):
        """Texto que debe mostrarse en pantalla ahora mismo."""
        if self.terminado:
            return self._texto_resumen_final()
        if self.evento_resuelto():
            return self.resultado_evento["resultado"]
        return self.nodo_actual.texto

    def categoria_actual(self):
        """
        Nodo hoja (NodoCategoria) del arbol de clasificacion al que
        pertenece la tablilla que se esta jugando ahora mismo, sin
        importar en que nodo interno del arbol de decisiones se
        encuentre el jugador dentro de esa tablilla.
        """
        if self.categoria_tablilla_actual is None:
            return None
        return " > ".join(nodo.nombre for nodo in self.categoria_tablilla_actual.ruta_desde_raiz()[1:])

    def evento_resuelto(self):
        """Indica que una decisión ya generó una consecuencia."""
        return self.resultado_evento is not None

    def evento_clasificado(self):
        """Indica que el jugador ya intentó clasificar el evento resuelto."""
        return self.evento_resuelto() and self.resultado_evento["clasificacion_jugador"] is not None

    def resultado_evento_actual(self):
        """Devuelve la clasificación y consecuencia del evento recién cerrado."""
        return self.resultado_evento

    def opciones_clasificacion_actuales(self):
        """Categorías que el jugador puede elegir después de ver la consecuencia."""
        if not self.evento_resuelto() or self.evento_clasificado():
            return []
        return list(OPCIONES_CLASIFICACION.keys())

    def clasificar_evento(self, clasificacion):
        """Evalúa la clasificación como trivia, sin alterar los efectos previos."""
        if not self.evento_resuelto() or self.evento_clasificado():
            return
        if clasificacion not in OPCIONES_CLASIFICACION:
            raise ValueError(f"Clasificación inválida: {clasificacion}")

        categoria_real = self.resultado_evento["categoria"][1]
        categoria_elegida = OPCIONES_CLASIFICACION[clasificacion]
        acerto = categoria_elegida == categoria_real
        efecto_clasificacion = {"sabiduria": 5 if acerto else -5}
        self._aplicar_efecto(efecto_clasificacion)
        self.resultado_evento.update({
            "clasificacion_jugador": clasificacion,
            "clasificacion_correcta": acerto,
            "efecto_clasificacion": efecto_clasificacion,
        })

    def continuar_despues_resultado(self):
        """Carga la siguiente tablilla después de que el jugador ve su clasificación."""
        if not self.evento_clasificado():
            return
        self.resultado_evento = None
        self.dia = min(self.tablillas_resueltas, 2)
        if self.tablillas_resueltas == 2 and not self.tablillas_pendientes:
            tablilla_dia_tres = construir_tablilla_dia_tres(self.historial_decisiones)
            self.tablillas_pendientes.append(tablilla_dia_tres)
            self.categorias_clasificadas.append(tablilla_dia_tres.categoria)
        self._cargar_siguiente_tablilla()

    def ruta_categoria_actual(self):
        """
        Recorrido real hacia la raiz del arbol de clasificacion:
        devuelve la lista de nombres desde 'Tablilla' hasta la
        categoria especifica de la tablilla actual, subiendo nodo
        por nodo a traves de los punteros 'padre'. Devuelve una
        lista vacia si no hay tablilla activa.
        """
        nodo_categoria = self.categoria_tablilla_actual
        if nodo_categoria is None:
            return []
        return [nodo.nombre for nodo in nodo_categoria.ruta_desde_raiz()]

    def rutas_categorias_clasificadas(self):
        """Devuelve todas las rutas del catalogo usadas por las tablillas."""
        return [
            [nodo.nombre for nodo in categoria.ruta_desde_raiz()]
            for categoria in self.categorias_clasificadas
        ]

    def opciones_actuales(self):
        """
        Lista de textos de opciones para dibujar como botones.
        Devuelve una lista vacia si el juego termino.
        """
        if self.terminado or self.evento_resuelto() or self.nodo_actual is None:
            return []
        return list(self.nodo_actual.opciones.keys())

    def elegir_opcion(self, texto_opcion):
        """
        Se llama cuando el jugador hace clic en un boton.
        Avanza el arbol de decisiones un nivel.
        """
        if self.terminado or self.nodo_actual is None:
            return

        if texto_opcion not in self.nodo_actual.opciones:
            raise ValueError(f"Opcion invalida: {texto_opcion}")

        self.camino_decision_actual.append(texto_opcion)
        self.nodo_actual = self.nodo_actual.opciones[texto_opcion]

        if self.nodo_actual.es_hoja():
            self._aplicar_efecto(self.nodo_actual.efecto)
            self.resultado_evento = {
                "categoria": self.ruta_categoria_actual(),
                "camino": list(self.camino_decision_actual),
                "resultado": self.nodo_actual.texto,
                "efecto_decision": dict(self.nodo_actual.efecto),
                "clasificacion_jugador": None,
                "clasificacion_correcta": None,
                "efecto_clasificacion": {},
            }
            self.historial_decisiones.append(self.resultado_evento)
            self.tablillas_resueltas += 1
            self.nodo_actual = None

    def juego_terminado(self):
        return self.terminado

    # -----------------------------------------------------------------
    # Funciones internas
    # -----------------------------------------------------------------

    def _aplicar_efecto(self, efecto):
        """Suma (o resta) los valores del efecto a los indicadores."""
        for clave, valor in efecto.items():
            if clave in self.indicadores:
                self.indicadores[clave] += valor
                # Los indicadores se mantienen entre 0 y 100
                self.indicadores[clave] = max(0, min(100, self.indicadores[clave]))

    def _cargar_siguiente_tablilla(self):
        """Toma la siguiente tablilla de la cola, o termina el juego."""
        if self.tablillas_pendientes:
            self.nodo_actual = self.tablillas_pendientes.pop(0)
            self.categoria_tablilla_actual = getattr(self.nodo_actual, "categoria", None)
            self.camino_decision_actual = []
            ruta_categoria = self.ruta_categoria_actual()
            categoria = ruta_categoria[1] if len(ruta_categoria) > 1 else "normal"
            tipo = "rumor" if categoria in ("Rumor Politico", "Acusacion Personal") else "normal"
            self.propagacion_actual = PropagacionInformacion(
                f"tablilla_{self.tablillas_resueltas + 1}",
                self.nodo_actual.texto,
                tipo,
            )
            self.propagaciones_informacion.append(self.propagacion_actual)
        else:
            self.nodo_actual = None
            self.categoria_tablilla_actual = None
            self.propagacion_actual = None
            self.terminado = True

    def _texto_resumen_final(self):
        susurros = self.indicadores["susurros_falsos"]
        if susurros >= 60:
            mensaje = "La desconfianza se apodero de La Copa."
        elif self.indicadores["armonia"] >= 60:
            mensaje = "La Copa mantiene su armonia."
        else:
            mensaje = "La aldea sigue en pie, aunque con dudas."
        return f"Fin de la ronda. {mensaje}"


# ---------------------------------------------------------------------------
# EJEMPLO DE USO (esto es lo que tu compañero haria desde pygame,
# reemplazando input()/print() por botones y texto en pantalla)
# ---------------------------------------------------------------------------

def demo_consola():
    estado = EstadoJuego()

    while not estado.juego_terminado():
        print(f"\nIndicadores: {estado.indicadores}")
        print(estado.texto_actual())
        opciones = estado.opciones_actuales()
        for i, op in enumerate(opciones, start=1):
            print(f"  {i}. {op}")

        idx = int(input("Elige una opcion: ")) - 1
        estado.elegir_opcion(opciones[idx])

    print(f"\nIndicadores finales: {estado.indicadores}")
    print(estado.texto_actual())


if __name__ == "__main__":
    demo_consola()
