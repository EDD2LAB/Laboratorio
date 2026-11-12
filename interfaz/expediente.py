"""Libro compartido: árbol legible, inserción animada y fichas con desplazamiento."""
import pygame
import time

from interfaz.arbol_expediente import (AnimacionAVL, RADIO, aprendizaje,
                                       dimension_caso, etiqueta_decision)
from nucleo.recursos import envolver_texto

ORO = (237, 185, 87)
CREMA = (255, 243, 210)
VERDE = (130, 222, 158)
DETALLE = pygame.Rect(495, 130, 390, 320)
ERAS = {"la_copa": "La Copa", "presente": "Distrito Conecta", "futuro": "Ciudad Núcleo"}
COLORES_ERAS = {"la_copa": VERDE, "presente": (130, 207, 237), "futuro": (203, 175, 246)}


def _casos(nodo):
    if not nodo:
        return {}
    return {**_casos(nodo["izquierda"]), nodo["caso"]["id"]: nodo["caso"], **_casos(nodo["derecha"])}


def lineas_detalle(panel, caso):
    datos = caso["datos"]
    resultado = datos["resultado"]
    pruebas = datos.get("pruebas", [])
    ver_pruebas = bool(pruebas and getattr(panel, "expediente_ver_pruebas", False))
    partes = [(caso["titulo"], ORO),
              (ERAS[dimension_caso(caso)] + " · Caso " + str(caso["orden"] + 1), VERDE),
              (datos["tipo"] + " · Gravedad " + str(caso["gravedad"]), CREMA),
              ("Decisión del equipo: " + etiqueta_decision(caso, panel.caso), CREMA)]
    if caso.get("detalle_remoto"):
        return [(caso["titulo"], ORO), ("Cargando la ficha completa con sus pruebas y referencias…", CREMA)], False
    if ver_pruebas:
        indice = getattr(panel, "prueba_expediente", 0) % len(pruebas)
        prueba = pruebas[indice]
        partes += [(f"Prueba {indice + 1}/{len(pruebas)}: " + prueba["titulo"], ORO), (prueba["texto"], CREMA)]
    else:
        if resultado.get("texto"):
            partes.append(("Qué ocurrió: " + resultado["texto"], CREMA))
        partes.append(("Para recordar: " + aprendizaje(caso), VERDE))
        if datos.get("conducta"):
            partes.append(("Conducta del caso: " + datos["conducta"], CREMA))
        for clave, titulo in (("ley", "Referencia del proyecto"), ("sancion", "Sanción registrada"), ("nota", "Nota")):
            if datos.get(clave):
                partes.append((titulo + ": " + datos[clave], CREMA))
        if datos.get("ley"):
            partes.append(("Contenido legal pendiente de revisión del profesor.", ORO))
    lineas = []
    for texto, color in partes:
        lineas += [(linea, color) for linea in envolver_texto(texto, panel.pequena, DETALLE.width - 12)]
        lineas.append(("", color))
    return lineas, ver_pruebas


def desplazar(panel, pasos):
    limite = getattr(panel, "expediente_scroll_max", 0)
    panel.expediente_scroll = max(0, min(limite, getattr(panel, "expediente_scroll", 0) + pasos))


def detalle_actual(panel, estado, casos=None):
    casos = casos if casos is not None else _casos(estado.get("raiz"))
    detalle = casos.get(getattr(panel, "caso_expediente", None)) or estado.get("pendiente") or next(iter(casos.values()), None)
    if detalle and detalle.get("detalle_remoto"):
        cache = getattr(panel, "expediente_fichas", {}).get(detalle["id"])
        if cache and cache["datos"]["resultado"].get("evento_id") == detalle["datos"]["resultado"].get("evento_id"):
            return cache
    return detalle


def solicitar_detalle(panel, cliente):
    if panel.modo != "expediente":
        return
    detalle = detalle_actual(panel, panel.caso.get("expediente") or {})
    if detalle and detalle.get("detalle_remoto"):
        clave = (detalle["id"], detalle["datos"]["resultado"].get("evento_id"))
        if not hasattr(panel, "expediente_solicitadas"):
            panel.expediente_solicitadas = set()
        if clave not in panel.expediente_solicitadas:
            panel.expediente_solicitadas.add(clave)
            cliente.actuar("expediente_leer", caso=detalle["id"])


