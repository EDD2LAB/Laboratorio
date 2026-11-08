"""Menú de pausa (Esc) del multijugador y de la campaña con bots.

Vistas: principal (continuar, ajustes, ayuda, salir), ajustes (modo de
pantalla, HUD, volumen), ayuda (controles) y confirmación de salida.
Se dibuja sobre el lienzo 960x720 con las utilidades de ``MenuInicio``.
"""
import warnings

import pygame

from nucleo import preferencias
from nucleo.recursos import envolver_texto
from un_jugador.ventana import tamano_ventana_inicial

ORO = (237, 185, 87)
CREMA = (255, 243, 210)
ROJO = (255, 161, 145)

# (clave de preferencia, nombre visible, método del GestorAudio)
CANALES_VOLUMEN = (
    ("volumen_general", "General", "establecer_volumen_general"),
    ("volumen_musica", "Música", "establecer_volumen_musica"),
    ("volumen_ambiente", "Ambiente", "establecer_volumen_ambiente"),
    ("volumen_efectos", "Efectos de sonido", "establecer_volumen_efectos"),
)

NOMBRES_MODO = {"maximizada": "Ventana maximizada", "ventana": "Modo ventana", "completa": "Pantalla completa"}

CONTROLES = (
    ("Flechas / WASD", "Caminar (con Shift: correr)"),
    ("E", "Ayudar o usar lo que tienes cerca"),
    ("Tab", "Cambiar entre objetivos cercanos"),
    ("I", "Pistas"),
    ("M", "Tu tarea"),
    ("Q", "Habilidad de tu rol"),
    ("J", "Detalles: tarea, indicadores y teclas"),
    ("H", "Ocultar o mostrar todo el HUD"),
    ("L", "Ocultar o mostrar los nombres"),
    ("F11", "Alternar pantalla completa"),
    ("Esc", "Cerrar ventanas / abrir este menú"),
    ("F3", "Depuración de bots"),
)

# Una pestaña por dimensión en la Ayuda de Ajustes: (nombre, párrafos).
PAGINAS_COMO_JUGAR = (
    ("La Copa", (
        "Cada caso empieza con un rumor. Entre todos descubren si es verdad.",
        "1. Sigue la luz hasta tu personaje y pulsa E para conseguir tu pista.",
        "2. Necesitas dos pistas. Pulsa I para leerlas y darlas a un compañero cercano, "
        "o envíalas desde un Tronco de los Ecos.",
        "3. En un tronco eliges con las flechas a quién escribir: a una persona o a todos. "
        "Los bots hacen lo que les pidas, por ejemplo venir al caldero.",
        "4. Vayan al caldero y elijan una poción: Quemar corrige lo falso, Colgar lo difunde "
        "e Ignorar no lo comparte. Con bots decide tu elección; entre personas, la mayoría.",
        "5. Clasifica qué tipo de información era.",
        "6. Después ayuden a la aldea: lleven los materiales al lugar marcado, hagan la actividad "
        "en pareja y confirmen en el caldero. En el primer caso también reparan el Puente 1: "
        "pulsa E tres veces en la zona verde.",
        "Son cuatro casos. Al terminar, la flecha dorada te lleva al portal.",
    )),
    ("Distrito Conecta", (
        "Una imagen viral acusa a Ronaldo Vélez. ¿Es real? Aquí la cámara va cerca de tu "
        "personaje: recorre el mapa para descubrirlo.",
        "1. Para viajar, ve al portal de La Copa y pulsa E. Cada persona del equipo debe "
        "aceptar junto al portal; los bots viajan con ustedes.",
        "2. Habla con las personas marcadas (E) hasta reunir las tres pistas: Darío Veraz, "
        "Tomás Red y Ronaldo Vélez.",
        "3. Vayan a la pantalla pública y elijan una poción: Consultar verifica, Quemar reporta, "
        "Ignorar la deja pendiente y Colgar la comparte. Aquí los bots solo acompañan: deciden las personas.",
        "4. Clasifica la publicación. Si la dejaron pendiente, pueden volver a decidir.",
        "Usa el portal para volver a La Copa. Los indicadores viajan contigo.",
    )),
    ("Ciudad Núcleo", (
        "Ciudad Núcleo es la época del futuro.",
        "Todavía está en construcción: aparece en el portal, pero aún no se puede viajar a ella.",
    )),
)


def aplicar_modo_pantalla(modo):
    """Crea la ventana en el modo pedido y devuelve la superficie de pantalla."""
    if modo == "completa":
        return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_mode(tamano_ventana_inicial(), pygame.RESIZABLE)
    try:
        with warnings.catch_warnings():
            # pygame-ce 2.5 no tiene otra forma de obtener la ventana de display.set_mode.
            warnings.simplefilter("ignore", DeprecationWarning)
            ventana = pygame.Window.from_display_module()
        if modo == "maximizada":
            ventana.maximize()
        else:
            ventana.restore()
            ventana.position = pygame.WINDOWPOS_CENTERED
    except (pygame.error, AttributeError) as error:
        print("[Pantalla] No se pudo ajustar la ventana:", error)
    return pygame.display.get_surface()


