"""El celular: toda la interfaz de Distrito Conecta ocurre en su red social.

Usa el arte real del celular (FeedRedSocial.jpg): la publicación es el contenido
de cada pantalla, Tendencias es el menú y los cuatro botones del arte son las
decisiones del equipo. Las coordenadas son las de ese arte en el lienzo 960x720.
"""
import pygame

from interfaz.arte import dibujar_icono, icono
from interfaz.boton import Boton
from multijugador.presentacion import ORDEN_INDICADORES, POLARIDAD, cambio_favorable, texto_cambio
from nucleo.recursos import cargar_imagen, cargar_spritesheet_frames, envolver_texto

TINTA = (31, 49, 62)
TEXTO = (44, 53, 69)
AZUL = (38, 70, 83)
FAVORABLE = (31, 122, 68)
DESFAVORABLE = (170, 52, 40)
ORO = (214, 150, 42)
TURQUESA = (106, 218, 204)
PALETA = {"normal": (24, 62, 84), "hover": (36, 90, 116), "presionado": (14, 40, 58),
          "borde": TURQUESA, "contorno": (6, 16, 28)}

NOMBRE_PERFIL = pygame.Rect(166, 97, 200, 36)
IMAGEN = pygame.Rect(104, 194, 126, 126)
TEXTO_X, TEXTO_Y, TEXTO_ANCHO = 246, 180, 345
ALCANCE = (198, 383)  # a la derecha de la etiqueta "Reach"
COMENTARIOS = (pygame.Rect(146, 479, 425, 26), pygame.Rect(146, 520, 425, 26))
FILA_ALTO, FILA_PASO = 36, 51.4
FILA_X, FILA_Y, FILA_ANCHO = 678, 105, 236
FILAS = 11
BARRA_ACCIONES = pygame.Rect(40, 588, 600, 124)  # botones y rótulos del arte
ACCIONES_Y = 628

# Botón del arte -> (nombre, zona, imagen, cuadro si la imagen es una hoja de 8).
OPCIONES = {
    "compartir": ("Publicar", pygame.Rect(58, 595, 130, 71), "Estados/fx_propagacion_tarjeta_8f_1024x128.png", 4),
    "verificar": ("Verificar", pygame.Rect(202, 595, 130, 71), "Estados/estado_fuente_verificada.png", None),
    "reportar": ("Denunciar", pygame.Rect(345, 595, 130, 71), "Iconos/Nuevos/icono_sancion.png", None),
    "dejar_pendiente": ("Ignorar", pygame.Rect(488, 595, 130, 71), "Iconos/Nuevos/icono_tiempo.png", None),
}


def nombre_opcion(clave):
    return OPCIONES[clave][0] if clave in OPCIONES else clave


class ArteCelular:
    """Se carga una vez, al llegar por primera vez a Distrito Conecta."""

    def __init__(self):
        self.feed = cargar_imagen("Iconos/Objetos varios/FeedRedSocial.jpg", (960, 720))
        # Fuera de las decisiones los cuatro botones del arte no significan nada:
        # se borran copiando el degradado del margen, fila por fila.
        self.feed_sin_botones = self.feed.copy()
        for y in range(BARRA_ACCIONES.top, BARRA_ACCIONES.bottom):
            self.feed_sin_botones.fill(self.feed.get_at((12, y)), (BARRA_ACCIONES.x, y, BARRA_ACCIONES.width, 1))
        # Lo que en el arte es un ejemplo ("Nombre de Perfil", foto de muestra).
        color_nombre, color_post = self.feed.get_at((163, 115)), self.feed.get_at((90, 340))
        for imagen in (self.feed, self.feed_sin_botones):
            imagen.fill(color_nombre, NOMBRE_PERFIL.inflate(8, -8))
            imagen.fill(color_post, IMAGEN.inflate(12, 14))
        self.publicacion = icono("Estados/estado_sin_fuente.png", (104, 104))
        self.iconos = {}
        for clave, (_, _, ruta, cuadro) in OPCIONES.items():
            if cuadro is None:
                self.iconos[clave] = icono(ruta, (84, 84))
                continue
            cuadros = cargar_spritesheet_frames(ruta, 8)
            if len(cuadros) > cuadro:
                imagen = cuadros[cuadro].subsurface(cuadros[cuadro].get_bounding_rect())
                factor = min(100 / imagen.get_width(), 84 / imagen.get_height())
                self.iconos[clave] = pygame.transform.scale(
                    imagen, (round(imagen.get_width() * factor), round(imagen.get_height() * factor)))
        self.retratos = {}  # (id de la imagen) -> retrato ya ajustado al recuadro

    def ajustar(self, imagen):
        """Ajusta un retrato al recuadro de la publicación una sola vez."""
        if id(imagen) not in self.retratos:
            lado = IMAGEN.width - 12
            factor = min(lado / imagen.get_width(), lado / imagen.get_height())
            self.retratos[id(imagen)] = pygame.transform.scale(
                imagen, (max(1, round(imagen.get_width() * factor)), max(1, round(imagen.get_height() * factor))))
        return self.retratos[id(imagen)]


