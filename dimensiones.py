"""Configuración y estado de las dimensiones disponibles."""

import copy


DIMENSION_LA_COPA = "la_copa"
DIMENSION_PRESENTE = "presente"
DIMENSION_FUTURO = "futuro"

DIMENSIONES = {
    DIMENSION_LA_COPA: {
        "nombre": "La Copa",
        "mapa": None,
        "hitboxes": "Mapas/Pr_MañanaLumi_hitboxes.json",
        "spawn": None,
        "musica": "ambiente",
        "mision_inicial": "tablillas_iniciales",
        "disponible": True,
    },
    DIMENSION_PRESENTE: {
        "nombre": "Distrito Conecta",
        "mapa": "Fondos/Mapas/Presente/MapaPresente.png",
        "hitboxes": "Mapas/Presente/MapaPresente_hitboxes.json",
        "spawn": (480, 620),
        "musica": "ambiente_presente",
        "mision_inicial": "contenido_sospechoso",
        "disponible": True,
    },
    DIMENSION_FUTURO: {
        "nombre": "Ciudad Núcleo",
        "mapa": None,
        "hitboxes": None,
        "spawn": None,
        "musica": "ambiente_futuro",
        "mision_inicial": None,
        "disponible": False,
    },
}


class GestorDimensiones:
    """Conserva la dimensión activa y coordina cambios serializables."""

    def __init__(self):
        self.dimension_actual = DIMENSION_LA_COPA
        self.dimension_anterior = None
        self.desbloqueadas = {DIMENSION_LA_COPA}
        self.estado_portales = {
            DIMENSION_PRESENTE: "bloqueado",
            DIMENSION_FUTURO: "bloqueado",
        }
        self.recursos_por_dimension = {}
        self.progreso_dimensiones = {
            dimension: {
                "completada": False,
                "eventos_resueltos": 0,
            }
            for dimension in DIMENSIONES
        }
        self.transicion_presente_realizada = False
        self.transicion_en_curso = False
        self.dimension_destino_pendiente = None

    def obtener_configuracion(self, dimension=None):
        return DIMENSIONES[dimension or self.dimension_actual]

    def desbloquear_dimension(self, dimension):
        if dimension not in DIMENSIONES:
            raise ValueError(f"Dimensión desconocida: {dimension}")
        if not DIMENSIONES[dimension]["disponible"]:
            raise ValueError(f"Dimensión todavía no implementada: {dimension}")
        self.desbloqueadas.add(dimension)
        if dimension in self.estado_portales:
            self.estado_portales[dimension] = "desbloqueado"

    def iniciar_transicion(self, destino):
        if destino not in DIMENSIONES:
            raise ValueError(f"Dimensión desconocida: {destino}")
        if not DIMENSIONES[destino]["disponible"]:
            raise ValueError(f"Dimensión todavía no implementada: {destino}")
        if destino not in self.desbloqueadas:
            raise ValueError(f"Dimensión bloqueada: {destino}")
        if self.transicion_en_curso:
            return None
        if destino == DIMENSION_PRESENTE and self.transicion_presente_realizada:
            return None

        self.transicion_en_curso = True
        self.dimension_destino_pendiente = destino
        self.estado_portales[destino] = "transicionando"
        return {
            "tipo": "cambio_dimension",
            "origen": self.dimension_actual,
            "destino": destino,
            "spawn": "spawn_presente" if destino == DIMENSION_PRESENTE else None,
        }

    def activar_dimension(self, destino):
        if not self.transicion_en_curso:
            raise RuntimeError("No hay una transición de dimensión activa.")
        if destino != self.dimension_destino_pendiente:
            raise ValueError(f"La transición activa no tiene como destino {destino}.")
        if not DIMENSIONES[destino]["disponible"]:
            raise ValueError(f"Dimensión todavía no implementada: {destino}")
        if destino not in self.desbloqueadas:
            raise ValueError(f"Dimensión bloqueada: {destino}")

        self.dimension_anterior = self.dimension_actual
        self.dimension_actual = destino
        self.desbloqueadas.add(destino)
        self.estado_portales[destino] = "abierto"
        self.transicion_en_curso = False
        self.dimension_destino_pendiente = None
        if destino == DIMENSION_PRESENTE:
            self.transicion_presente_realizada = True

    def cancelar_transicion(self):
        if self.dimension_destino_pendiente in self.estado_portales:
            self.estado_portales[self.dimension_destino_pendiente] = "bloqueado"
        self.transicion_en_curso = False
        self.dimension_destino_pendiente = None

    def guardar_recursos(self, dimension, recursos):
        self.recursos_por_dimension[dimension] = recursos

    def registrar_completada(self, dimension, eventos_resueltos=0):
        progreso = self.progreso_dimensiones[dimension]
        progreso["completada"] = True
        progreso["eventos_resueltos"] = eventos_resueltos

    def snapshot(self):
        return {
            "dimension_actual": self.dimension_actual,
            "dimension_anterior": self.dimension_anterior,
            "dimensiones_desbloqueadas": sorted(self.desbloqueadas),
            "estado_portales": copy.deepcopy(self.estado_portales),
            "progreso_dimensiones": copy.deepcopy(self.progreso_dimensiones),
            "transicion_presente_realizada": self.transicion_presente_realizada,
        }
