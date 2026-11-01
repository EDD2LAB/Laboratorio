"""Menú inicial y sala de espera LAN, dibujados sobre un lienzo 960x720."""
import os
import json
import queue
import socket
import threading

import pygame

from interfaz.boton import Boton
from multijugador.cliente import ClienteSala
from multijugador.cliente_internet import ClienteInternet, validar_url
from multijugador.servidor import ServidorSala
from multijugador.protocolo import PUERTO, ROLES, NOMBRES_ROLES

BASE = os.path.dirname(os.path.dirname(__file__))
ORO = (237, 185, 87)
CREMA = (255, 243, 210)
VERDE = (136, 219, 155)


class MenuInicio:
    def __init__(self):
        self.pantalla = pygame.display.set_mode((1100, 825), pygame.RESIZABLE)
        pygame.display.set_caption("La Copa — Consejo de los Ecos")
        self.lienzo = pygame.Surface((960, 720))
        self.fuentes = {n: pygame.font.Font(os.path.join(BASE, "Fuentes", "determination.ttf"), n)
                        for n in (14, 16, 18, 20, 24, 32, 44)}
        self.fondo = self.imagen("Fondos/Multijugador/FondoFernado.png", (1080, 725), recortar=False)
        self.iconos = [self.imagen("Iconos/Multijugador/" + nombre, (54, 54)) for nombre in (
            "IcRol-guardian.png", "IcRol-Mensajero.png", "IcRol-Habitante.png", "IcRol-Aspirante.png")]
        self.retratos = [self.imagen("Retratos/" + nombre, (105, 105)) for nombre in (
            "Retrato Guardián/RetratoGuardian_Num1.png",
            "Retrato Mensajero/RetratoMensajero_Num1.png",
            "Retrato Habitante Hombre/RetratoHabitanteH_Num1.png",
            "Retrato Aspirante Hombre/RetratoAspiranteH_Num1.png")]
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
                       "servidor": os.environ.get("COPA_SERVIDOR_INTERNET", url), "codigo": ""}
        self.foco = "nombre"
        self.botones = {}
        self.areas_campos = {}
        self.cliente = None
        self.servidor = None
        self.identificador = None
        self.estado = {"jugadores": [], "iniciada": False}
        self.partida = None
        self.mensaje = ""
        self.error = False
        self.conectando = False
        self.ips = "Consultando las direcciones locales…"
        self._direcciones = queue.Queue()
        threading.Thread(target=self._buscar_ip, daemon=True).start()

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

    def boton(self, clave, texto, centro, ancho=270, activo=True):
        boton = Boton(texto, centro=centro, fuente=self.fuentes[20], tamano=(ancho, 48), desactivado=not activo)
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
        self.partida = None
        self.conectando = False

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
                            self.partida = VistaPartida(self.identificador, evento)
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
            elif tipo == "error":
                self.mensaje, self.error = evento["mensaje"], True
            elif tipo in ("rechazado", "desconectado"):
                self.limpiar_conexion()
                self.vista = "formulario"
                self.mensaje = (evento["mensaje"] if tipo == "rechazado" or self.internet else
                                "No hay conexión con el anfitrión. Comprueba que la sala siga abierta, la IP, el puerto y el permiso de Python en la red privada.")
                self.error = True
                pygame.key.start_text_input()

    def accionar(self, clave):
        self.mensaje, self.error = "", False
        if clave == "individual":
            return "individual"
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
            self.limpiar_conexion()
            self.vista = "principal" if self.vista == "multijugador" else "multijugador"
            pygame.key.stop_text_input()
        elif clave.startswith("rol:") and self.cliente:
            rol = clave.split(":")[1]
            yo = next((j for j in self.estado["jugadores"] if j["id"] == self.identificador), {})
            self.cliente.enviar("rol", rol=None if yo.get("rol") == rol else rol)
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
            self.panel(pygame.Rect(240, 100, 480, 510))
            self.texto("LA COPA", 480, 145, 44, ORO, True)
            self.texto("Consejo de los Ecos", 480, 207, 24, centro=True)
            self.boton("individual", "Un jugador", (480, 315))
            self.boton("multi", "Multijugador", (480, 385))
            self.boton("salir", "Salir", (480, 455))
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
                rect = pygame.Rect(230, y + 29, 500, 46)
                self.panel(rect, (9, 24, 20, 255), ORO if clave == self.foco else (88, 113, 93))
                self.areas_campos[clave] = rect
                texto = self.campos[clave] + ("|" if self.foco == clave and pygame.time.get_ticks() % 1000 < 500 else "")
                ancho = self.fuentes[20].size(texto)[0]
                clip = self.lienzo.get_clip()
                self.lienzo.set_clip(rect.inflate(-20, -8))
                self.texto(texto, rect.x + 12 - max(0, ancho - rect.width + 26), rect.y + 11, 20)
                self.lienzo.set_clip(clip)
            if self.anfitrion:
                self.parrafo("Recibirás un código para invitar a tus compañeros desde cualquier red." if self.internet else
                             "Tus compañeros usarán tu IP local. Al salir de la sala se desconectará todo el equipo.", pygame.Rect(230, 295, 500, 65), 16)
            self.boton("conectar", "Conectando…" if self.conectando else ("Crear sala" if self.anfitrion else "Conectar"), (610, 510), 235, not self.conectando)
            self.boton("volver", "Cancelar" if self.conectando else "Volver", (345, 510), 200)
            self.parrafo(self.mensaje, pygame.Rect(215, 560, 535, 95), 16, (255, 161, 145) if self.error else CREMA)
        elif self.vista == "sala":
            self.dibujar_sala()
        elif self.vista == "partida" and self.partida:
            self.partida.dibujar(self.lienzo, self.codigo_sala)
            self.boton("volver", "Salir", (869, 689), 125)

    def dibujar_sala(self):
        self.panel(pygame.Rect(16, 16, 928, 688))
        self.texto("SALA DE ESPERA", 480, 38, 32, ORO, True)
        direccion = self.ips if self.anfitrion else self.campos["ip"].strip()
        cabecera = (f"Código de sala: {self.codigo_sala} · Comparte este código" if self.internet else
                    f"IP: {direccion}   Puerto: {self.campos['puerto']}")
        self.parrafo(cabecera, pygame.Rect(44, 84, 866, 45), 16)
        self.texto("2–4 jugadores · Cada rol solo puede elegirse una vez", 44, 132, 14)
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
        descripciones = (
            "Contrasta fuentes y verifica la información.", "Transporta mensajes y conecta al equipo.",
            "Escucha testimonios de la comunidad.", "Presenta propuestas y responde rumores.")
        for i, rol in enumerate(ROLES):
            x = 32 + i * 228
            dueno = next((j for j in jugadores if j["rol"] == rol), None)
            mio = dueno and dueno["id"] == self.identificador
            self.panel(pygame.Rect(x, 275, 212, 265), (34, 58, 39, 245), VERDE if mio else ORO)
            self.texto(NOMBRES_ROLES[i], x + 106, 290, 24, ORO, True)
            self.lienzo.blit(self.retratos[i], self.retratos[i].get_rect(midbottom=(x + 106, 425)))
            self.lienzo.blit(self.iconos[i], (x + 12, 350))
            self.parrafo(descripciones[i], pygame.Rect(x + 14, 434, 184, 55), 14)
            self.boton("rol:" + rol, "Liberar rol" if mio else "Ocupado" if dueno else "Elegir", (x + 106, 512), 176,
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
                ancho, alto = self.pantalla.get_size()
                escala = min(ancho / 960, alto / 720)
                destino = pygame.Rect(0, 0, round(960 * escala), round(720 * escala))
                destino.center = (ancho // 2, alto // 2)
                mx, my = pygame.mouse.get_pos()
                self.mouse = ((mx - destino.x) / escala, (my - destino.y) / escala) if destino.collidepoint(mx, my) else (-1, -1)
                self.recibir()
                # Preparar las áreas clicables antes de procesar la entrada.
                if self.vista == "partida" and self.partida and self.cliente:
                    self.partida.actualizar(segundos, self.cliente)
                self.dibujar()
                for evento in pygame.event.get():
                    if evento.type == pygame.QUIT:
                        return "salir"
                    if evento.type == pygame.VIDEORESIZE:
                        self.pantalla = pygame.display.set_mode((max(640, evento.w), max(480, evento.h)), pygame.RESIZABLE)
                    elif evento.type == pygame.TEXTINPUT and self.vista == "formulario" and not self.conectando:
                        limites = {"nombre": 20, "ip": 45, "puerto": 5, "servidor": 180, "codigo": 6}
                        caracteres = evento.text
                        if self.foco == "puerto":
                            caracteres = "".join(c for c in caracteres if c in "0123456789")
                        if self.foco == "codigo":
                            caracteres = "".join(c for c in caracteres.upper() if c.isascii() and c.isalnum())
                        caracteres = "".join(c for c in caracteres if c.isprintable())
                        self.campos[self.foco] = (self.campos[self.foco] + caracteres)[:limites[self.foco]]
                    elif evento.type == pygame.KEYDOWN:
                        if evento.key == pygame.K_ESCAPE:
                            if self.vista == "principal":
                                return "salir"
                            self.accionar("volver")
                        elif self.vista == "formulario":
                            if evento.key == pygame.K_BACKSPACE and not self.conectando:
                                self.campos[self.foco] = self.campos[self.foco][:-1]
                            elif evento.key == pygame.K_TAB:
                                campos = list(self.areas_campos)
                                self.foco = campos[(campos.index(self.foco) + 1) % len(campos)]
                            elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                                self.conectar()
                    elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                        pos = ((evento.pos[0] - destino.x) / escala, (evento.pos[1] - destino.y) / escala)
                        for clave, rect in self.areas_campos.items():
                            if rect.collidepoint(pos):
                                self.foco = clave
                        for clave, boton in list(self.botones.items()):
                            if boton.fue_clickeado(pos):
                                resultado = self.accionar(clave)
                                if resultado:
                                    return resultado
                                break
                self.dibujar()
                activo = any(b.rect.collidepoint(self.mouse) and not b.desactivado for b in self.botones.values())
                try:
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if activo else pygame.SYSTEM_CURSOR_ARROW)
                except pygame.error:
                    pass
                self.pantalla.fill((4, 12, 9))
                self.pantalla.blit(pygame.transform.scale(self.lienzo, destino.size), destino)
                pygame.display.flip()
        finally:
            pygame.key.stop_text_input()
            self.limpiar_conexion()


def mostrar_menu_inicio():
    pygame.init()
    return MenuInicio().ejecutar()