def equipo_distrito(panel, incluir_yo=False):
    """Quienes juegan, con el nombre de su personaje de Distrito Conecta."""
    from mundo.personajes import PERSONAJES_DISTRITO
    return [PERSONAJES_DISTRITO[j["rol"]][0] for j in panel.vista.estado.get("mundo", {}).get("jugadores", [])
            if j.get("rol") in PERSONAJES_DISTRITO and j.get("conectado", True)
            and (incluir_yo or j["id"] != panel.vista.identificador)]


def _texto(panel, superficie, texto, x, y, fuente=None, color=TEXTO, ancho=TEXTO_ANCHO):
    return panel.texto_lineas(superficie, texto, x, y, ancho, fuente or panel.pequena, color)


def _perfil(panel, superficie, nombre):
    render = panel.fuente.render(nombre, True, TINTA)
    if render.get_width() > NOMBRE_PERFIL.width:
        render = panel.pequena.render(nombre, True, TINTA)
    superficie.blit(render, render.get_rect(midleft=NOMBRE_PERFIL.midleft))


def _imagen(superficie, imagen, arte):
    pygame.draw.rect(superficie, (214, 222, 236), IMAGEN, border_radius=5)
    pygame.draw.rect(superficie, (39, 50, 72), IMAGEN, 2, border_radius=5)
    if imagen is not None:
        if imagen.get_width() > IMAGEN.width - 12 or imagen.get_height() > IMAGEN.height - 12:
            imagen = arte.ajustar(imagen)
        superficie.blit(imagen, imagen.get_rect(center=IMAGEN.center))


def _alcance(panel, superficie, texto):
    render = panel.pequena.render(texto, True, AZUL)
    superficie.blit(render, render.get_rect(midleft=ALCANCE))


def _comentarios(panel, superficie, *textos):
    """Hasta dos líneas, una en cada burbuja de comentario del arte."""
    lineas = [linea for texto in textos if texto for linea in envolver_texto(texto, panel.pequena, COMENTARIOS[0].width - 8)]
    for caja, linea in zip(COMENTARIOS, lineas):
        render = panel.pequena.render(linea, True, TEXTO)
        superficie.blit(render, render.get_rect(midleft=(caja.x + 4, caja.centery)))


def _boton(panel, superficie, clave, texto, centro, ancho=300, activo=True, alto=46):
    boton = Boton(texto, centro=centro, fuente=panel.fuente, tamano=(ancho, alto), desactivado=not activo, paleta=PALETA)
    boton.dibujar(superficie, panel.vista.mouse)
    panel.botones[clave] = boton


def _menu(panel, superficie, contexto, inventario):
    """Tendencias es el menú del celular; las pistas se abren desde ahí."""
    filas = [("introduccion", "Misión"), ("inventario", "Mis pistas"), ("caldero", "Decidir")]
    filas += [("pista:" + str(i), pista["titulo"].split(" · ")[0]) for i, pista in enumerate(inventario)]
    transparente = pygame.Surface((FILA_ANCHO, FILA_ALTO), pygame.SRCALPHA)
    for i in range(FILAS):
        rect = pygame.Rect(FILA_X, round(FILA_Y + i * FILA_PASO), FILA_ANCHO, FILA_ALTO)
        if i >= len(filas):
            texto = panel.pequena.render("DistritoConecta", True, (112, 130, 144))
            superficie.blit(texto, texto.get_rect(midleft=(729, rect.centery)))
            continue
        clave, nombre = filas[i]
        boton = Boton(nombre, transparente, rect.center)
        boton.actualizar(panel.vista.mouse)
        panel.botones[clave] = boton
        activa = panel.modo == clave or (clave.startswith("pista:") and panel.modo == "inventario"
                                         and int(clave[6:]) == panel.indice_pista % max(1, len(inventario)))
        if activa or boton.hover:
            pygame.draw.rect(superficie, ORO if activa else AZUL, rect.inflate(-2, 0), 2, border_radius=10)
        texto = panel.pequena.render(nombre, True, TINTA)
        superficie.blit(texto, texto.get_rect(midleft=(729, rect.centery)))


# ------------------------------------------------------------------ pantallas
def _mision(panel, superficie, contexto, arte):
    _perfil(panel, superficie, "Distrito Conecta")
    _imagen(superficie, arte.publicacion, arte)
    y = _texto(panel, superficie, contexto.get("titulo", ""), TEXTO_X, TEXTO_Y, panel.fuente, TINTA)
    _texto(panel, superficie, contexto.get("noticia", ""), TEXTO_X, y + 6)
    _alcance(panel, superficie, f"Pistas {contexto.get('pistas', 0)} de {contexto.get('total_pistas', 3)}")
    _comentarios(panel, superficie, _siguiente_paso(panel))
    _boton(panel, superficie, "inventario", "Ver mis pistas", (338, ACCIONES_Y))


