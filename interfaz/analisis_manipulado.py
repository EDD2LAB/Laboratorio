"""Análisis de Distrito Conecta: comparar video, escuchar la nota de voz y examinar la foto.

Todo se carga y se escala una sola vez, al llegar al Distrito; aquí el cliente
solo señala: qué cuenta como marca lo decide el servidor. Las coordenadas son las
del arte (ComparadordeVideos y PanelAnaliDeContenido) en el lienzo 960x720.
"""
import array
import wave

import pygame

from interfaz.arte import MULTI, NUEVOS, icono
from interfaz.boton import Boton
from nucleo.recursos import cargar_imagen, cargar_spritesheet_frames
from nucleo.rutas import RAIZ

CARPETA = "Manipulado/procesado/"
FPS_VIDEO = 6
CUADROS = 8
CREMA = (244, 236, 222)
TINTA = (31, 49, 62)
OSCURO = (45, 38, 76)
CORAL = (239, 110, 84)
AZUL_PISTA = (96, 136, 196)
ORO = (214, 150, 42)
VERDE = (76, 170, 110)
CLARO = (235, 228, 214)

PANEL_IZQ = pygame.Rect(64, 102, 388, 292)
PANEL_DER = pygame.Rect(511, 103, 386, 290)
TITULO_IZQ = pygame.Rect(190, 62, 165, 30)
TITULO_DER = pygame.Rect(625, 62, 150, 30)
BARRA = pygame.Rect(83, 444, 797, 19)
BANDA = pygame.Rect(68, 492, 823, 56)
CONTROLES = {"anterior": pygame.Rect(72, 572, 66, 66), "play": pygame.Rect(157, 572, 66, 66),
             "pausa": pygame.Rect(243, 572, 66, 66), "siguiente": pygame.Rect(327, 572, 66, 66),
             "marcar": pygame.Rect(413, 572, 66, 66)}
HUECOS = (pygame.Rect(545, 569, 110, 71), pygame.Rect(665, 569, 108, 71), pygame.Rect(784, 569, 107, 71))
FILA_INFERIOR = pygame.Rect(60, 564, 840, 84)
TAMANO_ONDA = (372, 130)

MESA_FOTOS = pygame.Rect(38, 38, 582, 566)
FOTO_ORIGINAL = pygame.Rect(54, 78, 272, 272)
FOTO_MANIPULADA = pygame.Rect(334, 78, 272, 272)
BARRAS_EVIDENCIA = tuple(pygame.Rect(761, y, 136, 18) for y in (300, 351, 402, 453))
MEDIDOR = pygame.Rect(652, 557, 255, 28)
FRANJA = pygame.Rect(16, 612, 928, 100)
RADIO_LUPA = 46
AUMENTO = 2
DURACION_CONCLUSION_MS = 1900


