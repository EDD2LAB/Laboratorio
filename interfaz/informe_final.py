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
TEXTO_REPORTE = pygame.Rect(497, 168, 369, 386)  # solo la parte lisa del pergamino
PISTA_BARRA = pygame.Rect(874, 168, 10, 386)
ZONA_BARRA = PISTA_BARRA.inflate(14, 0)  # más ancha que la barra para agarrarla sin puntería
COLOR_PISTA = (205, 170, 125)
MINIMO_PULGAR = 28
PASO_RUEDA = 40
PASO_TECLA = 24
SELLO = (96, 96)
CARPETA = RAIZ / "informes"


class ArteInforme:
    def __init__(self):
        self.pergamino = cargar_imagen(NUEVOS + "pergamino_informe.png", PERGAMINO.size)
        self.sello = icono(NUEVOS + "sello_consejo.png", SELLO)
        self.tiempo = icono(NUEVOS + "icono_tiempo.png", (46, 46))
        self.ley = icono(NUEVOS + "icono_ley.png", (16, 16))
        self.sancion = icono(NUEVOS + "icono_sancion.png", (16, 16))
        self.reporte = None
        self.reporte_de = None  # informe del que salió ``reporte``


def lineas_reporte(fila, corta=False):
    """Líneas de un caso; norma y pena solo aparecen si existen, sin dejar huecos."""
    decision = fila.get("decision_corta" if corta else "decision") if fila["resuelto"] else "sin resolver"
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
    final = datos.get("final_cooperativo") or {}
    if final.get("fase") == "victoria":
        lineas.extend(["FINAL COOPERATIVO: CIUDAD RECUPERADA", "Los cuatro roles devolvieron la supervisión de NÚCLEO a las personas.", ""])
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


def _contenido_reporte(panel, datos, arte):
    """Todo el texto del informe en una imagen, renderizada una sola vez."""
    if arte.reporte_de is not datos:
        lienzo = pygame.Surface((TEXTO_REPORTE.w, 4000), pygame.SRCALPHA)
        y = 0
        for fila in datos["casos"]:
            for tipo, texto in lineas_reporte(fila, corta=True):
                x = 0
                imagen = {"ley": arte.ley, "sancion": arte.sancion}.get(tipo)
                if imagen is not None:
                    lienzo.blit(imagen, (x, y + 1))
                    x += 20
                color = GRIS if not fila["resuelto"] else TINTA
                y = panel.texto_lineas(lienzo, texto, x, y, TEXTO_REPORTE.w - x, panel.pequena, color)
            y += 2
        arte.reporte, arte.reporte_de = lienzo.subsurface((0, 0, TEXTO_REPORTE.w, max(1, y))).copy(), datos
    return arte.reporte


def maximo_desplazamiento(panel):
    return max(0, panel.informe_alto - TEXTO_REPORTE.h)


def _desplazar_a(panel, valor):
    panel.informe_scroll = max(0, min(maximo_desplazamiento(panel), valor))


def rect_pulgar(panel):
    """La parte de la barra que se arrastra; None si todo el informe ya cabe."""
    maximo = maximo_desplazamiento(panel)
    if not maximo:
        return None
    alto = max(MINIMO_PULGAR, round(PISTA_BARRA.h * TEXTO_REPORTE.h / panel.informe_alto))
    y = PISTA_BARRA.y + round((PISTA_BARRA.h - alto) * panel.informe_scroll / maximo)
    return pygame.Rect(PISTA_BARRA.x, y, PISTA_BARRA.w, alto)


def _colocar_pulgar(panel, y, alto):
    recorrido = PISTA_BARRA.h - alto
    _desplazar_a(panel, (y - PISTA_BARRA.y) / recorrido * maximo_desplazamiento(panel))


def manejar_desplazamiento(panel, evento, posicion):
    """Rueda, flechas y arrastre de la barrita. True si el evento era para el informe."""
    if evento.type == pygame.MOUSEWHEEL:
        _desplazar_a(panel, panel.informe_scroll - evento.y * PASO_RUEDA)
        return True
    if evento.type == pygame.KEYDOWN:
        destino = {pygame.K_UP: panel.informe_scroll - PASO_TECLA, pygame.K_DOWN: panel.informe_scroll + PASO_TECLA,
                   pygame.K_PAGEUP: panel.informe_scroll - TEXTO_REPORTE.h, pygame.K_PAGEDOWN: panel.informe_scroll + TEXTO_REPORTE.h,
                   pygame.K_HOME: 0, pygame.K_END: maximo_desplazamiento(panel)}.get(evento.key)
        if destino is None:
            return False
        _desplazar_a(panel, destino)
        return True
    pulgar = rect_pulgar(panel)
    if pulgar is None:
        return False
    if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 and ZONA_BARRA.collidepoint(posicion):
        panel.informe_arrastre = posicion[1] - pulgar.y if pulgar.collidepoint(PISTA_BARRA.centerx, posicion[1]) else pulgar.h // 2
        _colocar_pulgar(panel, posicion[1] - panel.informe_arrastre, pulgar.h)
        return True
    if panel.informe_arrastre is None:
        return False
    if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
        panel.informe_arrastre = None
        return True
    if evento.type == pygame.MOUSEMOTION:
        if evento.buttons[0]:
            _colocar_pulgar(panel, posicion[1] - panel.informe_arrastre, pulgar.h)
        else:  # se soltó fuera de la ventana
            panel.informe_arrastre = None
        return True
    return False


def _dibujar_reporte(panel, superficie, datos, arte):
    superficie.blit(arte.pergamino, PERGAMINO)
    contenido = _contenido_reporte(panel, datos, arte)
    panel.informe_alto = contenido.get_height()
    _desplazar_a(panel, panel.informe_scroll)
    superficie.blit(contenido, TEXTO_REPORTE.topleft, (0, round(panel.informe_scroll), TEXTO_REPORTE.w, TEXTO_REPORTE.h))
    pulgar = rect_pulgar(panel)
    if pulgar is not None:
        pygame.draw.rect(superficie, COLOR_PISTA, PISTA_BARRA, border_radius=5)
        pygame.draw.rect(superficie, TINTA, pulgar, border_radius=5)


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