def _siguiente_paso(panel):
    caso = panel.vista.estado.get("mundo", {}).get("caso", {})
    return panel.vista._textos_objetivo(caso, panel.privado, {})[1]


def _fuente(panel, superficie, contexto, arte):
    persona, _, tema = panel.titulo.partition(" · ")
    _perfil(panel, superficie, persona)
    _imagen(superficie, arte.publicacion if persona.startswith("Pantalla") else panel.imagen_retrato(panel.titulo), arte)
    y = TEXTO_Y
    if tema:
        y = _texto(panel, superficie, tema, TEXTO_X, y, panel.fuente, TINTA) + 6
    _texto(panel, superficie, panel.texto, TEXTO_X, y)
    _comentarios(panel, superficie, _siguiente_paso(panel))
    _boton(panel, superficie, "inventario", "Ver mis pistas", (338, ACCIONES_Y))


def _pistas(panel, superficie, contexto, arte):
    inventario = panel.inventario()
    if not inventario:
        _perfil(panel, superficie, "Mis pistas")
        _imagen(superficie, arte.publicacion, arte)
        _texto(panel, superficie, "Aún no hay pistas. Habla con las personas marcadas en el mapa.", TEXTO_X, TEXTO_Y)
        _comentarios(panel, superficie, _siguiente_paso(panel))
        return
    panel.indice_pista %= len(inventario)
    pista = inventario[panel.indice_pista]
    persona, _, tema = pista["titulo"].partition(" · ")
    _perfil(panel, superficie, persona)
    _imagen(superficie, panel.imagen_retrato(pista["titulo"]), arte)
    y = _texto(panel, superficie, tema, TEXTO_X, TEXTO_Y, panel.fuente, TINTA)
    _texto(panel, superficie, pista["texto"], TEXTO_X, y + 6)
    _alcance(panel, superficie, f"Pista {panel.indice_pista + 1} de {len(inventario)}")
    panel.boton_flecha(superficie, "pista_anterior", panel.vista.arte.flecha_izq, "<", 330, 428)
    panel.boton_flecha(superficie, "pista_siguiente", panel.vista.arte.flecha_der, ">", 400, 428)
    equipo = ", ".join(equipo_distrito(panel))
    _comentarios(panel, superficie, "También la ven: " + equipo if equipo else "")
    completas = contexto.get("pistas", 0) >= contexto.get("total_pistas", 3)
    _boton(panel, superficie, "caldero", "Decidir qué hacer", (338, ACCIONES_Y), activo=completas)


def falta_para_decidir(panel, contexto):
    if contexto.get("pistas", 0) < contexto.get("total_pistas", 3):
        return "Reúnan las tres pistas de Distrito Conecta."
    return "" if panel.vista.cerca_id("presente:pantalla") else "Acércate a la pantalla pública para elegir."


def _decidir(panel, superficie, contexto, arte):
    _perfil(panel, superficie, "Publicación viral")
    _imagen(superficie, arte.publicacion, arte)
    y = _texto(panel, superficie, contexto.get("titulo", ""), TEXTO_X, TEXTO_Y, panel.fuente, TINTA)
    _texto(panel, superficie, contexto.get("noticia", ""), TEXTO_X, y + 6)
    _alcance(panel, superficie, f"Ya eligieron {contexto.get('votos_emitidos', 0)} de {contexto.get('votantes', 0)}")
    falta = falta_para_decidir(panel, contexto)
    voto = panel.privado_voto(contexto)
    transparente = {}
    apuntada = None
    for clave, texto in contexto.get("opciones", {}).items():
        if clave not in OPCIONES:
            continue
        zona = OPCIONES[clave][1]
        transparente.setdefault(zona.size, pygame.Surface(zona.size, pygame.SRCALPHA))
        boton = Boton(texto, transparente[zona.size], zona.center, desactivado=bool(falta))
        boton.actualizar(panel.vista.mouse)
        panel.botones["presente_votar:" + clave] = boton
        if boton.hover:
            apuntada = texto
            pygame.draw.rect(superficie, (255, 255, 255), zona.inflate(4, 4), 2, border_radius=12)
        if falta:
            velo = pygame.Surface(zona.size, pygame.SRCALPHA)
            pygame.draw.rect(velo, (30, 40, 50, 130), velo.get_rect(), border_radius=12)
            superficie.blit(velo, zona)
        if voto == clave:
            pygame.draw.rect(superficie, ORO, zona.inflate(6, 6), 3, border_radius=13)
    _comentarios(panel, superficie, apuntada or falta or "Elijan juntos qué hacer con esta publicación.",
                 "Tu elección: " + nombre_opcion(voto) if voto else "")


