"""Carga y reproducción centralizada de la música y los efectos del juego."""

import os
import unicodedata

import pygame


class GestorAudio:
    """Administra los recursos de audio y sus canales durante una partida."""

    CANAL_DECISIONES = 0
    CANAL_CALDERO = 1
    CANAL_POCIONES = 2
    CANAL_EVENTOS = 3
    CANALES_MUSICA = (4, 5)
    TIEMPO_COOLDOWN_POCION_AGOTADA = 650

    def __init__(self, ruta_base):
        carpeta_audios = os.path.join(ruta_base, "Audios")
        self.rutas_musica = {
            "ambiente": os.path.join(carpeta_audios, "Ambiente.mp3"),
            "introduccion": os.path.join(carpeta_audios, "intro_juego_naturaleza_mas_movida.mp3"),
            "victoria": os.path.join(carpeta_audios, "victoria_la_copa_voces_en_las_alturas.mp3"),
            "game_over": os.path.join(carpeta_audios, "game_over_la_copa_voces_alturas.mp3"),
        }
        carpeta_pociones = os.path.join(carpeta_audios, "audios_pociones_la_copa")
        self.rutas_efectos = {
            "caldero_inestable": os.path.join(carpeta_audios, "09_caldero_inestable.mp3"),
            "pocion_agotada": os.path.join(carpeta_audios, "12_pocion_agotada.mp3"),
            "tablilla_colgar": os.path.join(carpeta_audios, "tablilla_colgar.wav"),
            "tablilla_consultar": os.path.join(carpeta_audios, "tablilla_consultar.wav"),
            "tablilla_quemar": os.path.join(carpeta_audios, "tablilla_quemar.wav"),
            "tablilla_ignorar": os.path.join(carpeta_audios, "tablilla_ignorar.wav"),
            "informacion_verificada": os.path.join(carpeta_pociones, "10_informacion_verificada.wav"),
            "informacion_falsa": os.path.join(carpeta_pociones, "11_advertencia_informacion_falsa.wav"),
            "pocion_colgar_activacion": os.path.join(carpeta_pociones, "01_activacion_pocion.wav"),
            "pocion_colgar_efecto": os.path.join(carpeta_pociones, "02_pocion_eco_publicar_tablilla.wav"),
            "pocion_consultar_activacion": os.path.join(carpeta_pociones, "03_activacion_pocion_claridad.wav"),
            "pocion_consultar_efecto": os.path.join(carpeta_pociones, "04_claridad_revelacion_pista.wav"),
            "pocion_quemar_activacion": os.path.join(carpeta_pociones, "05_activacion_pocion_ceniza.wav"),
            "pocion_quemar_efecto": os.path.join(carpeta_pociones, "06_ceniza_quemar_tablilla.wav"),
            "pocion_ignorar_activacion": os.path.join(carpeta_pociones, "07_activacion_pocion_bruma.wav"),
            "pocion_ignorar_efecto": os.path.join(carpeta_pociones, "08_bruma_viento_alejandose.wav"),
        }
        self.efectos = {}
        self.musicas = {}
        self.volumen_musica = 0.45
        self.volumen_efectos = 0.70
        self.silenciado = False
        self._mixer_disponible = self._inicializar_mixer()
        self._canales_efectos = {}
        self._canales_musica = []
        self._canal_musica_actual = None
        self._musica_actual = None
        self._musica_por_canal = [None, None]
        self._introduccion_activa = False
        self._resultado_final = None
        self._estado_caldero = "estable"
        self._ultimo_pocion_agotada = -self.TIEMPO_COOLDOWN_POCION_AGOTADA

        if self._mixer_disponible:
            self._preparar_canales()
        self._cargar_recursos()

    @staticmethod
    def _inicializar_mixer():
        if pygame.mixer.get_init() is None:
            try:
                pygame.mixer.init()
            except pygame.error as error:
                print(f"[Audio] Advertencia: no se pudo inicializar pygame.mixer: {error}")
                return False
        return pygame.mixer.get_init() is not None

    def _preparar_canales(self):
        cantidad_canales = max(6, pygame.mixer.get_num_channels())
        pygame.mixer.set_num_channels(cantidad_canales)
        pygame.mixer.set_reserved(6)
        self._canales_efectos = {
            indice: pygame.mixer.Channel(indice)
            for indice in (
                self.CANAL_DECISIONES,
                self.CANAL_CALDERO,
                self.CANAL_POCIONES,
                self.CANAL_EVENTOS,
            )
        }
        self._canales_musica = [pygame.mixer.Channel(indice) for indice in self.CANALES_MUSICA]

    def _cargar_recursos(self):
        for identificador, ruta in self.rutas_musica.items():
            self.musicas[identificador] = self._cargar_sonido(ruta)
        for identificador, ruta in self.rutas_efectos.items():
            self.efectos[identificador] = self._cargar_sonido(ruta)

    def _cargar_sonido(self, ruta):
        if not os.path.isfile(ruta):
            print(f"[Audio] Advertencia: no se encontró {os.path.basename(ruta)}")
            return None
        if not self._mixer_disponible:
            return None
        try:
            return pygame.mixer.Sound(ruta)
        except (pygame.error, OSError) as error:
            print(f"[Audio] Advertencia: no se pudo cargar {ruta}: {error}")
            return None

    def establecer_volumen_musica(self, valor):
        self.volumen_musica = self._limitar_volumen(valor)
        self._actualizar_volumen_musicas()

    def establecer_volumen_efectos(self, valor):
        self.volumen_efectos = self._limitar_volumen(valor)
        self._actualizar_volumen_efectos()

    @staticmethod
    def _limitar_volumen(valor):
        return max(0.0, min(1.0, float(valor)))

    def alternar_silencio(self):
        self.silenciado = not self.silenciado
        self._actualizar_volumen_musicas()
        self._actualizar_volumen_efectos()
        return self.silenciado

    def pausar_todo(self):
        for canal in self._todos_los_canales():
            canal.pause()

    def reanudar_todo(self):
        for canal in self._todos_los_canales():
            canal.unpause()

    def detener_todo(self):
        for canal in self._todos_los_canales():
            canal.stop()
        self._canal_musica_actual = None
        self._musica_actual = None
        self._introduccion_activa = False

    def _todos_los_canales(self):
        return list(self._canales_efectos.values()) + self._canales_musica

    def reproducir_musica(self, identificador, en_bucle=None, fade_ms=800):
        sonido = self.musicas.get(identificador)
        if sonido is None:
            return False
        if identificador == self._musica_actual:
            canal_actual = self._canal_musica_actual
            if canal_actual is not None and canal_actual.get_busy():
                return True

        if not self._canales_musica:
            return False
        if en_bucle is None:
            en_bucle = identificador == "ambiente"

        canal_anterior = self._canal_musica_actual
        indice_nuevo = 0 if canal_anterior is None else 1 - self._canales_musica.index(canal_anterior)
        canal_nuevo = self._canales_musica[indice_nuevo]
        canal_nuevo.stop()
        canal_nuevo.set_volume(self._volumen_efectivo_musica(identificador))
        canal_nuevo.play(
            sonido,
            loops=-1 if en_bucle else 0,
            fade_ms=max(0, int(fade_ms)),
        )
        self._musica_por_canal[indice_nuevo] = identificador
        if canal_anterior is not None and canal_anterior != canal_nuevo:
            canal_anterior.fadeout(max(0, int(fade_ms)))

        self._canal_musica_actual = canal_nuevo
        self._musica_actual = identificador
        return True

    def detener_musica(self, fade_ms=600):
        for canal in self._canales_musica:
            if fade_ms > 0:
                canal.fadeout(int(fade_ms))
            else:
                canal.stop()
        self._canal_musica_actual = None
        self._musica_actual = None
        self._introduccion_activa = False

    def al_cambiar_escena(self, escena_anterior, escena_nueva, resultado=None):
        grupo_pausa = {"pausa", "ayuda"}
        if escena_anterior not in grupo_pausa and escena_nueva in grupo_pausa:
            self.pausar_todo()
        elif escena_anterior in grupo_pausa and escena_nueva not in grupo_pausa:
            self.reanudar_todo()

        if escena_anterior is None and escena_nueva == "mapa":
            self._introduccion_activa = True
            self._resultado_final = None
            self.reproducir_musica("introduccion", en_bucle=False)
        elif escena_nueva == "final":
            if resultado not in ("victoria", "game_over"):
                print(f"[Audio] Advertencia: resultado final no reconocido: {resultado!r}")
                return
            if resultado != self._resultado_final:
                self._resultado_final = resultado
                self._introduccion_activa = False
                self.actualizar_estado_caldero("estable")
                self.reproducir_musica(resultado, en_bucle=False)
        elif escena_anterior == "mapa" and escena_nueva == "tablilla" and self._introduccion_activa:
            self._introduccion_activa = False
            self.reproducir_musica("ambiente", en_bucle=True)
        elif escena_anterior == "final" and escena_nueva == "mapa":
            self._resultado_final = None
            self.actualizar_estado_caldero("estable")
            self.reproducir_musica("ambiente", en_bucle=True)

    def reproducir_efecto(self, identificador, canal=CANAL_EVENTOS):
        sonido = self.efectos.get(identificador)
        canal_audio = self._canales_efectos.get(canal)
        if sonido is None or canal_audio is None or self.silenciado:
            return False
        canal_audio.set_volume(self.volumen_efectos)
        canal_audio.play(sonido)
        return True

    def reproducir_secuencia_efectos(self, identificadores, canal):
        sonidos = [
            self.efectos[identificador]
            for identificador in identificadores
            if self.efectos.get(identificador) is not None
        ]
        canal_audio = self._canales_efectos.get(canal)
        if not sonidos or canal_audio is None or self.silenciado:
            return False
        canal_audio.set_volume(self.volumen_efectos)
        canal_audio.play(sonidos[0])
        for sonido in sonidos[1:]:
            canal_audio.queue(sonido)
        return True

    def actualizar_estado_caldero(self, estado):
        if estado not in ("estable", "peligroso", "critico"):
            print(f"[Audio] Advertencia: estado del caldero no reconocido: {estado!r}")
            return False
        if estado == self._estado_caldero:
            return False
        self._estado_caldero = estado
        canal = self._canales_efectos.get(self.CANAL_CALDERO)
        if canal is None:
            return True
        if estado == "estable":
            canal.fadeout(450)
        else:
            self.reproducir_efecto("caldero_inestable", self.CANAL_CALDERO)
        return True

    def procesar_evento(self, evento):
        if not isinstance(evento, dict):
            raise TypeError("El evento de audio debe ser un diccionario.")
        tipo = evento.get("tipo")
        if tipo == "decision_tablilla":
            accion = self._normalizar_accion(evento.get("accion"))
            if accion is None:
                print(f"[Audio] Advertencia: acción de tablilla no reconocida: {evento.get('accion')!r}")
                return False
            decision_reproducida = self.reproducir_efecto(
                f"tablilla_{accion}", self.CANAL_DECISIONES
            )
            pocion_reproducida = self.reproducir_secuencia_efectos(
                [f"pocion_{accion}_activacion", f"pocion_{accion}_efecto"],
                self.CANAL_POCIONES,
            )
            return decision_reproducida or pocion_reproducida
        if tipo == "caldero":
            return self.actualizar_estado_caldero(evento.get("estado"))
        if tipo == "pocion_agotada":
            ahora = pygame.time.get_ticks()
            if ahora - self._ultimo_pocion_agotada < self.TIEMPO_COOLDOWN_POCION_AGOTADA:
                return False
            self._ultimo_pocion_agotada = ahora
            return self.reproducir_efecto("pocion_agotada", self.CANAL_POCIONES)
        if tipo == "clasificacion":
            correcta = evento.get("correcta")
            if not isinstance(correcta, bool):
                print(f"[Audio] Advertencia: resultado de clasificación inválido: {correcta!r}")
                return False
            identificador = "informacion_verificada" if correcta else "informacion_falsa"
            return self.reproducir_efecto(identificador, self.CANAL_EVENTOS)
        if tipo == "final_partida":
            resultado = evento.get("resultado")
            if resultado not in ("victoria", "game_over"):
                print(f"[Audio] Advertencia: resultado final no reconocido: {resultado!r}")
                return False
            if resultado == self._resultado_final and self._musica_actual == resultado:
                return True
            self._resultado_final = resultado
            self.actualizar_estado_caldero("estable")
            return self.reproducir_musica(resultado, en_bucle=False)
        print(f"[Audio] Advertencia: evento de audio no reconocido: {tipo!r}")
        return False

    @staticmethod
    def _normalizar_accion(accion):
        if not isinstance(accion, str):
            return None
        texto = unicodedata.normalize("NFD", accion.lower())
        texto = "".join(caracter for caracter in texto if unicodedata.category(caracter) != "Mn")
        for nombre in ("colgar", "consultar", "quemar", "ignorar"):
            if nombre in texto:
                return nombre
        return None

    def _volumen_efectivo_musica(self, identificador):
        if self.silenciado:
            return 0.0
        multiplicador = 0.72 if identificador == "ambiente" else 1.0
        return self.volumen_musica * multiplicador

    def _actualizar_volumen_musicas(self):
        for indice, canal in enumerate(self._canales_musica):
            identificador = self._musica_por_canal[indice] or "ambiente"
            volumen = self._volumen_efectivo_musica(identificador)
            canal.set_volume(volumen)

    def _actualizar_volumen_efectos(self):
        volumen = 0.0 if self.silenciado else self.volumen_efectos
        for canal in self._canales_efectos.values():
            canal.set_volume(volumen)
