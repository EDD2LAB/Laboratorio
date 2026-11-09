"""Menú inicial y sala de espera LAN, dibujados sobre un lienzo 960x720."""
import os
import json
import queue
import socket
import threading

import pygame

from interfaz import arte
from interfaz.boton import Boton
from interfaz.logo import LogoAnimado
from interfaz.edicion_texto import EditorCampos
from interfaz.menu_pausa import MenuPausa
from interfaz.presentacion_pantalla import a_lienzo, presentar
from multijugador.cliente import ClienteSala
from multijugador.cliente_internet import ClienteInternet, validar_url
from multijugador.servidor import ServidorSala
from multijugador.protocolo import PUERTO, ROLES, NOMBRES_ROLES
from nucleo import portapapeles
from nucleo.recursos import cargar_fuente

BASE = os.path.dirname(os.path.dirname(__file__))
ORO = (237, 185, 87)
CREMA = (255, 243, 210)
VERDE = (136, 219, 155)
CENTRO_LOGO = (480, 124)
DESCRIPCIONES_ROL = (
    "Busca pistas y revisa los mensajes.", "Lleva pistas a tus compañeros.",
    "Habla con los vecinos y ayuda.", "Explica lo que pasó usando pistas.")


class MenuInicio:
    def __init__(self):
        self.mouse = (-1, -1)
        self.vista = "principal"
        self.partida = None
        self.pausa = MenuPausa(self)
        self.audio = self._crear_audio()
        self._musica_menu()
        self.pantalla = self.pausa.crear_pantalla()  # maximizada por defecto
        pygame.display.set_caption("Timeless Glitch")
        self.lienzo = pygame.Surface((960, 720))
        self.fuentes = {n: cargar_fuente(n) for n in (14, 16, 18, 20, 24, 32, 44)}
        self.fondo = self.imagen("Fondos/Multijugador/FondoFernado.png", (1080, 725), recortar=False)
        self.iconos = [self.imagen("Iconos/Multijugador/" + nombre, (54, 54)) for nombre in (
            "IcRol-guardian.png", "IcRol-Mensajero.png", "IcRol-Habitante.png", "IcRol-Aspirante.png")]
        self.retratos = {clave: arte.cargar_retratos(clave, (105, 105)) for clave in (*ROLES, "mira", "luma")}
        self.logo = LogoAnimado()
        self.emblemas_ayuda = arte.cargar_emblemas((56, 56))
        self.iconos_ajustes = {nombre: arte.icono(arte.NUEVOS + "icono_" + nombre + ".png", (30, 30))
                               for nombre in ("audio", "contraste", "apariencia", "libro", "arbol")}
        self.arbol_clasificacion = None  # se carga al abrir esa pestaña
        self.icono_sonido = arte.icono(arte.NUEVOS + "icono_sonido.png", (24, 24))
        self.icono_silencio = arte.icono(arte.NUEVOS + "icono_silencio.png", (24, 24))
        self.corona = self.imagen("Iconos/Multijugador/IcAnfitrión.png", (26, 26))
        self.listo = self.imagen("Iconos/Multijugador/IcListo.png", (28, 28))
        tira = pygame.image.load(os.path.join(BASE, "Imagenes", "Iconos", "Multijugador", "IcEsperaAnimate.png")).convert_alpha()
        self.espera = [pygame.transform.scale(tira.subsurface((i * 146, 0, 146, 146)), (28, 28)) for i in range(8)]
        self.vista = "principal"
        self.internet = True
        self.codigo_sala = ""
        self.anfitrion = False
        try:
            with open(os.path.join(BASE, "multijugador", "configuracion.json"), encoding="utf-8") as archivo:
                url = json.load(archivo).get("servidor_internet", "")
        except (OSError, ValueError, AttributeError):
            url = ""
        self.campos = {"nombre": "", "ip": "", "puerto": str(PUERTO),
                       "servidor": os.environ.get("COPA_SERVIDOR_INTERNET", url), "codigo": "", "sala": ""}
        self.editor = EditorCampos(
            self.campos, {"nombre": 20, "ip": 45, "puerto": 5, "servidor": 180, "codigo": 6, "sala": 40},
            {"puerto": lambda t: "".join(c for c in t if c in "0123456789"),
             "codigo": lambda t: "".join(c for c in t.upper() if c.isascii() and c.isalnum())},
            solo_lectura=("sala",))
        self.arrastrando = None  # campo en el que se selecciona con el ratón
        self.foco = "nombre"
        self.botones = {}
        self.areas_campos = {}
        self.cliente = None
        self.servidor = None
        self.identificador = None
        self.estado = {"jugadores": [], "iniciada": False}
        self.partida = None
        self.campana_local = False
        self.rol_solo = ROLES[0]
        self.dificultad_solo = "normal"
        self.mensaje = ""
        self.error = False
        self.conectando = False
        self.ips = "Consultando las direcciones locales…"
        self._direcciones = queue.Queue()
        threading.Thread(target=self._buscar_ip, daemon=True).start()

    def _crear_audio(self):
        """Gestor de audio compartido por el menú y las partidas (volúmenes guardados)."""
        try:
            from audio.audio_manager import GestorAudio
            from nucleo.rutas import RAIZ
            audio = GestorAudio(str(RAIZ), categorias=True)
        except Exception as error:  # sin mezclador (pruebas, equipos sin sonido)
            print("[Audio] Desactivado:", error)
            return False
        self.pausa.aplicar_volumenes(audio)
        return audio

    def _musica_menu(self):
        if self.audio:
            self.audio.reproducir_musica("introduccion", en_bucle=True)

    def _buscar_ip(self):
        try:
            ips = socket.gethostbyname_ex(socket.gethostname())[2]
            ips = list(dict.fromkeys(ip for ip in ips if not ip.startswith("127.")))
            self._direcciones.put(" / ".join(ips) if ips else "Consulta IPv4 con ipconfig")
        except OSError:
            self._direcciones.put("Consulta IPv4 con ipconfig")

    def imagen(self, ruta, tamano, recortar=True):
        imagen = pygame.image.load(os.path.join(BASE, "Imagenes", *ruta.split("/"))).convert_alpha()
        if recortar:
            limites = imagen.get_bounding_rect()
            if limites.width and limites.height:
                imagen = imagen.subsurface(limites)
        factor = min(tamano[0] / imagen.get_width(), tamano[1] / imagen.get_height())
        return pygame.transform.scale(imagen, (round(imagen.get_width() * factor), round(imagen.get_height() * factor)))

    def texto(self, texto, x, y, size=20, color=CREMA, centro=False):
        render = self.fuentes[size].render(texto, True, color)
        rect = render.get_rect(midtop=(x, y)) if centro else render.get_rect(topleft=(x, y))
        self.lienzo.blit(render, rect)

    def parrafo(self, texto, rect, size=16, color=CREMA):
        fuente = self.fuentes[size]
        y, linea = rect.y, ""
        for palabra in texto.split() + [None]:
            prueba = f"{linea} {palabra}".strip() if palabra is not None else ""
            if linea and (palabra is None or fuente.size(prueba)[0] > rect.width):
                self.texto(linea, rect.x, y, size, color)
                y += fuente.get_linesize() + 3
                linea = palabra or ""
            else:
                linea = prueba

    def panel(self, rect, color=(13, 32, 26, 232), borde=ORO):
        capa = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(capa, color, capa.get_rect(), border_radius=14)
        self.lienzo.blit(capa, rect)
        pygame.draw.rect(self.lienzo, borde, rect, 2, border_radius=14)

    def campo_texto(self, clave, rect, size):
        """Campo editable con su cursor parpadeante; el texto largo se desplaza."""
        self.panel(rect, (9, 24, 20, 255), ORO if clave == self.foco else (88, 113, 93))
        self.areas_campos[clave] = rect
        fuente = self.fuentes[size]
        texto = self.campos[clave]
        cursor, _ = self.editor.posiciones(clave)
        inicio, fin = self.editor.seleccion(clave)
        x = self._origen_texto(clave, rect, size)
        y = rect.centery - fuente.get_height() // 2
        clip = self.lienzo.get_clip()
        self.lienzo.set_clip(rect.inflate(-20, -8))
        if self.foco == clave and inicio != fin:
            izquierda = x + fuente.size(texto[:inicio])[0]
            pygame.draw.rect(self.lienzo, (46, 104, 150), (izquierda, y, fuente.size(texto[inicio:fin])[0], fuente.get_height()))
        self.texto(texto, x, y, size)
        if self.foco == clave and inicio == fin and pygame.time.get_ticks() % 1000 < 500:
            barra = x + fuente.size(texto[:cursor])[0] + 1
            pygame.draw.line(self.lienzo, CREMA, (barra, rect.y + 9), (barra, rect.bottom - 10), 2)
        self.lienzo.set_clip(clip)

    def _origen_texto(self, clave, rect, size):
        """Donde empieza el texto: se desplaza para que el cursor quede a la vista."""
        fuente = self.fuentes[size]
        cursor, _ = self.editor.posiciones(clave)
        return rect.x + 12 - max(0, fuente.size(self.campos[clave][:cursor])[0] - rect.width + 30)

    def _apariencia(self, rol):
        return self.pausa.preferencias.get("apariencia_" + rol, "hombre") if rol else None

    def aplicar_preferencias(self):
        """Lleva los ajustes guardados a la partida en curso."""
        if self.partida is None:
            return
        p = self.pausa.preferencias
        self.partida.hud.alto_contraste = p["alto_contraste"]
        self.partida.narrador.activo = p["narracion"]

    def _indice_raton(self, clave, x):
        size = self._tamano_campo(clave)
        return self.editor.indice_en(clave, x - self._origen_texto(clave, self.areas_campos[clave], size), self.fuentes[size])

    def _tamano_campo(self, clave):
        return 18 if self.vista in ("campana_rol", "sala") else 20

    def boton(self, clave, texto, centro, ancho=270, activo=True, alto=48, tamano_fuente=20):
        boton = Boton(texto, centro=centro, fuente=self.fuentes[tamano_fuente], tamano=(ancho, alto), desactivado=not activo)
        boton.dibujar(self.lienzo, self.mouse)
        self.botones[clave] = boton

    def limpiar_conexion(self):
        if self.cliente:
            self.cliente.cerrar()
        if self.servidor:
            self.servidor.cerrar()
        self.cliente = self.servidor = None
        self.identificador = None
        self.codigo_sala = ""
        self.estado = {"jugadores": [], "iniciada": False}
        volvio_de_partida = self.partida is not None
        self.partida = None
        self.campana_local = False
        self.conectando = False
        if volvio_de_partida:
            self._musica_menu()

    def conectar(self):
        if self.conectando:
            return
        nombre = self.campos["nombre"].strip()
        if not nombre:
            self.mensaje, self.error = "Escribe tu nombre para entrar.", True
            return
        if self.internet:
            try:
                if not self.campos["servidor"].strip():
                    raise ValueError("Falta publicar el servidor de Internet. Cuando esté disponible, escribe su dirección HTTPS aquí.")
                url = validar_url(self.campos["servidor"])
                codigo = self.campos["codigo"].strip().upper()
                if not self.anfitrion and (len(codigo) != 6 or not codigo.isalnum()):
                    raise ValueError("Escribe el código de sala de 6 caracteres.")
                self.limpiar_conexion()
                self.cliente = ClienteInternet(url, nombre, crear=self.anfitrion, codigo=codigo)
                self.conectando = True
                self.mensaje, self.error = "Conectando… El primer arranque del servidor puede tardar. Puedes cancelar mientras esperas.", False
            except ValueError as error:
                self.mensaje, self.error = str(error), True
            return
        try:
            puerto = int(self.campos["puerto"])
            if not 1024 <= puerto <= 65535:
                raise ValueError()
        except ValueError:
            self.mensaje, self.error = "El puerto debe estar entre 1024 y 65535.", True
            return
        ip = self.campos["ip"].strip()
        if not self.anfitrion and not ip:
            self.mensaje, self.error = "Escribe la IP local del anfitrión.", True
            return
        self.limpiar_conexion()
        try:
            if self.anfitrion:
                self.servidor = ServidorSala(puerto)
                self.servidor.iniciar()
            self.cliente = ClienteSala(
                "127.0.0.1" if self.anfitrion else ip, puerto, nombre,
                self.servidor.clave_host if self.servidor else "")
            self.conectando = True
            self.error = False
            self.mensaje = "Conectando…"
        except OSError:
            self.limpiar_conexion()
            self.mensaje, self.error = "No se pudo abrir el puerto. Prueba otro o cierra la sala anterior.", True

    def recibir(self):
        try:
            self.ips = self._direcciones.get_nowait()
        except queue.Empty:
            pass
        while self.cliente:
            try:
                evento = self.cliente.eventos.get_nowait()
            except queue.Empty:
                break
            tipo = evento.get("tipo")
            if tipo == "bienvenida":
                self.identificador = evento["id"]
                self.codigo_sala = evento.get("codigo", "")
                self.vista = "sala"
                self.conectando = False
                self.mensaje, self.error = "Elige un rol y confirma que estás listo.", False
                pygame.key.stop_text_input()
            elif tipo == "estado":
                self.estado = evento
                if evento.get("fase") == "partida":
                    try:
                        if self.partida is None:
                            from interfaz.partida_multijugador import VistaPartida
                            self.partida = VistaPartida(self.identificador, evento, self.audio)
                            self.aplicar_preferencias()
                        else:
                            self.partida.recibir(evento)
                        self.vista = "partida"
                    except (OSError, ValueError, RuntimeError) as error:
                        self.limpiar_conexion()
                        self.vista = "formulario"
                        self.mensaje, self.error = str(error), True
                        continue
                if evento["iniciada"]:
                    self.mensaje, self.error = "Todos los jugadores confirmaron el equipo.", False
            elif tipo == "reconectando":
                self.mensaje, self.error = evento["mensaje"], False
                if self.partida:
                    self.partida.aviso_red = evento["mensaje"]
            elif tipo == "acuse":
                if self.partida:
                    self.partida.panel.recibir(evento)
            elif tipo == "error":
                self.mensaje, self.error = evento["mensaje"], True
                if self.partida:
                    self.partida.panel.notificar(evento["mensaje"])
            elif tipo in ("rechazado", "desconectado"):
                self.limpiar_conexion()
                self.vista = "formulario"
                self.mensaje = (evento["mensaje"] if tipo == "rechazado" or self.internet else
                                "No hay conexión con el anfitrión. Comprueba que la sala siga abierta, la IP, el puerto y el permiso de Python en la red privada.")
                self.error = True
                pygame.key.start_text_input()

    def accionar(self, clave):
        self.mensaje, self.error = "", False
        if clave.startswith("pausa:"):
            return self.pausa.accionar(clave.split(":", 1)[1])
        if clave == "abrir_pausa":
            self.pausa.abrir()
            return
        if clave == "ajustes":
            self.pausa.abrir("ajustes")
            return
        if clave == "ayuda_f1":
            self.pausa.abrir("ayuda_f1")
            return
        if clave == "copiar_sala":
            portapapeles.copiar(self.campos["sala"])
            self.mensaje, self.error = "Copiado. Pégalo con Ctrl+V donde quieras compartirlo.", False
            return
        if clave == "alternar_hud" and self.partida:
            self.partida.mostrar_hud = not self.partida.mostrar_hud
            return
        if clave == "campana_local":
            self.vista = "campana_rol"
            self.foco = "nombre"
            pygame.key.start_text_input()
        elif clave.startswith("rol_solo:"):
            self.rol_solo = clave.split(":", 1)[1]
        elif clave.startswith("dificultad_solo:"):
            self.dificultad_solo = clave.split(":", 1)[1]
        elif clave == "iniciar_campana_solo":
            nombre = self.campos["nombre"].strip()
            if not nombre:
                self.mensaje, self.error = "Escribe tu nombre para iniciar.", True
                return
            try:
                from interfaz.partida_multijugador import VistaPartida
                from multijugador.partida_local import ClienteCampanaLocal
                self.limpiar_conexion()
                self.cliente = ClienteCampanaLocal(
                    nombre,
                    self.rol_solo,
                    self.dificultad_solo,
                    apariencia=self._apariencia(self.rol_solo),
                )
                self.campana_local = True
                self.identificador = self.cliente.identificador
                self.codigo_sala = "LOCAL"
                self.estado = self.cliente.eventos.get_nowait()
                self.partida = VistaPartida(self.identificador, self.estado, self.audio)
                self.aplicar_preferencias()
                self.vista = "partida"
                pygame.key.stop_text_input()
            except (OSError, ValueError, RuntimeError) as error:
                self.limpiar_conexion()
                self.vista = "campana_rol"
                self.mensaje, self.error = str(error), True
            return
        if clave == "salir":
            return "salir"
        if clave == "multi":
            self.vista = "multijugador"
        elif clave in ("crear", "unirse"):
            self.anfitrion = clave == "crear"
            self.vista = "formulario"
            self.foco = "nombre"
            pygame.key.start_text_input()
        elif clave == "conectar":
            self.conectar()
        elif clave == "volver":
            if self.vista == "campana_rol":
                self.vista = "principal"
                pygame.key.stop_text_input()
            elif self.campana_local:
                self.limpiar_conexion()
                self.vista = "campana_rol"
                pygame.key.start_text_input()
            else:
                self.limpiar_conexion()
                self.vista = "principal" if self.vista == "multijugador" else "multijugador"
                pygame.key.stop_text_input()
        elif clave.startswith("rol:") and self.cliente:
            rol = clave.split(":")[1]
            yo = next((j for j in self.estado["jugadores"] if j["id"] == self.identificador), {})
            self.cliente.enviar("rol", rol=None if yo.get("rol") == rol else rol, apariencia=self._apariencia(rol))
        elif clave == "listo" and self.cliente:
            yo = next((j for j in self.estado["jugadores"] if j["id"] == self.identificador), {})
            self.cliente.enviar("listo", listo=not yo.get("listo", False))
        elif clave == "iniciar" and self.cliente:
            self.cliente.enviar("iniciar")

    def dibujar(self):
        self.botones, self.areas_campos = {}, {}
        self.lienzo.blit(self.fondo, self.fondo.get_rect(center=(480, 360)))
        velo = pygame.Surface((960, 720), pygame.SRCALPHA)
        velo.fill((4, 17, 13, 120))
        self.lienzo.blit(velo, (0, 0))
        if self.vista == "principal":
            self.panel(pygame.Rect(240, 70, 480, 590))
            self.logo.dibujar(self.lienzo, CENTRO_LOGO, pygame.time.get_ticks())
            self.texto("TIMELESS GLITCH", 480, 172, 44, ORO, True)
            self.texto("Era I: La Copa · Era II: Distrito Conecta · Era III: Ciudad Núcleo", 480, 230, 14, centro=True)
            self.boton("campana_local", "Campaña con bots", (480, 300))
            self.boton("multi", "Multijugador", (480, 380))
            self.boton("ajustes", "Ajustes", (480, 460))
            self.boton("ayuda_f1", "Ayuda · F1", (480, 525))
            self.boton("salir", "Salir", (480, 600))
        elif self.vista == "campana_rol":
            self.panel(pygame.Rect(16, 16, 928, 688))
            self.texto("CAMPAÑA LOCAL CON BOTS", 480, 34, 32, ORO, True)
            self.texto("Elige tu personaje. Los otros tres los controlará un bot.", 480, 80, 16, centro=True)
            self.texto("Tu nombre", 250, 122, 18)
            self.campo_texto("nombre", pygame.Rect(355, 112, 360, 42), 18)
            for indice, rol in enumerate(ROLES):
                elegido = rol == self.rol_solo
                self.tarjeta_rol(indice, 170, elegido, "rol_solo:" + rol, "Elegido" if elegido else "Elegir")
            self.texto("Dificultad de los bots", 480, 448, 18, ORO, True)
            for indice, dificultad in enumerate(("facil", "normal", "dificil")):
                etiqueta = {"facil": "Fácil", "normal": "Normal", "dificil": "Difícil"}[dificultad]
                self.boton(
                    "dificultad_solo:" + dificultad,
                    f"» {etiqueta} «" if dificultad == self.dificultad_solo else etiqueta,
                    (300 + indice * 180, 498),
                    155,
                )
            self.boton("iniciar_campana_solo", "Iniciar campaña", (570, 590), 250)
            self.boton("volver", "Volver", (340, 590), 190)
            if self.mensaje:
                self.parrafo(
                    self.mensaje,
                    pygame.Rect(205, 635, 550, 38),
                    14,
                    (255, 161, 145) if self.error else CREMA,
                )
        elif self.vista == "multijugador":
            self.panel(pygame.Rect(200, 95, 560, 540))
            self.texto("MULTIJUGADOR", 480, 140, 32, ORO, True)
            self.texto("De 2 a 4 jugadores · Una PC por jugador", 480, 200, 18, centro=True)
            self.boton("crear", "Crear partida", (480, 305))
            self.boton("unirse", "Unirse a partida", (480, 375))
            self.boton("volver", "Volver", (480, 465))
            self.parrafo("Juega desde redes diferentes usando un código de sala." if self.internet else
                         "Conecta computadores de la misma red mediante la IP del anfitrión.", pygame.Rect(255, 540, 450, 65), 16)
        elif self.vista == "formulario":
            self.panel(pygame.Rect(160, 55, 640, 610))
            self.texto("CREAR PARTIDA" if self.anfitrion else "UNIRSE A PARTIDA", 480, 90, 32, ORO, True)
            campos = [("nombre", "Tu nombre", 195), ("puerto", "Puerto", 360)] if self.anfitrion else [
                ("nombre", "Tu nombre", 170), ("ip", "IP del anfitrión", 270), ("puerto", "Puerto", 370)]
            if self.internet:
                campos = [("nombre", "Tu nombre", 220)] if self.anfitrion else [
                    ("nombre", "Tu nombre", 195), ("codigo", "Código de sala", 345)]
            for clave, etiqueta, y in campos:
                self.texto(etiqueta, 230, y, 18)
                self.campo_texto(clave, pygame.Rect(230, y + 29, 500, 46), 20)
            if self.anfitrion:
                self.parrafo("Recibirás un código para invitar a tus compañeros desde cualquier red." if self.internet else
                             "Tus compañeros usarán tu IP local. Al salir de la sala se desconectará todo el equipo.", pygame.Rect(230, 295, 500, 65), 16)
            self.boton("conectar", "Conectando…" if self.conectando else ("Crear sala" if self.anfitrion else "Conectar"), (610, 510), 235, not self.conectando)
            self.boton("volver", "Cancelar" if self.conectando else "Volver", (345, 510), 200)
            self.parrafo(self.mensaje, pygame.Rect(215, 560, 535, 95), 16, (255, 161, 145) if self.error else CREMA)
        elif self.vista == "sala":
            self.dibujar_sala()
        elif self.vista == "partida" and self.partida:
            titulo = "CAMPAÑA LOCAL" if self.campana_local else self.codigo_sala
            self.partida.dibujar(self.lienzo, titulo, self.mouse)
            if not self.partida.panel.activo and (self.partida.mostrar_detalles or not self.partida.mostrar_hud):
                # Con los detalles abiertos o el HUD oculto (para poder recuperarlo).
                texto_hud = "Ocultar HUD · H" if self.partida.mostrar_hud else "Mostrar HUD · H"
                self.boton("alternar_hud", texto_hud, (757, 689), 150, alto=34, tamano_fuente=16)
                self.boton("abrir_pausa", "Menú · Esc", (892, 689), 110, alto=34, tamano_fuente=16)
        if self.pausa.activo:
            self.pausa.dibujar()

    def tarjeta_rol(self, indice, y, resaltada, clave, texto_boton, activo=True):
        """Tarjeta de personaje con retrato; la usan la sala y la campaña con bots."""
        x = 32 + indice * 228
        self.panel(pygame.Rect(x, y, 212, 265), (34, 58, 39, 245), VERDE if resaltada else ORO)
        self.texto(NOMBRES_ROLES[indice], x + 106, y + 15, 24, ORO, True)
        variante = {"aspirante": "mira", "habitante": "luma"}.get(ROLES[indice])
        frames = self.retratos[variante if variante and self._apariencia(ROLES[indice]) == "mujer" else ROLES[indice]]
        # El personaje elegido cambia de expresión; los demás quedan quietos.
        retrato = arte.expresion(frames, pygame.time.get_ticks()) if resaltada else (frames[0] if frames else None)
        if retrato is not None:
            self.lienzo.blit(retrato, retrato.get_rect(midbottom=(x + 106, y + 150)))
        self.lienzo.blit(self.iconos[indice], (x + 12, y + 75))
        self.parrafo(DESCRIPCIONES_ROL[indice], pygame.Rect(x + 14, y + 159, 184, 55), 14)
        self.boton(clave, texto_boton, (x + 106, y + 237), 176, activo)

    def dibujar_sala(self):
        self.panel(pygame.Rect(16, 16, 928, 688))
        self.texto("SALA DE ESPERA", 480, 38, 32, ORO, True)
        direccion = self.ips if self.anfitrion else self.campos["ip"].strip()
        self.campos["sala"] = self.codigo_sala if self.internet else f"{direccion}:{self.campos['puerto']}"
        self.texto("Código de sala:" if self.internet else "IP y puerto:", 44, 92, 16)
        ancho_campo = 120 if self.internet else 320
        self.campo_texto("sala", pygame.Rect(170, 84, ancho_campo, 36), 18)
        self.boton("copiar_sala", "Copiar", (170 + ancho_campo + 62, 102), 104, alto=34, tamano_fuente=16)
        self.texto("Comparte este dato con tu equipo", 170 + ancho_campo + 130, 92, 16)
        self.texto("Elijan personajes distintos y pulsen Estoy listo. Los roles libres los cubrirá un bot.", 44, 132, 14)
        jugadores = self.estado["jugadores"]
        yo = next((j for j in jugadores if j["id"] == self.identificador), {})
        for i in range(4):
            x = 32 + i * 228
            self.panel(pygame.Rect(x, 156, 212, 91), (26, 47, 35, 245), (102, 128, 104))
            if i >= len(jugadores):
                self.texto("Esperando jugador", x + 14, 188, 16, (163, 181, 163))
                continue
            jugador = jugadores[i]
            self.texto(jugador["nombre"][:16], x + 12, 171, 18, ORO if jugador["id"] == self.identificador else CREMA)
            self.texto(NOMBRES_ROLES[ROLES.index(jugador["rol"])] if jugador["rol"] else "Sin rol", x + 12, 205, 16)
            icono = self.listo if jugador["listo"] else self.espera[(pygame.time.get_ticks() // 150) % 8]
            self.lienzo.blit(icono, (x + 170, 207))
            if jugador["anfitrion"]:
                self.lienzo.blit(self.corona, (x + 173, 167))
        for i, rol in enumerate(ROLES):
            dueno = next((j for j in jugadores if j["rol"] == rol), None)
            mio = bool(dueno and dueno["id"] == self.identificador)
            self.tarjeta_rol(i, 275, mio, "rol:" + rol, "Elegir otro" if mio else "Ocupado" if dueno else "Elegir",
                             (not dueno or mio) and not self.estado["iniciada"])
        self.boton("volver", "Salir de sala", (157, 605), 220)
        self.boton("listo", "No estoy listo" if yo.get("listo") else "Estoy listo", (480, 605), 240,
                   bool(yo.get("rol")) and not self.estado["iniciada"])
        if yo.get("anfitrion"):
            preparado = len(jugadores) >= 2 and all(j["listo"] for j in jugadores)
            self.boton("iniciar", "Iniciar partida", (795, 605), 255, preparado and not self.estado["iniciada"])
        else:
            self.parrafo("El anfitrión confirma el equipo.", pygame.Rect(690, 580, 210, 65), 16)
        mensaje = self.mensaje
        if self.estado["iniciada"]:
            mensaje = "Preparando La Copa para el equipo…"
        self.parrafo(mensaje, pygame.Rect(44, 651, 866, 48), 16, (255, 161, 145) if self.error else VERDE)

    def ejecutar(self):
        reloj = pygame.time.Clock()
        try:
            while True:
                segundos = reloj.tick(60) / 1000
                # Pygame 2 redimensiona la superficie al maximizar o cambiar el tamaño.
                self.pantalla = pygame.display.get_surface() or self.pantalla
                tamano = self.pantalla.get_size()
                self.mouse = a_lienzo(pygame.mouse.get_pos(), tamano)
                self.recibir()
                # Preparar las áreas clicables antes de procesar la entrada.
                if self.vista == "partida" and self.partida and self.cliente:
                    self.partida.en_pausa = self.pausa.activo
                    self.partida.actualizar(segundos, self.cliente)
                    if self.campana_local and not self.pausa.activo:  # la campaña local se detiene
                        self.cliente.actualizar(segundos)
                        self.recibir()
                self.dibujar()
                for evento in pygame.event.get():
                    if evento.type == pygame.QUIT:
                        return "salir"
                    if evento.type == pygame.KEYDOWN and evento.key == pygame.K_F1:
                        self.pausa.abrir("ayuda_f1")
                        continue
                    if evento.type == pygame.KEYDOWN and evento.key == pygame.K_F11:
                        self.pausa.alternar_pantalla_completa()
                        continue
                    if self.pausa.activo and evento.type == pygame.KEYDOWN:
                        resultado = self.pausa.tecla(evento.key)
                        if resultado:
                            return resultado
                        continue
                    if not self.pausa.activo and self.vista == "partida" and self.partida:
                        posicion = a_lienzo(evento.pos, tamano) if hasattr(evento, "pos") else self.mouse
                        if self.partida.manejar_evento(evento, posicion, self.cliente):
                            continue
                        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                            self.pausa.abrir()  # Esc ya no saca de la partida: abre el menú
                            continue
                    if evento.type == pygame.VIDEORESIZE:
                        pass  # la superficie se toma de pygame.display.get_surface()
                    elif evento.type == pygame.TEXTINPUT and self.vista in ("formulario", "campana_rol") and not self.conectando:
                        self.editor.insertar("nombre" if self.vista == "campana_rol" else self.foco, evento.text)
                    elif evento.type == pygame.KEYDOWN:
                        if evento.key == pygame.K_ESCAPE:
                            if self.vista == "principal":
                                return "salir"
                            self.accionar("volver")
                        elif self.vista == "sala" and self.campos["sala"]:
                            self.editor.manejar_tecla(evento, "sala")
                        elif self.vista in ("formulario", "campana_rol"):
                            if not self.conectando and self.editor.manejar_tecla(
                                    evento, "nombre" if self.vista == "campana_rol" else self.foco):
                                pass
                            elif evento.key == pygame.K_TAB:
                                campos = list(self.areas_campos)
                                self.foco = campos[(campos.index(self.foco) + 1) % len(campos)]
                            elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                                self.conectar()
                    elif evento.type == pygame.MOUSEMOTION and self.arrastrando in self.areas_campos and evento.buttons[0]:
                        self.editor.colocar(self.arrastrando, self._indice_raton(self.arrastrando, a_lienzo(evento.pos, tamano)[0]), True)
                    elif evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                        self.arrastrando = None
                    elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                        pos = a_lienzo(evento.pos, tamano)
                        for clave, rect in self.areas_campos.items():
                            if rect.collidepoint(pos):
                                self.foco = clave
                                self.arrastrando = clave
                                indice = self._indice_raton(clave, pos[0])
                                if getattr(evento, "clicks", 1) >= 2:
                                    self.editor.seleccionar_todo(clave)
                                else:
                                    self.editor.colocar(clave, indice)
                        for clave, boton in list(self.botones.items()):
                            if boton.fue_clickeado(pos):
                                resultado = self.accionar(clave)
                                if resultado:
                                    return resultado
                                break
                self.dibujar()
                activo = any(b.rect.collidepoint(self.mouse) and not b.desactivado for b in self.botones.values())
                if self.vista == "partida" and self.partida and not self.pausa.activo:
                    activo = activo or self.partida.cursor_interactivo(self.mouse)
                try:
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if activo else pygame.SYSTEM_CURSOR_ARROW)
                except pygame.error:
                    pass
                presentar(self.pantalla, self.lienzo)  # el juego llega hasta los bordes
                pygame.display.flip()
        finally:
            pygame.key.stop_text_input()
            self.limpiar_conexion()


def mostrar_menu_inicio():
    pygame.init()
    return MenuInicio().ejecutar()
