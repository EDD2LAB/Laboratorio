"""Escenas superpuestas al mapa: análisis de publicación, transición, diálogo, mensaje y eco."""

import pygame
from nucleo.config import ALTO, ANCHO, CREMA, DURACION_MINIMA_HISTORIA_DIMENSION_MS, ORO
from nucleo.recursos import cargar_fuente, envolver_texto, superficie_con_alpha
from un_jugador.dibujo_mapa import (
    _mapa_actual_recursos,
    dibujar_decoraciones_editor,
    dibujar_fondo_mundo,
    dibujar_jugador,
    dibujar_mapa,
)


def rectangulos_opciones_mision():
    return [
        pygame.Rect(200, 413 + indice * 34, 560, 30)
        for indice in range(7)
    ]


def dibujar_analisis_publicacion(
    superficie, recursos, mundo, estado, hud, seleccion, mouse_pos,
):
    dibujar_mapa(
        superficie,
        recursos,
        mundo,
        estado,
        mouse_pos,
        hud,
        particulas=None,
        resaltar=False,
    )
    velo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    velo.fill((7, 17, 26, 190))
    superficie.blit(velo, (0, 0))
    panel = pygame.Rect(150, 88, 660, 570)
    pygame.draw.rect(superficie, (17, 34, 43), panel, border_radius=14)
    pygame.draw.rect(superficie, (73, 208, 197), panel, 2, border_radius=14)

    fuente_titulo = recursos["fuente_panel_titulo"]
    fuente = recursos["fuente_panel"]
    titulo = fuente_titulo.render("DISTRITO CONECTA · PUBLICACIÓN", True, (108, 227, 216))
    superficie.blit(titulo, titulo.get_rect(center=(panel.centerx, panel.y + 32)))
    imagen_publicacion = recursos.get("imagen_publicacion_aspirante")
    if imagen_publicacion:
        rect_imagen = pygame.Rect(panel.x + 30, panel.y + 70, 112, 90)
        pygame.draw.rect(superficie, (10, 20, 28), rect_imagen.inflate(6, 6), border_radius=5)
        imagen_escalada = pygame.transform.smoothscale(imagen_publicacion, rect_imagen.size)
        superficie.blit(imagen_escalada, rect_imagen)
    cuerpo = [
        "Una publicación viral acusa a Ronaldo mediante una imagen.",
        "¿Es auténtica o fue generada por IA?",
        "Reúne las pistas antes de clasificar o compartirla.",
    ]
    for indice, linea in enumerate(cuerpo):
        render = fuente.render(linea, True, CREMA)
        superficie.blit(render, (panel.x + 165, panel.y + 82 + indice * 27))

    pistas = estado.mision_presente["pistas"]
    nombres_pistas = {
        "fuente_ausente": "fuente original no identificada",
        "testimonio_y_contexto": "testimonio y contexto contrastados",
        "respuesta_kael": "respuesta de Ronaldo Vélez",
    }
    texto_pistas = "Pistas: " + (
        ", ".join(nombres_pistas.get(pista, pista) for pista in pistas)
        if pistas
        else "todavía no revisadas"
    )
    render_pistas = fuente.render(texto_pistas, True, (255, 213, 122))
    superficie.blit(render_pistas, (panel.x + 30, panel.y + 180))
    estado_mision = estado.mision_presente["estado"]
    if estado_mision == "completada":
        decision = estado.mision_presente.get("decision")
        if decision in ("verificar", "clasificar_ia") and not estado.mision_presente.get("correccion_difundida"):
            linea_estado = "Verificación lista: pulsa Q en el mapa para difundir la corrección."
        elif estado.mision_presente.get("correccion_difundida"):
            linea_estado = "Corrección difundida. La evidencia no demuestra culpabilidad."
        elif decision in ("clasificar_ia", "clasificar_real"):
            resultado = "correcta" if estado.mision_presente.get("clasificacion_correcta") else "incorrecta"
            linea_estado = (
                "¡Correcto! La imagen era generada por IA. Pulsa Q para difundir la corrección."
                if resultado == "correcta"
                else "Clasificación incorrecta: la imagen era generada por IA."
            )
        else:
            linea_estado = "Misión resuelta: la publicación quedó reportada."
    elif estado_mision == "pendiente":
        linea_estado = "La publicación quedó pendiente; puedes retomarla cuando quieras."
    else:
        faltantes = [
            "revisar la fuente",
            "comparar testimonios",
            "escuchar a Ronaldo Vélez",
        ]
        if "fuente_ausente" in pistas:
            faltantes.remove("revisar la fuente")
        if "testimonio_y_contexto" in pistas:
            faltantes.remove("comparar testimonios")
        if "respuesta_kael" in pistas:
            faltantes.remove("escuchar a Ronaldo Vélez")
        linea_estado = (
            "Investiga: " + ", ".join(faltantes) + "."
            if faltantes
            else "1-7 o flechas + Enter para elegir."
        )
    texto_estado = fuente.render(linea_estado, True, CREMA)
    superficie.blit(texto_estado, (panel.x + 30, panel.y + 215))

    opciones = (
        ("Revisar la fuente", "revisar_fuente"),
        ("Comparar con testimonios y contexto", "comparar_evidencia"),
        ("Clasificar la imagen como generada por IA", "clasificar_ia"),
        ("Clasificar la imagen como auténtica", "clasificar_real"),
        ("Dejar pendiente", "dejar_pendiente"),
        ("Reportar la publicación", "reportar"),
        ("Verificar antes de compartir", "verificar"),
    )
    if estado_mision == "completada":
        return
    for indice, (etiqueta, _) in enumerate(opciones):
        rect = rectangulos_opciones_mision()[indice]
        color = (32, 104, 105) if indice == seleccion else (27, 55, 62)
        borde = (255, 213, 122) if indice == seleccion else (91, 166, 164)
        pygame.draw.rect(superficie, color, rect, border_radius=7)
        pygame.draw.rect(superficie, borde, rect, 2, border_radius=7)
        texto = fuente.render(f"{indice + 1}. {etiqueta}", True, CREMA)
        superficie.blit(texto, texto.get_rect(midleft=(rect.x + 16, rect.centery)))


