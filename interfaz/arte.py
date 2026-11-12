"""Arte de la interfaz: retratos, emblemas e iconos de ``Imagenes/``.

Todo se carga una sola vez y después de ``set_mode``; el escalado es el de
pixel art (``scale``). Una imagen ausente da ``None`` y su sitio queda vacío.
"""
import pygame

from nucleo.recursos import cargar_imagen

NUEVOS = "Iconos/Nuevos/"
HABILIDAD = "Iconos/Habilidad/"
MULTI = "Iconos/Multijugador/"

# Solo identidades confirmadas por el nombre del archivo. Los demás retratos
# conservan el sprite de su era hasta que el equipo confirme a quién pertenecen.
RETRATOS_NOMBRADOS = {
    "naira": "NairaRetraro.png", "odran": "OdranRetrato.png",
    "darek": "DarekRetrato.png", "ronaldo vélez": "RonaldoVelezRetrato.png",
}


def ajustar_imagen(imagen, caja):
    """Encaja el contenido visible sin deformarlo ni cortar su silueta."""
    limites = imagen.get_bounding_rect()
    if not limites.width or not limites.height:
        return None
    imagen = imagen.subsurface(limites)
    factor = min(caja[0] / imagen.get_width(), caja[1] / imagen.get_height())
    return pygame.transform.scale(imagen, (max(1, round(imagen.get_width() * factor)),
                                           max(1, round(imagen.get_height() * factor))))

# clave -> (carpeta de Retratos, prefijo de sus cuatro expresiones Num1..Num4)
RETRATOS = {
    "guardian": ("Retrato Guardián", "RetratoGuardian"),
    "mensajero": ("Retrato Mensajero", "RetratoMensajero"),
    "habitante": ("Retrato Habitante Hombre", "RetratoHabitanteH"),
    "aspirante": ("Retrato Aspirante Hombre", "RetratoAspiranteH"),
    "luma": ("Retrato Habitante Mujer", "RetratoHabitanteFem"),
    "mira": ("Retrato Aspirante Mujer", "RetratoAspiranteFem"),
}
EMBLEMAS = {"la_copa": "emblema_copa.png", "presente": "emblema_presente.png", "futuro": "emblema_futuro.png"}
# rol -> iconos del poder: (normal, disponible, ya usado)
HABILIDADES = {
    "guardian": (MULTI + "LupaMemorGuardian.png", MULTI + "LupaMemorActive.png", MULTI + "LupaMemorRecarg.png"),
    "mensajero": (MULTI + "ImpulsoVientMensj.png", MULTI + "ImpulsoVientActive.png", MULTI + "ImpulsoVientRecarg.png"),
    "habitante": (MULTI + "VozComuHab.png", HABILIDAD + "VozComuActive.png", MULTI + "VozComuRecarg.png"),
    "aspirante": (MULTI + "ComunicadoPubAspirante.png", HABILIDAD + "ComunicadoPubActive.png", MULTI + "ComunicadoPubRecarg.png"),
}
# id de la pista (La Copa y Distrito Conecta) -> icono según qué tipo de prueba es.
ICONOS_PISTA = {
    "pista_guardian": NUEVOS + "icono_libro.png",
    "pista_mensajero": "Iconos/ruta.png",
    "pista_habitante": "Iconos/testimonio.png",
    "pista_aspirante": "Iconos/registro.png",
    "fuente_ausente": NUEVOS + "icono_captura.png",
    "testimonio_y_contexto": "Iconos/testimonio.png",
    "respuesta_kael": NUEVOS + "icono_tiempo.png",
}


def icono(ruta, caja):
    """Imagen recortada a su contenido y ajustada a ``caja`` sin deformarla."""
    imagen = cargar_imagen(ruta, requerido=False)
    if imagen is None:
        print("[Arte] Falta la imagen:", ruta)
        return None
    return ajustar_imagen(imagen, caja)


