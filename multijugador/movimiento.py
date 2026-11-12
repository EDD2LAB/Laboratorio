"""Geometría y movimiento autoritativo, sin Pygame ni recursos gráficos."""
import hashlib
import json
import math
from collections import deque
from pathlib import Path
import unicodedata
from logica.movimiento_suave import (desplazar, linea_toca_rect, permite_salir_bloqueos,
                                     rect_en_union, segmento_libre)

from .dimensiones_red import (DIMENSIONES_RED, FUTURO, INTERIORES, LA_COPA, PRESENTE, RADIO_PUERTA, RADIO_SALIDA, cargar_datos,
                              cargar_interior, cerca_de_rect, destinos, edificios_de, rect_portal, rect_salida, spawn_interior,
                              spawn_presente)

ANCHO, ALTO = 960, 720
VELOCIDAD = 155.0
# Shift: correr (mismo multiplicador que el modo de un jugador, mundo/jugador.py).
MULTIPLICADOR_CORRER = 1.65
# Distrito Conecta se ve con zoom 3 y La Copa con zoom 2: así avanzan igual en pantalla.
FACTOR_VELOCIDAD_PRESENTE = 2 / 3
MAPA = Path(__file__).resolve().parent.parent / "Hitboxes" / "Mapas" / "Pr_MañanaLumi_hitboxes.json"
LADO_CELDA = 32  # tamaño de las celdas del índice de paredes
MAX_MEMORIA_COLISIONES = 300_000
ORIENTACIONES = ("derecha", "abajo_derecha", "abajo", "abajo_izquierda",
                 "izquierda", "arriba_izquierda", "arriba", "arriba_derecha")


def orientacion_de(dx, dy):
    """Una de las ocho orientaciones de los sprites para un movimiento (y crece hacia abajo)."""
    return ORIENTACIONES[round(math.atan2(dy, dx) / (math.pi / 4)) % 8]


def normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower().replace("\\", "/")) if not unicodedata.combining(c))


def es_personaje_jugable(nombre):
    ruta = normalizar(nombre)
    # Kael, Mira, Tarek y Luma pueden estar en manos de un jugador: su sprite no es una pared.
    return ("guardian" in ruta or "/mensajero/" in ruta or "habitante hombre" in ruta or "habitante mujer" in ruta
            or "aspirante hombre" in ruta or "aspirante mujer" in ruta)


