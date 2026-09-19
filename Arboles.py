"""
Alcalde Digital - La Copa
Estructuras de arbol para la primera entrega:
  1. Arbol de decisiones (NodoDecision): modela las elecciones del jugador
     ante cada tablilla y sus consecuencias.
  2. Arbol de clasificacion (NodoCategoria): organiza los tipos de
     tablilla que puede generar el juego.
"""


# ---------------------------------------------------------------------------
# 1. ARBOL DE DECISIONES
# ---------------------------------------------------------------------------

class NodoDecision:
    """
    Nodo de un arbol general (n-ario).
    - texto: la pregunta o publicacion que se muestra al jugador.
    - opciones: dict {texto_de_la_opcion: NodoDecision_hijo}
    - efecto: dict con los cambios a los indicadores de la aldea.
              Solo se usa cuando el nodo es una hoja (no tiene opciones).
    """

    def __init__(self, texto, efecto=None, categoria=None):
        self.texto = texto
        self.opciones = {}
        self.efecto = efecto or {}
        # Solo se usa en la raiz de cada tablilla: indica a que rama
        # del arbol de clasificacion (NodoCategoria) pertenece.
        self.categoria = categoria

    def agregar_opcion(self, texto_opcion, nodo_hijo):
        """Inserta un nuevo nodo hijo bajo la opcion indicada."""
        self.opciones[texto_opcion] = nodo_hijo

    def eliminar_opcion(self, texto_opcion):
        """Elimina una opcion (y todo su subarbol) de este nodo."""
        if texto_opcion in self.opciones:
            del self.opciones[texto_opcion]

    def es_hoja(self):
        return len(self.opciones) == 0

    def recorrer(self, obtener_eleccion):
        """
        Recorrido en profundidad dirigido por el jugador.
        'obtener_eleccion' es una funcion que recibe el nodo actual
        y devuelve el texto de la opcion elegida por el jugador.
        Devuelve el nodo hoja final (con el efecto a aplicar).
        """
        nodo_actual = self
        while not nodo_actual.es_hoja():
            eleccion = obtener_eleccion(nodo_actual)
            if eleccion not in nodo_actual.opciones:
                raise ValueError(f"Opcion invalida: {eleccion}")
            nodo_actual = nodo_actual.opciones[eleccion]
        return nodo_actual

    def recorrer_completo(self, camino=""):
        """
        Recorrido DFS completo (todas las ramas), util para depuracion
        o para que el 'Guardian de la Memoria' revise el arbol entero.
        Devuelve una lista de tuplas (camino, texto_nodo).
        """
        resultados = [(camino, self.texto)]
        for opcion, hijo in self.opciones.items():
            nuevo_camino = f"{camino} -> {opcion}" if camino else opcion
            resultados.extend(hijo.recorrer_completo(nuevo_camino))
        return resultados


def construir_tablilla_rumor_politico():
    """
    Tablilla: 'El Aspirante Kael quiere cerrar el puente norte'
    Arbol con 3 opciones en la raiz, una de ellas se ramifica de nuevo.
    """
    raiz = NodoDecision(
        "El Aspirante Kael quiere cerrar el puente norte",
        categoria=buscar_categoria(ARBOL_CATEGORIAS, "Rumor Politico", "Sobre un Aspirante"),
    )

    consultar = NodoDecision("¿Es verdadera esta tablilla?")
    consultar.agregar_opcion(
        "Si",
        NodoDecision(
            "Colgaste una verdad confirmada",
            efecto={"sabiduria": +15, "confianza_consejo": +10},
        ),
    )
    consultar.agregar_opcion(
        "No",
        NodoDecision(
            "Quemaste un rumor falso a tiempo",
            efecto={"susurros_falsos": -18, "armonia": +10},
        ),
    )

    raiz.agregar_opcion(
        "Colgarla",
        NodoDecision(
            "La tablilla se propaga sin verificar",
            efecto={"susurros_falsos": +25, "confianza_consejo": -15, "armonia": -8},
        ),
    )
    raiz.agregar_opcion("Consultar", consultar)
    raiz.agregar_opcion(
        "Quemarla",
        NodoDecision(
            "La tablilla desaparece, pero pudo ser verdad",
            efecto={"sabiduria": -10, "confianza_consejo": -6},
        ),
    )
    return raiz


def construir_tablilla_suceso_natural():
    """
    Tablilla: 'Anoche cayo un rayo cerca del Mirador Alto'
    Ejemplo con solo 2 opciones en la raiz (mas corto que el anterior).
    """
    raiz = NodoDecision(
        "Anoche cayo un rayo cerca del Mirador Alto",
        categoria=buscar_categoria(ARBOL_CATEGORIAS, "Suceso Natural", "Clima"),
    )
    raiz.agregar_opcion(
        "Colgarla",
        NodoDecision(
            "La aldea se entera del suceso natural",
            efecto={"armonia": +12, "confianza_consejo": +5},
        ),
    )
    raiz.agregar_opcion(
        "Quemarla",
        NodoDecision(
            "Se ignora informacion util para la aldea",
            efecto={"confianza_consejo": -12, "armonia": -8},
        ),
    )
    return raiz


