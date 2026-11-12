"""Arte opcional de la etapa de presentación; ninguna carga al importar."""
import pygame

from nucleo.recursos import cargar_imagen


TARJETAS = {
    "aviso_comunitario": "aviso_comunitario.png",
    "generado_con_ia": "Generado_con_IA.png",
    "contenido_autentico": "Contenido_autentico.png",
    "contenido_manipulado": "Contenido_manipulado.png",
    "control_autonomo": "Control_autonomo.png",
    "suplantacion": "suplantación.png",
}


def tarjetas_disponibles(caja=(180, 200)):
    """Tarjetas con proporciones originales, en el mismo área clicable."""
    from interfaz.arte import ajustar_imagen
    resultado = {}
    for clave, archivo in TARJETAS.items():
        original = cargar_imagen("Clasificación/" + archivo, requerido=False)
        if original is None:
            continue
        ajustada = ajustar_imagen(original, caja)
        if ajustada is not None:
            tarjeta = pygame.Surface(caja, pygame.SRCALPHA)
            tarjeta.blit(ajustada, ajustada.get_rect(center=tarjeta.get_rect().center))
            resultado[clave] = tarjeta
    return resultado


class AnimacionesNucleo:
    """Celdas cuadradas: las tiras nuevas tienen nueve cuadros, no ocho.

    Se conservan tamaño y ancla entre cuadros. Nunca se escala al dibujar.
    La derrota se reserva para la etapa de batalla, todavía pendiente.
    """
    ARCHIVOS = {
        "reposo": "NucleoFila1.png", "inquieto": "NucleoInquieto.png",
        "carga": "NucleoCarga.png", "sereno": "NucleoSereno.png",
        "saturado": "NucleoSaturado.png", "cambio": "NucleoCambiodeFase.png",
    }

    def __init__(self, lado=32):
        self.cuadros = {}
        for estado, archivo in self.ARCHIVOS.items():
            imagen = cargar_imagen("NPCS/Nucleo/" + archivo, requerido=False)
            if imagen is None:
                continue
            ancho, alto = imagen.get_size()
            if alto <= 0 or ancho % alto or not 1 <= ancho // alto <= 32:
                continue
            self.cuadros[estado] = [pygame.transform.scale(
                imagen.subsurface((x, 0, alto, alto)), (lado, lado))
                for x in range(0, ancho, alto)]

    @staticmethod
    def estado(contexto):
        final = contexto.get("desafio_final") or {}
        if final.get("fase") == "victoria":
            return "sereno"
        if final.get("fase") == "activo":
            batalla = final.get("batalla", {})
            if batalla.get("fase") == 2 and batalla.get("turno") == "aviso" and batalla.get("segundos", 0) > 2.5:
                return "cambio"
            if batalla.get("turno") == "recarga":
                return "carga"
            return "saturado" if batalla.get("fase") == 2 else "inquieto"
        if final.get("fase") in ("preparacion", "reintento"):
            return "carga" if "habitante" in final.get("hechos", []) else "inquieto"
        resultado = contexto.get("resultado") or {}
        if resultado.get("correcto"):
            return "sereno"
        if resultado.get("opcion") == "compartir":
            return "saturado"
        if contexto.get("pistas", 0) >= max(1, contexto.get("total_pistas", 1)):
            return "carga"
        return "inquieto"

    def cuadro(self, contexto, ahora_ms):
        frames = self.cuadros.get(self.estado(contexto)) or self.cuadros.get("reposo")
        return frames[(ahora_ms // 180) % len(frames)] if frames else None