def dibujar_transicion_dimension(
    superficie, recursos, mundo, estado, hud, particulas, mouse_pos, tiempo_ms,
    dimension_cargada,
):
    dibujar_mapa(
        superficie,
        recursos,
        mundo,
        estado,
        mouse_pos,
        hud,
        particulas=particulas,
        resaltar=False,
    )
    if not dimension_cargada:
        alpha = min(235, round(235 * min(1.0, tiempo_ms / 1700)))
        velo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        velo.fill((5, 14, 24, alpha))
        superficie.blit(velo, (0, 0))
    elif tiempo_ms < 2450:
        destello = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        alpha = round(115 * (1 - abs(tiempo_ms - 2200) / 250))
        destello.fill((176, 249, 242, max(0, alpha)))
        superficie.blit(destello, (0, 0))
    else:
        alpha = max(0, round(220 * (1 - min(1, (tiempo_ms - 2450) / 650))))
        velo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        velo.fill((5, 14, 24, alpha))
        superficie.blit(velo, (0, 0))

    centro = (ANCHO // 2, ALTO // 2)
    fase = min(1.0, tiempo_ms / 2200)
    for indice in range(3):
        radio = round((40 + ((tiempo_ms * 0.18 + indice * 92) % 310)) * fase)
        if radio > 0:
            pygame.draw.circle(
                superficie,
                (69, 220, 210, 105),
                centro,
                radio,
                2,
            )
    if tiempo_ms < 2200 and tiempo_ms % 260 < 20:
        particulas.emitir(*centro, 5)

    if dimension_cargada and tiempo_ms >= 2750:
        titulo = recursos["fuente_resultado"].render(
            "DISTRITO CONECTA",
            True,
            (231, 255, 247),
        )
        alpha = round(255 * min(1.0, (tiempo_ms - 2750) / 420))
        titulo.set_alpha(alpha)
        superficie.blit(titulo, titulo.get_rect(center=(ANCHO // 2, 108)))
        panel = pygame.Rect(104, 151, 752, 238)
        fondo_historia = pygame.Surface(panel.size, pygame.SRCALPHA)
        fondo_historia.fill((11, 27, 30, round(220 * alpha / 255)))
        superficie.blit(fondo_historia, panel.topleft)
        pygame.draw.rect(
            superficie,
            (106, 218, 204, round(230 * alpha / 255)),
            panel,
            2,
            border_radius=10,
        )
        lineas = (
            "El Guardián investiga ahora como el periodista Elías Vega.",
            "Ronaldo Vélez, descendiente de Kael, aspira a la Alcaldía.",
            "Darío Veraz sigue el legado de Odran como agente de verificación.",
            "Mateo Ríos comunica por la ciudad, como hacía el Mensajero.",
            "Lía Nova difunde historias como influencer; Tomás Red participa en la comunidad.",
            "La publicación no demuestra culpabilidad: reúne pruebas antes de compartir.",
        )
        for indice, linea in enumerate(lineas):
            render = recursos["fuente_panel"].render(linea, True, (232, 247, 235))
            render.set_alpha(alpha)
            superficie.blit(render, (panel.x + 22, panel.y + 13 + indice * 28))
        if tiempo_ms >= DURACION_MINIMA_HISTORIA_DIMENSION_MS:
            instruccion = recursos["fuente_mapa"].render(
                "Pulsa cualquier tecla para continuar",
                True,
                (172, 231, 218),
            )
            superficie.blit(instruccion, instruccion.get_rect(center=(ANCHO // 2, 421)))


def dibujar_escena_dialogo(
    superficie, recursos, dialogos, mouse_pos, hud, jugador=None, particulas=None, mundo=None
):
    """El diálogo se superpone al mapa y bloquea sus demás interacciones."""
    if mundo:
        dibujar_fondo_mundo(superficie, recursos, mundo, particulas)
    else:
        superficie.blit(_mapa_actual_recursos(recursos), (0, 0))
        dibujar_decoraciones_editor(superficie, recursos)
        if jugador:
            dibujar_jugador(superficie, jugador)
        if particulas:
            particulas.dibujar(superficie)
    hud.dibujar(superficie)
    dialogos.dibujar(superficie, mouse_pos, ANCHO, ALTO)


def dibujar_escena_mensaje(
    superficie, recursos, mensajes, mouse_pos, hud, jugador=None, mundo=None
):
    """El pergamino se presenta sobre el mapa y bloquea las demás acciones."""
    if mundo:
        dibujar_fondo_mundo(superficie, recursos, mundo)
    else:
        superficie.blit(_mapa_actual_recursos(recursos), (0, 0))
        dibujar_decoraciones_editor(superficie, recursos)
        if jugador:
            dibujar_jugador(superficie, jugador)
    hud.dibujar(superficie)
    mensajes.dibujar(superficie, mouse_pos)


def dibujar_interfaz_eco(
    superficie, recursos, jugador, estado_eco, contactos, mensajes, mundo=None
):
    if mundo:
        dibujar_fondo_mundo(superficie, recursos, mundo)
    else:
        superficie.blit(_mapa_actual_recursos(recursos), (0, 0))
        dibujar_decoraciones_editor(superficie, recursos)
        dibujar_jugador(superficie, jugador)
    panel = pygame.Rect(190, 150, 580, 420)
    superficie.blit(superficie_con_alpha(panel.size, (17, 34, 28, 242)), panel.topleft)
    pygame.draw.rect(superficie, ORO, panel, 3, border_radius=14)
    frames_tronco = recursos.get("frames_tronco_eco", [])
    if frames_tronco:
        frame = frames_tronco[(pygame.time.get_ticks() // 140) % len(frames_tronco)]
        superficie.blit(pygame.transform.scale(frame, (64, 72)), (panel.right - 102, panel.y + 18))
    titulo = recursos["fuente_panel_titulo"].render("ECO DE TRONCOS", True, ORO)
    superficie.blit(titulo, titulo.get_rect(center=(panel.centerx, panel.y + 38)))
    if not contactos:
        lineas = ["No hay personajes disponibles en este mapa.", "Esc para volver."]
    elif estado_eco["respuesta"]:
        lineas = [
            f"Mensaje enviado a {contactos[estado_eco['destinatario']]}:",
            mensajes[estado_eco["mensaje"]][1],
            estado_eco["respuesta"],
            "Enter o Esc para volver.",
        ]
    else:
        destinatario = contactos[estado_eco["destinatario"]]
        mensaje = mensajes[estado_eco["mensaje"]][1]
        lineas = [
            f"Destinatario:  < {destinatario} >",
            f"Mensaje:  < {mensaje} >",
            "Arriba/abajo: destinatario | Izquierda/derecha: mensaje",
            "E o Enter: enviar | Esc: cancelar",
        ]
    # Los testimonios pueden ocupar varias líneas: ajustar dentro del panel.
    fuente = recursos["fuente_panel"]
    bloques = [envolver_texto(linea, fuente, panel.width - 56) for linea in lineas]
    alto = sum(len(bloque) * (fuente.get_linesize() + 3) + 10 for bloque in bloques)
    if alto > panel.height - 110:
        fuente = cargar_fuente(16)
        bloques = [envolver_texto(linea, fuente, panel.width - 56) for linea in lineas]
    y = panel.y + 100
    for bloque in bloques:
        for linea in bloque:
            texto = fuente.render(linea, True, CREMA)
            superficie.blit(texto, texto.get_rect(midtop=(panel.centerx, y)))
            y += fuente.get_linesize() + 3
        y += 10
