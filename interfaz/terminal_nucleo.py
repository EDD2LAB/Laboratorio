"""Terminales de Ciudad Núcleo: el cliente solo señala, el servidor valida."""
import pygame

from interfaz.analisis_manipulado import CLARO, CORAL, CREMA, FRANJA, MESA_FOTOS, ORO, OSCURO, TINTA, _zona
from interfaz.boton import Boton

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
        resaltada = contexto.get("registro_resaltado") == registro["id"]  # Lupa de Memoria
        if resaltada:
            pygame.draw.rect(superficie, ORO, (fila.x + 10, y + 3, fila.w - 20, 26), 2, border_radius=6)
        panel.texto_lineas(superficie, registro["firma"], fila.x + 16, y + 6, fila.w - 32, panel.pequena, (120, 70, 150))
    pygame.draw.rect(superficie, (19, 39, 49), FRANJA, border_radius=8)
    pygame.draw.rect(superficie, CIAN, FRANJA, 2, border_radius=8)
    panel.texto_lineas(superficie, "Una orden solo vale si la firma quien tiene autoridad para darla.",
                       FRANJA.x + 14, FRANJA.y + 14, 620, panel.pequena, CIAN)


def _dibujar_cuentas(panel, superficie, contexto, arte):
    pygame.draw.rect(superficie, AZUL_NOCHE, PANEL, border_radius=14)
    pygame.draw.rect(superficie, CIAN, PANEL, 3, border_radius=14)
    panel.texto_lineas(superficie, "CUENTAS QUE ATACAN AL CIUDADANO", 90, 76, 780, panel.encabezado, CIAN)
    panel.texto_lineas(superficie, "Tres son automáticas de NÚCLEO. Márcalas: fíjate en la hora, la frase y la fecha de creación.",
                       90, 110, 780, panel.pequena, CLARO)
    for indice, cuenta in enumerate(contexto["cuentas"]):
        tarjeta = pygame.Rect(84 + indice % 2 * 400, 142 + indice // 2 * 212, 392, 202)
        marcada, descartada = cuenta["id"] in panel.cuentas_marcadas, cuenta["id"] == contexto.get("cuenta_descartada")
        encima = not descartada and _zona(panel, arte.ui, "terminal:cuenta:" + cuenta["id"], tarjeta).hover
        pygame.draw.rect(superficie, (28, 44, 74) if not descartada else (40, 46, 56), tarjeta, border_radius=10)
        pygame.draw.rect(superficie, CORAL if marcada else ORO if encima else CIAN, tarjeta, 3 if marcada or encima else 1, border_radius=10)
        if arte.avatares:
            superficie.blit(arte.avatares[cuenta["avatar"] % len(arte.avatares)], (tarjeta.x + 12, tarjeta.y + 12))
        panel.texto_lineas(superficie, cuenta["nombre"], tarjeta.x + 54, tarjeta.y + 10, tarjeta.w - 64, panel.fuente, CLARO)
        panel.texto_lineas(superficie, cuenta["creada"], tarjeta.x + 54, tarjeta.y + 34, tarjeta.w - 64, panel.pequena, CIAN)
        y = tarjeta.y + 66
        for hora, texto in cuenta["publicaciones"]:
            y = panel.texto_lineas(superficie, f"{hora}  {texto}", tarjeta.x + 14, y, tarjeta.w - 28, panel.pequena, CLARO) + 4
        if descartada:
            panel.texto_lineas(superficie, "Persona real: descartada por la Voz Comunitaria", tarjeta.x + 14, tarjeta.bottom - 26, tarjeta.w - 28, panel.pequena, ORO)
    boton = Boton("Confirmar marcas", centro=(480, 624), fuente=panel.fuente, tamano=(260, 40))
    boton.dibujar(superficie, panel.vista.mouse)
    panel.botones["terminal:confirmar:cuentas"] = boton


PANTALLAS = {"conexiones": _dibujar_conexiones, "archivos": _dibujar_archivos, "cuentas": _dibujar_cuentas}


def dibujar(panel, superficie, contexto, arte):
    if panel.terminal in PANTALLAS and contexto.get("red"):
        PANTALLAS[panel.terminal](panel, superficie, contexto, arte)


def accion(panel, clave, cliente):
    _, tipo, valor = clave.split(":", 2)
    if tipo == "arista":
        cliente.actuar("futuro_resolver", terminal="conexiones", arista=int(valor))
    elif tipo == "cuenta":
        panel.cuentas_marcadas ^= {valor}
    elif tipo == "confirmar":
        cliente.actuar("futuro_resolver", terminal="cuentas", cuentas=sorted(panel.cuentas_marcadas))
    else:
        cliente.actuar("futuro_resolver", terminal="archivos", registro=valor)
