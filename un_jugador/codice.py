"""Códice y tutorial de cada dimensión."""

import pygame
from logica.dimensiones import DIMENSION_LA_COPA
from logica.dimensiones import DIMENSION_PRESENTE
from nucleo.config import CONTINUIDAD_PERSONAJES, CREMA, ORO, PAGINAS_CODICE
from nucleo.recursos import envolver_texto, superficie_con_alpha
from un_jugador.dibujo_mapa import dibujar_mapa
from un_jugador.hud import instrucciones_dimension, rectangulos_selector_mision


def construir_contenido_codice(estado, mundo, pagina, conversaciones_vistas=()):
    dimension = estado.dimension_actual
    if pagina == 0:
        lineas = ["MISIONES ACTIVAS"]
        if dimension == DIMENSION_LA_COPA:
            principal = (
                "completada"
                if estado.juego_terminado()
                else f"en progreso ({estado.tablillas_resueltas} tablillas resueltas)"
            )
            lineas.append(
                f"Principal — Historias de La Copa: resuelve las tablillas con testimonios antes de decidir. Estado: {principal}."
            )
            reparacion = mundo.get("reparacion_puentes")
            if reparacion is None:
                lineas.append("Secundaria — Reconstruir el Puente Norte: reparación no disponible en esta zona.")
            elif reparacion.estado == "REPAIRED":
                lineas.append("Secundaria — Reconstruir el Puente Norte: completada; el paso está abierto.")
            elif reparacion.estado == "REPAIR_ANIMATION":
                lineas.append("Secundaria — Reconstruir el Puente Norte: reparación en curso.")
            elif reparacion.estado == "REPAIR_MINIGAME":
                lineas.append(
                    "Secundaria — Reconstruir el Puente Norte: acierta "
                    f"{reparacion.progreso}/3 veces en el minijuego."
                )
            else:
                materiales = {
                    "tablas": "tablas",
                    "cuerda": "cuerda",
                    "herramientas": "herramientas",
                }
                recogidos = reparacion.materiales_recogidos
                faltantes = [
                    nombre for clave, nombre in materiales.items()
                    if clave not in recogidos
                ]
                estado_mision = (
                    "materiales reunidos; ve al puente"
                    if not faltantes
                    else "faltan " + ", ".join(faltantes)
                )
                lineas.append(
                    "Secundaria — Reconstruir el Puente Norte: "
                    f"{len(recogidos)}/3 materiales; {estado_mision}."
                )
        elif dimension == DIMENSION_PRESENTE:
            mision = estado.mision_presente
            lineas.append(
                "Principal — Investigar la publicación viral sobre Ronaldo: "
                f"estado {mision['estado']}."
            )
            lineas.append(
                f"Pistas reunidas: {len(mision['pistas'])}/"
                f"{len(estado.PISTAS_PARA_VERIFICAR)}. "
                "Habla con Darío Veraz, Tomás Red y Ronaldo Vélez."
            )
            if mision["estado"] == "completada":
                lineas.append("Clasificación: " + (mision.get("clasificacion") or "resuelta").replace("_", " ") + ".")
            lineas.append("Secundaria — Difundir una corrección: " + (
                "completada" if mision.get("correccion_difundida") else "disponible al verificar la publicación"
            ) + ".")
        else:
            lineas.append("No hay misiones disponibles en esta dimensión.")
        return lineas

    if pagina == 1:
        lineas = ["INFORMACIÓN QUE YA CONOCES"]
        evidencias = estado.historial_evidencias
        if dimension == DIMENSION_PRESENTE:
            descripciones = {
                "fuente_ausente": "No se encontró el archivo original; hay patrones compatibles con IA.",
                "testimonio_y_contexto": "El testigo no presenció el hecho ni conoce quién subió el archivo.",
                "respuesta_kael": "La agenda de Ronaldo lo sitúa en un debate, no en el lugar de la imagen.",
            }
            for pista in estado.PISTAS_PARA_VERIFICAR:
                marca = "✓" if pista in estado.mision_presente["pistas"] else "○"
                lineas.append(
                    f"{marca} {descripciones[pista]}"
                )
            clasificacion = estado.mision_presente.get("clasificacion")
            if clasificacion:
                lineas.append(f"Clasificaste la publicación como: {clasificacion.replace('_', ' ')}.")
        else:
            vistos = sorted({
                clave[1]
                for clave in conversaciones_vistas
                if isinstance(clave, tuple) and len(clave) > 1
            })
            lineas.append(
                "Personajes con quienes hablaste: "
                + (", ".join(vistos) if vistos else "todavía no has reunido testimonios.")
            )
            lineas.append(
                "Evidencias anotadas: "
                + (", ".join(str(item).replace("_", " ") for item in evidencias)
                   if evidencias else "ninguna por ahora.")
            )
            if estado.historial_decisiones:
                ultima = estado.historial_decisiones[-1]
                camino = ultima.get("camino") or ["sin registrar"]
                lineas.append(
                    "Última decisión: "
                    + str(camino[0])
                    + "."
                )
        lineas.append(
            "Recuerda: distingue una observación directa de un rumor o una inferencia."
        )
        return lineas

    lineas = ["CONTINUIDAD ENTRE DIMENSIONES"]
    lineas.extend(
        f"{pasado} → {presente}: {rol}."
        for pasado, presente, rol in CONTINUIDAD_PERSONAJES
    )
    return lineas