class ReproductorVideo:
    """A 6 cuadros por segundo; pausar y avanzar deja el cuadro fijo."""

    def __init__(self):
        self.pausado = False
        self.base = 0
        self.inicio = pygame.time.get_ticks()

    def frame(self):
        if self.pausado:
            return self.base
        return (self.base + (pygame.time.get_ticks() - self.inicio) * FPS_VIDEO // 1000) % CUADROS

    def pausar(self):
        self.base = self.frame()
        self.pausado = True

    def reanudar(self):
        if self.pausado:
            self.pausado = False
            self.inicio = pygame.time.get_ticks()

    def alternar(self):
        if self.pausado:
            self.reanudar()
        else:
            self.pausar()

    def paso(self, delta):
        self.pausar()
        self.base = (self.base + delta) % CUADROS

    def ir_a(self, cuadro):
        self.pausar()
        self.base = cuadro % CUADROS


class PistaAudio:
    """Muestras, forma de onda y sonido, una sola vez y sin numpy."""

    def __init__(self, ruta, color):
        with wave.open(str(ruta), "rb") as audio:
            tasa = audio.getframerate()
            muestras = array.array("h", audio.readframes(audio.getnframes()))
        self.duracion = len(muestras) / tasa
        self.pico = max(abs(m) for m in muestras)
        ancho, alto = TAMANO_ONDA
        paso = max(1, len(muestras) // ancho)
        self.forma = pygame.Surface(TAMANO_ONDA, pygame.SRCALPHA)
        for x in range(ancho):
            nivel = max((abs(m) for m in muestras[x * paso:(x + 1) * paso]), default=0)
            medio = round(nivel / 32768 * alto / 2)
            pygame.draw.line(self.forma, color, (x, alto // 2 - medio), (x, alto // 2 + medio))
        self.sonido = None
        if pygame.mixer.get_init():
            try:
                self.sonido = pygame.mixer.Sound(str(ruta))
                self.sonido.set_volume(.8)
            except pygame.error as error:
                print("[Audio] No se pudo cargar", ruta, error)


class ArteAnalisis:
    def __init__(self, sello_manipulado):
        self.video_original = cargar_spritesheet_frames(CARPETA + "video_original.png", CUADROS)
        self.video_manipulado = cargar_spritesheet_frames(CARPETA + "video_manipulado.png", CUADROS)
        self.miniaturas = [pygame.transform.scale(f, (74, 72)) for f in self.video_manipulado]
        self.foto_original = cargar_imagen(CARPETA + "foto_original.png")
        self.foto_manipulada = cargar_imagen(CARPETA + "foto_manipulada.png")
        lado = FOTO_ORIGINAL.size
        self.foto_original_vista = pygame.transform.scale(self.foto_original, lado)
        self.foto_manipulada_vista = pygame.transform.scale(self.foto_manipulada, lado)
        carpeta_audio = RAIZ / "Audios" / "Presente"
        self.audios = {"original": PistaAudio(carpeta_audio / "audio_original.wav", AZUL_PISTA),
                       "suplantado": PistaAudio(carpeta_audio / "audio_suplantado.wav", CORAL)}
        self.icono_audio = icono(NUEVOS + "icono_audio.png", (64, 64))
        self.icono_video = icono(NUEVOS + "icono_video.png", (64, 64))
        self.lupa = icono(MULTI + "LupaMemorActive.png", (42, 42))
        self.perfil = self._componer_perfil()
        self.nucleo = self._componer_nucleo()
        self.mascara_lupa = pygame.Surface((RADIO_LUPA * 2, RADIO_LUPA * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.mascara_lupa, (255, 255, 255, 255), (RADIO_LUPA, RADIO_LUPA), RADIO_LUPA)
        suplantacion = cargar_imagen("Estados/Suplantacióndetectada.png", requerido=False)
        self.sellos = {"manipulado": sello_manipulado, "suplantacion": [suplantacion] if suplantacion else []}
        self.video = ReproductorVideo()
        self.sonando = None
        self.canal_voz = None
        self.inicio_audio = 0
        self.vacios = {}
        self.conclusiones_vistas = set()
        self.conclusion_activa = None

    def _componer_perfil(self):
        """Tarjeta del perfil falso con la foto manipulada encima."""
        original = cargar_imagen(NUEVOS + "perfil_falso.png")
        tarjeta = original.subsurface(original.get_bounding_rect(min_alpha=200)).copy()
        ancho, alto = tarjeta.get_size()
        lado = round(ancho * .4)
        tarjeta.blit(pygame.transform.scale(self.foto_manipulada, (lado, lado)), (round(ancho * .54), round(alto * .36)))
        return tarjeta

    @staticmethod
    def _componer_nucleo():
        """Avatar provisional de NÚCLEO: una esfera luminosa, sin cara (ver docs/futuro.md)."""
        lado = 104
        imagen = pygame.Surface((lado, lado), pygame.SRCALPHA)
        for radio, alfa in ((50, 40), (42, 80), (32, 150)):
            pygame.draw.circle(imagen, (70, 220, 230, alfa), (lado // 2, lado // 2), radio)
        pygame.draw.circle(imagen, (225, 255, 255, 255), (lado // 2, lado // 2), 18)
        return imagen

    def _musica_en_pausa(self, en_pausa):
        """La música calla mientras se escucha la grabación."""
        from audio.audio_manager import GestorAudio
        if pygame.mixer.get_init():
            for indice in GestorAudio.CANALES_MUSICA:
                canal = pygame.mixer.Channel(indice)
                canal.pause() if en_pausa else canal.unpause()

    def reproducir(self, nombre):
        if self.canal_voz is not None:
            self.canal_voz.stop()
        self.sonando, self.inicio_audio = nombre, pygame.time.get_ticks()
        if self.audios[nombre].sonido is not None:
            self.canal_voz = pygame.mixer.find_channel(True)  # siempre hay un canal, aunque estén ocupados
            self.canal_voz.play(self.audios[nombre].sonido)
            self._musica_en_pausa(True)

    def progreso_audio(self):
        """(pista, segundos) de lo que suena, o (None, 0) si ya terminó."""
        if self.sonando is None:
            return None, 0
        segundos = (pygame.time.get_ticks() - self.inicio_audio) / 1000
        if segundos >= self.audios[self.sonando].duracion:
            self.sonando = None
            self._musica_en_pausa(False)
            return None, 0
        return self.sonando, segundos

    def lanzar_conclusion(self, conclusion_id, sello):
        """El sello de conclusión sale una sola vez por event_id."""
        if conclusion_id is None or conclusion_id in self.conclusiones_vistas:
            return False
        self.conclusiones_vistas.add(conclusion_id)
        self.conclusion_activa = (sello, pygame.time.get_ticks())
        return True

    def dibujar_conclusion(self, superficie):
        if self.conclusion_activa is None:
            return
        sello, inicio = self.conclusion_activa
        transcurrido = pygame.time.get_ticks() - inicio
        cuadros = self.sellos.get(sello) or []
        if transcurrido >= DURACION_CONCLUSION_MS or not cuadros:
            self.conclusion_activa = None
            return
        cuadro = cuadros[(transcurrido // 160) % len(cuadros)]
        superficie.blit(cuadro, cuadro.get_rect(center=(480, 280)))


# ------------------------------------------------------------------ utilidades
def _zona(panel, ui, clave, rect):
    """Zona clicable invisible sobre el arte."""
    vacia = ui.vacios.setdefault(rect.size, pygame.Surface(rect.size, pygame.SRCALPHA))
    boton = Boton("", vacia, rect.center)
    boton.actualizar(panel.vista.mouse)
    panel.botones[clave] = boton
    return boton


def _boton_texto(panel, clave, texto, rect, superficie):
    from interfaz.celular import PALETA
    boton = Boton(texto, centro=rect.center, fuente=panel.pequena, tamano=rect.size, paleta=PALETA)
    boton.dibujar(superficie, panel.vista.mouse)
    panel.botones[clave] = boton


def _rotulo(panel, superficie, rect, texto):
    pygame.draw.rect(superficie, CREMA, rect)
    render = panel.fuente.render(texto, True, TINTA)
    superficie.blit(render, render.get_rect(center=rect.center))


def _analisis_de(contexto):
    return contexto.get("analisis") or {"disponible": False, "total": 0, "minimo": 0, "halladas": [], "concluido": False}


def _cabecera(analisis):
    estado = "¡Análisis concluido!" if analisis.get("concluido") else f"Se necesitan {analisis.get('minimo', 0)}"
    return f"Marcas {len(analisis.get('halladas', []))} de {analisis.get('total', 0)} · {estado}"


def _lista_marcas(panel, superficie, analisis, x, y, ancho, color, columnas=1):
    for indice, marca in enumerate(analisis.get("halladas", [])):
        fila, columna = (indice // columnas, indice % columnas)
        render = panel.pequena.render(marca["texto"], True, color)
        superficie.blit(render, (x + columna * ancho // columnas, y + fila * 18))


# ------------------------------------------------------------------ video
def _cuadro_centrado(superficie, cuadro, rect):
    superficie.blit(cuadro, cuadro.get_rect(center=rect.center))


def _dibujar_video(panel, superficie, analisis, arte):
    ui = arte.ui
    if arte.comparador is not None:
        superficie.blit(arte.comparador, (0, 0))
    _rotulo(panel, superficie, TITULO_IZQ, "ORIGINAL")
    _rotulo(panel, superficie, TITULO_DER, "PUBLICADO")
    for rect in (PANEL_IZQ, PANEL_DER):
        pygame.draw.rect(superficie, CREMA, rect.inflate(-8, -8))
    cuadro = ui.video.frame()
    if analisis.get("disponible"):
        _cuadro_centrado(superficie, ui.video_original[cuadro], PANEL_IZQ)
    else:
        panel.texto_lineas(superficie, "Habla con Darío Veraz para conseguir el video original.",
                           PANEL_IZQ.x + 30, PANEL_IZQ.centery - 20, PANEL_IZQ.w - 60, panel.fuente, TINTA)
    _cuadro_centrado(superficie, ui.video_manipulado[cuadro], PANEL_DER)
    if _zona(panel, ui, "analisis:marcar_video", PANEL_DER).hover:
        pygame.draw.rect(superficie, ORO, PANEL_DER.inflate(-4, -4), 3, border_radius=6)
    marcados = {f for marca in analisis.get("halladas", []) for f in marca.get("frames", ())}
    pygame.draw.rect(superficie, OSCURO, BARRA.inflate(14, 12), border_radius=6)
    ancho = BARRA.width / CUADROS
    for i in range(CUADROS):
        zona = pygame.Rect(round(BARRA.x + i * ancho), BARRA.y, round(ancho) - 2, BARRA.height)
        pygame.draw.rect(superficie, CORAL if i in marcados else AZUL_PISTA, zona)
        if i == cuadro:
            pygame.draw.rect(superficie, (255, 255, 255), zona, 2)
        _zona(panel, ui, f"analisis:frame:{i}", zona)
    pygame.draw.rect(superficie, OSCURO, BANDA, border_radius=6)
    linea = _cabecera(analisis) + " · Espacio: pausa · ← →: cuadro · E o clic: marcar"
    superficie.blit(panel.pequena.render(linea, True, CLARO), (BANDA.x + 10, BANDA.y + 2))
    _lista_marcas(panel, superficie, analisis, BANDA.x + 10, BANDA.y + 20, BANDA.width - 20, CLARO, 2)
    for nombre, rect in CONTROLES.items():
        if _zona(panel, ui, "analisis:" + nombre, rect).hover:
            pygame.draw.rect(superficie, ORO, rect, 3, border_radius=10)
    for hueco, marca in zip(HUECOS, analisis.get("halladas", [])):
        _cuadro_centrado(superficie, ui.miniaturas[marca["frames"][0]], hueco)


# ------------------------------------------------------------------ nota de voz
def _caja_onda(panel_rect):
    return pygame.Rect(panel_rect.x + 7, panel_rect.y + 84, *TAMANO_ONDA)


def _dibujar_pista(panel, superficie, ui, rect, nombre, titulo, cerrado=False):
    pista = ui.audios[nombre]
    if ui.icono_audio is not None:
        superficie.blit(ui.icono_audio, (rect.x + 10, rect.y + 10))
    superficie.blit(panel.fuente.render(titulo, True, TINTA), (rect.x + 84, rect.y + 24))
    caja = _caja_onda(rect)
    pygame.draw.rect(superficie, OSCURO, caja, border_radius=4)
    if cerrado:
        panel.texto_lineas(superficie, "Consigue la grabación auténtica en la Sede del Aspirante.",
                           caja.x + 20, caja.y + 40, caja.w - 40, panel.pequena, CLARO)
        return caja
    superficie.blit(pista.forma, caja)
    sonando, segundos = ui.progreso_audio()
    if sonando == nombre:
        x = caja.x + round(segundos / pista.duracion * caja.w)
        pygame.draw.line(superficie, (255, 255, 255), (x, caja.y), (x, caja.bottom), 2)
    _boton_texto(panel, "analisis:reproducir:" + nombre, "Reproducir", pygame.Rect(rect.centerx - 80, rect.bottom - 58, 160, 38), superficie)
    return caja


def _dibujar_audio(panel, superficie, analisis, arte):
    ui = arte.ui
    if arte.comparador is not None:
        superficie.blit(arte.comparador, (0, 0))
    _rotulo(panel, superficie, TITULO_IZQ, "ORIGINAL")
    _rotulo(panel, superficie, TITULO_DER, "NOTA DE VOZ")
    for rect in (PANEL_IZQ, PANEL_DER):
        pygame.draw.rect(superficie, CREMA, rect.inflate(-8, -8))
    _dibujar_pista(panel, superficie, ui, PANEL_IZQ, "original", "Grabación auténtica", not analisis.get("disponible"))
    caja = _dibujar_pista(panel, superficie, ui, PANEL_DER, "suplantado", "La que circula")
    duracion = ui.audios["suplantado"].duracion
    for marca in analisis.get("halladas", []):
        if "rango" in marca:
            x1, x2 = (caja.x + round(s / duracion * caja.w) for s in marca["rango"])
            velo = pygame.Surface((max(1, x2 - x1), caja.h), pygame.SRCALPHA)
            velo.fill((*ORO, 90))
            superficie.blit(velo, (x1, caja.y))
    if _zona(panel, ui, "analisis:onda", caja).hover:
        pygame.draw.rect(superficie, ORO, caja, 2, border_radius=4)
    pygame.draw.rect(superficie, OSCURO, BARRA.inflate(14, 12), border_radius=6)
    sonando, segundos = ui.progreso_audio()
    if sonando:
        relleno = BARRA.copy()
        relleno.width = round(BARRA.width * segundos / ui.audios[sonando].duracion)
        pygame.draw.rect(superficie, CORAL if sonando == "suplantado" else AZUL_PISTA, relleno)
    pygame.draw.rect(superficie, OSCURO, BANDA, border_radius=6)
    instruccion = _cabecera(analisis) + " · Escucha las dos y haz clic en la onda donde algo suene mal."
    superficie.blit(panel.pequena.render(instruccion, True, CLARO), (BANDA.x + 10, BANDA.y + 20))
    pygame.draw.rect(superficie, CREMA, FILA_INFERIOR, border_radius=8)
    _boton_texto(panel, "analisis:zona:saturacion", "Comparar volumen", pygame.Rect(72, 586, 190, 40), superficie)
    if any(m["id"] == "saturacion" for m in analisis.get("halladas", [])):
        picos = f"Pico: original {ui.audios['original'].pico} · nota de voz {ui.audios['suplantado'].pico}"
        superficie.blit(panel.pequena.render(picos, True, TINTA), (72, 628))
    _lista_marcas(panel, superficie, analisis, 290, 576, 600, TINTA)


# ------------------------------------------------------------------ foto
def _dibujar_lupa(superficie, ui, posicion):
    escala = ui.foto_manipulada.get_width() / FOTO_MANIPULADA.width
    area = pygame.Rect(0, 0, RADIO_LUPA * 2 // AUMENTO, RADIO_LUPA * 2 // AUMENTO)
    area.center = ((posicion[0] - FOTO_MANIPULADA.x) * escala, (posicion[1] - FOTO_MANIPULADA.y) * escala)
    area.clamp_ip(ui.foto_manipulada.get_rect())
    vista = pygame.transform.scale(ui.foto_manipulada.subsurface(area), (RADIO_LUPA * 2, RADIO_LUPA * 2))
    vista.blit(ui.mascara_lupa, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    superficie.blit(vista, vista.get_rect(center=posicion))
    pygame.draw.circle(superficie, ORO, posicion, RADIO_LUPA, 3)
    pygame.draw.circle(superficie, (255, 255, 255), posicion, 2)
    if ui.lupa is not None:
        superficie.blit(ui.lupa, ui.lupa.get_rect(center=(posicion[0] + 38, posicion[1] + 38)))


def _dibujar_foto(panel, superficie, analisis, arte):
    ui = arte.ui
    if arte.analisis is not None:
        superficie.blit(arte.analisis, (0, 0))
    pygame.draw.rect(superficie, CREMA, MESA_FOTOS, border_radius=12)
    pygame.draw.rect(superficie, OSCURO, MESA_FOTOS, 3, border_radius=12)
    for rect, texto in ((FOTO_ORIGINAL, "ORIGINAL · Café Digital"), (FOTO_MANIPULADA, "DEL PERFIL FALSO")):
        render = panel.fuente.render(texto, True, TINTA)
        superficie.blit(render, render.get_rect(midbottom=(rect.centerx, rect.y - 6)))
    if analisis.get("disponible"):
        superficie.blit(ui.foto_original_vista, FOTO_ORIGINAL)
    else:
        pygame.draw.rect(superficie, CLARO, FOTO_ORIGINAL)
        panel.texto_lineas(superficie, "Consigue la foto original en el Café Digital.", FOTO_ORIGINAL.x + 24,
                           FOTO_ORIGINAL.centery - 20, FOTO_ORIGINAL.w - 48, panel.fuente, TINTA)
    superficie.blit(ui.foto_manipulada_vista, FOTO_MANIPULADA)
    for marca in analisis.get("halladas", []):
        x, y, ancho, alto = marca["rect"]
        pygame.draw.rect(superficie, ORO, (FOTO_MANIPULADA.x + x * FOTO_MANIPULADA.w, FOTO_MANIPULADA.y + y * FOTO_MANIPULADA.h,
                                           ancho * FOTO_MANIPULADA.w, alto * FOTO_MANIPULADA.h), 2)
    superficie.blit(panel.fuente.render(_cabecera(analisis), True, TINTA), (54, 364))
    _lista_marcas(panel, superficie, analisis, 54, 394, 550, TINTA)
    halladas, minimo = len(analisis.get("halladas", [])), max(1, analisis.get("minimo", 1))
    for barra, encendida in zip(BARRAS_EVIDENCIA, (i < halladas for i in range(len(BARRAS_EVIDENCIA)))):
        if encendida:
            pygame.draw.rect(superficie, VERDE, barra, border_radius=8)
    punta = MEDIDOR.x + round(MEDIDOR.width * min(1, halladas / minimo))
    pygame.draw.polygon(superficie, OSCURO, ((punta - 8, MEDIDOR.y - 10), (punta + 8, MEDIDOR.y - 10), (punta, MEDIDOR.y + 2)))
    pygame.draw.rect(superficie, (19, 39, 49), FRANJA, border_radius=8)
    pygame.draw.rect(superficie, (106, 218, 204), FRANJA, 2, border_radius=8)
    panel.texto_lineas(superficie, "Pasa la lupa por la foto del perfil y haz clic donde veas algo alterado.",
                       FRANJA.x + 14, FRANJA.y + 14, 250, panel.pequena, (153, 222, 214))
    _zona(panel, ui, "analisis:foto", FOTO_MANIPULADA)
    if FOTO_MANIPULADA.collidepoint(panel.vista.mouse):
        _dibujar_lupa(superficie, ui, panel.vista.mouse)


PANTALLAS = {"video": _dibujar_video, "audio": _dibujar_audio, "foto": _dibujar_foto}


def _tipo(contexto):
    return (contexto.get("evento") or {}).get("tipo", "video")


def dibujar(panel, superficie, contexto, arte):
    PANTALLAS[_tipo(contexto)](panel, superficie, _analisis_de(contexto), arte)


# ------------------------------------------------------------------ entrada
def _marcar_cuadro(panel, cliente):
    cliente.actuar("presente_marcar", frame=panel.vista.celular.ui.video.frame())


def tecla(panel, codigo, cliente):
    """Controles del comparador; devuelve True si la tecla era suya."""
    if _tipo(panel.contexto()) != "video":
        return False
    video = panel.vista.celular.ui.video
    if codigo == pygame.K_SPACE:
        video.alternar()
    elif codigo in (pygame.K_LEFT, pygame.K_RIGHT):
        video.paso(1 if codigo == pygame.K_RIGHT else -1)
    elif codigo == pygame.K_e:
        _marcar_cuadro(panel, cliente)
    else:
        return False
    return True


def accion(panel, clave, posicion, cliente):
    ui = panel.vista.celular.ui
    nombre = clave.split(":", 1)[1]
    if nombre in ("marcar", "marcar_video"):
        _marcar_cuadro(panel, cliente)
    elif nombre == "anterior":
        ui.video.paso(-1)
    elif nombre == "siguiente":
        ui.video.paso(1)
    elif nombre == "play":
        ui.video.reanudar()
    elif nombre == "pausa":
        ui.video.pausar()
    elif nombre.startswith("frame:"):
        ui.video.ir_a(int(nombre.split(":")[1]))
    elif nombre.startswith("reproducir:"):
        ui.reproducir(nombre.split(":")[1])
    elif nombre.startswith("zona:"):
        cliente.actuar("presente_marcar", zona=nombre.split(":")[1])
    elif nombre == "onda":
        caja = _caja_onda(PANEL_DER)
        segundo = (posicion[0] - caja.x) / caja.w * ui.audios["suplantado"].duracion
        cliente.actuar("presente_marcar", segundo=round(segundo, 2))
    elif nombre == "foto":
        cliente.actuar("presente_marcar", x=round((posicion[0] - FOTO_MANIPULADA.x) / FOTO_MANIPULADA.w, 4),
                       y=round((posicion[1] - FOTO_MANIPULADA.y) / FOTO_MANIPULADA.h, 4))
