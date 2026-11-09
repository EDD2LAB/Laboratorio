"""Informe final del expediente: recorrido inorden, línea de tiempo y reporte."""
from datetime import datetime

import pygame

from interfaz.arte import NUEVOS, icono
from interfaz.boton import Boton
from nucleo.recursos import cargar_imagen
from nucleo.rutas import RAIZ

SEGUNDOS_POR_NODO = .6
CIERRE = "Lo que empezó como un rumor cambió a toda una comunidad."
ORO = (237, 185, 87)
CREMA = (255, 243, 210)
TINTA = (61, 37, 25)
VERDE = (130, 222, 158)
GRIS = (120, 110, 96)
AREA_ARBOL = pygame.Rect(30, 90, 400, 230)
EJE_TIEMPO = pygame.Rect(90, 372, 330, 4)
PERGAMINO = pygame.Rect(440, 56, 500, 610)
TEXTO_REPORTE = pygame.Rect(492, 108, 396, 510)
SELLO = (96, 96)
CARPETA = RAIZ / "informes"


class ArteInforme:
    def __init__(self):
        self.pergamino = cargar_imagen(NUEVOS + "pergamino_informe.png", PERGAMINO.size)
        self.sello = icono(NUEVOS + "sello_consejo.png", SELLO)
        self.tiempo = icono(NUEVOS + "icono_tiempo.png", (46, 46))
        self.ley = icono(NUEVOS + "icono_ley.png", (16, 16))
        self.sancion = icono(NUEVOS + "icono_sancion.png", (16, 16))


def lineas_reporte(fila):
    """Líneas de un caso; norma y pena solo aparecen si existen, sin dejar huecos."""
    decision = fila["decision"] if fila["resuelto"] else "sin resolver"
    lineas = [("titulo", f"{fila['titulo']} ({fila['era']})"),
              ("datos", f"{fila['tipo']} · Gravedad {fila['gravedad']} · {decision}")]
    if fila.get("norma"):
        lineas.append(("ley", fila["norma"]))
    if fila.get("pena"):
        lineas.append(("sancion", fila["pena"]))
    return lineas


def exportar(datos, carpeta=None, ahora=None):
    """Escribe el informe en informes/informe_<fecha>.txt y devuelve su ruta."""
    carpeta = carpeta or CARPETA
    carpeta.mkdir(parents=True, exist_ok=True)
    ahora = ahora or datetime.now()
    ruta = carpeta / f"informe_{ahora:%Y-%m-%d_%H%M%S}.txt"
    lineas = ["INFORME FINAL DEL EXPEDIENTE - TIMELESS GLITCH", f"Fecha: {ahora:%Y-%m-%d %H:%M}", ""]
    for fila in datos["casos"]:
        for tipo, texto in lineas_reporte(fila):
            prefijo = {"titulo": "", "datos": "   ", "ley": "   Norma: ", "sancion": "   Pena: "}[tipo]
            lineas.append(prefijo + texto)
        lineas.append("")
    lineas.append(CIERRE)
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return ruta


def posiciones_arbol(raiz):
    """Nodo -> (x, y) dentro del área: inorden en x, profundidad en y."""
    orden = []

    def recorrer(nodo, nivel):
        if nodo:
            recorrer(nodo["izquierda"], nivel + 1)
            orden.append((nodo, nivel))
            recorrer(nodo["derecha"], nivel + 1)

    recorrer(raiz, 0)
    return orden, {n["caso"]["id"]: (round(AREA_ARBOL.x + (i + .5) * AREA_ARBOL.w / max(1, len(orden))), AREA_ARBOL.y + 30 + nivel * 62)
                   for i, (n, nivel) in enumerate(orden)}


def nodos_visitados(transcurrido, total):
    return min(total, int(transcurrido / SEGUNDOS_POR_NODO) + 1) if total else 0


