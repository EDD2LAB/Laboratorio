"""Vista del mapa compartido: sprites locales y posiciones del servidor."""
import math
import os
import time

import pygame

from multijugador.movimiento import ColisionesMapa, es_personaje_jugable
from multijugador.protocolo import ROLES, NOMBRES_ROLES

COLORES = ((83, 222, 212), (241, 199, 86), (183, 137, 246), (247, 140, 120))
DIRECCIONES = ("abajo", "derecha", "arriba", "izquierda")


def separar_frames(imagen, cantidad=8):
    """Usar los espacios transparentes para separar hojas de cuadros desiguales."""
    ocupadas = [imagen.subsurface((x, 0, 1, imagen.get_height())).get_bounding_rect().height > 0
                for x in range(imagen.get_width())]
    huecos, inicio = [], None
    for x, ocupada in enumerate(ocupadas):
        if not ocupada and inicio is None:
            inicio = x
        elif ocupada and inicio is not None:
            if inicio > 0 and x - inicio >= 3:
                huecos.append((x - inicio, (inicio + x) // 2))
            inicio = None
    if len(huecos) >= cantidad - 1:
        cortes = [0] + sorted(x for _, x in sorted(huecos, reverse=True)[:cantidad - 1]) + [imagen.get_width()]
    else:
        cortes = [round(i * imagen.get_width() / cantidad) for i in range(cantidad + 1)]
    frames = []
    for x1, x2 in zip(cortes, cortes[1:]):
        frame = imagen.subsurface((x1, 0, x2 - x1, imagen.get_height())).copy()
        limites = frame.get_bounding_rect()
        if limites.width and limites.height:
            frames.append(frame.subsurface(limites).copy())
    if len(frames) != cantidad:
        raise ValueError("La hoja de personajes no contiene ocho cuadros utilizables.")
    return frames


def cargar_personajes():
    import juego
    carpetas = ("Guardian", "mensajero", "Habitante hombre", "Aspirante hombre")
    caminar = (
        [f"Fila {i}. Guardián.png" for i in range(2, 6)],
        [f"fila {i} mensajero.png" for i in range(2, 6)],
        [f"HabHombre Fila {i}.png" for i in range(2, 6)],
        [f"Corriendo/Aspirante_a_cacique-corriendo_fila{i}.png" for i in range(1, 5)],
    )
    reposo = ("Guardian_reposo_fila", "Mensajero_reposo_fila", "Habitante_hombre_reposo_fila",
              "Aspirante_a_cacique-reposo_fila")
    personajes = {}
    for indice, rol in enumerate(ROLES):
        clips = {}
        for estado in ("caminar", "reposo"):
            for i, direccion in enumerate(DIRECCIONES):
                archivo = caminar[indice][i] if estado == "caminar" else f"Reposo/{reposo[indice]}{i + 1}.png"
                imagen = juego.cargar_imagen(os.path.join("NPCS", carpetas[indice], archivo))
                clips[(estado, direccion)] = separar_frames(imagen)
        alto = max(f.get_height() for frames in clips.values() for f in frames)
        escala = 53 / alto
        personajes[rol] = {
            clave: [pygame.transform.scale(f, (max(1, round(f.get_width() * escala)), max(1, round(f.get_height() * escala))))
                    for f in frames] for clave, frames in clips.items()
        }
    return personajes


class VistaPartida:
    def __init__(self, identificador, estado):
        import juego
        self.identificador = identificador
        self.firma = ColisionesMapa().firma
        self.personajes = cargar_personajes()
        _, decoraciones, _, _, _, _ = juego.cargar_mapa_principal()
        self.decoraciones = [o for o in decoraciones if not es_personaje_jugable(o["nombre"])]
        self.fondo = juego.cargar_imagen("Fondos/Mapas/Pr_MañanaLumi.png", (960, 720))
        self.fuente = juego.cargar_fuente(13)
        self.titulo = juego.cargar_fuente(20)
        self.jugadores = {}
        self.ultimo_paquete = time.monotonic()
        self.estado = estado
        self.frames_eco = juego.cargar_frames_tronco_eco()
        self.recibir(estado)

    def recibir(self, estado):
        mundo = estado.get("mundo", {})
        if mundo.get("firma_mapa") != self.firma:
            raise ValueError("El mapa no coincide con el servidor. Actualiza la rama multijugador en todas las PC y Render.")
        self.estado = estado
        self.ultimo_paquete = time.monotonic()
        presentes = set()
        for jugador in mundo.get("jugadores", []):
            clave = jugador["id"]
            presentes.add(clave)
            destino = pygame.Vector2(jugador["x"], jugador["y"])
            if clave not in self.jugadores:
                self.jugadores[clave] = {"posicion": destino.copy(), "reloj": 0.0}
            self.jugadores[clave].update(datos=jugador, destino=destino)
        for clave in set(self.jugadores) - presentes:
            del self.jugadores[clave]

    def actualizar(self, segundos, cliente):
        teclas = pygame.key.get_pressed()
        dx = int(teclas[pygame.K_d] or teclas[pygame.K_RIGHT]) - int(teclas[pygame.K_a] or teclas[pygame.K_LEFT])
        dy = int(teclas[pygame.K_s] or teclas[pygame.K_DOWN]) - int(teclas[pygame.K_w] or teclas[pygame.K_UP])
        if not pygame.key.get_focused():
            dx = dy = 0
        cliente.mover(dx, dy)
        for jugador in self.jugadores.values():
            factor = 1 - math.exp(-24 * min(segundos, .1))
            jugador["posicion"] = jugador["posicion"].lerp(jugador["destino"], factor)
            jugador["reloj"] += segundos

    def dibujar(self, superficie, codigo):
        import juego
        superficie.blit(self.fondo, (0, 0))
        for objeto in self.decoraciones:
            if objeto.get("tronco_eco") and self.frames_eco:
                frame = self.frames_eco[(pygame.time.get_ticks() // 140) % len(self.frames_eco)]
                superficie.blit(pygame.transform.scale(frame, objeto["rect"].size), objeto["rect"])
            elif objeto.get("puente_animable"):
                juego.dibujar_puente_balanceandose(superficie, objeto, pygame.time.get_ticks())
            elif objeto.get("frames"):
                frames = objeto["frames"]
                superficie.blit(frames[(pygame.time.get_ticks() // 140) % len(frames)], objeto["rect"])
            else:
                superficie.blit(objeto["imagen"], objeto["rect"])
        etiquetas = []
        for jugador in sorted(self.jugadores.values(), key=lambda j: j["posicion"].y):
            datos = jugador["datos"]
            rol = datos["rol"]
            color = COLORES[ROLES.index(rol)]
            x, y = round(jugador["posicion"].x), round(jugador["posicion"].y)
            estado = datos["animacion"] if time.monotonic() - self.ultimo_paquete < .5 else "reposo"
            frames = self.personajes[rol][(estado, datos["direccion"])]
            frame = frames[int(jugador["reloj"] * (9 if estado == "caminar" else 4)) % len(frames)]
            pygame.draw.ellipse(superficie, (17, 28, 22), (x - 14, y - 6, 28, 9))
            pygame.draw.ellipse(superficie, color, (x - 14, y - 6, 28, 9), 2)
            rect = frame.get_rect(midbottom=(x, y))
            superficie.blit(frame, rect)
            nombre = datos["nombre"] + (" (tú)" if datos["id"] == self.identificador else "")
            etiqueta = self.fuente.render(nombre, True, color)
            caja = etiqueta.get_rect(midbottom=(x, rect.top - 7))
            caja.clamp_ip(superficie.get_rect().inflate(-8, -8))
            while any(caja.inflate(12, 8).colliderect(anterior) for _, anterior, *_ in etiquetas) and caja.top > 24:
                caja.y -= 20
            etiquetas.append((etiqueta, caja, color, datos["id"] == self.identificador))
        for etiqueta, caja, color, local in etiquetas:
            pygame.draw.rect(superficie, (13, 29, 23), caja.inflate(10, 6), border_radius=4)
            superficie.blit(etiqueta, caja)
            if local:
                x = caja.centerx
                pygame.draw.polygon(superficie, color, ((x - 5, caja.top - 11), (x + 5, caja.top - 11), (x, caja.top - 5)))
        panel = pygame.Surface((960, 62), pygame.SRCALPHA)
        panel.fill((9, 25, 20, 235))
        superficie.blit(panel, (0, 658))
        etiqueta = self.titulo.render(f"LA COPA · Sala {codigo} · {len(self.jugadores)} jugadores", True, (237, 185, 87))
        superficie.blit(etiqueta, (22, 667))
        ayuda = self.fuente.render("WASD o flechas: caminar juntos | Esc: salir de la partida", True, (255, 243, 210))
        superficie.blit(ayuda, (22, 695))
        if time.monotonic() - self.ultimo_paquete > 1:
            aviso = self.titulo.render("Esperando al servidor…", True, (255, 207, 110))
            superficie.blit(aviso, aviso.get_rect(center=(480, 45)))