class MenuPausa:
    def __init__(self, menu):
        self.menu = menu
        self.vista = None
        self.pagina_ayuda = 0
        self.preferencias = preferencias.cargar()

    @property
    def activo(self):
        return self.vista is not None

    @property
    def en_partida(self):
        return self.menu.vista == "partida" and self.menu.partida is not None

    def abrir(self, vista="principal"):
        self.vista = vista

    def cerrar(self):
        self.vista = None

    # ----------------------------------------------------------- pantalla
    def crear_pantalla(self):
        return aplicar_modo_pantalla(self.preferencias["modo_pantalla"])

    def cambiar_modo(self, modo):
        if modo not in preferencias.MODOS_PANTALLA:
            return
        self.preferencias["modo_pantalla"] = modo
        preferencias.guardar(self.preferencias)
        self.menu.pantalla = self.crear_pantalla()

    def alternar_pantalla_completa(self):
        self.cambiar_modo("maximizada" if self.preferencias["modo_pantalla"] == "completa" else "completa")

    # ------------------------------------------------------------- volumen
    def aplicar_volumenes(self, audio):
        for clave, _, metodo in CANALES_VOLUMEN:
            getattr(audio, metodo)(self.preferencias[clave])

    def cambiar_volumen(self, clave, cambio):
        canal = next((c for c in CANALES_VOLUMEN if c[0] == clave), None)
        if canal is None:
            return
        valor = max(0.0, min(1.0, round(self.preferencias[clave] + cambio, 2)))
        self.preferencias[clave] = valor
        preferencias.guardar(self.preferencias)
        if self.menu.audio:
            getattr(self.menu.audio, canal[2])(valor)

    # ------------------------------------------------------------ entrada
    def tecla(self, tecla):
        """Teclado mientras el menú está abierto (se consume todo)."""
        if tecla == pygame.K_ESCAPE:
            if self.vista == "como_jugar":
                self.vista = "ajustes"
            elif self.vista == "principal" or not self.en_partida:
                self.cerrar()
            else:
                self.vista = "principal"
        elif tecla in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.vista == "confirmar_salida":
            return self.accionar("salir_partida")
        return None

    def accionar(self, clave):
        """Devuelve "salir" para cerrar el juego; None en los demás casos."""
        if clave == "continuar":
            self.cerrar()
        elif clave in ("ajustes", "ayuda", "confirmar_salida", "como_jugar"):
            self.vista = clave
        elif clave.startswith("pagina:"):
            self.pagina_ayuda = int(clave.split(":", 1)[1])
        elif clave == "volver":
            if self.en_partida:
                self.vista = "principal"
            else:
                self.cerrar()
        elif clave.startswith("modo:"):
            self.cambiar_modo(clave.split(":", 1)[1])
        elif clave == "hud" and self.en_partida:
            self.menu.partida.mostrar_hud = not self.menu.partida.mostrar_hud
        elif clave.startswith("volumen:"):
            _, canal, signo = clave.split(":")
            self.cambiar_volumen(canal, .1 if signo == "+" else -.1)
        elif clave == "salir_partida":
            self.cerrar()
            self.menu.accionar("volver")
        elif clave == "cerrar_juego":
            return "salir"
        return None

    # ------------------------------------------------------------- dibujo
    def _boton(self, clave, texto, centro, ancho=300, activo=True, alto=48, tamano_fuente=20):
        self.menu.boton("pausa:" + clave, texto, centro, ancho, activo, alto, tamano_fuente)

    def dibujar(self):
        menu = self.menu
        menu.botones = {}
        menu.areas_campos = {}
        velo = pygame.Surface((960, 720), pygame.SRCALPHA)
        velo.fill((3, 12, 9, 170))
        menu.lienzo.blit(velo, (0, 0))
        getattr(self, "_dibujar_" + self.vista)()

    def _dibujar_principal(self):
        menu = self.menu
        menu.panel(pygame.Rect(280, 110, 400, 500))
        menu.texto("PAUSA", 480, 140, 44, ORO, True)
        aviso = ("La campaña está detenida." if menu.campana_local else
                 "Tus compañeros siguen jugando.")
        menu.texto(aviso, 480, 200, 16, CREMA, True)
        self._boton("continuar", "Continuar", (480, 270))
        self._boton("ajustes", "Ajustes", (480, 345))
        self._boton("ayuda", "Ayuda y controles", (480, 420))
        self._boton("confirmar_salida", "Salir", (480, 525))

    def _dibujar_ajustes(self):
        menu = self.menu
        menu.panel(pygame.Rect(170, 50, 620, 620))
        menu.texto("AJUSTES", 480, 75, 32, ORO, True)
        menu.texto("Pantalla", 480, 118, 20, ORO, True)
        actual = self.preferencias["modo_pantalla"]
        for indice, modo in enumerate(preferencias.MODOS_PANTALLA):
            texto = f"» {NOMBRES_MODO[modo]} «" if modo == actual else NOMBRES_MODO[modo]
            self._boton("modo:" + modo, texto, (480, 165 + indice * 46), 340, alto=38, tamano_fuente=18)
        y = 278
        if self.en_partida:
            visible = menu.partida.mostrar_hud
            self._boton("hud", "HUD: visible (H)" if visible else "HUD: oculto (H)", (480, y + 22), 340,
                        alto=38, tamano_fuente=18)
            y += 52
        menu.texto("Sonido", 480, y + 8, 20, ORO, True)
        for fila, (clave, nombre, _) in enumerate(CANALES_VOLUMEN):
            fila_y = y + 58 + fila * 46
            valor = self.preferencias[clave]
            icono = menu.icono_sonido if valor > 0 else menu.icono_silencio
            if icono is not None:
                menu.lienzo.blit(icono, icono.get_rect(center=(193, fila_y)))
            menu.texto(nombre, 215, fila_y - 10, 18)
            # Barra de nivel
            barra = pygame.Rect(400, fila_y - 7, 180, 14)
            pygame.draw.rect(menu.lienzo, (9, 24, 20), barra, border_radius=7)
            if valor > 0:
                pygame.draw.rect(menu.lienzo, (136, 219, 155),
                                 (barra.x, barra.y, max(8, round(barra.width * valor)), barra.height), border_radius=7)
            pygame.draw.rect(menu.lienzo, ORO, barra, 2, border_radius=7)
            menu.texto(f"{round(valor * 100)}%", 592, fila_y - 10, 18)
            self._boton(f"volumen:{clave}:-", "-", (680, fila_y), 46, valor > 0, alto=36)
            self._boton(f"volumen:{clave}:+", "+", (738, fila_y), 46, valor < 1, alto=36)
        if not self.menu.audio:
            menu.texto("(sin dispositivo de sonido)", 480, y + 58 + 4 * 46 - 14, 14, ROJO, True)
        self._boton("como_jugar", "Ayuda: cómo jugar", (480, 592), 300, alto=36, tamano_fuente=18)
        self._boton("volver", "Volver", (480, 642), 220, alto=40)

    def _dibujar_como_jugar(self):
        menu = self.menu
        menu.panel(pygame.Rect(100, 30, 760, 660))
        menu.texto("CÓMO JUGAR", 480, 48, 32, ORO, True)
        emblema = list(menu.emblemas_ayuda.values())[self.pagina_ayuda]  # mismo orden que las páginas
        if emblema is not None:
            menu.lienzo.blit(emblema, emblema.get_rect(center=(160, 70)))
        for indice, (nombre, _) in enumerate(PAGINAS_COMO_JUGAR):
            texto = f"» {nombre} «" if indice == self.pagina_ayuda else nombre
            self._boton(f"pagina:{indice}", texto, (290 + indice * 190, 112), 178, alto=38, tamano_fuente=16)
        fuente = menu.fuentes[16]
        y = 150
        for parrafo in PAGINAS_COMO_JUGAR[self.pagina_ayuda][1]:
            for linea in envolver_texto(parrafo, fuente, 680):
                menu.texto(linea, 140, y, 16)
                y += fuente.get_linesize() + 2
            y += 8
        self._boton("ajustes", "Volver", (480, 655), 220, alto=40)

    def _dibujar_ayuda(self):
        menu = self.menu
        menu.panel(pygame.Rect(150, 40, 660, 640))
        menu.texto("AYUDA Y CONTROLES", 480, 65, 32, ORO, True)
        for indice, (tecla, accion) in enumerate(CONTROLES):
            y = 116 + indice * 31
            menu.texto(tecla, 190, y, 18, ORO)
            menu.texto(accion, 350, y, 18)
        menu.parrafo("Sigue el anillo y la flecha dorada hasta tu objetivo. Al terminar una dimensión, "
                     "la flecha te lleva al portal para elegir otra época.",
                     pygame.Rect(190, 470 + 20, 580, 80), 16)
        self._boton("volver", "Volver", (480, 630), 220)

    def _dibujar_confirmar_salida(self):
        menu = self.menu
        menu.panel(pygame.Rect(250, 170, 460, 380))
        menu.texto("¿Quieres salir?", 480, 200, 32, ORO, True)
        detalle = ("Se perderá el progreso de esta campaña." if menu.campana_local else
                   "Saldrás de la sala; tus compañeros podrán seguir.")
        menu.parrafo(detalle, pygame.Rect(290, 255, 380, 50), 16, ROJO)
        self._boton("salir_partida", "Sí, volver al menú", (480, 340), 320)
        self._boton("cerrar_juego", "Cerrar el juego", (480, 405), 320)
        self._boton("continuar", "No, seguir jugando", (480, 490), 320)