def dibujar_tutorial_dimension(
    superficie, recursos, mundo, estado, hud, dimension, mouse_pos, puede_continuar
):
    dibujar_mapa(
        superficie,
        recursos,
        mundo,
        estado,
        mouse_pos,
        hud,
        resaltar=False,
    )
    titulo, instrucciones = instrucciones_dimension(dimension)
    panel = pygame.Rect(118, 166, 724, 390)
    superficie.blit(
        superficie_con_alpha(panel.size, (14, 31, 28, 245)),
        panel.topleft,
    )
    pygame.draw.rect(superficie, ORO, panel, 3, border_radius=12)
    texto_titulo = recursos["fuente_panel_titulo"].render(titulo, True, ORO)
    superficie.blit(
        texto_titulo,
        texto_titulo.get_rect(center=(panel.centerx, panel.y + 42)),
    )
    y = panel.y + 92
    for instruccion in instrucciones:
        for linea in envolver_texto(
            "• " + instruccion,
            recursos["fuente_panel"],
            panel.width - 64,
        ):
            render = recursos["fuente_panel"].render(linea, True, CREMA)
            superficie.blit(render, (panel.x + 32, y))
            y += 30
        y += 8
    tecla = recursos["fuente_mapa"].render(
        "Pulsa una tecla para empezar"
        if puede_continuar
        else "Lee las instrucciones; podrás continuar en unos segundos",
        True,
        (255, 220, 136),
    )
    superficie.blit(tecla, tecla.get_rect(center=(panel.centerx, panel.bottom - 34)))


def dibujar_codice(
    superficie,
    recursos,
    estado,
    mundo,
    hud,
    pagina,
    conversaciones_vistas,
    mouse_pos,
    mision_seleccionada,
):
    dibujar_mapa(
        superficie,
        recursos,
        mundo,
        estado,
        mouse_pos,
        hud,
        resaltar=False,
    )
    panel = pygame.Rect(88, 76, 784, 568)
    superficie.blit(
        superficie_con_alpha(panel.size, (13, 30, 27, 245)),
        panel.topleft,
    )
    pygame.draw.rect(superficie, ORO, panel, 3, border_radius=12)
    titulo = recursos["fuente_resultado"].render("BITÁCORA DE MISIÓN", True, ORO)
    superficie.blit(titulo, titulo.get_rect(center=(panel.centerx, panel.y + 38)))

    fuente = recursos["fuente_panel"]
    for indice, etiqueta in enumerate(PAGINAS_CODICE):
        x = panel.x + 28 + indice * 238
        rect = pygame.Rect(x, panel.y + 68, 214, 32)
        seleccionado = indice == pagina
        pygame.draw.rect(
            superficie,
            (72, 97, 63) if seleccionado else (30, 52, 45),
            rect,
            border_radius=6,
        )
        pygame.draw.rect(
            superficie,
            ORO if seleccionado else (98, 125, 102),
            rect,
            1,
            border_radius=6,
        )
        texto = fuente.render(f"{indice + 1}. {etiqueta}", True, CREMA)
        superficie.blit(texto, texto.get_rect(center=rect.center))

    y = panel.y + 124
    if pagina == 0:
        rectangulos_misiones = rectangulos_selector_mision()
        for indice, (rect, nombre) in enumerate(zip(
            rectangulos_misiones, ("Principal", "Secundaria")
        )):
            seleccionado = mision_seleccionada == nombre.lower()
            pygame.draw.rect(
                superficie,
                (72, 97, 63) if seleccionado else (30, 52, 45),
                rect,
                border_radius=6,
            )
            pygame.draw.rect(
                superficie,
                ORO if seleccionado else (98, 125, 102),
                rect,
                2 if seleccionado else 1,
                border_radius=6,
            )
            texto = fuente.render(
                f"{indice + 1}. Flecha: {nombre}",
                True,
                CREMA,
            )
            superficie.blit(texto, texto.get_rect(center=rect.center))
        y += 48
    for linea in construir_contenido_codice(
        estado,
        mundo,
        pagina,
        conversaciones_vistas,
    ):
        for linea_envuelta in envolver_texto(linea, fuente, panel.width - 58):
            if y > panel.bottom - 62:
                break
            render = fuente.render(linea_envuelta, True, CREMA)
            superficie.blit(render, (panel.x + 30, y))
            y += 24
        y += 7
        if y > panel.bottom - 62:
            break
    ayuda = fuente.render(
        "←/→: sección · 1/2: elegir flecha · J o Esc: cerrar",
        True,
        (255, 220, 136),
    )
    superficie.blit(ayuda, ayuda.get_rect(center=(panel.centerx, panel.bottom - 28)))
