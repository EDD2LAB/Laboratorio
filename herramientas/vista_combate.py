"""Vista previa del combate final sin servidor ni campaña.

Abre el mapa del Futuro con cuatro personajes y simula, en local, los estados
que enviaría el servidor. Usa el mismo dibujo, efectos y sonidos que el juego
(``interfaz.batalla_cooperativa``, ``equipo_rebelion`` y ``efectos_combate``),
así que sirve para revisar arte y audio del final sin jugar todo. No cambia
reglas ni partidas: las duraciones de las pausas son cortas a propósito.

Uso: .venv\\Scripts\\python.exe -m herramientas.vista_combate
     (sin pantalla: --cuadros 240 --captura vista.png)
"""
import argparse
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame  # noqa: E402

from multijugador.aventura_final import ALCANCE_BLASTER, ESPERA_BLASTER  # noqa: E402
from multijugador.dimensiones_red import cargar_datos  # noqa: E402
from multijugador.movimiento import FACTOR_VELOCIDAD_PRESENTE, ColisionesMapa  # noqa: E402

ROLES = ("guardian", "habitante", "mensajero", "aspirante")
AVISO = {1: 3.0, 2: 2.5}
RAYO = .7
PAUSA = 6.0  # el juego usa 26 / 22 s; aquí se acorta para probar rápido
VISTA = (320, 240)  # mismo zoom ×3 que el Futuro
AYUDA = (
    "WASD/flechas mover · F disparar",
    "Espacio ciclo automático · 1 tanda de rayos ahora",
    "2 cambiar fase · M mini-núcleo · P pulso",
    "X caer/levantarse · L perder señal",
    "B pieza / fabricar · T probar sonido siguiente",
    "N música · +/- volumen efectos · F1 ayuda · Esc salir",
)


def punto_libre(colisiones, x, y):
    """Punto caminable más cercano en espiral (los sitios elegidos a ojo pueden caer en pared)."""
    for radio in range(0, 120, 4):
        for paso in range(max(1, radio)):
            angulo = paso / max(1, radio) * math.tau
            px, py = x + math.cos(angulo) * radio, y + math.sin(angulo) * radio
            if not colisiones.bloqueado(px, py):
                return px, py
    return x, y


