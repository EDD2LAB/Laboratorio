"""Intro de dos viñetas al empezar una partida nueva.

Es local de cada cliente: no envía nada por la red ni detiene al servidor. Si
faltan las imágenes, ``Intro.crear`` devuelve None y la partida empieza directo.
"""
import pygame

FONDO = (9, 18, 22)  # #091216: bandas de la viñeta 16:9
CREMA = (255, 243, 210)
ORO = (237, 185, 87)
APARICION = .5   # segundos del fundido del texto
AVANCE_FERIA = 6.0  # modo feria: cada viñeta avanza sola
PISTA = "Espacio: siguiente · Esc: saltar"
VINETAS = (
    ("Intro/vineta1.png", (960, 720), (
        "En tres épocas distintas, la verdad empezó a romperse.",
        "Un rumor en La Copa, contenido manipulado en Distrito Conecta y una IA que piensa por todos en Ciudad Núcleo.")),
    ("Intro/vineta2.png", (960, 536), (
        "Glitch Hunters: un equipo que viaja por el tiempo para devolverle la verdad a cada época.",
        "Investiguen, verifiquen y decidan juntos.")),
)


class Intro:
    def __init__(self, imagenes, fuente, fuente_pista, feria=False):
        from nucleo.recursos import envolver_texto
        self.imagenes = imagenes
        self.feria = feria
        self.indice = 0
        self.tiempo = 0.0
        self.terminada = False
        self.textos = []  # líneas ya renderizadas por viñeta (no se crean en cada cuadro)
        for _, _, parrafos in VINETAS:
            lineas = []
            for parrafo in parrafos:
                lineas.extend(fuente.render(linea, True, CREMA) for linea in envolver_texto(parrafo, fuente, 880))
            self.textos.append(lineas)
        self.pista = fuente_pista.render(PISTA, True, ORO)
        self.pista.set_alpha(190)
        self.alto_linea = fuente.get_linesize()

    @classmethod
    def crear(cls, feria=False, cargar=None, fuentes=None):
        """La intro lista para mostrarse, o None si falta alguna imagen."""
        if cargar is None:
            from nucleo.recursos import cargar_imagen as cargar
        imagenes = [cargar(ruta, tamano, requerido=False) for ruta, tamano, _ in VINETAS]
        if any(imagen is None for imagen in imagenes):
            print("[Arte] Intro sin imágenes en Imagenes/Intro/: se salta")
            return None
        if fuentes is None:
            from nucleo.recursos import cargar_fuente
            fuentes = (cargar_fuente(20), cargar_fuente(14))
        return cls(imagenes, *fuentes, feria=feria)

    # ------------------------------------------------------------ control
    def siguiente(self):
        self.indice += 1
        self.tiempo = 0.0
        if self.indice >= len(self.imagenes):
            self.terminar()

    def terminar(self):
        self.terminada = True

    def actualizar(self, segundos):
        if self.terminada:
            return
        self.tiempo += segundos
        if self.feria and self.tiempo >= AVANCE_FERIA:
            self.siguiente()

    def manejar_evento(self, evento):
        """Espacio, Enter o clic: siguiente viñeta. Esc: salta toda la intro."""
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_ESCAPE:
                self.terminar()
            elif evento.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.siguiente()
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            self.siguiente()

    # ------------------------------------------------------------- dibujo
    def dibujar(self, lienzo):
        if self.terminada:
            return
        imagen = self.imagenes[self.indice]
        lineas = self.textos[self.indice]
        alto_texto = len(lineas) * self.alto_linea
        if imagen.get_height() < lienzo.get_height():  # viñeta 16:9: bandas arriba y abajo
            lienzo.fill(FONDO)
            caja = imagen.get_rect(center=lienzo.get_rect().center)
            lienzo.blit(imagen, caja)
            banda = pygame.Rect(0, caja.bottom, lienzo.get_width(), lienzo.get_height() - caja.bottom)
        else:  # viñeta 4:3: banda semitransparente abajo, sobre la imagen
            lienzo.blit(imagen, (0, 0))
            alto = alto_texto + 40
            banda = pygame.Rect(0, lienzo.get_height() - alto, lienzo.get_width(), alto)
            capa = pygame.Surface(banda.size, pygame.SRCALPHA)
            capa.fill((5, 20, 25, 200))
            lienzo.blit(capa, banda)
            pygame.draw.line(lienzo, ORO, banda.topleft, banda.topright, 2)
        opacidad = round(255 * min(1.0, self.tiempo / APARICION))
        y = banda.y + (banda.height - 16 - alto_texto) // 2
        for linea in lineas:
            linea.set_alpha(opacidad)
            lienzo.blit(linea, linea.get_rect(midtop=(lienzo.get_width() // 2, y)))
            y += self.alto_linea
        lienzo.blit(self.pista, self.pista.get_rect(bottomright=(lienzo.get_width() - 12, lienzo.get_height() - 6)))
