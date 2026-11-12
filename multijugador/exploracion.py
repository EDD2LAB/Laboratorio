"""Descubrimientos opcionales: sin respuestas de casos ni premios repetibles."""
from .dimensiones_red import spawn_interior, rect_salida


# Cada visita explica una herramienta para investigar, no la solución del caso.
CONTENIDOS = {
    "centro_verificacion": ("Mesa de verificación", "Compara dos fuentes. Mira quién publicó el mensaje, cuándo lo hizo y qué pruebas aporta. Una imagen llamativa no demuestra que algo sea cierto."),
    "estudio_influencer": ("Observatorio de mensajes", "Una publicación puede llegar a muchas personas y aun así ser falsa. Antes de compartirla, pregunta: ¿quién la creó y dónde está el original?"),
    "sede_aspirante": ("Archivo de firmas", "La firma dice quién se hace responsable de un documento. Compara autor, fecha y permiso: una cuenta no puede darse autoridad a sí misma."),
    "cafe_digital": ("Mesa de testimonios", "Escucha a alguien que estuvo allí. Después busca otra fuente independiente. Dos copias del mismo mensaje siguen siendo una sola fuente."),
    "estacion_mensajero": ("Registro de rutas", "Conserva el origen y la fecha al llevar un mensaje. Si descubres un error, envía también la corrección a quienes recibieron el aviso."),
}
MESAS = {"centro_verificacion": "mesa_verificacion", "estudio_influencer": "sofa_estudio",
         "sede_aspirante": "mesa_reunion_sede", "cafe_digital": "mesa_cafe_central",
         "estacion_mensajero": "mesa_estacion"}
AYUDA_VECINOS = {
    "Elia": ("¿Cómo comparo las pistas?", "¿Y si mis compañeros piensan distinto?"),
    "Arel": ("¿Cómo comparto una pista?", "¿Qué hago con los suministros?"),
}


def colocar_vecinos(campana, colisiones):
    """Puntos accesibles cercanos a fuentes existentes, sin editar el mapa."""
    ocupadas = [(n["x"], n["y"]) for n in campana.dialogos.npcs_copa]
    for nombre, rol in (("Elia", "habitante"), ("Arel", "mensajero")):
        ancla = next(o for o in campana.objetivos if o.get("rol") == rol)
        x, y = colisiones.inicio_alcanzable(ancla["x"], ancla["y"], ocupadas, separacion=48)
        ocupadas.append((x, y))
        campana.dialogos.npcs_copa.append(dict(id=nombre.lower(), nombre=nombre, dimension="la_copa",
                                              x=round(x), y=round(y), exploracion=True))


class ExploracionInteriores:
    def __init__(self):
        self.objetivos = []
        self.visitados = {}  # jugador -> ids: se conserva al viajar y reconectar

    def configurar(self, dimension, interiores):
        for edificio, mapa in interiores.items():
            # Alejado de la salida y alcanzable desde el spawn, a pie.
            origen = spawn_interior(mapa.datos)
            salida = rect_salida(mapa.datos)
            x, y = mapa.inicio_alcanzable(*origen, [(salida[0] + salida[2] / 2,
                                                    salida[1] + salida[3] / 2)], separacion=90)
            mesa = next((h for h in mapa.datos["hitboxes"] if h.get("id") == MESAS[edificio]), None)
            if mesa:
                if mesa.get("type") == "circle":
                    frente = (mesa["cx"] * 960, mesa["cy"] * 720 + mesa["r"] * 960 + 14)
                else:
                    frente = ((mesa["rx"] + mesa["rw"] / 2) * 960, (mesa["ry"] + mesa["rh"]) * 720 + 14)
                if dimension in ("presente", "futuro"):
                    from logica.zonas_caminables import componente, ancla
                    candidato = ancla(componente(mapa, origen), frente)
                    # El componente ya prueba la conexión; no repetir A* al crear cada sala.
                    x, y = candidato
                else:
                    candidato = mapa.inicio_libre(*frente)
                    from bots.navegador_bot import NavegadorBot
                    ruta = NavegadorBot(mapa).buscar_ruta(origen, candidato, radio=8)
                    if ruta:
                        x, y = candidato
            self.objetivos.append(dict(id="explorar:" + dimension + ":" + edificio,
                                       nombre=CONTENIDOS[edificio][0], dimension=dimension,
                                       interior=edificio, x=round(x), y=round(y)))

    def inspeccionar(self, identificador, objetivo, jugadores, cerca):
        punto = next((o for o in self.objetivos if o["id"] == objetivo), None)
        if punto is None or not cerca(jugadores[identificador], punto):
            raise ValueError("Entra al edificio y acércate a la mesa de consulta.")
        self.visitados.setdefault(identificador, set()).add(punto["id"])
        titulo, texto = CONTENIDOS[punto["interior"]]
        return {"vista": "descubrimiento", "titulo": titulo, "mensaje": texto,
                "descubrimiento": punto["id"]}

    def publico(self):
        vistos = set().union(*self.visitados.values()) if self.visitados else set()
        return [dict(o, visitado=o["id"] in vistos) for o in self.objetivos]
