"""Ventana de diálogo con los NPC: marco del juego, texto letra por letra y respuestas."""
import pygame

from nucleo.recursos import cargar_imagen, envolver_texto

ANCHO, ALTO = 900, 320
POSICION = (30, 394)
TEXTO_X, TEXTO_Y, TEXTO_ANCHO = 210, 122, 600
NOMBRE_Y = 96
CENTRO_RETRATO = (112, 114)
LADO_RETRATO = 100
RESPUESTAS_X, RESPUESTA_ANCHO, RESPUESTA_ALTO = 190, 600, 30
RESPUESTAS_Y = (192, 230, 268)
LETRAS_POR_SEGUNDO = 45
TINTA = (61, 37, 25)
RESALTADO = (146, 66, 20)
CORTE, TIRA = .38, .02  # franja lisa del marco que se estira (los adornos no se deforman)


class ArteDialogo:
    """Marco y retratos se preparan una vez; abrir un diálogo no carga nada."""

    def __init__(self):
        original = cargar_imagen("Dialogo/Marco_dialogo.png", requerido=False)
        self.marco = None
        if original is None:
            print("[Arte] Falta la imagen: Dialogo/Marco_dialogo.png")
        else:
            ancho = round(original.get_width() * ALTO / original.get_height())
            base = pygame.transform.scale(original, (ancho, ALTO))
            corte, tira = round(ancho * CORTE), max(1, round(ancho * TIRA))
            self.marco = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
            self.marco.blit(base, (0, 0), (0, 0, corte, ALTO))
            estirada = ANCHO - (ancho - tira)
            self.marco.blit(pygame.transform.scale(base.subsurface((corte, 0, tira, ALTO)), (estirada, ALTO)), (corte, 0))
            self.marco.blit(base, (corte + estirada, 0), (corte + tira, 0, ancho - corte - tira, ALTO))
        self.retratos = {}

    def retrato(self, nombre, imagen):
        """Retrato o sprite ampliado con vecino más cercano, una vez por personaje."""
        if nombre not in self.retratos and imagen is not None:
            limites = imagen.get_bounding_rect()
            recorte = imagen.subsurface(limites) if limites.width and limites.height else imagen
            factor = LADO_RETRATO / max(recorte.get_size())
            self.retratos[nombre] = pygame.transform.scale(
                recorte, (max(1, round(recorte.get_width() * factor)), max(1, round(recorte.get_height() * factor))))
        return self.retratos.get(nombre)


def abrir(panel, dialogo):
    panel.dialogo = dict(dialogo, inicio=pygame.time.get_ticks(), completo=False, elegida=0, cache=(None, []), caja=[])
    panel.modo = "dialogo_npc"
    panel.vista.narrador.decir(dialogo["texto"])


def _visibles(panel, d):
    if d["completo"]:
        return len(d["texto"])
    visibles = (pygame.time.get_ticks() - d["inicio"]) * LETRAS_POR_SEGUNDO // 1000
    if visibles >= len(d["texto"]):
        d["completo"] = True
    return min(visibles, len(d["texto"]))


def _lineas(panel, d):
    """Se vuelve a renderizar solo cuando aparece una letra nueva."""
    cantidad = _visibles(panel, d)
    if d["cache"][0] == cantidad:
        return d["cache"][1]
    lineas, restantes = [], cantidad
    for linea in envolver_texto(d["texto"], panel.pequena, TEXTO_ANCHO):
        if restantes <= 0:
            break
        lineas.append(panel.pequena.render(linea[:restantes], True, TINTA))
        restantes -= len(linea) + 1
    d["cache"] = (cantidad, lineas)
    return lineas


def dibujar(panel, superficie):
    d = panel.dialogo
    arte = panel.vista.arte_dialogo
    x, y = POSICION
    if arte.marco is not None:
        superficie.blit(arte.marco, POSICION)
    else:
        pygame.draw.rect(superficie, (241, 226, 190), (x, y + 60, ANCHO, ALTO - 70), border_radius=14)
    retrato = arte.retrato(d["personaje"], panel.vista.imagen_npc(d["personaje"]))
    if retrato is not None:
        superficie.blit(retrato, retrato.get_rect(center=(x + CENTRO_RETRATO[0], y + CENTRO_RETRATO[1])))
    nombre = panel.fuente.render(d["personaje"], True, TINTA)
    superficie.blit(nombre, (x + TEXTO_X, y + NOMBRE_Y))
    for indice, linea in enumerate(_lineas(panel, d)):
        superficie.blit(linea, (x + TEXTO_X, y + TEXTO_Y + indice * 22))
    d["caja"] = []
    for indice, respuesta in enumerate(d["respuestas"][:len(RESPUESTAS_Y)]):
        caja = pygame.Rect(x + RESPUESTAS_X, y + RESPUESTAS_Y[indice], RESPUESTA_ANCHO, RESPUESTA_ALTO)
        d["caja"].append(caja)
        if caja.collidepoint(panel.vista.mouse):
            d["elegida"] = indice
        color = RESALTADO if indice == d["elegida"] else TINTA
        render = panel.pequena.render(f"{indice + 1}. {respuesta}", True, color)
        superficie.blit(render, render.get_rect(midleft=(caja.x + 34, caja.centery)))


def _cerrar(panel, cliente, respuesta):
    d = panel.dialogo
    panel.dialogo = None
    panel.modo = None
    cliente.actuar("responder_npc", npc=d["npc"], respuesta=respuesta)


def manejar(panel, evento, posicion, cliente):
    d = panel.dialogo
    if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
        if not d["completo"]:
            d["completo"] = True
            return True
        for indice, caja in enumerate(d["caja"]):
            if caja.collidepoint(posicion):
                _cerrar(panel, cliente, d["respuestas"][indice])
                break
        return True
    if evento.type != pygame.KEYDOWN:
        return True
    if evento.key == pygame.K_ESCAPE:
        _cerrar(panel, cliente, None)
    elif evento.key in (pygame.K_e, pygame.K_SPACE):
        d["completo"] = True
    elif d["completo"]:
        cantidad = len(d["respuestas"])
        numero = evento.key - pygame.K_1
        if 0 <= numero < cantidad:
            _cerrar(panel, cliente, d["respuestas"][numero])
        elif evento.key in (pygame.K_UP, pygame.K_LEFT):
            d["elegida"] = (d["elegida"] - 1) % cantidad
        elif evento.key in (pygame.K_DOWN, pygame.K_RIGHT):
            d["elegida"] = (d["elegida"] + 1) % cantidad
        elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            _cerrar(panel, cliente, d["respuestas"][d["elegida"]])
    return True