def cargar_retratos(clave, caja):
    """Las cuatro expresiones de un personaje (sin las que falten)."""
    carpeta, prefijo = RETRATOS[clave]
    frames = (icono(f"Retratos/{carpeta}/{prefijo}_Num{n}.png", caja) for n in range(1, 5))
    return [frame for frame in frames if frame is not None]


def expresion(frames, milisegundos):
    """Cambia de expresión poco a poco; None si no hay retrato."""
    return frames[(milisegundos // 700) % len(frames)] if frames else None


def cargar_emblemas(caja):
    return {dimension: icono(NUEVOS + archivo, caja) for dimension, archivo in EMBLEMAS.items()}


def dibujar_icono(superficie, imagen, centro):
    if imagen is not None:
        superficie.blit(imagen, imagen.get_rect(center=centro))


LADO_CESTO = 58


class ArtePartida:
    """Imágenes que usan la vista de la partida y su panel cooperativo."""

    def __init__(self):
        self.retratos = {clave: cargar_retratos(clave, (78, 88)) for clave in RETRATOS}
        self.retratos_nombrados = {nombre: icono("Retratos/" + archivo, (78, 88))
                                   for nombre, archivo in RETRATOS_NOMBRADOS.items()}
        from interfaz.presentacion_arte import AnimacionesNucleo
        self.nucleo = AnimacionesNucleo()
        self.modulo_final = icono("FinalCooperativo/ModuloSupervision.png", (16, 24))
        self.retrato_agente = icono("Retratos/RetratoAgenteDVerif.png", (78, 88))
        self.marco = icono(NUEVOS + "panel_expediente.png", (112, 120))
        self.flecha_izq = icono(NUEVOS + "Boton_izq.png", (44, 44))
        self.flecha_der = icono(NUEVOS + "Boton_der.png", (44, 44))
        self.emblemas_portal = cargar_emblemas((56, 56))
        self.emblemas_viaje = cargar_emblemas((128, 128))
        self.iconos_pista = {pista: icono(ruta, (40, 40)) for pista, ruta in ICONOS_PISTA.items()}
        self.poder_grande = {rol: icono(rutas[0], (72, 72)) for rol, rutas in HABILIDADES.items()}
        self.poder_listo = {rol: icono(rutas[1], (30, 30)) for rol, rutas in HABILIDADES.items()}
        self.poder_usado = {rol: icono(rutas[2], (30, 30)) for rol, rutas in HABILIDADES.items()}
        self.tiempo = icono(NUEVOS + "icono_tiempo.png", (18, 18))
        self.arbol = icono(NUEVOS + "icono_arbol.png", (36, 36))
        self.sello = icono(NUEVOS + "sello_consejo.png", (70, 70))
        self.insignia = icono(NUEVOS + "insignia_base.png", (70, 70))
        self.cestos = self.cargar_cestos(1)
        self.iconos_ajustes = {nombre: icono(NUEVOS + "icono_" + nombre + ".png", (30, 30))
                               for nombre in ("audio", "contraste", "apariencia", "libro", "arbol")}
        self.marco_dialogo = cargar_imagen("Dialogo/Marco_dialogo.png", (860, 484), requerido=False)
        if self.marco_dialogo is None:
            print("[Arte] Falta la imagen: Dialogo/Marco_dialogo.png")
        self.barra_recarga = {clave: icono("Barras/BarraRecarga" + archivo + ".png", (62, 16))
                              for clave, archivo in (("vacia", "Empty"), ("mitad", "Mitad"), ("llena", "Llena"))}

    @staticmethod
    def cargar_cestos(zoom):
        """El cesto de los encargos, escalado una vez al tamaño con que se dibuja."""
        lado = LADO_CESTO * zoom
        return {clave: icono(NUEVOS + "cesto_" + clave + ".png", (lado, lado)) for clave in ("vacio", "lleno")}
