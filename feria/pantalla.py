"""Pantalla grande de la Feria de los Ecos (fase 1).

Corre su propio bucle desde el menú, como «Ver la batalla final», y al salir
destruye la sesión y el servidor. Solo dibuja el arte de La Copa: no crea
partidas, no usa la campaña, el expediente ni las preferencias.
"""
import math
import time

import pygame

from feria.casos import CATEGORIAS, DECISIONES, NOMBRE_DECISION
from nucleo.recursos import cargar_fuente, cargar_imagen, envolver_texto

CREMA, ORO, VERDE, ROJO = (255, 243, 210), (237, 185, 87), (130, 222, 158), (255, 143, 134)
TINTA, TINTA_SUAVE = (58, 36, 18), (96, 62, 30)
CARPETA = "Modo feria/"
ESCALA_PANEL = 1.17
ORIGEN_PANEL = (21, 128)
HUECO_QR = (159, 133, 467, 186)          # pergamino claro de panel_qr.png (785 x 438)
HUECO_RESULTADO = (137, 93, 513, 266)    # pergamino de marco_resultado_final.png
COLORES_DECISION = {"compartir": (196, 74, 92), "verificar": (82, 168, 110), "detener": (70, 132, 196),
                    "ignorar": (150, 140, 120)}


def _escalar(imagen, factor):
    return pygame.transform.scale(imagen, (max(1, round(imagen.get_width() * factor)),
                                           max(1, round(imagen.get_height() * factor))))


def _recortada(nombre, alto):
    """Imagen de la feria recortada a su contenido y escalada a ``alto`` px (o None)."""
    imagen = cargar_imagen(CARPETA + nombre, requerido=False)
    if imagen is None:
        return None
    limites = imagen.get_bounding_rect(min_alpha=40)
    if limites.width and limites.height:
        imagen = imagen.subsurface(limites)
    return _escalar(imagen, alto / imagen.get_height())


def _hueco(hueco):
    x, y, w, h = hueco
    return pygame.Rect(ORIGEN_PANEL[0] + round(x * ESCALA_PANEL), ORIGEN_PANEL[1] + round(y * ESCALA_PANEL),
                       round(w * ESCALA_PANEL), round(h * ESCALA_PANEL))