class ColisionesMapa:
    def __init__(self, datos=None):
        if datos is None:
            datos = json.loads(MAPA.read_text(encoding="utf-8"))
        self.datos = datos
        # El exterior del Futuro tiene calles estrechas y figuras pequeñas:
        # colisionan los pies, no una caja del tamaño del cuerpo.
        self.tamano_pies = tuple(datos.get("tamano_pies", (12, 8)))
        self.factor_velocidad = 1.0
        self.firma = hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest()[:16]
        self.paredes = [h for h in datos.get("hitboxes", []) if h.get("role", "wall") == "wall"]
        self.zonas = [h for h in datos.get("hitboxes", []) if h.get("role") == "walkable"]
        self._zonas_union = [("rect", *self.rectangulo(h)) if h.get("type", "rect") == "rect"
                             else ("circle", h.get("cx", 0) * ANCHO, h.get("cy", 0) * ALTO, h.get("r", 0) * ANCHO)
                             for h in self.zonas if h.get("type", "rect") in ("rect", "circle")]
        # Rectángulos extra que bloquean el paso (p. ej., el Puente 1 roto).
        self.bloqueos = []
        # Área del mapa dentro de 960x720 (Distrito Conecta va centrado).
        self.limites = tuple(datos["rect_mapa"]) if datos.get("rect_mapa") else None
        self.npcs = []
        for objeto in datos.get("decoracion", []):
            ruta = normalizar(objeto["name"])
            if ruta.startswith("npcs/") and not es_personaje_jugable(ruta):
                self.npcs.append((round(objeto["x"] * ANCHO), round(objeto["y"] * ALTO),
                                  max(1, round(objeto["w"] * ANCHO)), max(1, round(objeto["h"] * ALTO))))
        self._celdas = self._indexar_paredes()
        # El mapa no cambia: cada posición entera se calcula una sola vez.
        self._memoria = {}

    def _caja_pared(self, pared):
        """Rectángulo (x1, y1, x2, y2) fuera del cual la pared no puede tocar a nadie."""
        tipo = pared.get("type", "rect")
        if tipo == "rect":
            x, y, w, h = self.rectangulo(pared)
            return x, y, x + w, y + h
        if tipo == "circle":
            cx, cy = pared.get("cx", 0) * ANCHO, pared.get("cy", 0) * ALTO
            radio = max(4, pared.get("r", 0) * ANCHO)
            return cx - radio, cy - radio, cx + radio, cy + radio
        if tipo == "line":
            x1, y1 = pared.get("x1", 0) * ANCHO, pared.get("y1", 0) * ALTO
            x2, y2 = pared.get("x2", 0) * ANCHO, pared.get("y2", 0) * ALTO
            margen = math.hypot(12, 8) / 2 + max(2, pared.get("thickness", .008) * ANCHO) / 2
            return min(x1, x2) - margen, min(y1, y2) - margen, max(x1, x2) + margen, max(y1, y2) + margen
        return None

    def _indexar_paredes(self):
        celdas = {}
        for pared in self.paredes:
            caja = self._caja_pared(pared)
            if caja is None:
                continue
            x1, y1, x2, y2 = (math.floor(valor / LADO_CELDA) for valor in caja)
            for cx in range(x1, x2 + 1):
                for cy in range(y1, y2 + 1):
                    celdas.setdefault((cx, cy), []).append(pared)
        return celdas

    @staticmethod
    def rectangulo(h):
        return (round(h.get("rx", 0) * ANCHO), round(h.get("ry", 0) * ALTO),
                max(1, round(h.get("rw", 0) * ANCHO)), max(1, round(h.get("rh", 0) * ALTO)))

    @staticmethod
    def solapa(a, b):
        x, y, w, h = a
        bx, by, bw, bh = b
        return x < bx + bw and x + w > bx and y < by + bh and y + h > by

    def bloqueado(self, x, y):
        # La posición pública representa el centro inferior de la hitbox de pies.
        clave = (round(x), round(y))
        rect = self.rect_pies(*clave)
        # Lo único que cambia durante la partida (p. ej., el Puente 1 roto).
        if self.bloqueos and any(self.solapa(rect, bloqueo) for bloqueo in self.bloqueos):
            return True
        return self._fijo(x, y)

    def _fijo(self, x, y):
        clave = (round(x), round(y))
        rect = self.rect_pies(*clave)
        resultado = self._memoria.get(clave)
        if resultado is None:
            if len(self._memoria) >= MAX_MEMORIA_COLISIONES:
                self._memoria.clear()
            resultado = self._memoria[clave] = self._bloqueado_fijo(rect)
        return resultado

    def rect_pies(self, x, y):
        ancho, alto = self.tamano_pies
        return round(x) - ancho // 2, round(y) - alto, ancho, alto

    def _paredes_cercanas(self, izquierda, arriba, derecha, abajo):
        vistas, resultado = set(), []
        for cx in range(izquierda // LADO_CELDA, derecha // LADO_CELDA + 1):
            for cy in range(arriba // LADO_CELDA, abajo // LADO_CELDA + 1):
                for pared in self._celdas.get((cx, cy), ()):
                    if id(pared) not in vistas:
                        vistas.add(id(pared))
                        resultado.append(pared)
        return resultado

    def _bloqueado_fijo(self, rect):
        izquierda, arriba, w, h = rect
        derecha, abajo = izquierda + w, arriba + h
        if izquierda < 0 or arriba < 0 or derecha > ANCHO or abajo > ALTO:
            return True
        if self.limites:
            lx, ly, lw, lh = self.limites
            if izquierda < lx or arriba < ly or derecha > lx + lw or abajo > ly + lh:
                return True
        for pared in self._paredes_cercanas(izquierda, arriba, derecha, abajo):
            tipo = pared.get("type", "rect")
            if tipo == "rect" and self.solapa(rect, self.rectangulo(pared)):
                return True
            if tipo == "circle":
                cx, cy = pared.get("cx", 0) * ANCHO, pared.get("cy", 0) * ALTO
                px, py = max(izquierda, min(cx, derecha)), max(arriba, min(cy, abajo))
                if (cx - px) ** 2 + (cy - py) ** 2 <= max(4, pared.get("r", 0) * ANCHO) ** 2:
                    return True
            if tipo == "line":
                x1, y1 = pared.get("x1", 0) * ANCHO, pared.get("y1", 0) * ALTO
                if linea_toca_rect(rect, x1, y1, pared.get("x2", 0) * ANCHO,
                                  pared.get("y2", 0) * ALTO, max(2, pared.get("thickness", .008) * ANCHO)):
                    return True
        if self.zonas:
            dentro = False
            for zona in self.zonas:
                if zona.get("type", "rect") == "rect":
                    zx, zy, zw, zh = self.rectangulo(zona)
                    dentro |= izquierda >= zx and arriba >= zy and derecha <= zx + zw and abajo <= zy + zh
                elif zona.get("type") == "circle":
                    cx, cy, radio = zona["cx"] * ANCHO, zona["cy"] * ALTO, zona["r"] * ANCHO
                    dentro |= all((px - cx) ** 2 + (py - cy) ** 2 <= radio ** 2
                                  for px, py in ((izquierda, arriba), (derecha, arriba), (izquierda, abajo), (derecha, abajo)))
            if not dentro and not rect_en_union(rect, self._zonas_union):
                return True
        return any(self.solapa(rect, npc) for npc in self.npcs)

    def mover(self, x, y, dx, dy, segundos, factor=1.0):
        norma = max(1, math.hypot(dx, dy))
        distancia = VELOCIDAD * self.factor_velocidad * factor * max(0, min(segundos, .15))
        return desplazar(x, y, dx / norma * distancia, dy / norma * distancia, self.puede_pasar)

    def puede_pasar(self, origen, destino):
        if self._fijo(*destino):
            return False
        pies = lambda p: self.rect_pies(*p)
        return permite_salir_bloqueos(pies(origen), pies(destino), self.bloqueos)

    def trayecto_libre(self, origen, destino):
        return segmento_libre(origen, destino, self.puede_pasar)

    def salida_bloqueo(self, x, y):
        """Salida más cercana alcanzable a pie, sin saltar paredes estáticas."""
        if self._fijo(x, y):
            return None
        candidatos = []
        ancho, alto = self.tamano_pies
        for bx, by, bw, bh in self.bloqueos:
            if self.solapa(self.rect_pies(x, y), (bx, by, bw, bh)):
                candidatos.extend(((bx - ancho / 2, y), (bx + bw + ancho / 2, y), (x, by), (x, by + bh + alto)))
        for punto in sorted(candidatos, key=lambda p: math.hypot(p[0] - x, p[1] - y)):
            if not self.bloqueado(*punto) and self.trayecto_libre((x, y), punto):
                return punto
        return None

    def _sitio_libre(self, x, y, ocupadas, separacion=22):
        return (not any(self.bloqueado(x + ox, y + oy) for ox, oy in ((0, 0), (-8, 0), (8, 0), (0, -8), (0, 8)))
                and all(math.hypot(x - a, y - b) >= separacion for a, b in ocupadas))

    def inicio_libre(self, x, y, ocupadas=()):
        for radio in range(0, 161, 4):
            for dx in range(-radio, radio + 1, 4):
                for dy in ({-radio, radio} if radio else {0}):
                    if self._sitio_libre(x + dx, y + dy, ocupadas):
                        return float(x + dx), float(y + dy)
        raise ValueError("No se encontró una posición inicial libre en el mapa.")

    def inicio_alcanzable(self, x, y, ocupadas=(), separacion=22):
        """Como ``inicio_libre``, pero buscando a pie desde (x, y): nunca aparece
        al otro lado de una pared, como en el vacío junto a una plataforma."""
        vistos, cola = {(x, y)}, deque([(x, y)])
        while cola and len(vistos) < 6000 and not self.bloqueado(x, y):
            px, py = cola.popleft()
            if self._sitio_libre(px, py, ocupadas, separacion):
                return float(px), float(py)
            for vecino in ((px + 4, py), (px - 4, py), (px, py + 4), (px, py - 4)):
                if vecino not in vistos and not self.bloqueado(*vecino):
                    vistos.add(vecino)
                    cola.append(vecino)
        return self.inicio_libre(x, y, ocupadas)


class PartidaMovimiento:
    def __init__(self, jugadores, ahora, colisiones=None, semilla=None):
        self.colisiones = colisiones or ColisionesMapa()
        self.jugadores = {}
        self.controles = {}
        self.ultima = ahora
        ocupadas = []
        for i, jugador in enumerate(jugadores):
            x, y = self.colisiones.inicio_libre(415 + (i % 2) * 130, 390 + (i // 2) * 70, ocupadas)
            ocupadas.append((x, y))
            self.jugadores[jugador["id"]] = {
                "id": jugador["id"], "nombre": jugador["nombre"], "rol": jugador["rol"],
                "x": x, "y": y, "direccion": "abajo", "animacion": "reposo", "seq": -1,
                "dimension": LA_COPA, "apariencia": jugador.get("apariencia"),
            }
        from .campana import CampanaCopa
        self.conectados = set(self.jugadores)
        self.mapas = {LA_COPA: self.colisiones}
        self.viajes = 0
        self.mision = CampanaCopa(self.jugadores, self.colisiones.datos, semilla=semilla)
        self.mision.linea_final = lambda jugador, a, b: self.colisiones_de_jugador(jugador).trayecto_libre(a, b)
        self.mision.viajar = self.viajar
        self.mision.cancelar_viaje = self.cancelar_viaje
        self.mision.entrar_edificio = self.entrar_edificio
        self.mision.salir_edificio = self.salir_edificio
        self.interiores = {}
        self.interiores_futuro = {}
        self.viaje = None  # propuesta de viaje en grupo (ver viajar)
        self._sincronizar_bloqueos()
        try:
            self.colisiones_de(PRESENTE)  # el portal funciona desde el primer momento
            self.colisiones_de(FUTURO)
            from .exploracion import colocar_vecinos
            colocar_vecinos(self.mision, self.colisiones)
        except (OSError, ValueError) as error:
            print("[Multijugador] Distrito Conecta no disponible:", error)

    def _sincronizar_bloqueos(self):
        self.colisiones.bloqueos = [self.mision.puente.rect] if self.mision.puente.bloquea_paso else []

    def colisiones_de(self, dimension):
        if dimension not in self.mapas:
            datos = cargar_datos(dimension)
            self.mapas[dimension] = ColisionesMapa(datos)
            if dimension in (PRESENTE, FUTURO):
                self.mapas[dimension].factor_velocidad = FACTOR_VELOCIDAD_PRESENTE
            if dimension == FUTURO and self.mision.futuro is None:
                from .nucleo import MisionNucleo
                self.mision.futuro = MisionNucleo(self.mapas[dimension], datos, self.mision.indicadores,
                                                  self.mision.siguiente_evento, self.mision.expediente)
                self.mision.futuro.avisar = self.mision._avisar
                from logica.dimensiones import EDIFICIOS_FUTURO
                self.mision.futuro.edificios = edificios_de(datos)
                for clave, puerta in self.mision.futuro.edificios.items():
                    puerta["nombre"] = EDIFICIOS_FUTURO[clave]["nombre"]
                self.interiores_futuro = {e: ColisionesMapa(cargar_interior(e, FUTURO)) for e in INTERIORES}
                for clave, mapa in self.interiores_futuro.items():
                    x, y = mapa.inicio_libre(*spawn_interior(mapa.datos))
                    self.mision.futuro.edificios[clave]["salida"] = dict(x=round(x), y=round(y))
                self.mision.exploracion.configurar(FUTURO, self.interiores_futuro)
            if dimension == PRESENTE and self.mision.presente is None:
                from .presente import MisionPresente
                self.interiores = {e: ColisionesMapa(cargar_interior(e)) for e in INTERIORES}
                self.mision.presente = MisionPresente(self.mapas[dimension], datos, self.mision.indicadores,
                                                      self.mision.siguiente_evento, self.mision.expediente,
                                                      self.interiores, edificios_de(datos))
                self.mision.exploracion.configurar(PRESENTE, self.interiores)
        return self.mapas[dimension]

    def colisiones_de_jugador(self, jugador):
        """Las paredes de donde está: su edificio o el mapa de su dimensión."""
        interiores = self.interiores_futuro if jugador.get("dimension") == FUTURO else self.interiores
        return interiores[jugador["interior"]] if jugador.get("interior") else self.colisiones_de(jugador.get("dimension", LA_COPA))

    def _colocar(self, identificador, x, y, interior):
        self.viajes += 1  # el cliente lo coloca sin recorrer el mapa
        self.controles.pop(identificador, None)
        self.jugadores[identificador].update(x=x, y=y, interior=interior, animacion="reposo", corriendo=False, viaje=self.viajes)

    def entrar_edificio(self, identificador, edificio):
        if not isinstance(edificio, str):
            raise ValueError("Elige un edificio válido.")
        jugador = self.jugadores[identificador]
        presente = self.mision.futuro if jugador.get("dimension") == FUTURO else self.mision.presente
        puerta = presente.edificios.get(edificio) if presente else None
        if jugador.get("dimension") == FUTURO and self.mision.futuro.barreras_activas:
            raise ValueError("NÚCLEO bloqueó este sector.")
        if jugador.get("dimension") not in (PRESENTE, FUTURO) or jugador.get("interior") or puerta is None:
            raise ValueError("Aquí no hay una puerta.")
        if not cerca_de_rect(jugador["x"], jugador["y"], puerta["rect"], RADIO_PUERTA):
            raise ValueError("Acércate a la puerta y pulsa E.")
        interiores = self.interiores_futuro if jugador.get("dimension") == FUTURO else self.interiores
        mapa = interiores[edificio]
        ocupadas = [(j["x"], j["y"]) for j in self.jugadores.values()
                    if j.get("interior") == edificio and j.get("dimension") == jugador.get("dimension")]
        colocar = mapa.inicio_alcanzable if jugador.get("dimension") == FUTURO else mapa.inicio_libre
        self._colocar(identificador, *colocar(*spawn_interior(mapa.datos), ocupadas), edificio)
        return {"mensaje": "Entraste a " + puerta["nombre"] + ".", "silencioso": True}

    def salir_edificio(self, identificador):
        jugador = self.jugadores[identificador]
        edificio = jugador.get("interior")
        if not edificio:
            raise ValueError("Ya estás en la calle.")
        interiores = self.interiores_futuro if jugador.get("dimension") == FUTURO else self.interiores
        if not cerca_de_rect(jugador["x"], jugador["y"], rect_salida(interiores[edificio].datos), RADIO_SALIDA):
            raise ValueError("Acércate a la salida y pulsa E.")
        mision = self.mision.futuro if jugador.get("dimension") == FUTURO else self.mision.presente
        puerta = mision.edificios[edificio]
        self._colocar(identificador, float(puerta["x"]), float(puerta["y"]), None)
        return {"mensaje": "Volviste a la calle.", "silencioso": True}

    def presentes_en(self, dimension):
        return {i for i in self.conectados if self.jugadores.get(i, {}).get("dimension", LA_COPA) == dimension}

    # ------------------------------------------------------------- portal
    # El equipo viaja junto: el portal registra una propuesta de destino y
    # cada humano debe ir al portal y aceptarla. Cuando todos los humanos de
    # la dimensión aceptaron (y siguen junto al portal), viaja todo el equipo,
    # incluidos los bots, y se cierra lo que estaba en curso en el mapa.
    RADIO_PORTAL = 48
    RADIO_PANTALLA = 68

    def _humano(self, identificador):
        return self.jugadores[identificador].get("controlador") != "bot"

    def _junto_al_portal(self, identificador, origen):
        jugador = self.jugadores[identificador]
        if jugador.get("dimension", LA_COPA) != origen or jugador.get("interior"):
            return False
        if cerca_de_rect(jugador["x"], jugador["y"], rect_portal(origen, self.colisiones_de(origen).datos), self.RADIO_PORTAL):
            return True
        # La pantalla pública también lleva a Ciudad Núcleo y de vuelta (sin portal propio en el mapa).
        mision = {PRESENTE: self.mision.presente, FUTURO: self.mision.futuro}.get(origen)
        return mision is not None and math.hypot(jugador["x"] - mision.pantalla["x"], jugador["y"] - mision.pantalla["y"]) <= self.RADIO_PANTALLA

    def faltan_viaje(self):
        """Humanos conectados de la dimensión de origen que aún no aceptaron."""
        if not self.viaje:
            return []
        origen, aceptan = self.viaje["origen"], self.viaje["aceptan"]
        return [i for i in sorted(self.presentes_en(origen)) if self._humano(i) and i not in aceptan]

    def viajar(self, identificador, destino):
        """Acepta (o propone) viajar a ``destino``; viajan todos cuando aceptan todos."""
        jugador = self.jugadores[identificador]
        origen = jugador.get("dimension", LA_COPA)
        if destino not in DIMENSIONES_RED or destino == origen:
            raise ValueError("Elige otra dimensión en el portal.")
        if not DIMENSIONES_RED[destino]["disponible"]:
            raise ValueError(DIMENSIONES_RED[destino]["nombre"] + " todavía está en construcción.")
        if not self._junto_al_portal(identificador, origen):
            raise ValueError("Acércate al portal y pulsa E.")
        nombre = DIMENSIONES_RED[destino]["nombre"]
        if not self.viaje or self.viaje["destino"] != destino or self.viaje["origen"] != origen:
            self.viaje = {"origen": origen, "destino": destino, "aceptan": set(), "propone": identificador}
            otros = [i for i in self.presentes_en(origen) if i != identificador and self._humano(i)]
            if otros:
                self.mision._avisar(otros, jugador["nombre"] + " quiere viajar a " + nombre +
                                    ". Vayan al portal y pulsen E para aceptar.", "logro")
        self.viaje["aceptan"].add(identificador)
        faltan = self.faltan_viaje()
        if faltan:
            nombres = ", ".join(self.jugadores[i]["nombre"] for i in faltan)
            return {"mensaje": "Aceptaste viajar a " + nombre + ". Esperando a: " + nombres + "."}
        self._viajar_equipo(origen, destino)
        return {"mensaje": "¡El equipo viaja junto a " + nombre + "!", "dimension": destino}

    def cancelar_viaje(self, identificador):
        if self.viaje:
            self.viaje["aceptan"].discard(identificador)
            if not self.viaje["aceptan"]:
                self.viaje = None
        return {"mensaje": "Ya no aceptas el viaje."}

    def _revisar_viaje(self):
        """Quien se aleja del portal o se desconecta deja de aceptar."""
        if not self.viaje:
            return
        origen = self.viaje["origen"]
        self.viaje["aceptan"] = {i for i in self.viaje["aceptan"]
                                 if i in self.conectados and self._junto_al_portal(i, origen)}
        if not self.viaje["aceptan"]:
            self.viaje = None

    def _viajar_equipo(self, origen, destino):
        mapa = self.colisiones_de(destino)
        if destino == LA_COPA:
            # Sobre las tablas, justo delante de la boca del portal.
            px, py, pw, ph = rect_portal(LA_COPA, mapa.datos)
            inicio = (px + pw // 2 - 9, py + ph + 3)
        else:
            inicio = spawn_presente(mapa.datos)
            if destino == FUTURO:
                inicio = mapa.inicio_libre(*inicio)
        viajeros = [i for i, j in self.jugadores.items() if j.get("dimension", LA_COPA) == origen]
        # Termina todo lo que estaba en curso en el mapa que se deja.
        if self.mision.puente.reparador in viajeros:
            self.mision.puente.liberar()
        encargo = getattr(self.mision, "encargo", None)
        if encargo is not None and encargo.ayudante in viajeros:
            encargo.ayudante = None
        ocupadas = [(j["x"], j["y"]) for j in self.jugadores.values() if j.get("dimension", LA_COPA) == destino]
        self.viajes += 1
        for identificador in viajeros:
            # Más juntos que al empezar: la plataforma del portal es estrecha.
            x, y = mapa.inicio_alcanzable(*inicio, ocupadas, separacion=18)
            ocupadas.append((x, y))
            self.controles.pop(identificador, None)
            self.jugadores[identificador].update(dimension=destino, x=x, y=y, direccion="abajo",
                                                 animacion="reposo", corriendo=False, viaje=self.viajes, interior=None)
        self.viaje = None
        nombre = DIMENSIONES_RED[destino]["nombre"]
        self.mision._avisar(viajeros, "El equipo llegó a " + nombre + ". Los indicadores viajan con ustedes.", "logro")

    def publico_viaje(self):
        if not self.viaje:
            return None
        destino = self.viaje["destino"]
        return {"origen": self.viaje["origen"], "destino": destino, "nombre": DIMENSIONES_RED[destino]["nombre"],
                "aceptan": sorted(self.viaje["aceptan"]),
                "faltan": [self.jugadores[i]["nombre"] for i in self.faltan_viaje()]}

    def actuar(self, identificador, datos, ahora):
        self.actualizar(ahora)
        presentes = self.conectados if datos.get("accion") == "expediente_paso" else self.presentes_en(LA_COPA)
        return self.mision.actuar(identificador, datos, ahora, presentes)

    def recibir(self, identificador, datos, ahora):
        if identificador not in self.jugadores:
            raise ValueError("Jugador fuera de la partida.")
        dx, dy, seq = datos.get("dx"), datos.get("dy"), datos.get("seq")
        correr = datos.get("correr", False)  # opcional: clientes antiguos no lo envían
        if (type(dx) is not int or type(dy) is not int or dx not in (-1, 0, 1) or dy not in (-1, 0, 1)
                or type(seq) is not int or not 0 <= seq <= 2 ** 53 or type(correr) is not bool):
            raise ValueError("Controles de movimiento inválidos.")
        if seq <= self.jugadores[identificador]["seq"]:
            return
        self.actualizar(ahora)
        self.controles[identificador] = (dx, dy, ahora, correr)
        self.jugadores[identificador]["seq"] = seq

    def actualizar(self, ahora):
        desde = self.ultima
        self.ultima = max(desde, ahora)
        for identificador, jugador in self.jugadores.items():
            dx, dy, recibido, correr = self.controles.get(identificador, (0, 0, 0, False))
            # Un cliente detenido o desconectado deja de mover al personaje.
            segundos = max(0, min(ahora, recibido + .35) - desde)
            x, y = jugador["x"], jugador["y"]
            factor = MULTIPLICADOR_CORRER if correr else 1.0
            if self.mision.futuro is not None:
                factor *= self.mision.futuro.factor_impulso(identificador)
            if (self.mision.futuro is not None and self.mision.futuro.final.fase == "activo"
                    and identificador in self.mision.futuro.final.batalla.derribados):
                segundos = 0
            nx, ny = self.colisiones_de_jugador(jugador).mover(x, y, dx, dy, segundos, factor)
            jugador["x"], jugador["y"] = nx, ny
            if ahora > desde:  # sin tiempo transcurrido nadie se mueve: se conserva su estado
                jugador["animacion"] = "caminar" if math.hypot(nx - x, ny - y) > .01 else "reposo"
                jugador["corriendo"] = correr and jugador["animacion"] == "caminar"
            if dx or dy:
                jugador["orientacion"] = orientacion_de(dx, dy)
            if dx:
                jugador["direccion"] = "derecha" if dx > 0 else "izquierda"
            elif dy:
                jugador["direccion"] = "abajo" if dy > 0 else "arriba"
        self._revisar_viaje()
        # Cada misión solo cuenta a quienes están en su dimensión.
        copa = self.presentes_en(LA_COPA)
        # En el Presente los bots solo acompañan: votan y deciden los humanos.
        # Decide quien juega; un equipo sin personas decide por sí mismo.
        sin_personas = not any(self._humano(i) for i in self.conectados)
        self.mision.presentes_presente = {i for i in self.presentes_en(PRESENTE) if sin_personas or self._humano(i)}
        self.mision.presentes_futuro = {i for i in self.presentes_en(FUTURO) if sin_personas or self._humano(i)}
        self.mision.participantes_final = self.presentes_en(FUTURO)
        if self.mision.futuro is not None:
            self.mision.futuro.final.aventura.faltan = (["La Copa"] if self.mision.fase != "final" else []) + (["Distrito Conecta"] if not self.mision.presente or not self.mision.presente.fin else [])
            self.mision.futuro.final.actualizar(ahora - desde, self.jugadores,
                                               self.mision.futuro.posiciones_pulsos(), self.mision._cerca_presente,
                                               self.mision.participantes_final)
        self.mision.resolver(copa)
        self.mision.actualizar(ahora - desde, copa)
        self._sincronizar_bloqueos()

    def quitar(self, identificador):
        self.jugadores.pop(identificador, None)
        self.controles.pop(identificador, None)
        self.conectados.discard(identificador)

    def estado(self, identificador=None):
        caso = self.mision.publico(self.conectados)
        from .expediente import resumen_para_red
        caso["expediente"] = resumen_para_red(caso["expediente"])
        if identificador in self.jugadores:  # solo los NPC del mapa en el que está
            dimension = self.jugadores[identificador].get("dimension", LA_COPA)
            caso["npcs"] = [n for n in caso.get("npcs", []) if n["dimension"] == dimension]
        return {"mapa": "la_copa", "firma_mapa": self.colisiones.firma,
                "portales": {d: list(rect_portal(d, m.datos)) for d, m in self.mapas.items()},
                "destinos": {d: destinos(d) for d in self.mapas},
                "viaje": self.publico_viaje(),
                "jugadores": [dict(j, conectado=clave in self.conectados) for clave, j in self.jugadores.items()],
                "caso": caso,
                "privado": self.mision.privado(identificador) if identificador else {}}
