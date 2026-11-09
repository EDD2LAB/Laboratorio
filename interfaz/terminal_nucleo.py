"""Terminales de Ciudad Núcleo: el cliente solo señala, el servidor valida."""
import pygame

from interfaz.analisis_manipulado import CLARO, CORAL, CREMA, FRANJA, MESA_FOTOS, ORO, OSCURO, TINTA, _zona

AZUL_NOCHE = (12, 24, 48)
CIAN = (90, 230, 230)
PANEL = pygame.Rect(60, 60, 840, 590)
AREA_GRAFO = pygame.Rect(120, 170, 720, 400)
BOTON_ARISTA = (72, 44)
FILA_REGISTRO = 158


def _componente(red):
    """Sectores unidos a la Plaza por conexiones abiertas (solo para colorear)."""
    vecinos = {}
    for a, b in red["abiertas"]:
        vecinos.setdefault(a, set()).add(b)
        vecinos.setdefault(b, set()).add(a)
    vistos, pendientes = {"plaza"}, ["plaza"]
    while pendientes:
        for vecino in vecinos.get(pendientes.pop(), ()):
            if vecino not in vistos:
                vistos.add(vecino)
                pendientes.append(vecino)
    return vistos


def _dibujar_conexiones(panel, superficie, contexto, arte):
    red = contexto["red"]
    pygame.draw.rect(superficie, AZUL_NOCHE, PANEL, border_radius=14)
    pygame.draw.rect(superficie, CIAN, PANEL, 3, border_radius=14)
    panel.texto_lineas(superficie, "RESTAURAR CONEXIONES", 90, 80, 780, panel.encabezado, CIAN)
    panel.texto_lineas(superficie, "NÚCLEO aisló sectores de la ciudad. Elige la conexión bloqueada que devuelve la zona roja a la red.",
                       90, 116, 780, panel.pequena, CLARO)
    punto = {s[0]: (round(AREA_GRAFO.x + s[2] * AREA_GRAFO.w), round(AREA_GRAFO.y + s[3] * AREA_GRAFO.h)) for s in red["sectores"]}
    for a, b in red["abiertas"]:
        pygame.draw.line(superficie, CIAN, punto[a], punto[b], 4)
    ui = arte.ui
    for indice, (a, b) in enumerate(red["bloqueadas"]):
        pygame.draw.line(superficie, CORAL, punto[a], punto[b], 3)
        centro = ((punto[a][0] + punto[b][0]) // 2, (punto[a][1] + punto[b][1]) // 2)
        rect = pygame.Rect((0, 0), BOTON_ARISTA)
        rect.center = centro
        encima = _zona(panel, ui, f"terminal:arista:{indice}", rect).hover
        pygame.draw.rect(superficie, ORO if encima else OSCURO, rect, border_radius=8)
        pygame.draw.rect(superficie, CORAL, rect, 2, border_radius=8)
        texto = panel.pequena.render("Reabrir", True, TINTA if encima else CLARO)
        superficie.blit(texto, texto.get_rect(center=centro))
    unidos = _componente(red)
    for sector_id, nombre, *_ in red["sectores"]:
        pygame.draw.circle(superficie, CIAN if sector_id in unidos else CORAL, punto[sector_id], 20)
        texto = panel.pequena.render(nombre, True, CLARO)
        superficie.blit(texto, texto.get_rect(midtop=(punto[sector_id][0], punto[sector_id][1] + 24)))


def _dibujar_archivos(panel, superficie, contexto, arte):
    if arte.analisis is not None:
        superficie.blit(arte.analisis, (0, 0))
    pygame.draw.rect(superficie, CREMA, MESA_FOTOS, border_radius=12)
    pygame.draw.rect(superficie, OSCURO, MESA_FOTOS, 3, border_radius=12)
    panel.texto_lineas(superficie, "Un registro fue alterado. Mira quién lo firma y márcalo.", 58, 52, 545, panel.fuente, TINTA)
    for indice, registro in enumerate(contexto["registros"]):
        fila = pygame.Rect(58, 106 + indice * FILA_REGISTRO, 542, FILA_REGISTRO - 14)
        encima = _zona(panel, arte.ui, "terminal:registro:" + registro["id"], fila).hover
        pygame.draw.rect(superficie, (255, 249, 236), fila, border_radius=10)
        pygame.draw.rect(superficie, ORO if encima else OSCURO, fila, 3 if encima else 2, border_radius=10)
        y = panel.texto_lineas(superficie, registro["titulo"], fila.x + 16, fila.y + 12, fila.w - 32, panel.fuente, TINTA)
        y = panel.texto_lineas(superficie, registro["texto"], fila.x + 16, y + 4, fila.w - 32, panel.pequena, TINTA)
        panel.texto_lineas(superficie, registro["firma"], fila.x + 16, y + 6, fila.w - 32, panel.pequena, (120, 70, 150))
    pygame.draw.rect(superficie, (19, 39, 49), FRANJA, border_radius=8)
    pygame.draw.rect(superficie, CIAN, FRANJA, 2, border_radius=8)
    panel.texto_lineas(superficie, "Una orden solo vale si la firma quien tiene autoridad para darla.",
                       FRANJA.x + 14, FRANJA.y + 14, 620, panel.pequena, CIAN)


PANTALLAS = {"conexiones": _dibujar_conexiones, "archivos": _dibujar_archivos}


def dibujar(panel, superficie, contexto, arte):
    if panel.terminal in PANTALLAS and contexto.get("red"):
        PANTALLAS[panel.terminal](panel, superficie, contexto, arte)


def accion(panel, clave, cliente):
    _, tipo, valor = clave.split(":", 2)
    if tipo == "arista":
        cliente.actuar("futuro_resolver", terminal="conexiones", arista=int(valor))
    else:
        cliente.actuar("futuro_resolver", terminal="archivos", registro=valor)