def dibujar(panel, superficie):
    estado = panel.caso.get("expediente") or {}
    pygame.draw.rect(superficie, (13, 35, 28), (20, 20, 920, 680), border_radius=14)
    pygame.draw.rect(superficie, ORO, (20, 20, 920, 680), 2, border_radius=14)
    panel.texto_lineas(superficie, "EL LIBRO DE LOS CASOS", 50, 40, 850, panel.encabezado)
    panel.texto_lineas(superficie, "T: abrir o cerrar · Ocho casos, tres eras, un libro del equipo.", 50, 78, 850, panel.pequena)
    for i, (era, nombre) in enumerate((("la_copa", "La Copa"), ("presente", "Conecta"), ("futuro", "Núcleo"))):
        x = 65 + i * 130
        pygame.draw.circle(superficie, COLORES_ERAS[era], (x, 131), 5)
        superficie.blit(panel.pequena.render(nombre, True, COLORES_ERAS[era]), (x + 12, 123))
    casos = _casos(estado.get("raiz"))
    if not hasattr(panel, "animacion_expediente"):
        panel.animacion_expediente = AnimacionAVL()
    forma, puntos, aviso, animando = panel.animacion_expediente.actualizar(
        estado, pygame.time.get_ticks(), getattr(panel, "expediente_repetir", False))
    panel.expediente_repetir = False
    panel.nodos_expediente = {}

    def dibujar_ramas(nodo):
        if nodo is None:
            return
        for lado in ("i", "d"):
            hijo = nodo[lado]
            if hijo:
                pygame.draw.line(superficie, (135, 161, 130), puntos[nodo["id"]], puntos[hijo["id"]], 2)
                dibujar_ramas(hijo)
    dibujar_ramas(forma)
    for clave, (x, y) in puntos.items():
        caso = casos.get(clave)
        if not caso:
            continue
        color = ORO if clave == estado.get("comparar_con") else COLORES_ERAS[dimension_caso(caso)]
        pygame.draw.circle(superficie, color, (round(x), round(y)), RADIO)
        if clave == getattr(panel, "caso_expediente", None):
            pygame.draw.circle(superficie, CREMA, (round(x), round(y)), RADIO + 4, 2)
        etiqueta = panel.fuente.render(str(caso["gravedad"]), True, (13, 35, 28))
        superficie.blit(etiqueta, etiqueta.get_rect(center=(round(x), round(y))))
        orden = panel.pequena.render(str(caso["orden"] + 1), True, CREMA)
        superficie.blit(orden, orden.get_rect(midtop=(round(x), round(y + 22))))
        if not animando:
            panel.nodos_expediente[clave] = pygame.Rect(round(x) - 22, round(y) - 22, 44, 44)
    panel.texto_lineas(superficie, "Pulsa un círculo para leer su caso.", 50, 425, 400, panel.pequena)
    panel.texto_lineas(superficie, "Grande: gravedad (1 a 9). Debajo: orden del caso. Izquierda: menor; derecha: mayor.", 50, 458, 400, panel.pequena)
    if aviso:
        panel.texto_lineas(superficie, aviso, 50, 515, 400, panel.pequena, ORO)
    elif estado.get("animacion"):
        panel.boton(superficie, "expediente_repetir", "Ver cómo se ordenó", 245, 525, 330)
    pendiente = estado.get("pendiente")
    detalle = detalle_actual(panel, estado, casos)
    if detalle:
        lineas, ver_pruebas = lineas_detalle(panel, detalle)
        clave = (detalle["id"], ver_pruebas, getattr(panel, "prueba_expediente", 0))
        if getattr(panel, "expediente_lectura", None) != clave:
            panel.expediente_scroll = 0
            panel.expediente_lectura = clave
        alto = panel.pequena.get_linesize() + 3
        visibles = max(1, DETALLE.height // alto)
        panel.expediente_scroll_max = max(0, len(lineas) - visibles)
        desplazar(panel, 0)
        inicio = getattr(panel, "expediente_scroll", 0)
        clip = superficie.get_clip()
        superficie.set_clip(DETALLE.clip(clip))
        for indice, (texto, color) in enumerate(lineas[inicio:inicio + visibles]):
            imagen = panel.pequena.render(texto, True, color)
            superficie.blit(imagen, (DETALLE.x, DETALLE.y + indice * alto))
        superficie.set_clip(clip)
        if panel.expediente_scroll_max:
            barra = pygame.Rect(892, DETALLE.y, 6, DETALLE.height)
            pygame.draw.rect(superficie, (49, 73, 63), barra, border_radius=3)
            alto_marca = max(20, round(barra.height * visibles / len(lineas)))
            marca_y = barra.y + round((barra.height - alto_marca) * inicio / panel.expediente_scroll_max)
            pygame.draw.rect(superficie, ORO, (barra.x, marca_y, barra.width, alto_marca), border_radius=3)
            panel.boton(superficie, "expediente_subir", "Arriba", 797, 480, 76)
            panel.boton(superficie, "expediente_bajar", "Abajo", 881, 480, 76)
        if ver_pruebas:
            panel.boton(superficie, "expediente_prueba", "Otra prueba", 625, 480, 230)
        if detalle["datos"].get("pruebas"):
            panel.boton(superficie, "expediente_vista", "Ver el resumen" if ver_pruebas else "Ver las pruebas", 690, 525, 230)
    else:
        panel.texto_lineas(superficie, "Resuelvan el primer caso. Aquí guardaremos lo que descubran.", 495, 150, 390)
    if pendiente:
        panel.texto_lineas(superficie, "Por guardar: " + pendiente["titulo"] + " · gravedad " + str(pendiente["gravedad"]), 50, 560, 850, panel.pequena)
        panel.texto_lineas(superficie, "Compara con el círculo dorado. Si empatan, el más nuevo va a la derecha.", 50, 594, 850, panel.pequena)
        panel.boton(superficie, "expediente:izquierda", "Izquierda", 210, 655, 230, activo=not animando)
        panel.boton(superficie, "expediente:derecha", "Derecha", 490, 655, 230, activo=not animando)
    panel.boton(superficie, "expediente_cerrar", "Cerrar · T", 790, 655, 230)
    if panel.toast and time.monotonic() < panel.toast_hasta:
        panel.texto_lineas(superficie, panel.toast, 50, 105, 850, panel.pequena)
