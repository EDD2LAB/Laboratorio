"""Libro compartido de La Copa: consulta y colocación de casos en el AVL."""
import pygame
import time


def dibujar(panel, superficie):
    estado = panel.caso.get("expediente") or {}
    pygame.draw.rect(superficie, (13, 35, 28), (20, 20, 920, 680), border_radius=14)
    pygame.draw.rect(superficie, (237, 185, 87), (20, 20, 920, 680), 2, border_radius=14)
    panel.texto_lineas(superficie, "EL LIBRO DE LOS CASOS", 50, 40, 850, panel.encabezado)
    panel.texto_lineas(superficie, "T: abrir o cerrar · Guarda lo que descubrieron entre todos.", 50, 78, 850, panel.pequena)
    nodos = []

    def recorrer(nodo, nivel=0):
        if not nodo:
            return
        recorrer(nodo["izquierda"], nivel + 1)
        nodos.append((nodo, nivel))
        recorrer(nodo["derecha"], nivel + 1)

    recorrer(estado.get("raiz"))
    posiciones = {n["caso"]["id"]: (65 + (i + .5) * 390 / max(1, len(nodos)), 170 + nivel * 100)
                  for i, (n, nivel) in enumerate(nodos)}
    for nodo, _ in nodos:
        x, y = posiciones[nodo["caso"]["id"]]
        for lado in ("izquierda", "derecha"):
            if nodo[lado]:
                pygame.draw.line(superficie, (135, 161, 130), (x, y), posiciones[nodo[lado]["caso"]["id"]], 3)
    for nodo, _ in nodos:
        caso = nodo["caso"]
        x, y = posiciones[caso["id"]]
        color = (237, 185, 87) if caso["id"] == estado.get("comparar_con") else (130, 222, 158)
        pygame.draw.circle(superficie, color, (int(x), int(y)), 28)
        etiqueta = panel.fuente.render(str(caso["gravedad"]), True, (13, 35, 28))
        superficie.blit(etiqueta, etiqueta.get_rect(center=(x, y)))
        rect = pygame.Rect(x - 32, y - 32, 64, 64)
        panel.nodos_expediente[caso["id"]] = rect
        panel.texto_lineas(superficie, str(caso["orden"] + 1), x - 5, y + 32, 30, panel.pequena)

    elegidos = {n["caso"]["id"]: n["caso"] for n, _ in nodos}
    seleccionado = elegidos.get(getattr(panel, "caso_expediente", None))
    pendiente = estado.get("pendiente")
    detalle = seleccionado or pendiente or (nodos[0][0]["caso"] if nodos else None)
    panel.texto_lineas(superficie, "Pulsa un círculo para leer el caso.", 50, 440, 400, panel.pequena)
    panel.texto_lineas(superficie, "El número grande indica la gravedad (1 a 5). El pequeño indica cuándo lo resolvieron.", 50, 475, 400, panel.pequena)
    if detalle:
        y = panel.texto_lineas(superficie, detalle["titulo"], 495, 130, 390)
        datos = detalle["datos"]
        y = panel.texto_lineas(superficie, datos["tipo"] + " · Gravedad " + str(detalle["gravedad"]), 495, y + 6, 390, panel.pequena)
        resultado = datos["resultado"]
        y = panel.texto_lineas(superficie, "Decisión: " + panel.caso.get("opciones", {}).get(resultado["opcion"], resultado["opcion"]), 495, y + 8, 390, panel.pequena)
        pruebas = datos.get("pruebas", [])
        indice = getattr(panel, "prueba_expediente", 0) % max(1, len(pruebas))
        if pruebas:
            prueba = pruebas[indice]
            y = panel.texto_lineas(superficie, f"Prueba {indice + 1}/{len(pruebas)}: " + prueba["titulo"], 495, y + 12, 390, panel.pequena)
            panel.texto_lineas(superficie, prueba["texto"], 495, y + 4, 390, panel.pequena)
            panel.boton(superficie, "expediente_prueba", "Otra prueba", 690, 440, 230)
        panel.texto_lineas(superficie, "Leyes y sanciones: por confirmar con el profesor.", 495, 480, 390, panel.pequena)
    else:
        panel.texto_lineas(superficie, "Resuelvan el primer caso. Aquí guardaremos sus descubrimientos.", 495, 150, 390)
    if pendiente:
        titulo = "Por guardar: " + pendiente["titulo"] + " (gravedad " + str(pendiente["gravedad"]) + ")"
        panel.texto_lineas(superficie, titulo, 50, 548, 850, panel.pequena)
        panel.texto_lineas(superficie, "Menor: izquierda. Mayor: derecha. Si son iguales, el más nuevo va a la derecha.", 50, 576, 850, panel.pequena)
        panel.boton(superficie, "expediente:izquierda", "Izquierda", 210, 635, 230)
        panel.boton(superficie, "expediente:derecha", "Derecha", 490, 635, 230)
    panel.boton(superficie, "expediente_cerrar", "Cerrar · T", 790, 635, 230)
    if estado.get("rotaciones") and not pendiente:
        panel.texto_lineas(superficie, "¡El árbol se equilibró para facilitar la búsqueda!", 50, 555, 800, panel.pequena)
    if panel.toast:
        panel.texto_lineas(superficie, panel.toast if time.monotonic() < panel.toast_hasta else "", 50, 102, 850, panel.pequena)
