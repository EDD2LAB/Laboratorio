"""Vista del mapa compartido: sprites locales y posiciones del servidor."""
import json
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
# Boca del caldero en el lienzo 960x720 (el objetivo "caldero" está en su base, 480,380).
BOCA_CALDERO = (480, 336)
FILAS_CALDERO = {"estable": 1, "peligroso": 2, "critico": 3}
COLORES_CALDERO = {
    "estable": ((93, 218, 205), (111, 219, 150), (190, 245, 255)),
    "peligroso": ((238, 201, 92), (255, 150, 70), (200, 130, 255)),
    "critico": ((255, 95, 95), (190, 80, 230), (255, 150, 70)),
}
DIRECCIONES = ("abajo", "derecha", "arriba", "izquierda")
DIAGONALES = ("abajo_derecha", "arriba_derecha", "arriba_izquierda", "abajo_izquierda")
ALTURA_PERSONAJE = 53
ALTURA_DISTRITO = 30  # en Distrito Conecta el mapa está dibujado a menor escala
ESCALA_ANILLOS_DISTRITO = .6
# La cámara va siempre cerca del personaje: el mapa se descubre al recorrerlo
# en lugar de mostrarse completo de una vez. En La Copa el zoom es entero para
# que el pixel art quede nítido.
ZOOM_PRESENTE = 3
ZOOM_COPA = 2
ZOOMS = {LA_COPA: ZOOM_COPA, PRESENTE: ZOOM_PRESENTE}


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


def cargar_clips_personajes():
    """Cuadros originales de cada rol, sin escalar."""
    from mundo.personajes import RECTA_EQUIVALENTE
    from nucleo.recursos import cargar_imagen
    carpetas = ("Guardian", "mensajero", "Habitante hombre", "Aspirante hombre")
    caminar = (
        [f"Fila {i}. Guardián.png" for i in range(2, 6)],
        [f"fila {i} mensajero.png" for i in range(2, 6)],
        [f"HabHombre Fila {i}.png" for i in range(2, 6)],
        # La Aspirante tiene caminata propia (antes caminaba con la hoja de correr).
        [f"Fila {i}. Aspirante_a_cacique-Idle.png" for i in range(2, 6)],
    )
    # Hojas de correr (Shift). Guardián y Habitante no tienen: usan su caminata más rápida.
    correr = (
        None,
        [f"Mensajero_corriendo_{i}.png" for i in range(1, 5)],
        None,
        [f"Corriendo/Aspirante_a_cacique-corriendo_fila{i}.png" for i in range(1, 5)],
    )
    reposo = ("Guardian_reposo_fila", "Mensajero_reposo_fila", "Habitante_hombre_reposo_fila",
              "Aspirante_a_cacique-reposo_fila")
    # Filas 6 a 9: caminar en diagonal (en el orden de DIAGONALES).
    diagonales = ("Fila {}. Guardián.png", "Fila {} - Mensajero.png", "HabHombre Fila {}.png",
                  "Fila {} - Aspirante_a_cacique.png")
    por_rol = {}
    for indice, rol in enumerate(ROLES):
        clips = {}
        for estado in ("caminar", "reposo"):
            for i, direccion in enumerate(DIRECCIONES):
                archivo = caminar[indice][i] if estado == "caminar" else f"Reposo/{reposo[indice]}{i + 1}.png"
                imagen = cargar_imagen(os.path.join("NPCS", carpetas[indice], archivo))
                clips[(estado, direccion)] = separar_frames(imagen)
        for i, direccion in enumerate(DIRECCIONES):
            frames = clips[("caminar", direccion)]
            if correr[indice]:
                try:
                    imagen = cargar_imagen(os.path.join("NPCS", carpetas[indice], correr[indice][i]))
                    frames = separar_frames(imagen)
                except (pygame.error, ValueError, FileNotFoundError) as error:
                    print("[Multijugador] Sin animación de correr para", rol, direccion, error)
            clips[("correr", direccion)] = frames
        for fila, orientacion in enumerate(DIAGONALES, start=6):
            imagen = cargar_imagen(os.path.join("NPCS", carpetas[indice], diagonales[indice].format(fila)))
            frames = separar_frames(imagen)
            clips[("caminar", orientacion)] = clips[("correr", orientacion)] = frames
            # Las diagonales no tienen hoja de reposo: usan la de la dirección recta.
            clips[("reposo", orientacion)] = clips[("reposo", RECTA_EQUIVALENTE[orientacion])]
        por_rol[rol] = clips
    return por_rol


# Variantes femeninas: carpeta, prefijo de la caminata y archivos de reposo.
VARIANTES_MUJER = {
    "aspirante": ("Aspirante mujer", "MujerAspirante Fila {}.png",
                  ("Aspirante_mujer_reposo_fila1.png", "Aspirante_mujer_reposo _fila2.png",
                   "Aspirante_mujer_reposo _fila3.png", "Aspirante_mujer_reposo_ fila4.png")),
    "habitante": ("Habitante mujer", "HabMujer Fila {}.png",
                  tuple(f"Habitante_femenina-reposo_fila{i}.png" for i in range(1, 5))),
}


def cargar_clips_variante(rol):
    """Cuadros de la variante de un rol. No tiene diagonales ni hoja de correr propias."""
    from nucleo.recursos import cargar_imagen
    carpeta, caminar, reposo = VARIANTES_MUJER[rol]
    clips = {}
    for i, direccion in enumerate(DIRECCIONES):
        marcha = separar_frames(cargar_imagen(os.path.join("NPCS", carpeta, caminar.format(i + 2))))
        clips[("caminar", direccion)] = clips[("correr", direccion)] = marcha
        clips[("reposo", direccion)] = separar_frames(cargar_imagen(os.path.join("NPCS", carpeta, "Reposo", reposo[i])))
    return clips


def escalar_personajes(por_rol, altura):
    """Ajusta cada rol a ``altura`` (se escala una vez, con la de reposo como referencia)."""
    personajes = {}
    for rol, clips in por_rol.items():
        # Referencia: las cuatro direcciones rectas, para que el tamaño no varíe.
        escala = altura / max(f.get_height() for clave, frames in clips.items()
                              if clave[1] in DIRECCIONES for f in frames)
        personajes[rol] = {
            clave: [pygame.transform.scale(f, (max(1, round(f.get_width() * escala)), max(1, round(f.get_height() * escala))))
                    for f in frames] for clave, frames in clips.items()
        }
    return personajes