class PantallaFeria:
    def __init__(self, sesion, url, aviso_red=""):
        from interfaz.boton import Boton
        from mundo.mapas import cargar_fondo_unificado
        from feria.qr import superficie_qr
        self.Boton = Boton
        self.sesion, self.url, self.aviso_red = sesion, url, aviso_red
        self.fuentes = {n: cargar_fuente(n) for n in (14, 16, 18, 20, 24, 32, 44)}
        self.fondo = cargar_fondo_unificado(1)
        velo = pygame.Surface((960, 720), pygame.SRCALPHA)
        velo.fill((6, 14, 12, 120))
        self.fondo.blit(velo, (0, 0))
        self.panel_qr = self._panel("panel_qr.png")
        self.marco = self._panel("marco_resultado_final.png")
        self.hueco_qr, self.hueco_resultado = _hueco(HUECO_QR), _hueco(HUECO_RESULTADO)
        self.qr = superficie_qr(url, self.hueco_qr.height - 16)
        self.celular = _recortada("icono_celular_qr.png", 74)
        self.espera = _recortada("sello_esperando.png", 56)
        self.recibido = _recortada("sello_voto_recibido.png", 56)
        self.colectivo = _recortada("sello_resultado_colectivo.png", 70)
        self.calderos = {"positivo": _recortada("caldero_positivo.png", 210),
                         "critico": _recortada("caldero_critico.png", 210)}
        dudoso = self.calderos["positivo"]
        if dudoso is not None:  # sin arte propio: el positivo, apagado y en tonos morados
            dudoso = dudoso.copy()
            dudoso.fill((150, 120, 190, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self.calderos["dudoso"] = dudoso
        self.botones = {}
        self.votando_aqui = None   # {"decision", "categoria"} mientras alguien vota en la pantalla
        self.votos_pantalla = 0
        self.ultimo_total = 0
        self.destello_voto = 0.0

    def _panel(self, nombre):
        imagen = cargar_imagen(CARPETA + nombre, requerido=False)
        return None if imagen is None else _escalar(imagen, ESCALA_PANEL)

    # --- Utilidades de dibujo -------------------------------------------------
    def texto(self, superficie, texto, centro=None, tam=20, color=CREMA, izquierda=None):
        imagen = self.fuentes[tam].render(texto, True, color)
        rect = imagen.get_rect(center=centro) if centro else imagen.get_rect(topleft=izquierda)
        superficie.blit(imagen, rect)
        return rect

    def parrafo(self, superficie, texto, x, y, ancho, tam=18, color=TINTA, interlineado=4):
        fuente = self.fuentes[tam]
        for linea in envolver_texto(texto, fuente, ancho):
            superficie.blit(fuente.render(linea, True, color), (x, y))
            y += fuente.get_linesize() + interlineado
        return y

    def boton(self, superficie, clave, texto, centro, ancho=200, alto=40, tam=18, activo=True):
        b = self.Boton(texto, centro=centro, fuente=self.fuentes[tam], tamano=(ancho, alto), desactivado=not activo)
        b.dibujar(superficie, self.mouse)
        self.botones[clave] = b

    def _respaldo_panel(self, superficie, hueco):
        """Si falta el arte, un marco de madera dibujado alrededor del hueco."""
        pygame.draw.rect(superficie, (92, 56, 28), hueco.inflate(56, 56), border_radius=12)
        pygame.draw.rect(superficie, ORO, hueco.inflate(56, 56), 3, border_radius=12)
        superficie.fill((243, 232, 214), hueco)

    # --- Estados --------------------------------------------------------------
    def dibujar(self, superficie, mouse, ahora_ms):
        self.mouse = mouse
        self.botones = {}
        estado = self.sesion.para_pantalla()
        superficie.blit(self.fondo, (0, 0))
        if self.celular is not None:
            superficie.blit(self.celular, self.celular.get_rect(topleft=(34, 18)))
        self.texto(superficie, "FERIA DE LOS ECOS", (480, 44), 44, ORO)
        self.texto(superficie, f"Ronda {estado['ronda']} · {estado['caso']['titulo']}", (480, 92), 20)
        if self.votando_aqui is not None:
            self._dibujar_ronda(superficie, estado, ahora_ms)
            self._dibujar_voto_pantalla(superficie, estado)
        elif estado["abierta"]:
            self._dibujar_ronda(superficie, estado, ahora_ms)
        else:
            self._dibujar_resultado(superficie, estado)
        if self.aviso_red:
            self.texto(superficie, self.aviso_red, (480, 118), 14, ROJO)

    def _dibujar_ronda(self, superficie, estado, ahora_ms):
        hueco = self.hueco_qr
        if self.panel_qr is not None:
            superficie.blit(self.panel_qr, ORIGEN_PANEL)
        else:
            self._respaldo_panel(superficie, hueco)
        qr = self.qr.get_rect(midleft=(hueco.x + 10, hueco.centery))
        superficie.blit(self.qr, qr)
        x, ancho = qr.right + 18, hueco.right - qr.right - 28
        caso = estado["caso"]
        y = self.parrafo(superficie, caso["tablilla"], x, hueco.y + 8, ancho, 24, TINTA)
        y = self.parrafo(superficie, "Fuente: " + caso["fuente"], x, y + 6, ancho, 16, TINTA_SUAVE)
        self.parrafo(superficie, "Escanea el código con tu celular y decide qué hacer con este mensaje.",
                     x, max(y + 10, hueco.bottom - 46), ancho, 14, TINTA_SUAVE, 2)
        # Contador: el total, nunca el voto de cada persona.
        if estado["votos"] > self.ultimo_total:
            self.destello_voto = time.monotonic()
        self.ultimo_total = estado["votos"]
        recien = time.monotonic() - self.destello_voto < .8
        sello = self.recibido if recien else self.espera
        if sello is not None:
            if not recien:
                sello = pygame.transform.rotate(sello, -90 * ((ahora_ms // 400) % 4))
            superficie.blit(sello, sello.get_rect(center=(80, 676)))
        self.texto(superficie, f"Voces reunidas: {estado['votos']}", None, 24, VERDE if recien else CREMA, (120, 652))
        puntos = "." * (1 + (ahora_ms // 450) % 3)
        self.texto(superficie, "La comunidad está decidiendo" + puntos, None, 16, CREMA, (120, 684))
        if self.votando_aqui is None:
            self.boton(superficie, "votar_aqui", "Votar aquí", (640, 676), 170)
            self.boton(superficie, "cerrar", "Ver resultado", (840, 676), 190, activo=estado["votos"] > 0)

    def _dibujar_voto_pantalla(self, superficie, estado):
        """Para quien no tiene celular: la misma votación, con el ratón."""
        velo = pygame.Surface((960, 720), pygame.SRCALPHA)
        velo.fill((4, 12, 20, 200))
        superficie.blit(velo, (0, 0))
        caja = pygame.Rect(150, 150, 660, 470)
        pygame.draw.rect(superficie, (23, 58, 46), caja, border_radius=12)
        pygame.draw.rect(superficie, ORO, caja, 3, border_radius=12)
        self.texto(superficie, "Vota desde esta pantalla", (480, 186), 24, ORO)
        self.texto(superficie, "1. ¿Qué haces con este mensaje?", (480, 236), 18)
        for i, (clave, nombre) in enumerate(DECISIONES):
            marca = "» " if self.votando_aqui.get("decision") == clave else ""
            self.boton(superficie, "decision:" + clave, marca + nombre, (255 + i * 150, 286), 140)
        self.texto(superficie, "2. ¿Qué tipo de información es?", (480, 356), 18)
        for i, (clave, nombre) in enumerate(CATEGORIAS):
            marca = "» " if self.votando_aqui.get("categoria") == clave else ""
            self.boton(superficie, "categoria:" + clave, marca + nombre, (290 + i * 190, 406), 180, tam=16)
        self.parrafo(superficie, estado["caso"]["tablilla"], 200, 452, 560, 20, CREMA)
        listo = bool(self.votando_aqui.get("decision") and self.votando_aqui.get("categoria"))
        self.boton(superficie, "enviar_pantalla", "Enviar mi voz", (380, 540), 200, activo=listo)
        self.boton(superficie, "cancelar_pantalla", "Cancelar", (590, 540), 160)

    def _dibujar_resultado(self, superficie, estado):
        resultado = estado["resultado"] or {}
        hueco = self.hueco_resultado
        if self.marco is not None:
            superficie.blit(self.marco, ORIGEN_PANEL)
        else:
            self._respaldo_panel(superficie, hueco)
        if self.colectivo is not None:
            superficie.blit(self.colectivo, self.colectivo.get_rect(topright=(930, 30)))
        etiqueta = self.fuentes[24].render("RESULTADO COLECTIVO", True, ORO)
        caja = etiqueta.get_rect(center=(480, 140)).inflate(28, 10)
        pygame.draw.rect(superficie, (23, 58, 46), caja, border_radius=8)
        pygame.draw.rect(superficie, ORO, caja, 2, border_radius=8)
        superficie.blit(etiqueta, etiqueta.get_rect(center=caja.center))
        caldero = self.calderos.get(resultado.get("caldero"))
        if caldero is not None:
            superficie.blit(caldero, caldero.get_rect(midleft=(hueco.x + 6, hueco.centery + 6)))
        x = hueco.x + 196
        ancho = hueco.right - x - 12
        total = max(1, resultado.get("total", 0))
        y = hueco.y + 10
        for clave, nombre in DECISIONES:
            cantidad = resultado.get("decisiones", {}).get(clave, 0)
            fraccion = cantidad / total
            self.texto(superficie, nombre, None, 16, TINTA, (x, y))
            barra = pygame.Rect(x + 96, y + 3, ancho - 150, 14)
            pygame.draw.rect(superficie, (214, 198, 172), barra, border_radius=3)
            pygame.draw.rect(superficie, COLORES_DECISION[clave], (barra.x, barra.y, round(barra.width * fraccion), barra.height),
                             border_radius=3)
            self.texto(superficie, f"{round(fraccion * 100)} %", None, 16, TINTA, (barra.right + 8, y))
            y += 24
        aciertos = resultado.get("aciertos_categoria", 0)
        y = self.parrafo(superficie, f"Era un {resultado.get('nombre_categoria', '')}: lo reconoció el "
                                     f"{round(aciertos / total * 100)} % de las voces.", x, y + 6, ancho, 16, TINTA)
        y = self.parrafo(superficie, resultado.get("verdad", ""), x, y + 4, ancho, 16, (120, 40, 30))
        self.parrafo(superficie, resultado.get("ensenanza", ""), x, y + 4, ancho, 16, TINTA_SUAVE)
        mensaje = {"positivo": "La Copa respira: la mayoría verificó o detuvo el mensaje.",
                   "critico": "El rumor se propagó: demasiadas voces compartieron sin comprobar.",
                   "dudoso": "La Copa duda: el grupo se dividió entre verificar y dejar pasar."}
        self.texto(superficie, mensaje.get(resultado.get("caldero"), ""), (480, 628), 18,
                   VERDE if resultado.get("caldero") == "positivo" else ROJO if resultado.get("caldero") == "critico" else CREMA)
        self.texto(superficie, f"{resultado.get('total', 0)} voces en esta ronda · {estado['participantes']} en la sesión",
                   (480, 656), 14)
        self.boton(superficie, "nueva", "Nueva ronda", (480, 694), 220, 34, 16)

    # --- Entrada ----------------------------------------------------------------
    def accionar(self, clave):
        if clave == "votar_aqui":
            self.votando_aqui = {}
        elif clave == "cerrar":
            self.sesion.cerrar_ronda()
        elif clave == "nueva":
            self.sesion.abrir_ronda()
            self.ultimo_total = 0
        elif clave.startswith("decision:") and self.votando_aqui is not None:
            self.votando_aqui["decision"] = clave.split(":", 1)[1]
        elif clave.startswith("categoria:") and self.votando_aqui is not None:
            self.votando_aqui["categoria"] = clave.split(":", 1)[1]
        elif clave == "enviar_pantalla" and self.votando_aqui:
            from feria.sesion import VotoInvalido
            self.votos_pantalla += 1
            try:
                self.sesion.votar(f"pantalla-{self.votos_pantalla:04d}", self.sesion.ronda_actual,
                                  self.votando_aqui.get("decision"), self.votando_aqui.get("categoria"))
            except VotoInvalido:
                pass
            self.votando_aqui = None
        elif clave == "cancelar_pantalla":
            self.votando_aqui = None

    def tecla(self, tecla):
        """Atajos del presentador: Espacio/Enter cierra la ronda, N abre otra."""
        if self.votando_aqui is not None:
            return
        if tecla in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER) and self.sesion.abierta:
            self.sesion.cerrar_ronda()
        elif tecla == pygame.K_n and not self.sesion.abierta:
            self.accionar("nueva")


def jugar_desde_menu(lienzo, audio=None, cuadros=0, servidor=None, al_dibujar=None):
    """Feria de los Ecos QR desde el menú. Esc vuelve (None); cerrar la ventana, "salir".

    Arranca un servidor local en este computador; al salir lo detiene y borra la
    sesión, así que no queda ningún voto guardado. Un error inesperado nunca
    cierra el juego: se explica en pantalla y se anota en cache/feria_error.log."""
    try:
        return _jugar(lienzo, cuadros, servidor, al_dibujar)
    except Exception as error:  # noqa: BLE001 — el juego sigue aunque la feria falle
        _anotar_error()
        return _error_red(lienzo, f"{type(error).__name__}: {error}")


def _anotar_error():
    import traceback
    from nucleo.rutas import RAIZ
    try:
        carpeta = RAIZ / "cache"
        carpeta.mkdir(exist_ok=True)
        with open(carpeta / "feria_error.log", "a", encoding="utf-8") as registro:
            registro.write(time.strftime("%Y-%m-%d %H:%M:%S ") + traceback.format_exc() + "\n")
    except OSError:
        pass


def _jugar(lienzo, cuadros, servidor, al_dibujar):
    from interfaz.presentacion_pantalla import a_lienzo, presentar
    from feria.web import ServidorFeriaLocal, ip_local
    import importlib.util
    if importlib.util.find_spec("segno") is None:
        # Se comprueba antes de abrir el servidor: así no queda ningún puerto ocupado.
        return _error_red(lienzo, "Falta la librería del QR (segno). Abre el juego con Jugar.bat o instala "
                                  "requirements.txt en el Python que uses.")
    propio = servidor is None
    aviso_red = ""
    try:
        servidor = servidor or ServidorFeriaLocal().iniciar()
    except RuntimeError as error:
        return _error_red(lienzo, str(error))
    sesion = servidor.registro.crear()
    reloj, cuadro = pygame.time.Clock(), 0
    try:
        ip = ip_local()
        if ip.startswith("127."):
            aviso_red = "Sin red: conecta este computador a una Wi-Fi para que los celulares puedan votar."
        pantalla_feria = PantallaFeria(sesion, servidor.url(sesion.codigo_sesion, ip), aviso_red)
        while True:
            reloj.tick(60)
            pantalla = pygame.display.get_surface()
            tamano = pantalla.get_size() if pantalla is not None else (960, 720)
            mouse = a_lienzo(pygame.mouse.get_pos(), tamano)
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    return "salir"
                if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                    if pantalla_feria.votando_aqui is not None:
                        pantalla_feria.votando_aqui = None
                        continue
                    return None
                if evento.type == pygame.KEYDOWN:
                    pantalla_feria.tecla(evento.key)
                if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    posicion = a_lienzo(evento.pos, tamano)
                    for clave, boton in list(pantalla_feria.botones.items()):
                        if boton.fue_clickeado(posicion):
                            pantalla_feria.accionar(clave)
                            break
            pantalla_feria.dibujar(lienzo, mouse, pygame.time.get_ticks())
            pista = pantalla_feria.fuentes[14].render("Esc: volver al menú · Espacio: ver resultado · N: nueva ronda",
                                                      True, (205, 225, 215))
            lienzo.blit(pista, pista.get_rect(topright=(944, 6)))
            if al_dibujar:
                al_dibujar(pantalla_feria, cuadro)
            if pantalla is not None:
                presentar(pantalla, lienzo)
                pygame.display.flip()
            cuadro += 1
            if cuadros and cuadro >= cuadros:
                return None
    finally:
        servidor.registro.cerrar(sesion.codigo_sesion)
        if propio:
            servidor.detener()


def _error_red(lienzo, mensaje):
    """Si no se pudo abrir el servidor, se explica y se vuelve al menú con una tecla."""
    from interfaz.presentacion_pantalla import presentar
    fuente, titulo = cargar_fuente(18), cargar_fuente(32)
    reloj = pygame.time.Clock()
    inicio = time.monotonic()
    while time.monotonic() - inicio < 30:
        reloj.tick(30)
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return "salir"
            if evento.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return None
        lienzo.fill((10, 24, 20))
        lienzo.blit(titulo.render("No se pudo abrir la Feria de los Ecos", True, ORO), (120, 280))
        y = 340
        for linea in envolver_texto(mensaje, fuente, 720)[:5]:
            lienzo.blit(fuente.render(linea, True, CREMA), (120, y))
            y += 28
        lienzo.blit(fuente.render("El detalle queda en cache/feria_error.log.", True, CREMA), (120, y + 14))
        lienzo.blit(fuente.render("Pulsa cualquier tecla para volver al menú.", True, CREMA), (120, y + 54))
        pantalla = pygame.display.get_surface()
        if pantalla is not None:
            presentar(pantalla, lienzo)
            pygame.display.flip()
    return None