def _resultado(panel, superficie, contexto, arte):
    resultado = contexto.get("resultado") or {}
    _perfil(panel, superficie, "Consecuencia")
    _imagen(superficie, arte.iconos.get(resultado.get("opcion")), arte)
    y = _texto(panel, superficie, resultado.get("texto", ""), TEXTO_X, TEXTO_Y)
    columna = 0
    for nombre in ORDEN_INDICADORES:
        cambio = resultado.get("efectos", {}).get(nombre)
        if not cambio or nombre not in POLARIDAD:
            continue
        color = FAVORABLE if cambio_favorable(nombre, cambio) else DESFAVORABLE
        render = panel.pequena.render(texto_cambio(nombre, cambio, "presente"), True, color)
        superficie.blit(render, (TEXTO_X, y + 6 + columna * 20))
        columna += 1
    propia = panel.clasificacion_propia()
    if not propia:
        _comentarios(panel, superficie, "Antes de seguir: ¿qué tipo de información era?")
        _boton(panel, superficie, "clasificar_abrir", "Clasificar la publicación", (338, ACCIONES_Y), 360)
    elif resultado.get("opcion") == "dejar_pendiente":
        _comentarios(panel, superficie, "Sigue circulando sin aclaración. Pueden volver a decidir.")
        _boton(panel, superficie, "caldero", "Volver a decidir", (338, ACCIONES_Y), activo=panel.vista.cerca_id("presente:pantalla"))
    else:
        _comentarios(panel, superficie, _siguiente_paso(panel))


def _clasificar(panel, superficie, contexto, arte):
    _perfil(panel, superficie, "Clasificar")
    _imagen(superficie, arte.publicacion, arte)
    y = _texto(panel, superficie, "¿Cómo clasificarías esta publicación?", TEXTO_X, TEXTO_Y, panel.fuente, TINTA)
    _texto(panel, superficie, contexto.get("noticia", ""), TEXTO_X, y + 6)
    _comentarios(panel, superficie, "Elige la categoría que consideres correcta.")
    opciones = contexto.get("clasificacion_opciones") or []
    ancho = min(270, 560 // max(1, len(opciones)) - 14)
    for i, opcion in enumerate(opciones):
        x = 338 + round((i - (len(opciones) - 1) / 2) * (ancho + 14))
        _boton(panel, superficie, "clasificar:" + opcion, opcion, (x, ACCIONES_Y), ancho)


def _clasificado(panel, superficie, contexto, arte):
    propia = panel.clasificacion_propia()
    if not propia:
        return _resultado(panel, superficie, contexto, arte)
    _perfil(panel, superficie, "Clasificación")
    _imagen(superficie, arte.iconos.get("verificar" if propia["correcta"] else "reportar"), arte)
    y = _texto(panel, superficie, f"Tu respuesta: {propia['opcion']}", TEXTO_X, TEXTO_Y, panel.fuente,
               FAVORABLE if propia["correcta"] else DESFAVORABLE)
    y = _texto(panel, superficie, "CORRECTA" if propia["correcta"] else "INCORRECTA", TEXTO_X, y + 2, panel.pequena,
               FAVORABLE if propia["correcta"] else DESFAVORABLE)
    y = _texto(panel, superficie, "En realidad era: " + str(propia["categoria"][-1]), TEXTO_X, y + 6, panel.pequena, TINTA)
    _texto(panel, superficie, (contexto.get("resultado") or {}).get("texto", ""), TEXTO_X, y + 6)
    sabiduria = propia.get("efectos", {}).get("sabiduria", 0)
    _alcance(panel, superficie, f"Alfabetización digital {'+' if sabiduria > 0 else ''}{sabiduria}")
    _comentarios(panel, superficie, "Haz clic para continuar.")


PANTALLAS = {"caldero": _decidir, "resultado": _resultado, "clasificar": _clasificar,
             "clasificacion_resultado": _clasificado, "fuente": _fuente, "inventario": _pistas}


def dibujar(panel, superficie):
    arte = panel.vista.celular
    contexto = panel.contexto()
    superficie.blit(arte.feed if panel.modo == "caldero" else arte.feed_sin_botones, (0, 0))
    _menu(panel, superficie, contexto, panel.inventario())
    PANTALLAS.get(panel.modo, _mision)(panel, superficie, contexto, arte)
    if panel.modo != "clasificacion_resultado":
        boton = Boton("Guardar el celular", centro=(795, 700), fuente=panel.pequena, tamano=(232, 30), paleta=PALETA)
        boton.dibujar(superficie, panel.vista.mouse)
        panel.botones["cerrar"] = boton