class Simulador:
    """Estado con la misma forma que ``desafio_final`` del servidor."""

    def __init__(self, colisiones):
        self.colisiones = colisiones
        rx, ry, w, h = colisiones.datos["rect_mapa"]
        cx, cy = rx + w * .5, ry + h * .55
        desfases = ((-40, 10), (30, 25), (0, -30), (60, -5))
        self.jugadores = []
        for i, (rol, (dx, dy)) in enumerate(zip(ROLES, desfases)):
            x, y = punto_libre(colisiones, cx + dx, cy + dy)
            self.jugadores.append(dict(id=i, x=x, y=y, rol=rol, dimension="futuro", orientacion="abajo", andando=False))
        self.centro = (cx, cy)
        self.fase, self.fase_batalla, self.turno, self.segundos = "activo", 1, "recarga", PAUSA
        self.oleada, self.blancos, self.derribados = 1, [], set()
        self.integridad, self.fabricado = 3, True
        self.minis, self.numero_mini, self.trazo, self.trazo_hasta = [], 0, None, 0.0
        self.cargas, self.entregadas = {}, []
        self.automatico, self.reloj, self.enfriamiento = True, 0.0, 0.0

    @property
    def yo(self):
        return self.jugadores[0]

    # --- Acciones de las teclas -------------------------------------------------
    def tanda(self):
        self.turno, self.segundos, self.oleada = "aviso", AVISO[self.fase_batalla], 1
        self.blancos = [(j["x"], j["y"]) for j in self.jugadores if j["id"] not in self.derribados][:4]

    def cambiar_fase(self):
        self.fase_batalla = 2 if self.fase_batalla == 1 else 1

    def nuevo_mini(self):
        if len(self.minis) >= 2:
            return
        self.numero_mini += 1
        angulo = self.numero_mini * 2.1
        x, y = punto_libre(self.colisiones, self.yo["x"] + math.cos(angulo) * 110, self.yo["y"] + math.sin(angulo) * 80)
        self.minis.append(dict(id=self.numero_mini, x=x, y=y, vida=2, aviso=4.0))

    def pulso(self):
        for mini in self.minis:
            mini["aviso"] = 0.01

    def disparar(self, linea_libre):
        from interfaz.efectos_combate import elegir_objetivo
        mini, apuntable = elegir_objetivo(self.minis, (self.yo["x"], self.yo["y"]), linea_libre)
        if (not mini or not apuntable or self.reloj < self.enfriamiento
                or self.turno not in ("aviso", "rayo") or self.yo["id"] in self.derribados):
            return False
        self.trazo = [round(self.yo["x"]), round(self.yo["y"]), round(mini["x"]), round(mini["y"])]
        self.trazo_hasta, self.enfriamiento = self.reloj + .18, self.reloj + ESPERA_BLASTER
        mini["vida"] -= 1
        if mini["vida"] <= 0:
            self.minis.remove(mini)
        return True

    def caer_o_levantarse(self):
        self.derribados ^= {self.yo["id"]}

    def perder_senal(self):
        self.integridad -= 1
        if self.integridad <= 0:
            self.integridad = 3  # en el juego sería reintento; aquí se repone para seguir probando

    def preparacion(self):
        """Recoger una pieza, entregarla y, con tres, fabricar (vuelve al combate)."""
        if self.fase == "activo":
            self.fase, self.fabricado, self.cargas, self.entregadas = "preparacion", False, {}, []
        elif not self.cargas and len(self.entregadas) < 3:
            self.cargas = {self.yo["id"]: "pieza"}
        elif self.cargas:
            self.cargas, self.entregadas = {}, self.entregadas + ["pieza%d" % len(self.entregadas)]
        else:
            self.fase, self.fabricado = "activo", True

    # --- Tiempo -------------------------------------------------------------------
    def mover(self, dx, dy, dt):
        yo = self.yo
        yo["andando"] = bool(dx or dy) and yo["id"] not in self.derribados
        if not yo["andando"]:
            return
        yo["x"], yo["y"] = self.colisiones.mover(yo["x"], yo["y"], dx, dy, dt)
        if abs(dx) > abs(dy):
            yo["orientacion"] = "derecha" if dx > 0 else "izquierda"
        else:
            yo["orientacion"] = "abajo" if dy > 0 else "arriba"

    def paso(self, dt):
        self.reloj += dt
        if self.reloj >= self.trazo_hasta:
            self.trazo = None
        if self.fase != "activo":
            return
        self.segundos = max(0.0, self.segundos - dt)
        if self.segundos <= 0:
            if self.turno == "aviso":
                self.turno, self.segundos = "rayo", RAYO
                golpeados = {j["id"] for j in self.jugadores for bx, by in self.blancos
                             if math.hypot(j["x"] - bx, j["y"] - by) <= (22 if self.fase_batalla == 1 else 30)}
                if golpeados - self.derribados:
                    self.derribados |= golpeados
                    self.perder_senal()
            elif self.turno == "rayo":
                if self.fase_batalla == 2 and self.oleada == 1:
                    self.tanda()
                    self.oleada, self.segundos = 2, AVISO[2]
                else:
                    self.turno, self.segundos, self.blancos = "recarga", PAUSA, []
                    self.derribados.clear()  # en la pausa se recuperan los caídos
            elif self.automatico:
                self.tanda()
            else:
                self.segundos = PAUSA
        if self.turno in ("aviso", "rayo"):
            for mini in self.minis:
                mini["aviso"] -= dt
                if mini["aviso"] <= 0:
                    mini["aviso"] = 4.0
                    for j in self.jugadores:
                        if math.hypot(j["x"] - mini["x"], j["y"] - mini["y"]) <= 38:
                            self.derribados.add(j["id"])

    def estado(self):
        return dict(
            fase=self.fase, ronda=1, integridad=self.integridad, hechos=["guardian"],
            puntos=dict(aspirante=dict(x=self.centro[0] - 150, y=self.centro[1] - 80)),
            batalla=dict(fase=self.fase_batalla, turno=self.turno, segundos=round(self.segundos, 1),
                         oleada=self.oleada, blancos=list(self.blancos), derribados=sorted(self.derribados)),
            aventura=dict(fabricado=self.fabricado, disparo=self.trazo,
                          minis=[dict(m, aviso=round(m["aviso"], 1)) for m in self.minis],
                          minis_activos=self.turno in ("aviso", "rayo"), taller=dict(x=self.centro[0] - 200, y=self.centro[1]),
                          cargas=dict(self.cargas), entregadas=list(self.entregadas), materiales=[]))


