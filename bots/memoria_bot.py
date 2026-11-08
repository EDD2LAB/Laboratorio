class MemoriaEquipo:
    def __init__(self, jugadores):
        self.pruebas_disponibles = set()
        self.pruebas_compartidas = set()
        self.roles_ocupados = {j["rol"]: j["id"] for j in jugadores}
        self.roles_humanos = {
            j["rol"]: j["id"] for j in jugadores if j.get("controlador") == "humano"
        }
        self.roles_bots = {
            j["rol"]: j["id"] for j in jugadores if j.get("controlador") == "bot"
        }
        self.tareas_en_progreso = {}
        self.votos_propuestos = {}
        self.solicitudes_ayuda = {}
        self.suministros_pendientes = set()
        # Tareas de preparación que solo debe hacer un bot (sujetar, trabajar,
        # reparar el puente). Clave con la ronda: no hace falta limpiarlas.
        self.reservas_preparacion = {}

    def reservar_preparacion(self, bot_id, tarea):
        propietario = self.reservas_preparacion.setdefault(tarea, bot_id)
        return propietario == bot_id

    def reservar_tarea(self, bot_id, tarea):
        propietario = self.tareas_en_progreso.get(tarea)
        if propietario not in (None, bot_id):
            return False
        self.tareas_en_progreso[tarea] = bot_id
        return True

    def liberar_tarea(self, bot_id):
        self.tareas_en_progreso = {
            tarea: propietario
            for tarea, propietario in self.tareas_en_progreso.items()
            if propietario != bot_id
        }

    def solicitar_ayuda(self, bot_id, destino):
        self.solicitudes_ayuda[bot_id] = dict(destino)

    def completar_ayuda(self, bot_id):
        self.solicitudes_ayuda.pop(bot_id, None)

    def nueva_ronda(self):
        self.pruebas_disponibles.clear()
        self.pruebas_compartidas.clear()
        self.tareas_en_progreso.clear()
        self.votos_propuestos.clear()
        self.solicitudes_ayuda.clear()
        self.suministros_pendientes.clear()
