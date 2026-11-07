"""Vista del mapa compartido: sprites locales y posiciones del servidor."""
import math
import os
import time

import pygame

from multijugador.movimiento import ColisionesMapa, es_personaje_jugable
from multijugador.dimensiones_red import LA_COPA, PRESENTE
from multijugador.protocolo import ROLES, NOMBRES_ROLES
from multijugador.reparacion import CONFIGURACION as _CONFIG_REPARACION

CONFIG_REPARACION_MS = _CONFIG_REPARACION["duracion_animacion_ms"]

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
        from interfaz.efectos_visuales import AdornosMapa, FlechaGuia
        from interfaz.escenas_multijugador import RecursosEscenas
        from interfaz.hud import HUDIndicadores
        from interfaz.suministros import configurar_sprites
        from multijugador.presentacion import COLOR_ROJO, COLOR_VERDE, ETIQUETAS, POLARIDAD
        from particulas import SistemaParticulas
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
        # --- Features del modo de un jugador (cargadas una sola vez) ---
        self.dimension = LA_COPA
        self.mapas = {LA_COPA: {"fondo": self.fondo, "decoraciones": self.decoraciones, "colisiones": self.colisiones}}
        self.escenas = RecursosEscenas(self.fondo, self.decoraciones)
        configurar_sprites(self.escenas.materiales)
        self.flecha = FlechaGuia()
        self.adornos = AdornosMapa()
        self.hud = HUDIndicadores(juego.cargar_fuente(11), self.escenas.iconos_hud,
                                  negativos={k for k, v in POLARIDAD.items() if v == "malo"},
                                  colores_avisos=(COLOR_VERDE, COLOR_ROJO), etiquetar_avisos=True)
        self.etiquetas = ETIQUETAS
        self.hud.establecer_etiquetas(ETIQUETAS[LA_COPA])
        self.mostrar_hud = True
        self.particulas = SistemaParticulas(960, 720)
        self.animacion_pocion = None
        self.transicion = None
        self.audio = None
        self.estado_caldero = None
        self.final_sonado = None
        self.inicio_reparacion = None
        self.evento_reparacion_visto = None
        self.puente_1 = next((o for o in self.decoraciones
                              if o.get("nombre", "").replace("\\", "/").lower().endswith("puentes/puente1.png")), None)
        self.puente_roto = None
        if self.puente_1 is not None and self.escenas.puente_roto is not None:
            self.puente_roto = pygame.transform.scale(self.escenas.puente_roto, self.puente_1["rect"].size)
        from reparacion_puentes import SistemaReparacionPuente
        self.frames_reparacion = [SistemaReparacionPuente._escalar_conservar_proporcion(f, self.puente_1["rect"].size)
                                  for f in self.escenas.efecto_reparacion] if self.puente_1 else []
        from interfaz.cooperativo import PanelCooperativo
        self.panel = PanelCooperativo(self)
        self.seleccion = None
        self.ultima_guia_seleccion = None
        self.mouse = (-1, -1)
        self.depurar = False
        self.recibir(estado)
        self.sonido_musica()

    # ------------------------------------------------------------------ audio
    def sonido(self, evento):
        """GestorAudio del modo de un jugador; si no hay audio, se ignora."""
        if self.audio is None:
            try:
                import juego
                from audio_manager import GestorAudio
                self.audio = GestorAudio(os.path.dirname(os.path.abspath(juego.__file__)))
            except Exception as error:  # sin mezclador (pruebas, servidores)
                print("[Multijugador] Audio desactivado:", error)
                self.audio = False
        if self.audio:
            try:
                self.audio.procesar_evento(evento)
            except Exception as error:
                print("[Multijugador] No se pudo reproducir el sonido:", error)

    def sonido_musica(self):
        if self.audio is None:
            self.sonido({"tipo": "caldero", "estado": "estable"})
        if self.audio:
            try:
                self.audio.reproducir_musica("ambiente_presente" if self.dimension == PRESENTE else "ambiente")
            except Exception as error:
                print("[Multijugador] Sin música:", error)

    # ------------------------------------------------------------ dimensiones
    def _cargar_dimension(self, dimension):
        if dimension not in self.mapas:
            import juego
            from dimensiones import DIMENSIONES
            from multijugador.dimensiones_red import cargar_datos
            recursos = juego.cargar_mapa_presente(DIMENSIONES[dimension])
            if recursos is None:
                raise ValueError("No se pudo cargar " + dimension)
            self.mapas[dimension] = {"fondo": recursos["mapa"], "decoraciones": recursos["decoraciones"],
                                     "colisiones": ColisionesMapa(cargar_datos(dimension))}
        return self.mapas[dimension]

    def cambiar_dimension(self, dimension):
        from interfaz.escenas_multijugador import Transicion
        from multijugador.dimensiones_red import DIMENSIONES_RED
        try:
            mapa = self._cargar_dimension(dimension)
        except (ValueError, OSError, RuntimeError) as error:
            self.panel.notificar("No se pudo cargar la dimensión: " + str(error))
            return
        self.dimension = dimension
        self.fondo, self.decoraciones, self.colisiones = mapa["fondo"], mapa["decoraciones"], mapa["colisiones"]
        # Nadie de la dimensión anterior queda dibujado ni se interpola.
        self.jugadores = {}
        self.ruta_guia, self.destino_ruta, self.seleccion = [], None, None
        self.particulas.configurar_dimension(dimension)
        self.particulas.particulas.clear()
        self.hud.establecer_etiquetas(self.etiquetas.get(dimension, self.etiquetas[LA_COPA]))
        self.panel.modo = None
        self.transicion = Transicion(DIMENSIONES_RED[dimension]["nombre"])
        self.sonido_musica()

    def yo(self):
        return next((j for j in self.estado.get("mundo", {}).get("jugadores", []) if j["id"] == self.identificador), None)

    def destinos(self):
        from multijugador.dimensiones_red import destinos
        return self.estado.get("mundo", {}).get("destinos", {}).get(self.dimension) or destinos(self.dimension)

    def rect_portal(self):
        rect = self.estado.get("mundo", {}).get("portales", {}).get(self.dimension)
        return pygame.Rect(rect) if rect else None

    def viajar(self, cliente, destino):
        cliente.actuar("usar_portal", destino=destino)
        self.panel.modo = None

    def iniciar_pocion(self, resultado, noticia):
        from interfaz.escenas_multijugador import AnimacionPocion
        tipo = resultado.get("tipo_pocion")
        if not tipo:
            return
        self.animacion_pocion = AnimacionPocion(tipo, noticia, resultado.get("evento_id"))
        self.sonido({"tipo": "decision_tablilla", "accion": tipo})

    def contexto(self):
        caso = self.estado.get("mundo", {}).get("caso", {})
        return (caso.get("presente") or {}) if self.dimension == PRESENTE else caso

    def dimension_completa(self):
        caso = self.estado.get("mundo", {}).get("caso", {})
        if self.dimension == PRESENTE:
            return bool((caso.get("presente") or {}).get("completada"))
        return bool(caso.get("dimension_completa"))

    def recibir(self, estado):
        from multijugador.dimensiones_red import jugadores_visibles
        mundo = estado.get("mundo", {})
        if mundo.get("firma_mapa") != self.firma:
            raise ValueError("El mapa no coincide con el servidor. Actualiza la rama multijugador en todas las PC y Render.")
        self.estado = estado
        yo = self.yo()
        if yo and yo.get("dimension", LA_COPA) != self.dimension:
            self.cambiar_dimension(yo.get("dimension", LA_COPA))
        destino_guia = (mundo.get("privado", {}).get("guia", {}).get("objetivo") or {}).get("id")
        if destino_guia != self.ultima_guia_seleccion:
            self.seleccion = None
            self.ultima_guia_seleccion = destino_guia
        self.ultimo_paquete = time.monotonic()
        self.aviso_red = ""
        presentes = set()
        for jugador in jugadores_visibles(mundo.get("jugadores", []), self.dimension):
            clave = jugador["id"]
            presentes.add(clave)
            destino = pygame.Vector2(jugador["x"], jugador["y"])
            if clave not in self.jugadores or jugador.get("viaje") != self.jugadores[clave]["datos"].get("viaje"):
                # Recién llegado: aparece en su spawn, sin recorrer el mapa.
                self.jugadores[clave] = {"posicion": destino.copy(), "reloj": 0.0}
            self.jugadores[clave].update(datos=jugador, destino=destino)
        for clave in set(self.jugadores) - presentes:
            del self.jugadores[clave]
        caso = mundo.get("caso", {})
        puente = caso.get("puente") or {}
        self.mapas[LA_COPA]["colisiones"].bloqueos = ([tuple(puente["rect"])] if puente.get("rect") and puente.get("estado") != "REPAIRED" else [])
        if puente.get("estado") == "REPAIR_ANIMATION" and puente.get("evento_reparacion") != self.evento_reparacion_visto:
            self.evento_reparacion_visto = puente.get("evento_reparacion")
            self.inicio_reparacion = time.monotonic()
            if self.puente_1 is not None:
                self.particulas.emitir(*self.puente_1["rect"].center, 18)
        from interfaz.escenas_multijugador import estado_caldero
        indicadores = caso.get("indicadores", {})
        if indicadores:
            nuevo = estado_caldero(indicadores)
            if nuevo != self.estado_caldero:
                if self.estado_caldero is not None:
                    self.sonido({"tipo": "caldero", "estado": nuevo})
                self.estado_caldero = nuevo
        completa = self.dimension_completa()
        if completa and self.final_sonado is False and self.dimension == LA_COPA:
            positivos = sum(indicadores.get(k, 0) for k in ("sabiduria", "confianza", "armonia")) / 3
            negativos = indicadores.get("susurros_falsos", 0) + indicadores.get("desinformacion", 0)
            self.sonido({"tipo": "final_partida", "resultado": "victoria" if positivos >= 55 and negativos < 100 else "game_over"})
        self.final_sonado = completa
        self.panel.actualizar()

    def cerca(self, objetivo, radio=68):
        yo = self.yo()
        if yo is None or yo.get("dimension", LA_COPA) != objetivo.get("dimension", LA_COPA):
            return False
        return math.hypot(yo["x"] - objetivo["x"], yo["y"] - objetivo["y"]) <= radio

    def cerca_id(self, clave):
        return any(o["id"] == clave and self.cerca(o) for o in self.contexto().get("objetivos", []))

    def cerca_portal(self):
        from multijugador.dimensiones_red import cerca_de_rect
        yo, rect = self.yo(), self.rect_portal()
        return bool(yo and rect and cerca_de_rect(yo["x"], yo["y"], tuple(rect), 44))

    def candidatos(self):
        mundo = self.estado.get("mundo", {})
        yo = self.yo()
        if not yo:
            return []
        caso = mundo.get("caso", {})
        puente = caso.get("puente") or {}
        objetivos = [dict(o) for o in self.contexto().get("objetivos", []) if self.cerca(o)
                     and not (o["id"] == "puente_1" and puente.get("estado") not in ("READY_TO_REPAIR", "REPAIR_MINIGAME"))]
        encargo = caso.get("encargo") if self.dimension == LA_COPA else None
        if encargo:
            for o in objetivos:
                for material in encargo["materiales"]:
                    if o["id"] == material["fuente"]["id"] and not material["entregado"]:
                        o["nombre"] = "Recoger " + material["nombre"]
                if o["id"] == encargo["destino"]["id"]:
                    o["nombre"] = "Entregar: " + encargo["destino"]["nombre"]
                if o["id"] == "caldero":
                    o["nombre"] = "Confirmar el siguiente caso"
        objetivos.extend({"id": "jugador:" + j["id"], "nombre": "Compartir con " + j["nombre"], "x": j["x"], "y": j["y"]}
                         for j in (v["datos"] for v in self.jugadores.values())
                         if j["id"] != self.identificador and j.get("conectado", True) and self.cerca(j, 64)
                         and self.dimension == LA_COPA)
        if self.cerca_portal():
            rect = self.rect_portal()
            objetivos.append({"id": "portal", "nombre": "Viajar por el portal", "x": rect.centerx, "y": rect.bottom})
        recomendado = mundo.get("privado", {}).get("guia", {}).get("objetivo") or {}
        objetivos.sort(key=lambda o: math.hypot(yo["x"] - o["x"], yo["y"] - o["y"]) - (1000 if o["id"] == recomendado.get("id") or (o["id"] == "portal" and self.dimension_completa()) else 15 if o.get("rol") == yo["rol"] else 0))
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
        if self.animacion_pocion or self.transicion:
            if (evento.type == pygame.MOUSEBUTTONDOWN or (evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE)) \
                    and self.animacion_pocion and self.animacion_pocion.datos["tiempo_transcurrido"] > .6:
                self.animacion_pocion = None  # se puede saltar tras verla empezar
            return True
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_F3:
            self.depurar = not self.depurar
            return True
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_h and not self.panel.activo:
            self.mostrar_hud = not self.mostrar_hud
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
                if self.seleccion == "portal":
                    self.panel.abrir("portal")
                elif self.seleccion:
                    cliente.actuar("interactuar", objetivo=self.seleccion)
                else:
                    self.panel.notificar("Acércate a una fuente, al caldero, al portal o a otro jugador para pulsar E.")
            return True
        return False

    def actualizar(self, segundos, cliente):
        teclas = pygame.key.get_pressed()
        dx = int(tecla_activa(teclas, pygame.K_d, pygame.K_RIGHT)) - int(tecla_activa(teclas, pygame.K_a, pygame.K_LEFT))
        dy = int(tecla_activa(teclas, pygame.K_s, pygame.K_DOWN)) - int(tecla_activa(teclas, pygame.K_w, pygame.K_UP))
        if not pygame.key.get_focused() or self.panel.activo or self.animacion_pocion or self.transicion:
            dx = dy = 0
        cliente.mover(dx, dy)
        if self.animacion_pocion:
            self.animacion_pocion.actualizar(segundos)
            if self.animacion_pocion.terminada:
                self.animacion_pocion = None
        if self.transicion:
            self.transicion.actualizar(segundos, self.particulas)
            if self.transicion.terminada:
                self.transicion = None
        self.panel.actualizar_tiempo(segundos)
        self.particulas.actualizar(segundos * 1000)
        caso = self.estado.get("mundo", {}).get("caso", {})
        from multijugador.presentacion import ORDEN_INDICADORES
        indicadores = caso.get("indicadores", {})
        self.hud.actualizar({k: indicadores[k] for k in ORDEN_INDICADORES if k in indicadores}, segundos)
        if self.audio:
            self.audio.actualizar()
        rect = self.rect_portal()
        if rect and self.dimension_completa() and int(time.monotonic() * 2) != int((time.monotonic() - segundos) * 2):
            self.particulas.emitir(rect.centerx, rect.centery, 2)
        mundo = self.estado.get("mundo", {})
        destino = mundo.get("privado", {}).get("guia", {}).get("objetivo") if self.dimension == LA_COPA else None
        if self.dimension == PRESENTE:
            destino = self._objetivo_presente()
        yo = self.yo()
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

    def _objetivo_presente(self):
        """Siguiente paso en Distrito Conecta: pista pendiente o pantalla."""
        presente = self.contexto()
        if not presente or presente.get("completada"):
            return None
        conocidas = {p["id"] for p in (self.estado.get("mundo", {}).get("privado", {}).get("presente") or {}).get("inventario", [])}
        yo = self.yo() or {"x": 480, "y": 620}
        pendientes = [o for o in presente.get("objetivos", []) if o.get("pista") and o["pista"] not in conocidas]
        if pendientes:
            return min(pendientes, key=lambda o: math.hypot(o["x"] - yo["x"], o["y"] - yo["y"]))
        return next((o for o in presente.get("objetivos", []) if o["id"] == "presente:pantalla"), None)

    def _dibujar_mapa(self, superficie, ahora_ms):
        import juego
        superficie.blit(self.fondo, (0, 0))
        puente = self.estado.get("mundo", {}).get("caso", {}).get("puente") or {}
        for objeto in self.decoraciones:
            if self.dimension == LA_COPA and objeto is self.puente_1 and puente.get("estado", "REPAIRED") != "REPAIRED":
                # Puente 1 roto (imagen real Puente1Roto.png) hasta repararlo.
                superficie.blit(self.puente_roto or objeto["imagen"], objeto["rect"])
                continue
            if juego.es_hoja_portales(objeto.get("nombre", "")) and self.adornos.portal:
                continue  # se dibuja el portal animado
            if objeto.get("tronco_eco") and self.frames_eco:
                frame = self.frames_eco[(ahora_ms // 140) % len(self.frames_eco)]
                superficie.blit(pygame.transform.scale(frame, objeto["rect"].size), objeto["rect"])
            elif objeto.get("puente_animable"):
                juego.dibujar_puente_balanceandose(superficie, objeto, ahora_ms)
            elif objeto.get("frames"):
                frames = objeto["frames"]
                superficie.blit(frames[(ahora_ms // 140) % len(frames)], objeto["rect"])
            else:
                superficie.blit(objeto["imagen"], objeto["rect"])
        rect = self.rect_portal()
        if rect:
            self.adornos.dibujar_portal(superficie, rect, ahora_ms, True)
        if self.dimension == LA_COPA and self.inicio_reparacion and self.frames_reparacion and self.puente_1:
            # Efecto de reparación de 8 cuadros sobre el puente.
            transcurrido = (time.monotonic() - self.inicio_reparacion) * 1000
            if transcurrido < CONFIG_REPARACION_MS:
                indice = min(len(self.frames_reparacion) - 1, int(transcurrido / CONFIG_REPARACION_MS * len(self.frames_reparacion)))
                frame = self.frames_reparacion[indice]
                superficie.blit(frame, frame.get_rect(center=self.puente_1["rect"].center))
            else:
                self.inicio_reparacion = None

    def dibujar(self, superficie, codigo, mouse=(-1, -1)):
        from multijugador.dimensiones_red import DIMENSIONES_RED
        self.mouse = mouse
        ahora_ms = pygame.time.get_ticks()
        self._dibujar_mapa(superficie, ahora_ms)
        self.adornos.ruta(superficie, self.ruta_guia, ahora_ms)
        etiquetas = []
        from interfaz.suministros import dibujar_carga, dibujar_encargos
        caso_actual = self.estado.get("mundo", {}).get("caso", {})
        if self.dimension == LA_COPA:
            dibujar_encargos(superficie, caso_actual, self.fuente)
        caso = caso_actual
        privado = self.estado.get("mundo", {}).get("privado", {})
        guia = privado.get("guia", {})
        objetivo = (guia.get("objetivo") or privado.get("objetivo") or {}) if self.dimension == LA_COPA else (self._objetivo_presente() or {})
        for o in self.contexto().get("objetivos", []):
            mismo_rol = objetivo.get("rol") and o.get("rol") == objetivo["rol"]
            if o["id"] == objetivo.get("id") or mismo_rol or o["id"] in ("caldero", "presente:pantalla"):
                if o["id"] == "puente_1" and (caso.get("puente") or {}).get("estado") == "REPAIRED":
                    continue
                self.adornos.anillo_objetivo(superficie, (o["x"], o["y"] + 5), o.get("rol") or "mensajero", ahora_ms)
        for jugador in sorted(self.jugadores.values(), key=lambda j: j["posicion"].y):
            datos = jugador["datos"]
            rol = datos["rol"]
            color = COLORES[ROLES.index(rol)]
            x, y = round(jugador["posicion"].x), round(jugador["posicion"].y)
            estado = datos["animacion"] if time.monotonic() - self.ultimo_paquete < .5 else "reposo"
            frames = self.personajes[rol][(estado, datos["direccion"])]
            frame = frames[int(jugador["reloj"] * (9 if estado == "caminar" else 4)) % len(frames)]
            pygame.draw.ellipse(superficie, (17, 28, 22), (x - 13, y - 5, 26, 8))
            self.adornos.anillo_jugador(superficie, rol, (x, y - 1), color)
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
            fondo = pygame.Surface(caja.inflate(10, 6).size, pygame.SRCALPHA)
            fondo.fill((13, 29, 23, 215))
            superficie.blit(fondo, caja.inflate(10, 6))
            superficie.blit(etiqueta, caja)
            if local:
                self.adornos.marcador_local(superficie, (caja.centerx, caja.top - 4), color, ahora_ms)
        self.particulas.dibujar(superficie)
        yo = self.yo()
        rect_portal = self.rect_portal()
        if self.dimension_completa() and yo and rect_portal and not self.panel.activo:
            # Igual que el modo de un jugador: al completar la dimensión, la
            # flecha guía hasta el portal.
            mio = self.jugadores.get(self.identificador)
            origen = mio["posicion"] if mio else (yo["x"], yo["y"])
            self.flecha.dibujar(superficie, (origen[0], origen[1] - 20), rect_portal.center, ahora_ms,
                                limites=(30, 180, 930, 640))
        panel = pygame.Surface((960, 62), pygame.SRCALPHA)
        panel.fill((9, 25, 20, 235))
        superficie.blit(panel, (0, 658))
        nombre_dimension = DIMENSIONES_RED[self.dimension]["nombre"].upper()
        etiqueta = self.titulo.render(f"{nombre_dimension} · Sala {codigo} · {len(self.jugadores)} aquí", True, (237, 185, 87))
        superficie.blit(etiqueta, (22, 667))
        opciones = self.candidatos()
        claves = [o["id"] for o in opciones]
        if self.seleccion not in claves:
            self.seleccion = claves[0] if claves else None
        seleccion = next((o for o in opciones if o["id"] == self.seleccion), None)
        instruccion = ("[E] " + seleccion["nombre"] + (" | Tab: cambiar" if len(opciones) > 1 else "")) if seleccion else "Flechas: caminar | E: ayudar | I: pistas | M: tarea | H: indicadores"
        ayuda = self.fuente.render(instruccion, True, (255, 243, 210))
        superficie.blit(ayuda, (22, 695))
        if caso:
            hud = pygame.Surface((590, 150), pygame.SRCALPHA)
            hud.fill((8, 28, 20, 240)); superficie.blit(hud, (12, 12))
            if self.dimension == PRESENTE:
                presente = caso.get("presente") or {}
                titulo = "Distrito Conecta · " + presente.get("titulo", "")
                if presente.get("completada"):
                    detalle = "¡Misión completada! Sigue la flecha hasta el portal para elegir otra época."
                elif presente.get("pistas", 0) < presente.get("total_pistas", 3):
                    detalle = f"Pistas {presente.get('pistas', 0)}/{presente.get('total_pistas', 3)}: habla con las personas marcadas (E). Luego decidan en la pantalla pública."
                else:
                    detalle = "¡Tienen las tres pistas! Vayan a la pantalla pública y elijan una poción."
                self.panel.texto_lineas(superficie, titulo, 25, 23, 560, self.titulo, (237, 185, 87))
                self.panel.texto_lineas(superficie, detalle, 25, 58, 560, self.fuente)
            else:
                self.panel.texto_lineas(superficie, guia.get("titulo", caso["titulo"]), 25, 23, 560, self.titulo, (237, 185, 87))
                self.panel.texto_lineas(superficie, guia.get("detalle", privado.get("instruccion", "")), 25, 58, 560, self.fuente)
            if not self.panel.activo and self.dimension == LA_COPA:
                pygame.draw.rect(superficie, (126, 81, 45), self.boton_guia, border_radius=7)
                pygame.draw.rect(superficie, (237, 185, 87), self.boton_guia, 2, border_radius=7)
                objetivo_guia = guia.get("objetivo") or {}
                texto_boton = guia.get("boton", "Ver mi tarea")
                if objetivo_guia and guia.get("accion") == "interactuar" and not self.cerca(objetivo_guia):
                    texto_boton = "Ver mi tarea · M"
                texto = self.panel.pequena.render(texto_boton, True, (255, 243, 210))
                superficie.blit(texto, texto.get_rect(center=self.boton_guia.center))
            badge = pygame.Surface((330, 128), pygame.SRCALPHA)
            badge.fill((8, 28, 20, 240))
            superficie.blit(badge, (618, 12))
            from interfaz.guia import estrella
            estrella(superficie, (646, 36), 15, (255, 215, 90))
            estrellas = caso.get("estrellas", 0)
            self.panel.texto_lineas(superficie, f"{estrellas} / {caso.get('estrellas_total', 11)} estrellas", 672, 25, 260, self.titulo)
            oleada = "Primera aventura: sin reloj" if caso.get("sin_prisa") else f"El rumor crece en {caso.get('proxima_oleada', 60)} s"
            if self.dimension == PRESENTE:
                oleada = "La Copa sigue esperándote"
            self.panel.texto_lineas(superficie, oleada, 632, 59, 300, self.fuente, (237, 185, 87))
            self.panel.texto_lineas(superficie, "I: pistas · M: tarea · H: indicadores", 632, 83, 300, self.fuente)
            estados_puente = {
                "DAMAGED": "Puente 1: roto", "MATERIALS_PENDING": "Puente 1: faltan materiales",
                "READY_TO_REPAIR": "Puente 1: ¡listo para reparar!", "REPAIR_MINIGAME": "Puente 1: en reparación",
                "REPAIR_ANIMATION": "Puente 1: reparándose…", "REPAIRED": "Puente 1: reparado",
            }
            estado_puente = estados_puente.get((caso.get("puente") or {}).get("estado"))
            if estado_puente and self.dimension == LA_COPA:
                self.panel.texto_lineas(superficie, estado_puente, 632, 107, 300, self.fuente, (237, 185, 87))
            for i in range(min(11, estrellas)):
                estrella(superficie, (305 + i * 30, 630), 7, (255, 222, 112))
            if self.mostrar_hud and not self.panel.activo:
                self.hud.dibujar(superficie, 18, 176)
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
        if self.animacion_pocion:
            self.animacion_pocion.dibujar(superficie, self.escenas)
        if self.transicion:
            self.transicion.dibujar(superficie, self.escenas.r["fuente_resultado"])
