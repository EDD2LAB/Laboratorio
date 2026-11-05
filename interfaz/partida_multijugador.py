"""Vista del mapa compartido: sprites locales y posiciones del servidor."""
import math
import os
import time

import pygame

from multijugador.movimiento import ColisionesMapa, es_personaje_jugable
from multijugador.protocolo import ROLES, NOMBRES_ROLES

COLORES = ((83, 222, 212), (241, 199, 86), (183, 137, 246), (247, 140, 120))
DIRECCIONES = ("abajo", "derecha", "arriba", "izquierda")


def tecla_activa(teclas, *codigos):
    if teclas is None:
        return False
    for codigo in codigos:
        try:
            valor = teclas[codigo]
        except (KeyError, TypeError):
            valor = False
        if valor:
            return True
    return False


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
        self.colisiones = ColisionesMapa()
        self.firma = self.colisiones.firma
        self.ruta_guia = []
        self.clave_ruta = None
        self.destino_ruta = None
        self.ultima_ruta = 0
        self.boton_guia = pygame.Rect(25, 112, 330, 37)
        self.personajes = cargar_personajes()
        _, decoraciones, _, _, _, _ = juego.cargar_mapa_principal()
        self.decoraciones = [o for o in decoraciones if not es_personaje_jugable(o["nombre"])]
        self.fondo = juego.cargar_imagen("Fondos/Mapas/Pr_MañanaLumi.png", (960, 720))
        self.fuente = juego.cargar_fuente(16)
        self.titulo = juego.cargar_fuente(20)
        self.jugadores = {}
        self.ultimo_paquete = time.monotonic()
        self.aviso_red = ""
        self.estado = estado
        self.frames_eco = juego.cargar_frames_tronco_eco()
        from interfaz.cooperativo import PanelCooperativo
        self.panel = PanelCooperativo(self)
        self.seleccion = None
        self.ultima_guia_seleccion = None
        self.mouse = (-1, -1)
        self.depurar = False
        self.recibir(estado)

    def recibir(self, estado):
        mundo = estado.get("mundo", {})
        if mundo.get("firma_mapa") != self.firma:
            raise ValueError("El mapa no coincide con el servidor. Actualiza la rama multijugador en todas las PC y Render.")
        self.estado = estado
        destino_guia = (mundo.get("privado", {}).get("guia", {}).get("objetivo") or {}).get("id")
        if destino_guia != self.ultima_guia_seleccion:
            self.seleccion = None
            self.ultima_guia_seleccion = destino_guia
        self.ultimo_paquete = time.monotonic()
        self.aviso_red = ""
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
        self.panel.actualizar()

    def cerca(self, objetivo, radio=68):
        yo = next((j for j in self.estado.get("mundo", {}).get("jugadores", []) if j["id"] == self.identificador), None)
        return yo is not None and math.hypot(yo["x"] - objetivo["x"], yo["y"] - objetivo["y"]) <= radio

    def candidatos(self):
        mundo = self.estado.get("mundo", {})
        yo = next((j for j in mundo.get("jugadores", []) if j["id"] == self.identificador), None)
        if not yo:
            return []
        objetivos = [dict(o) for o in mundo.get("caso", {}).get("objetivos", []) if self.cerca(o)]
        encargo = mundo.get("caso", {}).get("encargo")
        if encargo:
            for o in objetivos:
                for material in encargo["materiales"]:
                    if o["id"] == material["fuente"]["id"]:
                        o["nombre"] = "Recoger " + material["nombre"]
                if o["id"] == encargo["destino"]["id"]:
                    o["nombre"] = "Entregar: " + encargo["destino"]["nombre"]
                if o["id"] == "caldero":
                    o["nombre"] = "Confirmar el siguiente caso"
        objetivos.extend({"id": "jugador:" + j["id"], "nombre": "Compartir con " + j["nombre"], "x": j["x"], "y": j["y"]}
                         for j in mundo.get("jugadores", []) if j["id"] != self.identificador and j.get("conectado", True) and self.cerca(j, 64))
        recomendado = mundo.get("privado", {}).get("guia", {}).get("objetivo") or {}
        objetivos.sort(key=lambda o: math.hypot(yo["x"] - o["x"], yo["y"] - o["y"]) - (1000 if o["id"] == recomendado.get("id") else 15 if o.get("rol") == yo["rol"] else 0))
        return objetivos

    def accion_guiada(self, cliente):
        guia = self.estado.get("mundo", {}).get("privado", {}).get("guia", {})
        accion = guia.get("accion")
        if accion == "pedir_pista":
            cliente.actuar("pedir_pista")
        elif accion == "inventario":
            self.panel.abrir("inventario")
        elif accion == "interactuar" and guia.get("objetivo") and self.cerca(guia["objetivo"]):
            cliente.actuar("interactuar", objetivo=guia["objetivo"]["id"])
        else:
            self.panel.abrir("introduccion")

    def manejar_evento(self, evento, posicion, cliente):
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_F3:
            self.depurar = not self.depurar
            return True
        if self.panel.manejar(evento, posicion, cliente):
            return True
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 and self.boton_guia.collidepoint(posicion):
            self.accion_guiada(cliente)
            return True
        if evento.type == pygame.KEYDOWN and evento.key in (pygame.K_e, pygame.K_TAB):
            opciones = self.candidatos()
            claves = [o["id"] for o in opciones]
            if self.seleccion not in claves:
                self.seleccion = claves[0] if claves else None
            if evento.key == pygame.K_TAB and claves:
                self.seleccion = claves[(claves.index(self.seleccion) + 1) % len(claves)]
            elif evento.key == pygame.K_e:
                if self.seleccion:
                    cliente.actuar("interactuar", objetivo=self.seleccion)
                else:
                    self.panel.notificar("Acércate a una fuente, al caldero o a otro jugador para pulsar E.")
            return True
        return False

    def actualizar(self, segundos, cliente):
        teclas = pygame.key.get_pressed()
        dx = int(tecla_activa(teclas, pygame.K_d, pygame.K_RIGHT)) - int(tecla_activa(teclas, pygame.K_a, pygame.K_LEFT))
        dy = int(tecla_activa(teclas, pygame.K_s, pygame.K_DOWN)) - int(tecla_activa(teclas, pygame.K_w, pygame.K_UP))
        if not pygame.key.get_focused() or self.panel.activo:
            dx = dy = 0
        cliente.mover(dx, dy)
        mundo = self.estado.get("mundo", {})
        destino = mundo.get("privado", {}).get("guia", {}).get("objetivo")
        yo = next((j for j in mundo.get("jugadores", []) if j["id"] == self.identificador), None)
        if destino and yo:
            clave = (destino["id"], round(yo["x"]/24), round(yo["y"]/24))
            if destino["id"] != self.destino_ruta or (clave != self.clave_ruta and time.monotonic()-self.ultima_ruta > .8):
                from interfaz.guia import buscar_camino
                self.ruta_guia = buscar_camino(self.colisiones, (yo["x"], yo["y"]), (destino["x"], destino["y"]))
                self.clave_ruta, self.ultima_ruta = clave, time.monotonic()
                self.destino_ruta = destino["id"]
        else:
            self.ruta_guia = []
        for jugador in self.jugadores.values():
            factor = 1 - math.exp(-24 * min(segundos, .1))
            jugador["posicion"] = jugador["posicion"].lerp(jugador["destino"], factor)
            jugador["reloj"] += segundos

    def dibujar(self, superficie, codigo, mouse=(-1, -1)):
        import juego
        self.mouse = mouse
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
        for i, punto in enumerate(self.ruta_guia):
            if i % 3 == (pygame.time.get_ticks()//280) % 3:
                pygame.draw.circle(superficie, (255, 224, 121), punto, 3)
        etiquetas = []
        from interfaz.suministros import dibujar_carga, dibujar_encargos
        caso_actual = self.estado.get("mundo", {}).get("caso", {})
        dibujar_encargos(superficie, caso_actual, self.fuente)
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
            carga = (caso_actual.get("encargo") or {}).get("cargas", {}).get(datos["id"])
            if carga:
                dibujar_carga(superficie, carga, (x + 22, y - 24))
            if datos["id"] in caso_actual.get("tutorial_cargas", []):
                dibujar_carga(superficie, "farol", (x + 22, y - 24))
            nombre = datos["nombre"] + (" (tú)" if datos["id"] == self.identificador else "")
            if datos.get("controlador") == "bot":
                nombre = "Bot · " + nombre
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
        opciones = self.candidatos()
        claves = [o["id"] for o in opciones]
        if self.seleccion not in claves:
            self.seleccion = claves[0] if claves else None
        seleccion = next((o for o in opciones if o["id"] == self.seleccion), None)
        instruccion = ("[E] " + seleccion["nombre"] + (" | Tab: cambiar" if len(opciones) > 1 else "")) if seleccion else "Flechas: caminar | E: ayudar | I: pistas | M: tarea"
        ayuda = self.fuente.render(instruccion, True, (255, 243, 210))
        superficie.blit(ayuda, (22, 695))
        caso = self.estado.get("mundo", {}).get("caso", {})
        privado = self.estado.get("mundo", {}).get("privado", {})
        if caso:
            guia = privado.get("guia", {})
            hud = pygame.Surface((590, 150), pygame.SRCALPHA)
            hud.fill((8, 28, 20, 240)); superficie.blit(hud, (12, 12))
            self.panel.texto_lineas(superficie, guia.get("titulo", caso["titulo"]), 25, 23, 560, self.titulo, (237, 185, 87))
            self.panel.texto_lineas(superficie, guia.get("detalle", privado.get("instruccion", "")), 25, 58, 560, self.fuente)
            if not self.panel.activo:
                pygame.draw.rect(superficie, (126, 81, 45), self.boton_guia, border_radius=7)
                pygame.draw.rect(superficie, (237, 185, 87), self.boton_guia, 2, border_radius=7)
                objetivo = guia.get("objetivo") or {}
                etiqueta = guia.get("boton", "Ver mi tarea")
                if objetivo and guia.get("accion") == "interactuar" and not self.cerca(objetivo):
                    etiqueta = "Ver mi tarea · M"
                texto = self.panel.pequena.render(etiqueta, True, (255, 243, 210))
                superficie.blit(texto, texto.get_rect(center=self.boton_guia.center))
            objetivo = guia.get("objetivo") or privado.get("objetivo", {})
            for o in caso["objetivos"]:
                mismo_rol = objetivo.get("rol") and o.get("rol") == objetivo["rol"]
                if o["id"] == objetivo.get("id") or mismo_rol or o["id"] == "caldero":
                    color = (126, 231, 188) if o.get("rol") else (237, 185, 87)
                    radio = 16 + round(math.sin(pygame.time.get_ticks() / 220) * 3)
                    pygame.draw.circle(superficie, color, (o["x"], o["y"] + 5), radio, 3)
            badge = pygame.Surface((330, 204), pygame.SRCALPHA)
            badge.fill((8, 28, 20, 240))
            superficie.blit(badge, (618, 12))
            from interfaz.guia import estrella
            estrella(superficie, (646, 36), 15, (255, 215, 90))
            estrellas = caso.get("estrellas", 0)
            self.panel.texto_lineas(superficie, f"{estrellas} / {caso.get('estrellas_total', 11)} estrellas", 672, 25, 260, self.titulo)
            oleada = "Primera aventura: sin reloj" if caso.get("sin_prisa") else f"El rumor crece en {caso.get('proxima_oleada', 60)} s"
            self.panel.texto_lineas(superficie, oleada, 632, 59, 300, self.fuente, (237, 185, 87))
            self.panel.texto_lineas(superficie, "I: pistas · M: mi tarea", 632, 83, 300, self.fuente)
            for i, (nombre, valor) in enumerate(caso.get("indicadores", {}).items()):
                self.panel.texto_lineas(superficie, f"{nombre.capitalize()}: {valor}", 632, 111 + i * 20, 300, self.fuente)
            estados_puente = {
                "sin_verificar": "Puente: información sin verificar",
                "revision_programada": "Puente: revisión mañana",
                "alarma_injustificada": "Puente: falsa alarma",
                "aviso_pendiente": "Puente: aviso pendiente",
            }
            estado_puente = estados_puente.get(caso.get("estado_puente"))
            if estado_puente:
                self.panel.texto_lineas(superficie, estado_puente, 632, 177, 300, self.fuente, (237, 185, 87))
            for i in range(min(11, estrellas)):
                estrella(superficie, (305 + i * 30, 630), 7, (255, 222, 112))
        if self.depurar:
            bots = [
                jugador["datos"] for jugador in self.jugadores.values()
                if jugador["datos"].get("controlador") == "bot"
            ]
            caja = pygame.Surface((338, 206), pygame.SRCALPHA)
            caja.fill((8, 24, 19, 238))
            superficie.blit(caja, (610, 226))
            pygame.draw.rect(superficie, (237, 185, 87), (610, 226, 338, 206), 2)
            self.panel.texto_lineas(
                superficie, "DEPURACIÓN DE BOTS · F3", 622, 235, 312,
                self.titulo, (237, 185, 87),
            )
            for indice, bot in enumerate(bots):
                y = 265 + indice * 48
                self.panel.texto_lineas(
                    superficie,
                    f"{bot['nombre']} · {bot.get('bot_estado', 'ESPERANDO')}",
                    622, y, 312, self.fuente,
                )
                self.panel.texto_lineas(
                    superficie,
                    f"Destino: {bot.get('bot_objetivo') or '—'} · Pruebas: {len(bot.get('bot_pruebas', []))} · Confianza: {bot.get('bot_confianza', 0):.2f}",
                    622, y + 18, 312, self.fuente,
                )
                if bot.get("bot_error"):
                    self.panel.texto_lineas(
                        superficie,
                        "Error: " + bot["bot_error"],
                        622, y + 34, 312, self.fuente, (255, 161, 145),
                    )
        if self.aviso_red or time.monotonic() - self.ultimo_paquete > 1:
            mensaje = self.aviso_red or "Esperando al servidor…"
            if self.estado.get("fase") == "partida" and self.estado.get("revision") is not None:
                mensaje = ""
            if mensaje:
                aviso = self.titulo.render(mensaje, True, (255, 207, 110))
                superficie.blit(aviso, aviso.get_rect(center=(480, 45)))
        self.panel.dibujar(superficie)
        if time.monotonic() < self.panel.celebrar_hasta:
            from interfaz.guia import estrella
            reloj = pygame.time.get_ticks()/350
            for i in range(14):
                x = 48 if i < 7 else 912
                y = 165+(i%7)*65+int(10*math.sin(reloj+i))
                estrella(superficie, (x, y), 8+int(3*math.sin(reloj*2+i)), (255, 223, 104))