def _dibujar_arbol(panel, superficie, datos, transcurrido):
    orden, puntos = posiciones_arbol(datos["raiz"])
    for nodo, _ in orden:
        for lado in ("izquierda", "derecha"):
            if nodo[lado]:
                pygame.draw.line(superficie, GRIS, puntos[nodo["caso"]["id"]], puntos[nodo[lado]["caso"]["id"]], 3)
    visitados = nodos_visitados(transcurrido, len(orden))
    for indice, (nodo, _) in enumerate(orden):
        punto = puntos[nodo["caso"]["id"]]
        pygame.draw.circle(superficie, ORO if indice == visitados - 1 else VERDE if indice < visitados else GRIS, punto, 22)
        texto = panel.fuente.render(str(nodo["caso"]["gravedad"]), True, (13, 35, 28))
        superficie.blit(texto, texto.get_rect(center=punto))


def _dibujar_tiempo(panel, superficie, datos, arte):
    if arte.tiempo is not None:
        superficie.blit(arte.tiempo, arte.tiempo.get_rect(center=(56, EJE_TIEMPO.centery)))
    pygame.draw.rect(superficie, GRIS, EJE_TIEMPO)
    resueltos = sorted((f for f in datos["casos"] if f["resuelto"]), key=lambda f: f["orden"])
    for i, fila in enumerate(resueltos):
        x = EJE_TIEMPO.x + round((i + .5) * EJE_TIEMPO.w / len(resueltos))
        pygame.draw.circle(superficie, VERDE if fila["correcto"] else ORO, (x, EJE_TIEMPO.centery), 8)
        numero = panel.pequena.render(str(i + 1), True, CREMA)
        superficie.blit(numero, numero.get_rect(midtop=(x, EJE_TIEMPO.centery + 10)))


def _dibujar_reporte(panel, superficie, datos, arte):
    superficie.blit(arte.pergamino, PERGAMINO)
    y = TEXTO_REPORTE.y
    for fila in datos["casos"]:
        for tipo, texto in lineas_reporte(fila):
            x = TEXTO_REPORTE.x
            imagen = {"ley": arte.ley, "sancion": arte.sancion}.get(tipo)
            if imagen is not None:
                superficie.blit(imagen, (x, y + 1))
                x += 20
            color = GRIS if not fila["resuelto"] else TINTA
            fuente = panel.pequena
            y = panel.texto_lineas(superficie, texto, x, y, TEXTO_REPORTE.right - x, fuente, color)
        y += 5


def dibujar(panel, superficie):
    if panel.arte_informe is None:
        panel.arte_informe = ArteInforme()
    arte, datos = panel.arte_informe, panel.informe
    superficie.fill((12, 24, 22))
    panel.texto_lineas(superficie, "INFORME FINAL DEL EXPEDIENTE", 30, 28, 400, panel.encabezado, ORO)
    panel.texto_lineas(superficie, "Recorrido del árbol: de menor a mayor gravedad.", 30, 66, 400, panel.pequena, CREMA)
    transcurrido = (pygame.time.get_ticks() - panel.informe_inicio) / 1000
    _dibujar_arbol(panel, superficie, datos, transcurrido)
    _dibujar_tiempo(panel, superficie, datos, arte)
    _dibujar_reporte(panel, superficie, datos, arte)
    if nodos_visitados(transcurrido, datos["total_arbol"]) >= datos["total_arbol"] and transcurrido >= datos["total_arbol"] * SEGUNDOS_POR_NODO:
        if arte.sello is not None:
            superficie.blit(arte.sello, arte.sello.get_rect(center=(90, 490)))
        panel.texto_lineas(superficie, CIERRE, 150, 462, 270, panel.fuente, ORO)
    if panel.informe_exportado:
        panel.texto_lineas(superficie, "Guardado en: " + panel.informe_exportado, 30, 570, 400, panel.pequena, VERDE)
    for clave, texto, centro in (("informe_exportar", "Exportar a .txt", (130, 660)), ("informe_cerrar", "Cerrar", (330, 660))):
        boton = Boton(texto, centro=centro, fuente=panel.fuente, tamano=(180, 44))
        boton.dibujar(superficie, panel.vista.mouse)
        panel.botones[clave] = boton
