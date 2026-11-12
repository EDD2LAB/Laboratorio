"""Configuración y estado de las dimensiones disponibles."""

import copy


DIMENSION_LA_COPA = "la_copa"
DIMENSION_PRESENTE = "presente"
DIMENSION_FUTURO = "futuro"

EDIFICIOS_PRESENTE = {
    "centro_verificacion": {
        "nombre": "Centro de Verificación",
        "funcion": "Verificar imágenes, fuentes y contexto",
        "personaje": "Darío Veraz",
        "rol": "Agente de verificación",
        "interior": "Fondos/Mapas/Presente/CentrodeVerifInt.png",
        "interior_hitboxes": "Mapas/Presente/CentrodeVerifInt_hitboxes.json",
        "mision": "verificar_publicacion",
        "spawn_exterior": (0.1604, 0.2126),
    },
    "estudio_influencer": {
        "nombre": "Estudio del Influencer",
        "funcion": "Crear y difundir publicaciones",
        "personaje": "Lía Nova",
        "rol": "Influencer",
        "interior": "Fondos/Mapas/Presente/EstudioInfluencerInt.png",
        "interior_hitboxes": "Mapas/Presente/EstudioInfluencerInt_hitboxes.json",
        "mision": "alcance_publicacion",
        "spawn_exterior": (0.8104, 0.2054),
    },
    "sede_aspirante": {
        "nombre": "Sede del Aspirante",
        "funcion": "Sede política de Ronaldo Vélez",
        "personaje": "Ronaldo Vélez",
        "rol": "Aspirante",
        "interior": "Fondos/Mapas/Presente/SededelAspiranteInt.png",
        "interior_hitboxes": "Mapas/Presente/SededelAspiranteInt_hitboxes.json",
        "mision": "campana_alcaldia",
        "spawn_exterior": (0.0979, 0.5081),
    },
    "cafe_digital": {
        "nombre": "Café Digital",
        "funcion": "Redacción y archivo digital",
        "personaje": "Elías Vega",
        "rol": "Periodista",
        "interior": "Fondos/Mapas/Presente/CaféDigitalInt.png",
        "interior_hitboxes": "Mapas/Presente/CaféDigitalInt_hitboxes.json",
        "mision": "investigacion_digital",
        "spawn_exterior": (0.8646, 0.5225),
    },
    "estacion_mensajero": {
        "nombre": "Estación del Mensajero",
        "funcion": "Distribuir y rastrear mensajes urbanos",
        "personaje": "Mateo Ríos",
        "rol": "Mensajero urbano",
        "interior": "Fondos/Mapas/Presente/EstacionMensajeroInt.png",
        "interior_hitboxes": "Mapas/Presente/EstacionMensajeroInt_hitboxes.json",
        "mision": "rastrear_propagacion",
        "spawn_exterior": (0.4354, 0.8324),
    },
}

# Interiores del Futuro: conservan sus imágenes y paredes propias.
# Solo heredan la configuración general del edificio; el JSON se reemplaza abajo.
EDIFICIOS_FUTURO = {
    clave: dict(EDIFICIOS_PRESENTE[clave], nombre=nombre,
                interior="Fondos/Mapas/Futuro/" + archivo,
                interior_hitboxes="Mapas/Futuro/" + archivo[:-4] + "_hitboxes.json")
    for clave, nombre, archivo in (
        ("centro_verificacion", "Centro de Supervisión", "Centro-Verif-FuturoInt.png"),
        ("estudio_influencer", "Observatorio de Mensajes", "estudioInflu-Futuroint.png"),
        ("sede_aspirante", "Archivo del Consejo", "Sede-Aspirante-FuturoInt.png"),
        ("cafe_digital", "Café de Datos", "CafefuturoInt.png"),
        ("estacion_mensajero", "Estación de Enlaces", "EstacióndeMensajeriaInt.png"),
    )
}

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
        "musica": "musica_presente",
        "mision_inicial": "contenido_sospechoso",
        "disponible": True,
    },
    DIMENSION_FUTURO: {
        "nombre": "Ciudad Núcleo",
        "mapa": "Fondos/Mapas/Futuro/MapaFuturo.png",
        "hitboxes": "Mapas/Futuro/MapaFuturo_hitboxes.json",
        "spawn": (480, 620),
        "musica": "musica_nucleo",
        "mision_inicial": "nucleo_control",
        "disponible": True,
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