class Vista:
    def __init__(self, sonido=True):
        from interfaz.efectos_combate import EfectosCombate
        from mundo.personajes import PERSONAJES_FUTURO, cargar_personajes_distrito
        from nucleo.recursos import cargar_fuente
        from nucleo.rutas import RAIZ
        datos = cargar_datos("futuro")
        self.colisiones = ColisionesMapa(datos)
        self.colisiones.factor_velocidad = FACTOR_VELOCIDAD_PRESENTE
        self.mapa = pygame.Rect(datos["rect_mapa"])
        imagen = pygame.image.load(str(RAIZ / "Imagenes" / "Fondos" / "Mapas" / "Futuro" / "MapaFuturo.png")).convert()
        self.fondo = pygame.transform.scale(imagen, self.mapa.size)
        self.personajes = cargar_personajes_distrito(30, PERSONAJES_FUTURO)
        self.fuente, self.fuente_chica = cargar_fuente(16), cargar_fuente(14)
        self.capa = pygame.Surface((960, 720)).convert()
        self.sim, self.efectos = Simulador(self.colisiones), EfectosCombate()
        self.ayuda, self.musica, self.aviso, self.aviso_hasta = True, False, "", 0
        self.sonido_prueba = 0
        self.audio = None
        if sonido:
            try:
                from audio.audio_manager import GestorAudio
                self.audio = GestorAudio(str(RAIZ), categorias=True)
            except Exception as error:  # sin mezclador, la vista sigue funcionando muda
                print("[Vista] Sin audio:", error)

    def avisar(self, texto, ahora_ms):
        self.aviso, self.aviso_hasta = texto, ahora_ms + 1600

    def tecla(self, tecla, ahora_ms):
        sim = self.sim
        acciones = {
            pygame.K_f: lambda: sim.disparar(self.colisiones.trayecto_libre) or self.avisar("No hay mini-núcleo al alcance", ahora_ms),
            pygame.K_1: sim.tanda, pygame.K_2: sim.cambiar_fase,
            pygame.K_m: sim.nuevo_mini, pygame.K_p: sim.pulso, pygame.K_x: sim.caer_o_levantarse,
            pygame.K_l: sim.perder_senal, pygame.K_b: sim.preparacion,
        }
        if tecla in acciones:
            acciones[tecla]()
        elif tecla == pygame.K_SPACE:
            sim.automatico = not sim.automatico
            self.avisar("Ciclo automático " + ("activado" if sim.automatico else "en pausa"), ahora_ms)
        elif tecla == pygame.K_t and self.audio:
            nombre = self.audio.SONIDOS_BATALLA[self.sonido_prueba % len(self.audio.SONIDOS_BATALLA)]
            self.sonido_prueba += 1
            self.audio.reproducir_batalla(nombre)
            self.avisar("Sonido: " + nombre, ahora_ms)
        elif tecla == pygame.K_n and self.audio:
            self.musica = not self.musica
            if self.musica:
                self.audio.reproducir_musica("batalla_fase%d" % sim.fase_batalla, en_bucle=True)
            else:
                self.audio.detener_musica()
        elif tecla in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS, pygame.K_MINUS, pygame.K_KP_MINUS) and self.audio:
            cambio = -.1 if tecla in (pygame.K_MINUS, pygame.K_KP_MINUS) else .1
            self.audio.establecer_volumen_efectos(self.audio.volumen_efectos + cambio)
            self.avisar("Volumen de efectos: %d %%" % round(self.audio.volumen_efectos * 100), ahora_ms)
        elif tecla == pygame.K_F1:
            self.ayuda = not self.ayuda

    def actualizar(self, dt, teclas, ahora_ms):
        dx = (teclas[pygame.K_d] or teclas[pygame.K_RIGHT]) - (teclas[pygame.K_a] or teclas[pygame.K_LEFT])
        dy = (teclas[pygame.K_s] or teclas[pygame.K_DOWN]) - (teclas[pygame.K_w] or teclas[pygame.K_UP])
        self.sim.mover(dx, dy, dt)
        self.sim.paso(dt)
        if self.musica and self.audio:
            self.audio.reproducir_musica("batalla_fase%d" % self.sim.fase_batalla, en_bucle=True)

    def _personaje(self, superficie, jugador, ahora_ms):
        clips = self.personajes.get(jugador["rol"], {})
        accion = "caminar" if jugador.get("andando") else "reposo"
        cuadros = clips.get((accion, jugador["orientacion"])) or clips.get(("reposo", "abajo"))
        if not cuadros:
            pygame.draw.rect(superficie, (240, 240, 240), (jugador["x"] - 4, jugador["y"] - 18, 8, 18))
            return
        cuadro = cuadros[(ahora_ms // 110) % len(cuadros)]
        if jugador["id"] in self.sim.derribados:
            cuadro = pygame.transform.rotate(cuadro, 90)
        superficie.blit(cuadro, cuadro.get_rect(midbottom=(round(jugador["x"]), round(jugador["y"]))))

    def dibujar(self, pantalla, ahora_ms):
        from interfaz import batalla_cooperativa, equipo_rebelion
        from interfaz.efectos_combate import elegir_objetivo
        sim, capa = self.sim, self.capa
        final = sim.estado()
        self.efectos.actualizar(final, ahora_ms, sim.yo["id"], (sim.yo["x"], sim.yo["y"]))
        if self.audio:
            for nombre, volumen in self.efectos.tomar_sonidos():
                self.audio.reproducir_batalla(nombre, volumen)
        capa.fill((0, 0, 0))
        capa.blit(self.fondo, self.mapa)
        objetivo = elegir_objetivo(sim.minis, (sim.yo["x"], sim.yo["y"]), self.colisiones.trayecto_libre)
        # Mismo orden que el juego: suelo y efectos primero, personajes encima.
        equipo_rebelion.dibujar(capa, final, sim.jugadores, self.efectos, ahora_ms, objetivo)
        batalla_cooperativa.dibujar_ataques(capa, final, sim.jugadores, self.efectos, ahora_ms)
        self.efectos.dibujar(capa)
        for jugador in sorted(sim.jugadores, key=lambda j: j["y"]):
            self._personaje(capa, jugador, ahora_ms)
        vista = pygame.Rect((0, 0), VISTA)
        vista.center = (round(sim.yo["x"]), round(sim.yo["y"]))
        vista.clamp_ip(self.mapa)
        dx, dy = self.efectos.desplazamiento(ahora_ms)
        vista = vista.move(dx, dy).clamp(capa.get_rect())
        pygame.transform.scale(capa.subsurface(vista), pantalla.get_size(), pantalla)
        if final["fase"] == "activo":
            batalla_cooperativa.dibujar_aviso(pantalla, final, self.fuente, sim.yo, self.efectos, ahora_ms)
        else:
            texto = "Preparación: piezas entregadas %d/3 · B para avanzar" % len(sim.entregadas)
            imagen = self.fuente.render(texto, True, (255, 240, 200))
            pygame.draw.rect(pantalla, (8, 22, 32), (20, 110, 920, 40), border_radius=4)
            pantalla.blit(imagen, imagen.get_rect(center=(480, 130)))
        cabecera = self.fuente.render("VISTA PREVIA DEL COMBATE · no es una partida real", True, (255, 214, 120))
        pantalla.blit(cabecera, cabecera.get_rect(midtop=(480, 12)))
        if self.ayuda:
            alto = 18 * len(AYUDA) + 12
            caja = pygame.Rect(16, 562 - alto, 420, alto)  # sobre la barra inferior, sin tapar el HUD
            fondo = pygame.Surface(caja.size, pygame.SRCALPHA)
            fondo.fill((8, 22, 32, 215))
            pantalla.blit(fondo, caja)
            for i, linea in enumerate(AYUDA):
                pantalla.blit(self.fuente_chica.render(linea, True, (226, 236, 240)), (caja.x + 8, caja.y + 6 + i * 18))
        if ahora_ms < self.aviso_hasta:
            imagen = self.fuente.render(self.aviso, True, (255, 240, 200))
            rect = imagen.get_rect(midbottom=(480, 560))
            pygame.draw.rect(pantalla, (8, 22, 32), rect.inflate(20, 10), border_radius=4)
            pantalla.blit(imagen, rect)


def main(argumentos=None):
    opciones = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    opciones.add_argument("--cuadros", type=int, default=0, help="termina tras N cuadros (pruebas)")
    opciones.add_argument("--captura", help="guarda el último cuadro en este PNG")
    opciones.add_argument("--sin-sonido", action="store_true")
    opciones = opciones.parse_args(argumentos)
    pygame.init()
    pantalla = pygame.display.set_mode((960, 720), pygame.SCALED)
    pygame.display.set_caption("Timeless Glitch · Vista previa del combate")
    vista = Vista(sonido=not opciones.sin_sonido)
    reloj, cuadro = pygame.time.Clock(), 0
    if opciones.cuadros:  # guion corto para pruebas sin pantalla
        vista.sim.nuevo_mini()
        vista.sim.tanda()
    while True:
        dt = reloj.tick(60) / 1000
        ahora_ms = pygame.time.get_ticks()
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT or (evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE):
                pygame.quit()
                return 0
            if evento.type == pygame.KEYDOWN:
                vista.tecla(evento.key, ahora_ms)
        if opciones.cuadros and cuadro == opciones.cuadros // 2:
            vista.sim.disparar(lambda a, b: True)
        vista.actualizar(dt, pygame.key.get_pressed(), ahora_ms)
        vista.dibujar(pantalla, ahora_ms)
        pygame.display.flip()
        cuadro += 1
        if opciones.cuadros and cuadro >= opciones.cuadros:
            if opciones.captura:
                pygame.image.save(pantalla, opciones.captura)
            pygame.quit()
            return 0


if __name__ == "__main__":
    os.environ.setdefault("SDL_HINT_RENDER_SCALE_QUALITY", "0")
    sys.exit(main())