def cargar_personajes():
    return escalar_personajes(cargar_clips_personajes(), ALTURA_PERSONAJE)


def caso_jugadores(estado):
    return estado.get("mundo", {}).get("jugadores", [])


class VistaPartida:
    def __init__(self, identificador, estado, audio=None):
        from mundo.mapas import cargar_fondo_unificado, cargar_mapa_principal, decoraciones_ampliadas, suavizar_cascada
        from mundo.personajes import cargar_variantes_tronco_eco, preparar_reposo
        from nucleo.recursos import cargar_fuente, cargar_imagen
        from interfaz.arte import ArtePartida
        from interfaz.efectos_visuales import AdornosMapa, FlechaGuia
        from interfaz.escenas_multijugador import RecursosEscenas
        from interfaz.hud import HUDIndicadores
        from interfaz.suministros import configurar_sprites
        from multijugador.presentacion import COLOR_ROJO, COLOR_VERDE, ETIQUETAS, POLARIDAD
        from graficos.particulas import SistemaParticulas
        self.identificador = identificador
        self.colisiones = ColisionesMapa()
        self.firma = self.colisiones.firma
        self.ruta_guia = []
        self.clave_ruta = None
        self.destino_ruta = None
        self.ultima_ruta = 0
        self.boton_guia = pygame.Rect(25, 112, 330, 37)
        clips = cargar_clips_personajes()
        self.personajes = escalar_personajes(clips, ALTURA_PERSONAJE)
        self.personajes_zoom = escalar_personajes(clips, ALTURA_PERSONAJE * ZOOM_COPA)
        _, decoraciones, _, _, _, _ = cargar_mapa_principal()
        self.decoraciones = [o for o in decoraciones if not es_personaje_jugable(o["nombre"])]
        for objeto in self.decoraciones:
            if objeto.get("fondo_animado"):
                suavizar_cascada(objeto)
        self._marcar_cesto(estado)
        self.decoraciones_zoom = decoraciones_ampliadas(self.decoraciones, ZOOM_COPA)
        for objeto in self.decoraciones + self.decoraciones_zoom:
            if objeto.get("personaje"):
                preparar_reposo(objeto)
        self.fondo_zoom = cargar_fondo_unificado(ZOOM_COPA)
        self.escenas_zoom = {LA_COPA: {
            "zoom": ZOOM_COPA, "origen": (0, 0), "fondo": self.fondo_zoom,
            "capa": pygame.Surface(self.fondo_zoom.get_size()).convert(),
            "decoraciones": self.decoraciones_zoom, "personajes": self.personajes_zoom,
        }}
        self.capa_efectos = pygame.Surface((960, 720), pygame.SRCALPHA)
        self.fondo = pygame.transform.scale(self.fondo_zoom, (960, 720))
        self.fuente = cargar_fuente(16)
        self.titulo = cargar_fuente(20)
        self.jugadores = {}
        self.ultimo_paquete = time.monotonic()
        self.aviso_red = ""
        self.estado = estado
        self.variantes_eco = cargar_variantes_tronco_eco()
        self._frames_tronco_escalados = {}
        self.rect_caldero, self.cuadros_caldero = self._cargar_caldero()
        from audio.narracion import Narrador
        self.narrador = Narrador()
        self.celular = None  # se carga al llegar a Distrito Conecta
        # --- Features del modo de un jugador (cargadas una sola vez) ---
        self.dimension = LA_COPA
        self.mapas = {LA_COPA: {"fondo": self.fondo, "decoraciones": self.decoraciones, "colisiones": self.colisiones}}
        self.escenas = RecursosEscenas(self.fondo, self.decoraciones)
        self.arte = ArtePartida()
        configurar_sprites(self.escenas.materiales)
        self.cesto_zoom = self.arte.cargar_cestos(ZOOM_COPA)
        self.flecha = FlechaGuia()
        self.adornos = AdornosMapa()
        self.hud = HUDIndicadores(cargar_fuente(11), self.escenas.iconos_hud,
                                  negativos={k for k, v in POLARIDAD.items() if v == "malo"},
                                  colores_avisos=(COLOR_VERDE, COLOR_ROJO), etiquetar_avisos=True)
        self.etiquetas = ETIQUETAS
        self.hud.establecer_etiquetas(ETIQUETAS[LA_COPA])
        self.mostrar_hud = True  # H o el botón de la barra: oculta/muestra todo el HUD
        self.mostrar_nombres = True  # L: oculta/muestra las etiquetas de nombre
        self.mostrar_detalles = False  # J: tarea completa, indicadores y teclas
        self.en_pausa = False  # lo fija el menú de pausa: sin movimiento mientras está abierto
        self.camara = None  # centro de la cámara del Presente (mundo); None = sin zoom
        self.capa_mundo = None
        self.particulas = SistemaParticulas(960, 720)
        self.animacion_pocion = None
        self.transicion = None
        self.audio = audio  # gestor compartido del menú (None: se crea al sonar)
        self.estado_caldero = None
        self.reloj_caldero = 0.0
        self.final_sonado = None
        self.inicio_reparacion = None
        self.evento_reparacion_visto = None
        from interfaz.efectos_mapa import EfectosMapa
        self.efectos_mapa = EfectosMapa(ZOOM_COPA)
        self.efectos_vistos = None  # al unirse no se repite lo que ya pasó
        self.pantalla_final = None  # ilustración del final del equipo
        self.final_visto = False
        self.puente_1 = next((o for o in self.decoraciones
                              if o.get("nombre", "").replace("\\", "/").lower().endswith("puentes/puente1.png")), None)
        self.puente_roto = None
        if self.puente_1 is not None and self.escenas.puente_roto is not None:
            self.puente_roto = pygame.transform.scale(self.escenas.puente_roto, self.puente_1["rect"].size)
        from mundo.reparacion_puentes import SistemaReparacionPuente
        self.frames_reparacion = [SistemaReparacionPuente._escalar_conservar_proporcion(f, self.puente_1["rect"].size)
                                  for f in self.escenas.efecto_reparacion] if self.puente_1 else []
        self.puente_1_zoom = next((o for o in self.decoraciones_zoom if o["original"] is self.puente_1), None)
        self.puente_roto_zoom = None
        self.frames_reparacion_zoom = []
        self.puente_det = self.puente_det_zoom = None
        if self.puente_1 is not None and self.escenas.puente_det is not None:
            self.puente_det = pygame.transform.scale(self.escenas.puente_det, self.puente_1["rect"].size)
        if self.puente_1_zoom is not None and self.escenas.puente_det is not None:
            self.puente_det_zoom = pygame.transform.scale(self.escenas.puente_det, self.puente_1_zoom["rect"].size)
        if self.puente_1_zoom is not None:
            tamano = self.puente_1_zoom["rect"].size
            if self.escenas.puente_roto is not None:
                self.puente_roto_zoom = pygame.transform.scale(self.escenas.puente_roto, tamano)
            self.frames_reparacion_zoom = [SistemaReparacionPuente._escalar_conservar_proporcion(f, tamano)
                                           for f in self.escenas.efecto_reparacion]
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
                from audio.audio_manager import GestorAudio
                from nucleo.rutas import RAIZ
                self.audio = GestorAudio(str(RAIZ), categorias=True)
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
                # Única pista de ambiente del proyecto (no hay una propia del Presente).
                self.audio.reproducir_musica("ambiente", en_bucle=True)
            except Exception as error:
                print("[Multijugador] Sin música:", error)

    def _marcar_cesto(self, estado):
        """El servidor decide qué tronco es el cesto de los encargos."""
        objetivos = estado.get("mundo", {}).get("caso", {}).get("objetivos", [])
        cesto = next((o for o in objetivos if o["id"] == "cesto"), None)
        troncos = [o for o in self.decoraciones if o.get("tronco_eco")]
        if cesto and troncos:
            min(troncos, key=lambda o: math.hypot(o["rect"].centerx - cesto["x"], o["rect"].bottom - cesto["y"]))["cesto"] = True

    # ------------------------------------------------------------ dimensiones
    def _cargar_dimension(self, dimension):
        if dimension not in self.mapas:
            from logica.dimensiones import DIMENSIONES
            from multijugador.dimensiones_red import cargar_datos
            from mundo.mapas import cargar_mapa_presente
            from interfaz.celular import ArteCelular
            recursos = cargar_mapa_presente(DIMENSIONES[dimension])
            if recursos is None:
                raise ValueError("No se pudo cargar " + dimension)
            colisiones = ColisionesMapa(cargar_datos(dimension))
            self.mapas[dimension] = {"fondo": recursos["mapa"], "decoraciones": recursos["decoraciones"],
                                     "colisiones": colisiones}
            self.escenas_zoom[dimension] = self._escena_presente(DIMENSIONES[dimension], recursos, colisiones)
            self.celular = self.celular or ArteCelular()
        return self.mapas[dimension]

    @staticmethod
    def _escena_presente(configuracion, recursos, colisiones):
        """Todo escalado una sola vez a su tamaño final: en cada cuadro solo se recorta."""
        from mundo.mapas import cargar_fondo_presente, npcs_presente_ampliados
        from mundo.personajes import cargar_personajes_distrito
        rect = tuple(colisiones.datos["rect_mapa"])
        fondo = cargar_fondo_presente(configuracion, rect, ZOOM_PRESENTE)
        return {
            "zoom": ZOOM_PRESENTE, "origen": rect[:2], "fondo": fondo,
            "capa": pygame.Surface(fondo.get_size()).convert(),
            "decoraciones": npcs_presente_ampliados(recursos["decoraciones"], ZOOM_PRESENTE, rect[:2]),
            "personajes": cargar_personajes_distrito(ALTURA_DISTRITO * ZOOM_PRESENTE),
        }

    def _npcs_gemelos(self):
        """Quien juega ya es ese personaje: su NPC no se dibuja para que no haya dos."""
        from mundo.personajes import PERSONAJES_DISTRITO
        if self.dimension != PRESENTE:
            return ()
        return {PERSONAJES_DISTRITO[j["datos"]["rol"]][0] for j in self.jugadores.values()}

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
        self.camara = None  # se recoloca sobre el jugador al llegar
        # Lo que estaba ocurriendo en el mapa anterior termina al viajar.
        self.animacion_pocion = None
        self.inicio_reparacion = None
        self.transicion = Transicion(DIMENSIONES_RED[dimension]["nombre"], self.arte.emblemas_viaje.get(dimension))
        self.sonido_musica()

    def yo(self):
        return next((j for j in self.estado.get("mundo", {}).get("jugadores", []) if j["id"] == self.identificador), None)

    def destinos(self):
        from multijugador.dimensiones_red import destinos
        return self.estado.get("mundo", {}).get("destinos", {}).get(self.dimension) or destinos(self.dimension)

    def rect_portal(self):
        rect = self.estado.get("mundo", {}).get("portales", {}).get(self.dimension)
        return pygame.Rect(rect) if rect else None

    def viaje(self):
        """Propuesta de viaje en grupo de mi dimensión (o None)."""
        viaje = self.estado.get("mundo", {}).get("viaje")
        return viaje if viaje and viaje.get("origen") == self.dimension else None

    def _dibujar_aviso_viaje(self, superficie):
        viaje = self.viaje()
        if not viaje or self.panel.activo:
            return
        if self.identificador in viaje["aceptan"]:
            texto = "Viaje a " + viaje["nombre"] + (": esperando a " + ", ".join(viaje["faltan"]) if viaje["faltan"] else "")
        else:
            texto = "¡Viaje a " + viaje["nombre"] + "! Ve al portal y pulsa E para aceptar"
        render = self.titulo.render(texto, True, (255, 236, 170))
        caja = render.get_rect(center=(480, 196)).inflate(28, 16)
        fondo = pygame.Surface(caja.size, pygame.SRCALPHA)
        fondo.fill((10, 30, 36, 235))
        superficie.blit(fondo, caja)
        pygame.draw.rect(superficie, (106, 218, 204), caja, 2, border_radius=8)
        superficie.blit(render, render.get_rect(center=caja.center))

    def viajar(self, cliente, destino):
        cliente.actuar("usar_portal", destino=destino)
        self.panel.modo = None

    def iniciar_pocion(self, resultado, noticia):
        from interfaz.escenas_multijugador import AnimacionPocion
        tipo = resultado.get("tipo_pocion")
        if self.dimension == PRESENTE:  # en Distrito Conecta no hay pociones
            self.sonido({"tipo": "clasificacion", "correcta": bool(resultado.get("correcto"))})
            if self.celular is not None:
                self.celular.efectos.por_resultado(resultado)
            return
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
        self._revisar_final()
        self._lanzar_efectos(mundo.get("caso", {}))
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

    def _clave_figura(self, datos):
        """Rol o variante elegida; se carga la primera vez que alguien la usa."""
        rol = datos["rol"]
        if datos.get("apariencia") != "mujer" or rol not in VARIANTES_MUJER or self.dimension != LA_COPA:
            return rol
        clave = rol + "_mujer"
        if clave not in self.personajes:
            try:
                clips = {clave: cargar_clips_variante(rol)}
            except (pygame.error, ValueError, FileNotFoundError, RuntimeError) as error:
                print("[Arte] Sin variante de", rol, error)
                return rol
            self.personajes.update(escalar_personajes(clips, ALTURA_PERSONAJE))
            self.personajes_zoom.update(escalar_personajes(clips, ALTURA_PERSONAJE * ZOOM_COPA))
        return clave

    def _lanzar_efectos(self, caso):
        """Poderes, rumores y correcciones: una vez por evento, solo en La Copa."""
        ronda = caso.get("ronda")
        resultado = caso.get("resultado") or {}
        eventos = {("poder", ronda, i) for i in caso.get("habilidades_usadas", [])}
        if caso.get("oleadas"):
            eventos.add(("rumor", ronda, caso["oleadas"]))
        if resultado.get("correcto") and resultado.get("evento_id"):
            eventos.add(("correccion", resultado["evento_id"], None))
        if self.efectos_vistos is None:
            self.efectos_vistos = eventos
            return
        for evento in eventos - self.efectos_vistos:
            self.efectos_vistos.add(evento)
            if self.dimension != LA_COPA:
                continue
            if evento[0] == "poder":
                jugador = next((j for j in caso_jugadores(self.estado) if j["id"] == evento[2]), None)
                if jugador:
                    self.efectos_mapa.lanzar("poder", jugador["x"], jugador["y"] - 28)
            else:
                self._cruzar_puente(evento[0])

    def _cruzar_puente(self, tipo):
        """La señal recorre el puente que el jugador tiene más cerca."""
        yo = self.yo()
        puentes = [o for o in self.decoraciones if o.get("puente_animable")]
        if yo and puentes:
            puente = min(puentes, key=lambda o: math.hypot(o["rect"].centerx - yo["x"], o["rect"].centery - yo["y"]))
            self.efectos_mapa.recorrer(tipo, puente["rect"].midleft, puente["rect"].midright)

    def _revisar_final(self):
        """Al completar La Copa y Distrito Conecta, una vez por partida."""
        caso = self.estado.get("mundo", {}).get("caso", {})
        if self.final_visto or caso.get("fase") != "final" or not (caso.get("presente") or {}).get("completada"):
            return
        from interfaz.finales import PantallaFinal
        self.final_visto = True
        self.pantalla_final = PantallaFinal(caso.get("indicadores", {}), self.etiquetas[self.dimension],
                                            self.escenas.r["fuente_resultado"], self.titulo)

    def manejar_evento(self, evento, posicion, cliente):
        if self.pantalla_final is not None:
            if evento.type == pygame.MOUSEBUTTONDOWN or (evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE):
                self.pantalla_final = None
            return True
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
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_j and not self.panel.activo:
            self.mostrar_detalles = not self.mostrar_detalles
            return True
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_l and not self.panel.activo:
            self.mostrar_nombres = not self.mostrar_nombres
            return True
        if self.panel.manejar(evento, posicion, cliente):
            return True
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 and self.mostrar_hud and self.mostrar_detalles \
                and self.dimension == LA_COPA and self.boton_guia.collidepoint(posicion):
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
        if not pygame.key.get_focused() or self.en_pausa or self.panel.activo or self.animacion_pocion or self.transicion:
            dx = dy = 0
        correr = tecla_activa(teclas, pygame.K_LSHIFT, pygame.K_RSHIFT)
        cliente.mover(dx, dy, correr)
        if self.animacion_pocion:
            self.animacion_pocion.actualizar(segundos)
            if self.animacion_pocion.terminada:
                self.animacion_pocion = None
        if self.transicion:
            self.transicion.actualizar(segundos, self.particulas)
            if self.transicion.terminada:
                self.transicion = None
        self.panel.actualizar_tiempo(segundos)
        if self.dimension == LA_COPA:
            self.reloj_caldero += segundos
            if self.reloj_caldero >= .2:
                self.reloj_caldero %= .2
                self.particulas.emitir_columna(*BOCA_CALDERO, 2, COLORES_CALDERO.get(self.estado_caldero))
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
        self._seguir_camara(segundos)

    # ---------------------------------------------------------- cámara
    def _rect_mapa(self):
        rect = self.colisiones.datos.get("rect_mapa") if self.colisiones else None
        return pygame.Rect(rect) if rect else pygame.Rect(0, 0, 960, 720)

    def _seguir_camara(self, segundos):
        if self.dimension not in ZOOMS:
            self.camara = None
            return
        mio = self.jugadores.get(self.identificador)
        if not mio:
            return
        objetivo = pygame.Vector2(mio["posicion"])
        if self.camara is None:
            self.camara = objetivo
        else:
            self.camara = self.camara.lerp(objetivo, 1 - math.exp(-6 * min(segundos, .1)))

    def vista_camara(self):
        """Rect del mundo visible, siempre dentro del mapa (sin mostrar fuera de sus bordes)."""
        if self.dimension not in ZOOMS:
            return None
        mio = self.jugadores.get(self.identificador)
        centro = self.camara if self.camara is not None else (mio["posicion"] if mio else None)
        if centro is None:
            return None
        mapa = self._rect_mapa()
        ancho = min(mapa.width, round(960 / ZOOMS[self.dimension]))
        alto = min(mapa.height, round(720 / ZOOMS[self.dimension]))
        vista = pygame.Rect(0, 0, ancho, alto)
        vista.center = (round(centro.x), round(centro.y))
        vista.clamp_ip(mapa)
        return vista

    def a_pantalla(self, x, y, vista=None):
        vista = vista if vista is not None else self.vista_camara()
        if vista is None:
            return x, y
        return (x - vista.x) * 960 / vista.width, (y - vista.y) * 720 / vista.height

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

    def _frames_tronco(self, tamano, variante=1):
        """Cuadros de un diseño de tronco, escalados una sola vez por tamaño."""
        if (tamano, variante) not in self._frames_tronco_escalados:
            self._frames_tronco_escalados[(tamano, variante)] = [
                pygame.transform.scale(f, tamano) for f in self.variantes_eco.get(variante, [])]
        return self._frames_tronco_escalados[(tamano, variante)]

    def _cargar_caldero(self):
        """Caldero animado sobre el pintado en el mapa; (zoom, fila) -> cuadros.

        El ajuste fino está en Hitboxes/caldero_alineacion.json (mundo 960x720).
        Filas: 1 estable, 2 peligroso, 3 crítico y 4 campaña terminada."""
        from nucleo.recursos import cargar_spritesheet_frames
        from nucleo.rutas import RAIZ
        try:
            datos = json.loads((RAIZ / "Hitboxes" / "caldero_alineacion.json").read_text(encoding="utf-8"))
            rect = pygame.Rect(datos["x"], datos["y"], datos["w"], datos["h"])
        except (OSError, ValueError, KeyError) as error:
            print("[Arte] Sin alineación del caldero:", error)
            return None, {}
        cuadros = {}
        for fila in range(1, 5):
            originales = cargar_spritesheet_frames(f"Caldero/Caldero-ecos-fila{fila}.png", 4)
            for zoom in (1, ZOOM_COPA):
                cuadros[(zoom, fila)] = [self._caldero_con_sombra(c, (rect.w * zoom, rect.h * zoom)) for c in originales]
        return rect, cuadros

    @staticmethod
    def _caldero_con_sombra(cuadro, tamano):
        """La sombra de contacto tapa, entre las patas, la base del caldero pintado."""
        lienzo = pygame.Surface(tamano, pygame.SRCALPHA)
        ancho, alto = tamano
        pygame.draw.ellipse(lienzo, (47, 35, 24), (ancho * 22 // 100, alto * 76 // 100, ancho * 56 // 100, alto * 18 // 100))
        lienzo.blit(pygame.transform.scale(cuadro, tamano), (0, 0))
        return lienzo

    def _dibujar_caldero(self, superficie, ahora_ms, zoom, area):
        if self.rect_caldero is None:
            return
        fase_final = self.estado.get("mundo", {}).get("caso", {}).get("fase") == "final"
        fila = 4 if fase_final else FILAS_CALDERO.get(self.estado_caldero, 1)
        cuadros = self.cuadros_caldero.get((zoom, fila))
        rect = pygame.Rect(self.rect_caldero.x * zoom, self.rect_caldero.y * zoom, self.rect_caldero.w * zoom, self.rect_caldero.h * zoom)
        if cuadros and (area is None or rect.colliderect(area)):
            superficie.blit(cuadros[(ahora_ms // 180) % len(cuadros)], rect)

    def _dibujar_mapa(self, superficie, ahora_ms, escena=None, area=None):
        """Mapa y decoraciones. ``escena`` y ``area``: recursos ampliados y zona
        visible en su capa; sin ellas, escala normal."""
        from interfaz.suministros import clave_cesto
        from nucleo.recursos import es_hoja_portales
        from un_jugador.dibujo_mapa import dibujar_mariposa, dibujar_puente_balanceandose
        zoom, origen_x, origen_y = (escena["zoom"], *escena["origen"]) if escena else (1, 0, 0)
        if escena is not None:
            superficie.set_clip(area)
            superficie.blit(escena["fondo"], area, area)
            decoraciones, puente_1, puente_roto, frames_reparacion = (
                escena["decoraciones"], self.puente_1_zoom, self.puente_roto_zoom, self.frames_reparacion_zoom)
            puente_det = self.puente_det_zoom
        else:
            superficie.blit(self.fondo, (0, 0))
            decoraciones, puente_1, puente_roto, frames_reparacion = (
                self.decoraciones, self.puente_1, self.puente_roto, self.frames_reparacion)
            puente_det = self.puente_det
        caso = self.estado.get("mundo", {}).get("caso", {})
        puente = caso.get("puente") or {}
        encargo = caso.get("encargo")
        cestos = self.cesto_zoom if escena is not None else self.arte.cestos
        gemelos = self._npcs_gemelos()
        for objeto in decoraciones:
            if objeto.get("personaje") in gemelos:
                continue
            if area is not None and not objeto.get("mariposa") and not objeto["rect"].inflate(40, 40).colliderect(area):
                continue  # fuera de cámara: no se escala ni se rota
            if self.dimension == LA_COPA and objeto is puente_1 and puente.get("estado", "REPAIRED") != "REPAIRED":
                # Roto hasta que estén los materiales; deteriorado mientras se repara.
                listo = puente.get("estado") in ("READY_TO_REPAIR", "REPAIR_MINIGAME", "REPAIR_ANIMATION")
                superficie.blit((puente_det if listo else None) or puente_roto or objeto["imagen"], objeto["rect"])
                continue
            if objeto.get("cuadros_reposo"):  # NPC con su animación de reposo
                cuadros = objeto["cuadros_reposo"]
                cuadro = cuadros[(ahora_ms // 180) % len(cuadros)]
                superficie.blit(cuadro, cuadro.get_rect(midbottom=objeto["ancla_reposo"]))
                continue
            if es_hoja_portales(objeto.get("nombre", "")) and self.adornos.portal:
                continue  # se dibuja el portal animado
            if objeto.get("cesto") and cestos.get(clave_cesto(encargo)) is not None:
                imagen = cestos[clave_cesto(encargo)]
                superficie.blit(imagen, imagen.get_rect(midbottom=objeto["rect"].midbottom))
            elif objeto.get("tronco_eco") and self._frames_tronco(objeto["rect"].size, objeto.get("variante_tronco", 1)):
                frames = self._frames_tronco(objeto["rect"].size, objeto.get("variante_tronco", 1))
                superficie.blit(frames[(ahora_ms // 140) % len(frames)], objeto["rect"])
            elif objeto.get("puente_animable"):
                dibujar_puente_balanceandose(superficie, objeto, ahora_ms)
            elif objeto.get("mariposa") and objeto.get("frames"):
                dibujar_mariposa(superficie, objeto, ahora_ms)
            elif objeto.get("frames"):
                frames = objeto["frames"]
                superficie.blit(frames[(ahora_ms // 140) % len(frames)], objeto["rect"])
            else:
                superficie.blit(objeto["imagen"], objeto["rect"])
        if self.dimension == LA_COPA:
            self._dibujar_caldero(superficie, ahora_ms, zoom, area)
        rect = self.rect_portal()
        if rect:
            self.adornos.dibujar_portal(
                superficie, pygame.Rect((rect.x - origen_x) * zoom, (rect.y - origen_y) * zoom, rect.w * zoom, rect.h * zoom),
                ahora_ms, True)
        if self.dimension == LA_COPA and self.inicio_reparacion and frames_reparacion and puente_1:
            # Efecto de reparación de 8 cuadros sobre el puente.
            transcurrido = (time.monotonic() - self.inicio_reparacion) * 1000
            if transcurrido < CONFIG_REPARACION_MS:
                indice = min(len(frames_reparacion) - 1, int(transcurrido / CONFIG_REPARACION_MS * len(frames_reparacion)))
                frame = frames_reparacion[indice]
                superficie.blit(frame, frame.get_rect(center=puente_1["rect"].center))
            else:
                self.inicio_reparacion = None
        if area is not None:
            superficie.set_clip(None)

    def _dibujar_suelo(self, superficie, ahora_ms):
        """Ruta guía, encargos y anillos de objetivo (coordenadas del mundo)."""
        from interfaz.suministros import dibujar_encargos
        self.adornos.ruta(superficie, self.ruta_guia, ahora_ms)
        mundo = self.estado.get("mundo", {})
        caso = mundo.get("caso", {})
        privado = mundo.get("privado", {})
        guia = privado.get("guia", {})
        if self.dimension == LA_COPA:
            # Con la cámara cerca el texto se amplía: se parte de una fuente menor.
            dibujar_encargos(superficie, caso, self.hud.fuente)
        objetivo = (guia.get("objetivo") or privado.get("objetivo") or {}) if self.dimension == LA_COPA else (self._objetivo_presente() or {})
        for o in self.contexto().get("objetivos", []):
            mismo_rol = objetivo.get("rol") and o.get("rol") == objetivo["rol"]
            if o["id"] == objetivo.get("id") or mismo_rol or o["id"] in ("caldero", "presente:pantalla"):
                if o["id"] == "puente_1" and (caso.get("puente") or {}).get("estado") == "REPAIRED":
                    continue
                self.adornos.anillo_objetivo(superficie, (o["x"], o["y"] + 5), o.get("rol") or "mensajero", ahora_ms,
                                             ESCALA_ANILLOS_DISTRITO if self.dimension == PRESENTE else 1)

    def _dibujar_jugadores(self, suelo, vista=None, figuras=None, escena=None):
        """Sombras, anillos y cargas en ``suelo``. Con ``figuras`` (lista), los
        personajes en alta resolución se devuelven ahí, en coordenadas de pantalla."""
        from interfaz.suministros import dibujar_carga
        caso = self.estado.get("mundo", {}).get("caso", {})
        anclas = []
        for jugador in sorted(self.jugadores.values(), key=lambda j: j["posicion"].y):
            datos = jugador["datos"]
            rol = datos["rol"]
            color = COLORES[ROLES.index(rol)]
            x, y = round(jugador["posicion"].x), round(jugador["posicion"].y)
            estado = datos["animacion"] if time.monotonic() - self.ultimo_paquete < .5 else "reposo"
            if estado == "caminar" and datos.get("corriendo"):
                estado = "correr"
            hojas = (escena["personajes"] if figuras is not None else self.personajes)[self._clave_figura(datos)]
            frames = hojas.get((estado, datos.get("orientacion"))) or hojas[(estado, datos["direccion"])]
            velocidad_cuadros = {"caminar": 9, "correr": 14}.get(estado, 4)
            frame = frames[int(jugador["reloj"] * velocidad_cuadros) % len(frames)]
            if self.dimension == PRESENTE:
                pygame.draw.ellipse(suelo, (17, 28, 22), (x - 8, y - 3, 16, 5))
                self.adornos.anillo_jugador(suelo, rol, (x, y - 1), color, ESCALA_ANILLOS_DISTRITO)
            else:
                pygame.draw.ellipse(suelo, (17, 28, 22), (x - 13, y - 5, 26, 8))
                self.adornos.anillo_jugador(suelo, rol, (x, y - 1), color)
            if figuras is not None:
                zoom = escena["zoom"]
                rect = frame.get_rect(midbottom=((x - vista.x) * zoom, (y - vista.y) * zoom))
                figuras.append((frame, rect))
                tope = y - frame.get_height() // zoom
            else:
                rect = frame.get_rect(midbottom=(x, y))
                suelo.blit(frame, rect)
                tope = rect.top
            carga = (caso.get("encargo") or {}).get("cargas", {}).get(datos["id"])
            if carga:
                dibujar_carga(suelo, carga, (x + 22, y - 24))
            if datos["id"] in caso.get("tutorial_cargas", []):
                dibujar_carga(suelo, "farol", (x + 22, y - 24))
            anclas.append((datos, color, (x, tope)))
        return anclas

    def _mundo_ampliado(self, pantalla, vista, ahora_ms, escena):
        """Cámara cercana: mapa, decoraciones y personajes ya están escalados a
        su tamaño final; en cada cuadro solo se recorta lo visible."""
        zoom, (origen_x, origen_y) = escena["zoom"], escena["origen"]
        area = pygame.Rect((vista.x - origen_x) * zoom, (vista.y - origen_y) * zoom, 960, 720)
        self._dibujar_mapa(escena["capa"], ahora_ms, escena, area)
        pantalla.blit(escena["capa"], (0, 0), area)
        efectos = self.capa_efectos
        efectos.fill((0, 0, 0, 0))
        self._dibujar_suelo(efectos, ahora_ms)
        figuras = []
        anclas = self._dibujar_jugadores(efectos, vista, figuras, escena)
        pantalla.blit(pygame.transform.scale(efectos.subsurface(vista), pantalla.get_size()), (0, 0))
        for frame, rect in figuras:
            pantalla.blit(frame, rect)
        if self.dimension == LA_COPA:
            self.efectos_mapa.dibujar(pantalla, vista)
        self.particulas.dibujar(pantalla, camara=(vista.x, vista.y, zoom))
        return anclas

    def _mundo_escalado(self, pantalla, vista, ahora_ms):
        """Distrito Conecta: el mundo se dibuja en una capa y se amplía la zona visible."""
        superficie = pantalla
        if vista is not None:
            if self.capa_mundo is None:
                self.capa_mundo = pygame.Surface((960, 720)).convert()
            superficie = self.capa_mundo
        self._dibujar_mapa(superficie, ahora_ms)
        self._dibujar_suelo(superficie, ahora_ms)
        anclas = self._dibujar_jugadores(superficie)
        self.particulas.dibujar(superficie)
        if vista is not None:
            # Pixel art: scale.
            pygame.transform.scale(superficie.subsurface(vista), pantalla.get_size(), pantalla)
        return anclas

    def _destino_flecha(self, vista):
        """A dónde señala la flecha: el portal al terminar, o un objetivo fuera de cámara."""
        rect = self.rect_portal()
        if self.dimension_completa() and rect:
            return rect.center
        mundo = self.estado.get("mundo", {})
        objetivo = (mundo.get("privado", {}).get("guia", {}).get("objetivo") if self.dimension == LA_COPA
                    else self._objetivo_presente())
        if objetivo and vista is not None and not vista.inflate(-60, -60).collidepoint(objetivo["x"], objetivo["y"]):
            return objetivo["x"], objetivo["y"]
        return None

    def dibujar(self, superficie, codigo, mouse=(-1, -1)):
        self.mouse = mouse
        ahora_ms = pygame.time.get_ticks()
        vista = self.vista_camara()
        escena = self.escenas_zoom.get(self.dimension) if vista is not None else None
        if escena is not None:
            anclas = self._mundo_ampliado(superficie, vista, ahora_ms, escena)
        else:
            anclas = self._mundo_escalado(superficie, vista, ahora_ms)
        mio = self.jugadores.get(self.identificador)
        destino = self._destino_flecha(vista)
        if destino and mio and not self.panel.activo:
            origen = self.a_pantalla(mio["posicion"].x, mio["posicion"].y - 20, vista)
            self.flecha.dibujar(superficie, origen, self.a_pantalla(*destino, vista), ahora_ms,
                                limites=(40, 60, 920, 640))
        etiquetas = []
        for datos, color, (x, tope) in anclas:
            x, tope = self.a_pantalla(x, tope, vista)
            x, tope = round(x), round(tope)
            if not self.mostrar_nombres:
                if datos["id"] == self.identificador:  # sin etiquetas, igual te ubicas
                    self.adornos.marcador_local(superficie, (x, tope - 6), color, ahora_ms)
                continue
            nombre = datos["nombre"] + (" (tú)" if datos["id"] == self.identificador else "")
            if datos.get("controlador") == "bot" and self.dimension == PRESENTE:
                from mundo.personajes import PERSONAJES_DISTRITO
                nombre = "Bot · " + PERSONAJES_DISTRITO[datos["rol"]][0]
            elif datos.get("controlador") == "bot":
                nombre = "Bot · " + nombre
            etiqueta = self.fuente.render(nombre, True, color)
            caja = etiqueta.get_rect(midbottom=(x, tope - 7))
            caja.clamp_ip(superficie.get_rect().inflate(-8, -8))
            while any(caja.inflate(12, 8).colliderect(anterior) for _, anterior, *_ in etiquetas) and caja.top > 24:
                caja.y -= 20
            etiquetas.append((etiqueta, caja, color, datos["id"] == self.identificador))
        for etiqueta, caja, color, local in etiquetas:
            fondo = pygame.Surface(caja.inflate(10, 6).size, pygame.SRCALPHA)
            fondo.fill((13, 29, 23, 150))
            superficie.blit(fondo, caja.inflate(10, 6))
            superficie.blit(etiqueta, caja)
            if local:
                self.adornos.marcador_local(superficie, (caja.centerx, caja.top - 4), color, ahora_ms)
        if self.mostrar_hud:
            mundo = self.estado.get("mundo", {})
            privado = mundo.get("privado", {})
            self._dibujar_hud(superficie, codigo, mundo.get("caso", {}), privado, privado.get("guia", {}))
        self._dibujar_capas_superiores(superficie)

    @staticmethod
    def _pastilla(superficie, rect, alfa=115):
        """Fondo discreto y translúcido para el HUD."""
        capa = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(capa, (8, 24, 18, alfa), capa.get_rect(), border_radius=8)
        superficie.blit(capa, rect)

    def _texto_pastilla(self, superficie, texto, fuente, color=(255, 243, 210), **ancla):
        render = fuente.render(texto, True, color)
        caja = render.get_rect(**ancla)
        self._pastilla(superficie, caja.inflate(20, 10))
        superficie.blit(render, caja)
        return caja

    def _textos_objetivo(self, caso, privado, guia):
        """(título corto siempre visible, detalle que se abre con J)."""
        if self.dimension != PRESENTE:
            return guia.get("titulo", caso["titulo"]), guia.get("detalle", privado.get("instruccion", ""))
        presente = caso.get("presente") or {}
        pistas, total = presente.get("pistas", 0), presente.get("total_pistas", 3)
        if presente.get("completada"):
            return "¡Misión completada! Ve al portal", "Sigue la flecha hasta el portal para elegir otra época."
        if pistas < total:
            return f"Pistas {pistas}/{total}", "Habla con las personas marcadas (E). Tus pistas quedan en el celular (C)."
        return "Vayan a la pantalla pública", "¡Tienen las tres pistas! Vayan a la pantalla pública y decidan en el celular (C)."

    def _dibujar_hud(self, superficie, codigo, caso, privado, guia):
        """Solo lo importante a la vista; lo demás se abre con J."""
        from interfaz.guia import estrella
        from multijugador.dimensiones_red import DIMENSIONES_RED
        opciones = self.candidatos()
        claves = [o["id"] for o in opciones]
        if self.seleccion not in claves:
            self.seleccion = claves[0] if claves else None
        seleccion = next((o for o in opciones if o["id"] == self.seleccion), None)
        if seleccion and not self.panel.activo:
            texto = "[E] " + seleccion["nombre"] + (" · Tab: cambiar" if len(opciones) > 1 else "")
            self._texto_pastilla(superficie, texto, self.fuente, midbottom=(480, 704))
        if not caso:
            return
        titulo, detalle = self._textos_objetivo(caso, privado, guia)
        self._texto_pastilla(superficie, titulo, self.fuente, (237, 185, 87), topleft=(22, 16))
        # Arriba a la derecha: estrellas, reloj y poder.
        self._pastilla(superficie, pygame.Rect(762, 10, 186, 38))
        estrella(superficie, (782, 29), 9, (255, 215, 90))
        estrellas = self.fuente.render(f"{caso.get('estrellas', 0)}/{caso.get('estrellas_total', 11)}", True, (255, 243, 210))
        superficie.blit(estrellas, estrellas.get_rect(midleft=(796, 29)))
        if self.dimension != PRESENTE and not caso.get("sin_prisa"):
            arte_tiempo = self.arte.tiempo
            if arte_tiempo is not None:
                superficie.blit(arte_tiempo, arte_tiempo.get_rect(center=(852, 29)))
            segundos = self.fuente.render(f"{caso.get('proxima_oleada', 60)}s", True, (237, 185, 87))
            superficie.blit(segundos, segundos.get_rect(midleft=(864, 29)))
        rol = (self.yo() or {}).get("rol")
        if self.dimension == LA_COPA and rol:
            iconos = self.arte.poder_usado if privado.get("habilidad_usada") else self.arte.poder_listo
            if iconos.get(rol) is not None:
                superficie.blit(iconos[rol], iconos[rol].get_rect(center=(928, 29)))
            barra = self.arte.barra_recarga[self._estado_recarga(privado, rol)]
            if barra is not None:
                superficie.blit(barra, barra.get_rect(center=(915, 58)))
        if not self.mostrar_detalles:
            if not self.panel.activo:
                self.hud.dibujar_avisos(superficie, 22, 70)
                pista = self.hud.fuente.render("J: detalles · Esc: menú", True, (205, 214, 190))
                caja = pista.get_rect(bottomright=(946, 710))
                self._pastilla(superficie, caja.inflate(12, 6), 90)
                superficie.blit(pista, caja)
            return
        # Detalles (J): tarea completa, indicadores y teclas.
        nombre = DIMENSIONES_RED[self.dimension]["nombre"]
        self._pastilla(superficie, pygame.Rect(12, 48, 590, 112), 165)
        self.panel.texto_lineas(superficie, detalle, 25, 56, 560, self.fuente)
        derecha = [f"{nombre} · Sala {codigo} · {len(self.jugadores)} aquí"]
        if self.dimension != PRESENTE:
            derecha.append("Primera aventura: sin reloj" if caso.get("sin_prisa") else f"El rumor crece en {caso.get('proxima_oleada', 60)} s")
            estados_puente = {
                "DAMAGED": "Puente 1: roto", "MATERIALS_PENDING": "Puente 1: faltan materiales",
                "READY_TO_REPAIR": "Puente 1: ¡listo para reparar!", "REPAIR_MINIGAME": "Puente 1: en reparación",
                "REPAIR_ANIMATION": "Puente 1: reparándose…", "REPAIRED": "Puente 1: reparado",
            }
            if (caso.get("puente") or {}).get("estado") in estados_puente:
                derecha.append(estados_puente[caso["puente"]["estado"]])
        for indice, linea in enumerate(derecha[:3]):
            superficie.blit(self.hud.fuente.render(linea, True, (237, 185, 87)), (368, 112 + indice * 15))
        if not self.panel.activo:
            if self.dimension == LA_COPA:
                pygame.draw.rect(superficie, (126, 81, 45), self.boton_guia, border_radius=7)
                pygame.draw.rect(superficie, (237, 185, 87), self.boton_guia, 2, border_radius=7)
                objetivo_guia = guia.get("objetivo") or {}
                texto_boton = guia.get("boton", "Ver mi tarea")
                if objetivo_guia and guia.get("accion") == "interactuar" and not self.cerca(objetivo_guia):
                    texto_boton = "Ver mi tarea · M"
                texto = self.panel.pequena.render(texto_boton, True, (255, 243, 210))
                superficie.blit(texto, texto.get_rect(center=self.boton_guia.center))
            self.hud.dibujar(superficie, 18, 176)
            self._texto_pastilla(superficie, "Shift: correr | E: ayudar | I: pistas | M: tarea | Q: poder | H: HUD | L: nombres",
                                 self.hud.fuente, bottomleft=(22, 672))

    @staticmethod
    def _estado_recarga(privado, rol):
        """Llena: se puede usar; media: falta tu prueba; vacía: se recarga el próximo caso."""
        if privado.get("habilidad_usada"):
            return "vacia"
        return "llena" if any(p.get("id") == "pista_" + rol for p in privado.get("inventario", [])) else "mitad"

    def _dibujar_capas_superiores(self, superficie):
        self._dibujar_aviso_viaje(superficie)
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
        if self.pantalla_final is not None:
            self.pantalla_final.dibujar(superficie)
