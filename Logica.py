"""
Alcalde Digital - La Copa
Logica del juego: mantiene el estado de la partida (indicadores,
tablilla actual, nodo actual del arbol) y expone funciones simples
para que la interfaz grafica (botones) las use, sin necesitar saber
como funciona el arbol por dentro.

Este modulo depende de arboles.py (NodoDecision, construir_tablilla_*).
"""

from arboles import (
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

        self.tablillas_resueltas = 0
        self.nodo_actual = None
        self.terminado = False

        self._cargar_siguiente_tablilla()

    # -----------------------------------------------------------------
    # Funciones que la interfaz grafica (botones) puede llamar
    # -----------------------------------------------------------------

    def texto_actual(self):
        """Texto que debe mostrarse en pantalla ahora mismo."""
        if self.terminado:
            return self._texto_resumen_final()
        return self.nodo_actual.texto

    def opciones_actuales(self):
        """
        Lista de textos de opciones para dibujar como botones.
        Devuelve una lista vacia si el juego termino.
        """
        if self.terminado or self.nodo_actual is None:
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

        self.nodo_actual = self.nodo_actual.opciones[texto_opcion]

        if self.nodo_actual.es_hoja():
            self._aplicar_efecto(self.nodo_actual.efecto)
            self.tablillas_resueltas += 1
            self._cargar_siguiente_tablilla()

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
        else:
            self.nodo_actual = None
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