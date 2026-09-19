"""
Alcalde Digital - La Copa
Logica del juego: mantiene el estado de la partida (indicadores,
tablilla actual, nodo actual del arbol) y expone funciones simples
para que la interfaz grafica (botones) las use, sin necesitar saber
como funciona el arbol por dentro.

Este modulo depende de arboles.py (NodoDecision, construir_tablilla_*).
"""

from Arboles import (
    construir_tablilla_rumor_politico,
    construir_tablilla_suceso_natural,
    construir_tablilla_acusacion,
)


class EstadoJuego:
    """
    Guarda todo lo que cambia durante una partida:
    - los indicadores de la aldea
    - la lista de tablillas pendientes (arboles de decision)
    - el nodo actual dentro de la tablilla que se esta jugando
    """

    def __init__(self):
        self.indicadores = {
            "sabiduria": 50,
            "confianza_consejo": 50,
            "armonia": 50,
            "susurros_falsos": 0,
            "grietas_puentes": 0,
        }

        # Cola de tablillas pendientes. Cada elemento es la raiz
        # de un arbol de decisiones (NodoDecision).
        self.tablillas_pendientes = [
            construir_tablilla_rumor_politico(),
            construir_tablilla_suceso_natural(),
            construir_tablilla_acusacion(),
        ]
        self.categorias_clasificadas = [
            tablilla.categoria for tablilla in self.tablillas_pendientes
        ]

        self.tablillas_resueltas = 0
        self.nodo_actual = None
        self.categoria_tablilla_actual = None
        self.camino_decision_actual = []
        self.historial_decisiones = []
        # La clasificación se guarda como resultado: no se revela mientras
        # el jugador todavía está tomando decisiones sobre la tablilla.
        self.resultado_evento = None
        self.terminado = False

        self._cargar_siguiente_tablilla()

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
        """Indica que hay un resultado de clasificación pendiente de mostrar."""
        return self.resultado_evento is not None

    def resultado_evento_actual(self):
        """Devuelve la clasificación y consecuencia del evento recién cerrado."""
        return self.resultado_evento

    def continuar_despues_resultado(self):
        """Carga la siguiente tablilla después de que el jugador ve su clasificación."""
        if not self.evento_resuelto():
            return
        self.resultado_evento = None
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
                "efecto": dict(self.nodo_actual.efecto),
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
        else:
            self.nodo_actual = None
            self.categoria_tablilla_actual = None
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