def construir_tablilla_acusacion():
    """
    Tablilla: 'La Aspirante Mira regalo comida a cambio de votos'
    Ejemplo con 4 opciones en la raiz para mostrar variedad de ramas.
    """
    raiz = NodoDecision(
        "La Aspirante Mira regalo comida a cambio de votos",
        categoria=buscar_categoria(ARBOL_CATEGORIAS, "Acusacion Personal", "Entre Aspirantes"),
    )
    raiz.agregar_opcion(
        "Colgarla",
        NodoDecision(
            "El rumor crece rapido",
            efecto={"susurros_falsos": +30, "armonia": -15, "confianza_consejo": -12},
        ),
    )
    raiz.agregar_opcion(
        "Consultar",
        NodoDecision(
            "El Guardian confirma que es exagerado",
            efecto={"sabiduria": +12, "susurros_falsos": -18, "confianza_consejo": +6},
        ),
    )
    raiz.agregar_opcion(
        "Quemarla",
        NodoDecision(
            "Se evita un conflicto innecesario",
            efecto={"grietas_puentes": -15, "armonia": +10},
        ),
    )
    raiz.agregar_opcion(
        "Ignorarla",
        NodoDecision(
            "La tablilla se pierde entre otras",
            efecto={"susurros_falsos": +10, "grietas_puentes": +8},
        ),
    )
    return raiz


# ---------------------------------------------------------------------------
# 2. ARBOL DE CLASIFICACION DE PUBLICACIONES
# ---------------------------------------------------------------------------

class NodoCategoria:
    """
    Nodo de un arbol general y estatico que clasifica los tipos
    de tablilla que puede generar el juego.
    """

    def __init__(self, nombre, padre=None):
        self.nombre = nombre
        self.subcategorias = []
        self.padre = padre

    def agregar_subcategoria(self, nodo_hijo):
        self.subcategorias.append(nodo_hijo)
        nodo_hijo.padre = self

    def ruta_desde_raiz(self):
        ruta = []
        nodo = self
        while nodo is not None:
            ruta.append(nodo)
            nodo = nodo.padre
        return list(reversed(ruta))

    def es_hoja(self):
        return len(self.subcategorias) == 0

    def imprimir(self, nivel=0):
        print("  " * nivel + "- " + self.nombre)
        for hijo in self.subcategorias:
            hijo.imprimir(nivel + 1)


def construir_arbol_categorias():
    raiz = NodoCategoria("Tablilla")

    rumor_politico = NodoCategoria("Rumor Politico")
    rumor_politico.agregar_subcategoria(NodoCategoria("Sobre un Aspirante"))
    rumor_politico.agregar_subcategoria(NodoCategoria("Sobre una decision del Consejo"))

    suceso_natural = NodoCategoria("Suceso Natural")
    suceso_natural.agregar_subcategoria(NodoCategoria("Clima"))
    suceso_natural.agregar_subcategoria(NodoCategoria("Fauna del bosque"))

    acusacion = NodoCategoria("Acusacion Personal")
    acusacion.agregar_subcategoria(NodoCategoria("Entre Aspirantes"))
    acusacion.agregar_subcategoria(NodoCategoria("Entre Habitantes"))

    raiz.agregar_subcategoria(rumor_politico)
    raiz.agregar_subcategoria(suceso_natural)
    raiz.agregar_subcategoria(acusacion)
    return raiz


def buscar_categoria(raiz, *nombres):
    nodo = raiz
    for nombre in nombres:
        nodo = next((hijo for hijo in nodo.subcategorias if hijo.nombre == nombre), None)
        if nodo is None:
            raise ValueError(f"Categoria inexistente: {' > '.join(nombres)}")
    return nodo


ARBOL_CATEGORIAS = construir_arbol_categorias()


# ---------------------------------------------------------------------------
# DEMO EN CONSOLA
# ---------------------------------------------------------------------------

def pedir_eleccion_consola(nodo):
    print(f"\n{nodo.texto}")
    opciones = list(nodo.opciones.keys())
    for i, op in enumerate(opciones, start=1):
        print(f"  {i}. {op}")
    while True:
        try:
            idx = int(input("Elige una opcion: ")) - 1
            if 0 <= idx < len(opciones):
                return opciones[idx]
        except ValueError:
            pass
        print("Opcion invalida, intenta de nuevo.")


def main():
    print("=== Arbol de clasificacion de tablillas ===")
    arbol_categorias = construir_arbol_categorias()
    arbol_categorias.imprimir()

    print("\n=== Tablilla de prueba: rumor politico ===")
    tablilla = construir_tablilla_rumor_politico()
    hoja = tablilla.recorrer(pedir_eleccion_consola)
    print(f"\nResultado: {hoja.texto}")
    print(f"Efecto aplicado: {hoja.efecto}")

    print("\n=== Recorrido completo del arbol (todas las ramas) ===")
    for camino, texto in tablilla.recorrer_completo():
        print(f"[{camino}] -> {texto}")


if __name__ == "__main__":
    main()
