"""Paneles de investigación y cooperación sobre el mapa compartido."""
import math
import re
import time

import pygame
from interfaz import analisis_manipulado, celular, dialogo_npc, terminal_nucleo
from interfaz.arte import dibujar_icono, expresion
from interfaz.boton import Boton
from interfaz.suministros import dibujar_carga
from multijugador.mision import TODOS
from multijugador.reparacion import CONFIGURACION as CONFIG_REPARACION

ORO = (237, 185, 87)
CREMA = (255, 243, 210)
VERDE = (130, 222, 158)


class PanelCooperativo:
    def __init__(self, vista):
        from nucleo.recursos import cargar_fuente
        self.vista = vista
        self.modo = "introduccion"
        self.titulo = ""
        self.texto = ""
        self.indice_pista = self.indice_destino = 0
        self.destino_fijo = None
        self._velo = None
        self.dialogo = None  # conversación abierta con un NPC
        self.caso_presente = None  # índice del caso de Distrito Conecta a la vista
        self.terminal = None  # terminal abierta en Ciudad Núcleo
        self.botones = {}
        self.fuente = cargar_fuente(18)
        self.pequena = cargar_fuente(14)
        self.encabezado = cargar_fuente(24)
        self.toast = ""
        self.toast_hasta = 0
        self.aviso_id = 0
        self.resultado_visto = None
        self.ronda_vista = None
        self.estrellas_vistas = None
        self.tutorial_visto = None
        self.celebrar_hasta = 0
        # Efectos ya reproducidos (event_id del servidor): nunca se repiten.
        self.eventos_vistos = None
        self.resultado_presente_visto = None
        self.botones_clasificacion = {}
        self.tiempo_aguja_ms = 0.0
        self.estado_indicador = "normal"
        self.indicador_hasta = 0.0
        self.intento_ultimo = None
        self.clasificacion_sonada = set()
        self.nodos_expediente = {}
        self.caso_expediente = None
        self.prueba_expediente = 0

    @property
    def dimension(self):
        return self.vista.dimension

    def contexto(self):
        """Caso de la dimensión del jugador (La Copa o Distrito Conecta)."""
        if self.digital:
            return dict(self.caso.get(self.dimension) or {}, dimension=self.dimension)
        return dict(self.caso, dimension="la_copa")

    @property
    def digital(self):
        """Distrito Conecta y Ciudad Núcleo se juegan desde el celular."""
        return self.dimension != "la_copa"

    def privado_voto(self, contexto):
        if contexto.get("dimension") != "la_copa":
            return (self.privado.get(contexto.get("dimension")) or {}).get("voto")
        return self.privado.get("voto")

    def clasificacion_propia(self):
        if self.digital:
            return (self.privado.get(self.dimension) or {}).get("clasificacion")
        return self.privado.get("clasificacion")

    def _eventos_actuales(self):
        eventos = []
        resultado = self.caso.get("resultado")
        if resultado and resultado.get("evento_id"):
            eventos.append(("la_copa", resultado, self.caso.get("noticia", "")))
        for dimension in ("presente", "futuro"):
            mision = self.caso.get(dimension) or {}
            if mision.get("resultado") and mision["resultado"].get("evento_id"):
                eventos.append((dimension, mision["resultado"], mision.get("noticia", "")))
        return eventos

    @property
    def activo(self):
        return self.modo is not None

    @property
    def caso(self):
        return self.vista.estado.get("mundo", {}).get("caso", {})

    @property
    def privado(self):
        return self.vista.estado.get("mundo", {}).get("privado", {})

    def abrir(self, modo):
        self.modo = modo
        self.destino_fijo = None
        if modo == "eco":
            tronco = next((o for o in self.caso.get("objetivos", []) if o["tipo"] == "eco" and self.vista.cerca(o)), None)
            if tronco:
                self.vista.efectos_mapa.lanzar("eco", tronco["x"], tronco["y"] - 28)

    def actualizar(self):
        estrellas = self.caso.get("estrellas", 0)
        tutorial = self.privado.get("tutorial", {}).get("estado")
        if (self.estrellas_vistas is not None and estrellas > self.estrellas_vistas) or (self.tutorial_visto == "activo" and tutorial == "terminado"):
            self.celebrar_hasta = time.monotonic() + 2.5
        self.estrellas_vistas = estrellas
        self.tutorial_visto = tutorial
        ronda = self.caso.get("ronda", 0)
        if self.ronda_vista != ronda:
            self.ronda_vista = ronda
            self.resultado_visto = None
            self.indice_pista = 0
            self.abrir("introduccion")
        for aviso in self.privado.get("avisos", []):
            if aviso["id"] > self.aviso_id:
                self.aviso_id = aviso["id"]
                if aviso.get("tipo") != "resultado":
                    self.notificar(aviso["texto"])
        resultado = self.caso.get("resultado")
        if resultado and self.dimension == "la_copa":
            clave = (ronda, resultado["opcion"], self.caso.get("rectificacion"))
            if clave != self.resultado_visto:
                self.resultado_visto = clave
                self.abrir("resultado")
        distrito = self.caso.get("presente") or {}
        indice = (distrito.get("evento") or {}).get("indice")
        if indice != self.caso_presente:
            if self.caso_presente is not None and self.dimension == "presente":
                self.notificar("Nuevo caso: " + distrito.get("titulo", ""))
                self.abrir("introduccion")
            self.caso_presente = indice
        presente = (self.caso.get(self.dimension) or {}).get("resultado") if self.digital else None
        if presente and presente.get("evento_id") != self.resultado_presente_visto:
            self.resultado_presente_visto = presente.get("evento_id")
            self.abrir("resultado")
        # Poción, caldero y sonido: una vez por evento_id y solo en su dimensión.
        eventos = self._eventos_actuales()
        if self.eventos_vistos is None:
            self.eventos_vistos = {r["evento_id"] for _, r, _ in eventos}  # al unirse no se repite lo pasado
        for dimension, resultado, noticia in eventos:
            if resultado["evento_id"] in self.eventos_vistos:
                continue
            self.eventos_vistos.add(resultado["evento_id"])
            if dimension == self.dimension:
                self.vista.iniciar_pocion(resultado, noticia)
        propia = self.clasificacion_propia()
        if propia and (self.dimension, self.caso.get("ronda"), propia["opcion"]) not in self.clasificacion_sonada:
            self.clasificacion_sonada.add((self.dimension, self.caso.get("ronda"), propia["opcion"]))
            self.vista.sonido({"tipo": "clasificacion", "correcta": bool(propia["correcta"])})

    def notificar(self, texto):
        self.vista.narrador.decir(texto)
        self.toast, self.toast_hasta = texto, time.monotonic() + 6

    def recibir(self, acuse):
        if acuse.get("ok") and acuse.get("vista") == "dialogo_npc":
            dialogo_npc.abrir(self, acuse["dialogo"])
            return
        if acuse.get("silencioso"):
            return
        self.notificar(acuse.get("mensaje", "Acción confirmada."))
        if acuse.get("ok") and acuse.get("resultado") in ("acierto", "error"):
            self.estado_indicador = acuse["resultado"]
            self.indicador_hasta = time.monotonic() + CONFIG_REPARACION["duracion_resultado_ms"] / 1000
            return
        if acuse.get("ok") and acuse.get("dimension"):
            self.modo = None
            return
        if acuse.get("ok") and acuse.get("vista") == "reparar":
            if self.modo != "reparar":
                self.tiempo_aguja_ms = 0.0
                self.estado_indicador = "normal"
            self.modo = "reparar"
            self._abierto = time.monotonic()
            return
        if acuse.get("ok") and acuse.get("vista") == "cerrar":
            self.modo = None
            return
        if acuse.get("ok") and acuse.get("vista"):
            self.terminal = acuse.get("terminal", self.terminal)
            self.abrir("inventario" if acuse["vista"] == "compartir" else acuse["vista"])
            self.titulo = acuse.get("titulo", "Testimonio")
            self.texto = acuse.get("mensaje", "")
            self.destino_fijo = acuse.get("destinatario")
            self.indice_destino = 0

    def cerca_eco(self):
        if self.digital:
            return False  # los troncos son de La Copa
        return any(o["tipo"] == "eco" and self.vista.cerca(o) for o in self.caso.get("objetivos", []))

    def texto_lineas(self, superficie, texto, x, y, ancho=535, fuente=None, color=CREMA):
        from nucleo.recursos import envolver_texto
        fuente = fuente or self.fuente
        for linea in envolver_texto(texto, fuente, ancho):
            superficie.blit(fuente.render(linea, True, color), (x, y))
            y += fuente.get_linesize() + 4
        return y

    def boton(self, superficie, clave, texto, x, y, ancho=280, activo=True):
        b = Boton(texto, centro=(x, y), fuente=self.fuente, tamano=(ancho, 42), desactivado=not activo)
        b.dibujar(superficie, self.vista.mouse)
        self.botones[clave] = b

    def boton_flecha(self, superficie, clave, imagen, texto, x, y):
        """Flecha con su arte (o el texto si falta la imagen)."""
        b = Boton(texto, imagen, centro=(x, y), fuente=self.fuente, tamano=(70, 42))
        b.dibujar(superficie, self.vista.mouse)
        self.botones[clave] = b

    def imagen_retrato(self, nombre):
        """Retrato real de quien habla; si no tiene, su sprite o el del jugador."""
        arte = self.vista.arte
        clave = nombre.lower().split(" · ")[0].split(":")[0]
        # \b: "mirador" no es Mira.
        for patron, frames in (("luma", arte.retratos["luma"]), ("mira", arte.retratos["mira"])):
            if re.search(rf"\b{patron}\b", clave) and frames:
                return expresion(frames, pygame.time.get_ticks())
        if "darío" in clave and arte.retrato_agente is not None:
            return arte.retrato_agente
        if self.digital:
            return self._retrato_distrito(clave)
        if "naira" in clave:
            sprite = next((o.get("imagen") for o in self.vista.decoraciones if "naira" in o.get("nombre", "").lower()), None)
            if sprite is not None:
                return sprite
        yo = next((j for j in self.vista.estado.get("mundo", {}).get("jugadores", []) if j["id"] == self.vista.identificador), {})
        femenina = yo.get("apariencia") == "mujer" or (yo.get("rol") == "aspirante" and yo.get("apariencia") is None)
        variante = {"habitante": "luma", "aspirante": "mira"}.get(yo.get("rol")) if femenina else None
        frames = arte.retratos.get(variante or yo.get("rol"))
        if frames:
            return expresion(frames, pygame.time.get_ticks())
        return self.vista.personajes.get(yo.get("rol"), {}).get(("reposo", "abajo"), [None])[0]

    def _retrato_distrito(self, clave):
        """En Distrito Conecta solo se ven sus propios personajes."""
        from mundo.personajes import PERSONAJES_DISTRITO, PERSONAJES_FUTURO
        escena = self.vista.escenas_zoom.get(self.dimension) or {}
        tabla = PERSONAJES_FUTURO if self.dimension == "futuro" else PERSONAJES_DISTRITO
        rol = next((r for r, datos in tabla.items() if datos[0].lower() in clave), None)
        if rol is None:
            rol = next((j["rol"] for j in self.vista.estado.get("mundo", {}).get("jugadores", [])
                        if j["id"] == self.vista.identificador), None)
        return (escena.get("personajes", {}).get(rol, {}).get(("reposo", "abajo")) or [None])[0]

    def retrato(self, superficie, nombre, x=170, y=175):
        imagen = self.imagen_retrato(nombre)
        marco = self.vista.arte.marco
        if marco is not None:
            superficie.blit(marco, marco.get_rect(center=(x + 48, y + 52)))
        else:
            pygame.draw.rect(superficie, (29, 58, 42), (x, y, 96, 104), border_radius=10)
            pygame.draw.rect(superficie, ORO, (x, y, 96, 104), 2, border_radius=10)
        if imagen is not None:
            escala = min(78 / imagen.get_width(), 88 / imagen.get_height())
            img = pygame.transform.scale(imagen, (max(1, round(imagen.get_width()*escala)), max(1, round(imagen.get_height()*escala))))
            superficie.blit(img, img.get_rect(center=(x+48, y+52)))

    def falta_para_elegir(self):
        if self.caso.get("votantes", 0) < 2:
            return "Espera a que entre otro compañero."
        if len(self.privado.get("inventario", [])) < 2:
            return "Te falta una pista. Pídesela a un compañero."
        if self.caso.get("investigadores", 0) < 2:
            return "Otro compañero debe hablar con su personaje."
        if not self.caso.get("entregas"):
            return "Compartan al menos una pista con I."
        if not self.en_caldero():
            return "Acércate al caldero brillante para elegir."
        return ""

    def actualizar_tiempo(self, segundos):
        if self.modo == "reparar":
            self.tiempo_aguja_ms += segundos * 1000
            if self.indicador_hasta and time.monotonic() > self.indicador_hasta:
                self.estado_indicador, self.indicador_hasta = "normal", 0
            puente = self.caso.get("puente") or {}
            if puente.get("estado") != "REPAIR_MINIGAME" or puente.get("reparador") != self.vista.identificador:
                if puente.get("estado") in ("REPAIR_ANIMATION", "REPAIRED") or time.monotonic() - (getattr(self, "_abierto", 0) or time.monotonic()) > 1.5:
                    self.modo = None

    def _dibujar_pantalla_completa(self, superficie):
        """Escenas del modo de un jugador; devuelve True si dibujó una."""
        from interfaz import escenas_multijugador as escenas
        from un_jugador.tablilla import (
            construir_botones_clasificacion,
            dibujar_pregunta_clasificacion,
            dibujar_resultado_evento,
        )
        contexto = self.contexto()
        if self.modo == "caldero":
            opciones = contexto.get("opciones", {})
            falta = self.falta_para_elegir()
            mensaje = falta or ("Eligieron distinto. Hablen y prueben otra vez." if self.caso.get("empate") else "Lee tus pistas. ¿Qué poción usamos?")
            votos = f"Tus pistas: {self.cantidad_pruebas()} · Ya eligieron {contexto.get('votos_emitidos', 0)} de {contexto.get('votantes', 0)}"
            voto = self.privado_voto(contexto)
            if voto:
                votos += " · Tu poción: " + escenas.nombre_pocion(contexto.get("tipos_pocion", {}).get(voto, ""))
            escenas.dibujar_decision(self, superficie, contexto, opciones, contexto.get("tipos_pocion", {}), falta, mensaje, votos)
            if self.cantidad_pruebas() < 2:
                self.boton(superficie, "pedir_pista", "Pedir pista", 880, 700, 150)
            self.boton(superficie, "cerrar", "Volver", 82, 700, 150)
            return True
        if self.modo == "resultado":
            resultado = contexto.get("resultado") or {}
            rect = escenas.dibujar_consecuencia(self, superficie, resultado, contexto["dimension"])
            propia = self.clasificacion_propia()
            if not propia:
                self.texto_lineas(superficie, "Antes de seguir: ¿qué tipo de información era?", rect.x + 40, rect.bottom - 70, rect.width - 80, self.pequena, ORO)
                dibujar_icono(superficie, self.vista.arte.arbol, (rect.right - 50, rect.bottom - 60))
                self.boton(superficie, "clasificar_abrir", "Clasificar el evento", 480, 595, 420)
            else:
                if not resultado.get("correcto") and not self.caso.get("rectificacion"):
                    self.boton(superficie, "rectificar", "Leer las pistas e intentar otra vez", 480, 595, 570, self.en_caldero())
                self.boton(superficie, "introduccion", "Ver nuestras estrellas" if self.caso.get("fase") == "final" else "Vamos a ayudar a la aldea", 480, 650, 540)
            self.boton(superficie, "cerrar", "Volver al mapa", 480, 700, 310)
            return True
        if self.modo == "clasificar":
            opciones = tuple(contexto.get("clasificacion_opciones") or ())
            r = self.vista.escenas.r
            if opciones not in self.botones_clasificacion:
                self.botones_clasificacion[opciones] = construir_botones_clasificacion(list(opciones), r, r["fuente_boton"])
            botones = self.botones_clasificacion[opciones]
            dibujar_pregunta_clasificacion(superficie, r, escenas.AdaptadorEstado(), botones, self.vista.mouse)
            for boton in botones:
                self.botones["clasificar:" + boton.texto] = boton
            return True
        if self.modo == "clasificacion_resultado":
            propia = self.clasificacion_propia()
            if not propia:
                return False
            resultado = contexto.get("resultado") or {}
            adaptador = escenas.AdaptadorEstado(resultado=dict(
                categoria=propia["categoria"], clasificacion_jugador=propia["opcion"],
                clasificacion_correcta=propia["correcta"], efecto_clasificacion=propia["efectos"],
                resultado=resultado.get("texto", "")))
            dibujar_resultado_evento(superficie, self.vista.escenas.r, adaptador)
            return True
        if self.modo == "reparar":
            escenas.dibujar_minijuego(self, superficie, self.caso.get("puente") or {}, self.tiempo_aguja_ms, self.estado_indicador)
            return True
        if self.modo == "portal":
            escenas.dibujar_portal(self, superficie, self.vista.destinos(), self.dimension)
            self.boton(superficie, "cerrar", "Quedarme aquí", 480, 520, 300)
            return True
        return False

    def inventario(self):
        if self.digital:
            return (self.privado.get(self.dimension) or {}).get("inventario", [])
        pistas = self.privado.get("inventario", [])
        avisos = [dict(id=p["id"], titulo="Aviso: " + p["titulo"], texto=p["temporal"]["texto"],
                       es_temporal=True, vigente=p["temporal"]["vigente"], segundos=p["temporal"]["segundos"])
                  for p in pistas if p.get("temporal")]
        return pistas + avisos

    def cantidad_pruebas(self):
        return sum(not p.get("es_temporal") for p in self.inventario())

    def dibujar(self, superficie):
        self.botones = {}
        if self.modo != "reparar":
            self._abierto = 0
        elif not getattr(self, "_abierto", 0):
            self._abierto = time.monotonic()
        if self.modo == "expediente":
            from interfaz.expediente import dibujar
            self.nodos_expediente = {}
            dibujar(self, superficie)
            return
        if self.modo == "dialogo_npc" and self.dialogo:
            dialogo_npc.dibujar(self, superficie)
            return
        if self.activo and self.digital and self.modo != "portal":
            celular.dibujar(self, superficie)
            if time.monotonic() < self.toast_hasta:
                pygame.draw.rect(superficie, (19, 39, 49), (20, 10, 920, 40), border_radius=7)
                self.texto_lineas(superficie, self.toast, 32, 20, 895, self.pequena, (153, 222, 214))
            return
        if self.activo and self.modo == "fuente" and self.vista.arte.marco_dialogo is not None:
            self._dibujar_dialogo(superficie)
            if time.monotonic() < self.toast_hasta:
                pygame.draw.rect(superficie, (10, 30, 23), (20, 10, 920, 40), border_radius=7)
                self.texto_lineas(superficie, self.toast, 32, 20, 895, self.pequena, VERDE)
            return
        if self.activo and self._dibujar_pantalla_completa(superficie):
            if time.monotonic() < self.toast_hasta and self.modo not in ("clasificar", "clasificacion_resultado"):
                pygame.draw.rect(superficie, (10, 30, 23), (20, 108, 920, 40), border_radius=7)
                self.texto_lineas(superficie, self.toast, 32, 116, 895, self.pequena, VERDE)
            return
        if not self.activo:
            if time.monotonic() < self.toast_hasta:
                # Bajo los paneles superiores: no tapa el portal ni los spawns.
                fondo = pygame.Surface((700, 50), pygame.SRCALPHA)
                fondo.fill((10, 30, 23, 228))
                superficie.blit(fondo, (240, 150))
                pygame.draw.rect(superficie, (70, 120, 90), (240, 150, 700, 50), 1, border_radius=8)
                self.texto_lineas(superficie, self.toast, 254, 156, 672, self.pequena, VERDE)
            return
        if self._velo is None:
            self._velo = pygame.Surface((960, 720), pygame.SRCALPHA)
            self._velo.fill((2, 12, 8, 150))
        superficie.blit(self._velo, (0, 0))
        rect = pygame.Rect(130, 58, 700, 610)
        pygame.draw.rect(superficie, (17, 39, 29), rect, border_radius=16)
        pygame.draw.rect(superficie, ORO, rect, 3, border_radius=16)
        titulos = {"introduccion": "TU SIGUIENTE AVENTURA", "inventario": "MIS PISTAS", "caldero": "¿QUÉ LE CONTAMOS A LA ALDEA?", "fuente": self.titulo,
                   "eco": "EL TRONCO NOS CONECTA", "eco_mensajes": "UN MENSAJE PARA EL EQUIPO", "resultado": "¡LO HICIMOS EN EQUIPO!", "actividad": "¡MANOS A LA OBRA!"}
        t = self.encabezado.render(titulos.get(self.modo, "AYUDEMOS A LA ALDEA"), True, ORO)
        if t.get_width() > 650:
            t = self.fuente.render(titulos.get(self.modo, "AYUDEMOS A LA ALDEA"), True, ORO)
        superficie.blit(t, t.get_rect(midtop=(480, 85)))
        self.texto_lineas(superficie, self.caso.get("titulo", ""), 165, 127, 630, self.pequena, VERDE)
        inventario = self.inventario()
        guia = self.privado.get("guia", {})
        tutorial = self.privado.get("tutorial", {})
        if self.modo == "introduccion":
            if tutorial.get("estado") == "pendiente" and self.caso.get("ronda", 0) == 0:
                self.retrato(superficie, "guía")
                self.texto_lineas(superficie, "¡Hola, detectives! La aldea necesita su ayuda.", 290, 180, 495)
                self.texto_lineas(superficie, "Aprendamos a caminar, hablar y llevar un farol. Será una misión corta, sin reloj.", 290, 265, 495)
                self.boton(superficie, "iniciar_tutorial", "Aprender jugando", 480, 420, 430)
                dibujar_carga(superficie, "farol", (735, 420), 34)
                self.boton(superficie, "saltar_tutorial", "Ya sé jugar", 480, 480, 330)
            elif self.caso.get("fase") == "preparacion":
                self.dibujar_encargo(superficie)
            elif self.caso.get("fase") == "final":
                self.texto_lineas(superficie, "¡Gracias por ayudar a la aldea!", 165, 180, 630, color=ORO)
                self.texto_lineas(superficie, f"Estrellas del equipo: {self.caso.get('estrellas', 0)} de {self.caso.get('estrellas_total', 11)}", 165, 237, 630)
                dibujar_icono(superficie, self.vista.arte.sello, (760, 215))
                insignia = self.vista.arte.insignia
                dibujar_icono(superficie, insignia, (670, 215))
                if insignia is not None:
                    # Centro del disco (es redondo: tan alto como ancho); las cintas cuelgan debajo.
                    limites = insignia.get_bounding_rect()
                    disco_x = 670 - insignia.get_width() // 2 + limites.centerx
                    disco_y = 215 - insignia.get_height() // 2 + limites.y + limites.width // 2
                    cantidad = str(self.caso.get("estrellas", 0))
                    fuente = next((f for f in (self.encabezado, self.fuente) if f.size(cantidad)[0] <= 28), self.pequena)
                    cifra = fuente.render(cantidad, True, (61, 37, 25))
                    # Se centra la tinta, no la caja de la línea, que deja aire arriba.
                    tinta = cifra.get_bounding_rect()
                    superficie.blit(cifra, (disco_x - tinta.centerx, disco_y - tinta.centery))
                for i, caso in enumerate(self.caso.get("balance", [])):
                    self.texto_lineas(superficie, ("Descubierto: " if caso["correcto"] else "Aprendimos de: ") + caso["caso"], 165, 310 + i*46, 630, self.fuente)
            else:
                self.texto_lineas(superficie, guia.get("titulo", "Busca tu pista"), 165, 180, 630, color=ORO)
                self.texto_lineas(superficie, guia.get("detalle", "Sigue las luces del camino."), 165, 232, 630)
                self.texto_lineas(superficie, self.caso.get("noticia", ""), 165, 327, 630)
                if guia.get("accion") == "pedir_pista":
                    self.boton(superficie, "pedir_pista", "Pedir una pista", 480, 455, 430)
                self.texto_lineas(superficie, "Flechas: caminar · E: hablar o ayudar", 165, 535, 630, self.pequena, VERDE)
                self.boton(superficie, "poder", "Mi poder especial · Q", 480, 578, 380)
        elif self.modo == "fuente":
            self.retrato(superficie, self.titulo)
            self.texto_lineas(superficie, self.texto, 290, 180, 495)
            self.texto_lineas(superficie, "Siguiente paso: " + guia.get("detalle", "Sigue la luz del mapa."), 165, 405, 630, self.fuente, VERDE)
            if guia.get("paso") == "tutorial":
                self.boton(superficie, "seguir", "Llevar el farol", 480, 535, 470)
                dibujar_carga(superficie, "farol", (750, 535), 34)
            else:
                self.boton(superficie, "inventario", "Ver y compartir mis pistas", 480, 535, 470)
        elif self.modo == "inventario":
            if not inventario:
                self.texto_lineas(superficie, "Aún no tienes pistas. Habla con el personaje que tiene una luz.", 165, 190, 630)
            else:
                self.indice_pista %= len(inventario)
                pista = inventario[self.indice_pista]
                self.texto_lineas(superficie, pista["titulo"], 165, 170, 630, color=ORO)
                self.texto_lineas(superficie, pista["texto"], 165, 215, 630)
                if pista.get("es_temporal") and pista.get("vigente"):
                    self.texto_lineas(superficie, f"Vigente por {pista['segundos']} s. Compartirlo conserva su fecha original.", 165, 300, 630, self.pequena, VERDE)
                dibujar_icono(superficie, self.vista.arte.iconos_pista.get(pista["id"]), (775, 186))
                arte = self.vista.arte
                self.boton_flecha(superficie, "pista_anterior", arte.flecha_izq, "<", 205, 353)
                self.boton_flecha(superficie, "pista_siguiente", arte.flecha_der, ">", 755, 353)
                self.texto_lineas(superficie, f"Pista {self.indice_pista+1} de {len(inventario)}", 390, 343, 250, self.pequena)
                destinatarios = self.destinos_pista()
                if destinatarios:
                    self.indice_destino %= len(destinatarios)
                    destino = destinatarios[self.indice_destino]
                    self.texto_lineas(superficie, "Para: " + destino["nombre"], 165, 400, 630)
                    self.boton_flecha(superficie, "destino_anterior", arte.flecha_izq, "<", 330, 450)
                    self.boton_flecha(superficie, "destino_siguiente", arte.flecha_der, ">", 630, 450)
                    persona = self.pequena.render("Cambiar persona", True, VERDE)
                    superficie.blit(persona, persona.get_rect(center=(480, 450)))
                    cerca = self.cerca_eco() or self.vista.cerca(destino, 64)
                    vigente = not pista.get("es_temporal") or pista.get("vigente")
                    self.boton(superficie, "entregar", ("Enviar mi pista" if self.cerca_eco() else "Dar mi pista") if vigente else "Aviso caducado: visita la fuente", 480, 506, 420, cerca and vigente)
                    if not cerca:
                        self.texto_lineas(superficie, "Acércate a esa persona o a un tronco para enviarla.", 165, 538, 630, self.pequena, ORO)
            if self.cantidad_pruebas() < 2:
                self.boton(superficie, "pedir_pista", "Me falta una pista: pedir ayuda", 480, 582, 530)
        elif self.modo == "caldero":
            self.texto_lineas(superficie, self.caso.get("noticia", ""), 165, 175, 630)
            falta = self.falta_para_elegir()
            mensaje = falta or ("Eligieron distinto. Hablen y prueben otra vez." if self.caso.get("empate") else "Lee tus pistas. ¿Qué crees que pasó?")
            self.texto_lineas(superficie, mensaje, 165, 265, 630, color=ORO)
            self.texto_lineas(superficie, f"Tus pistas: {self.cantidad_pruebas()} · Ya eligieron {self.caso.get('votos_emitidos', 0)} de {self.caso.get('votantes', 0)}", 165, 325, 630, self.pequena)
            if self.cantidad_pruebas() < 2:
                self.boton(superficie, "pedir_pista", "Pedir la pista que me falta", 480, 375, 500)
            elif self.privado.get("voto"):
                self.texto_lineas(superficie, "Tu elección: " + self.caso["opciones"][self.privado["voto"]], 165, 365, 630, self.pequena, VERDE)
            for i, (clave, texto) in enumerate(self.caso.get("opciones", {}).items()):
                self.boton(superficie, "votar:"+clave, texto, 480, 435+i*62, 580, not falta)
        elif self.modo == "eco":
            self.texto_lineas(superficie, "Este tronco puede llevar tus pistas y mensajes a todo el mapa.", 165, 180, 630)
            self.dibujar_selector_destino(superficie, 275)
            self.boton(superficie, "inventario", "Enviar una pista", 480, 355, 440)
            self.boton(superficie, "eco_mensajes", "Enviar un mensaje", 480, 420, 440)
        elif self.modo == "eco_mensajes":
            for i, mensaje in enumerate(self.caso.get("mensajes_eco", [])):
                self.boton(superficie, "eco:"+str(i), mensaje, 480, 225+i*75, 620)
            self.dibujar_selector_destino(superficie, 540)
        elif self.modo == "actividad":
            self.dibujar_actividad(superficie)
        elif self.modo == "poder":
            self.texto_lineas(superficie, self.privado.get("habilidad", "Mi poder"), 165, 185, 630, color=ORO)
            rol = next((j["rol"] for j in self.vista.estado.get("mundo", {}).get("jugadores", []) if j["id"] == self.vista.identificador), None)
            dibujar_icono(superficie, self.vista.arte.poder_grande.get(rol), (750, 205))
            self.texto_lineas(superficie, self.privado.get("descripcion_habilidad", ""), 165, 255, 630)
            self.texto_lineas(superficie, "Puedes usarlo una vez por misterio.", 165, 380, 630, color=VERDE)
            self.boton(superficie, "habilidad", "Usar mi poder", 480, 495, 430, not self.privado.get("habilidad_usada"))
        elif self.modo == "resultado":
            resultado = self.caso.get("resultado") or {}
            self.texto_lineas(superficie, resultado.get("texto", ""), 165, 175, 630)
            self.texto_lineas(superficie, f"Estrellas del equipo: {self.caso.get('estrellas', 0)}", 165, 355, 630, color=ORO)
            self.texto_lineas(superficie, "Ahora vamos a ayudar con nuestras manos.", 165, 410, 630, color=VERDE)
            if not resultado.get("correcto") and not self.caso.get("rectificacion"):
                self.boton(superficie, "rectificar", "Leer las pistas e intentar otra vez", 480, 495, 570, self.en_caldero())
                if not self.en_caldero():
                    self.texto_lineas(superficie, "Vuelve al caldero para intentarlo otra vez.", 165, 528, 630, self.pequena)
            self.boton(superficie, "introduccion", "Ver nuestras estrellas" if self.caso.get("fase") == "final" else "Vamos a ayudar a la aldea", 480, 579, 540)
        self.boton(superficie, "cerrar", "Volver al mapa", 480, 638, 310)
        if time.monotonic() < self.toast_hasta:
            pygame.draw.rect(superficie, (10, 30, 23), (20, 3, 920, 49), border_radius=7)
            self.texto_lineas(superficie, self.toast, 32, 8, 895, self.pequena, VERDE)

    def _dibujar_dialogo(self, superficie):
        """Conversación con un personaje en el marco de diálogo del juego."""
        if self._velo is None:
            self._velo = pygame.Surface((960, 720), pygame.SRCALPHA)
            self._velo.fill((2, 12, 8, 150))
        superficie.blit(self._velo, (0, 0))
        marco = self.vista.arte.marco_dialogo
        x, y = 50, 118
        superficie.blit(marco, (x, y))
        imagen = self.imagen_retrato(self.titulo)
        if imagen is not None:
            escala = min(136 / imagen.get_width(), 136 / imagen.get_height())
            img = pygame.transform.scale(imagen, (max(1, round(imagen.get_width() * escala)), max(1, round(imagen.get_height() * escala))))
            superficie.blit(img, img.get_rect(center=(x + 172, y + 174)))
        tinta = (61, 37, 25)
        fin = self.texto_lineas(superficie, self.titulo, x + 292, y + 158, 430, self.fuente, tinta)
        self.texto_lineas(superficie, self.texto, x + 292, fin + 2, 430, self.pequena, tinta)
        guia = self.privado.get("guia", {})
        tutorial = guia.get("paso") == "tutorial"
        opciones = [("seguir", "Llevar el farol") if tutorial else ("inventario", "Ver y compartir mis pistas"), ("cerrar", "Volver al mapa")]
        for (clave, texto), caja in zip(opciones, (pygame.Rect(x + 292, y + 292, 412, 42), pygame.Rect(x + 292, y + 347, 412, 42))):
            boton = Boton(texto, pygame.Surface(caja.size, pygame.SRCALPHA), caja.center)
            boton.actualizar(self.vista.mouse)
            self.botones[clave] = boton
            render = self.pequena.render(texto, True, (146, 66, 20) if boton.hover else tinta)
            superficie.blit(render, render.get_rect(center=caja.center))
        self.texto_lineas(superficie, "Siguiente paso: " + guia.get("detalle", "Sigue la luz del mapa."), x + 40, y + 500, 780, self.fuente, VERDE)

    def dibujar_selector_destino(self, superficie, y):
        destinos = self.destinos_eco()
        self.indice_destino %= len(destinos)
        texto = self.fuente.render("Para: " + destinos[self.indice_destino]["nombre"], True, ORO)
        superficie.blit(texto, texto.get_rect(center=(480, y)))
        self.boton_flecha(superficie, "destino_anterior", self.vista.arte.flecha_izq, "<", 220, y)
        self.boton_flecha(superficie, "destino_siguiente", self.vista.arte.flecha_der, ">", 740, y)
        ayuda = self.pequena.render("Flechas izquierda y derecha: cambiar destinatario", True, VERDE)
        superficie.blit(ayuda, ayuda.get_rect(center=(480, y + 30)))

    def dibujar_encargo(self, superficie):
        from interfaz.suministros import dibujar_carga
        e = self.caso.get("encargo") or {}
        self.texto_lineas(superficie, e.get("titulo", "Ayudemos juntos"), 165, 175, 630, color=ORO)
        self.texto_lineas(superficie, e.get("motivo", ""), 165, 219, 630)
        for i, m in enumerate(e.get("materiales", [])):
            dibujar_carga(superficie, m["id"], (190, 325+i*45))
            self.texto_lineas(superficie, m["nombre"] + (": ya llegó" if m["entregado"] else ": busca la luz del mapa"), 225, 314+i*45, 560, self.fuente, VERDE if m["entregado"] else CREMA)
        self.texto_lineas(superficie, "Llevas: " + (self.privado.get("carga") or "las manos libres"), 165, 417, 630, color=ORO)
        self.texto_lineas(superficie, "Destino: " + e.get("destino", {}).get("nombre", ""), 165, 458, 630)
        if e.get("materiales_listos") and not e.get("completo"):
            self.boton(superficie, "actividad", "Hacer la actividad juntos", 480, 535, 540)
        elif e.get("completo"):
            self.texto_lineas(superficie, "¡Terminado! Ganaron una estrella por ayudar.", 165, 502, 630, self.pequena, VERDE)
            self.boton(superficie, "continuar", "Estoy listo para otra aventura", 480, 575, 540, self.en_caldero() and not self.privado.get("preparado"))
        else:
            self.texto_lineas(superficie, "Sigue las luces. E recoge y entrega. Cada uno lleva un material.", 165, 535, 630, self.fuente, VERDE)

    def dibujar_actividad(self, superficie):
        e = self.caso.get("encargo") or {}
        a = e.get("actividad", {})
        self.texto_lineas(superficie, e.get("titulo", "Ayudemos a la aldea"), 165, 180, 630, color=ORO)
        jugadores = self.vista.estado.get("mundo", {}).get("jugadores", [])
        ayudante = next((j for j in jugadores if j["id"] == a.get("ayudante") and j.get("conectado", True) and self.vista.cerca(j, 136)), None)
        nombre = ayudante["nombre"] if ayudante else "Un compañero"
        self.texto_lineas(superficie, (nombre + " está ayudando. ¡El otro hace la tarea!" if ayudante else "Uno pulsa 'Yo ayudo'. El otro hace la tarea tres veces."), 165, 240, 630)
        for i in range(3):
            caja = pygame.Rect(285+i*140, 335, 110, 65)
            pygame.draw.rect(superficie, VERDE if i < a.get("progreso", 0) else (42, 69, 49), caja, border_radius=10)
            texto = self.encabezado.render(str(i+1), True, (15, 35, 25) if i<a.get("progreso",0) else CREMA)
            superficie.blit(texto, texto.get_rect(center=caja.center))
        cerca = bool(e.get("destino")) and self.vista.cerca(e["destino"])
        if e.get("completo"):
            self.texto_lineas(superficie, "¡Gran equipo! " + e.get("efecto", ""), 165, 445, 630, color=VERDE)
            self.boton(superficie, "introduccion", "Ver el siguiente paso", 480, 560, 480)
        else:
            self.boton(superficie, "sujetar", "Yo ayudo: me quedo aquí", 480, 463, 530, cerca and (not ayudante or ayudante["id"]==self.vista.identificador))
            self.boton(superficie, "trabajar", a.get("verbo", "Hacer la tarea"), 480, 525, 530, cerca and ayudante is not None and ayudante["id"] != self.vista.identificador)
            self.texto_lineas(superficie, "Quédate junto al cesto." if cerca else "Acércate al círculo verde del cesto.", 165, 570, 630, self.pequena, ORO)

    def en_caldero(self):
        return any(o["id"] == "caldero" and self.vista.cerca(o) for o in self.caso.get("objetivos", []))

    def destinatarios(self):
        jugadores = [j for j in self.vista.estado.get("mundo", {}).get("jugadores", [])
                     if j["id"] != self.vista.identificador and j.get("conectado", True)]
        pedidos = {p["id"] for p in self.privado.get("pedidos", [])}
        jugadores.sort(key=lambda j: j["id"] not in pedidos)
        if self.destino_fijo:
            jugadores.sort(key=lambda j: j["id"] != self.destino_fijo)
        return jugadores

    def destinos_eco(self):
        return [{"id": TODOS, "nombre": "Todos"}] + self.destinatarios()

    def destinos_pista(self):
        """Junto a un tronco una pista también puede ir a todo el equipo."""
        return self.destinos_eco() if self.cerca_eco() and not self.destino_fijo else self.destinatarios()

    def manejar(self, evento, posicion, cliente):
        if self.modo == "dialogo_npc" and self.dialogo:
            return dialogo_npc.manejar(self, evento, posicion, cliente)
        if self.modo == "reparar" and evento.type == pygame.KEYDOWN:
            if evento.key in (pygame.K_e, pygame.K_SPACE):
                cliente.actuar("intento_reparacion", tiempo_aguja_ms=round(self.tiempo_aguja_ms, 1))
            elif evento.key == pygame.K_ESCAPE:
                cliente.actuar("cerrar_reparacion")
                self.modo = None
            return True
        if self.modo == "clasificacion_resultado" and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            self.abrir("resultado")
            return True
        if evento.type == pygame.KEYDOWN:
            if self.modo == "analizar" and self.dimension == "presente" and analisis_manipulado.tecla(self, evento.key, cliente):
                return True
            if evento.key == pygame.K_t:
                self.modo = None if self.modo == "expediente" else "expediente"
                return True
            if evento.key == pygame.K_ESCAPE and self.activo:
                self.modo = None
                return True
            if evento.key in (pygame.K_LEFT, pygame.K_RIGHT) and self.modo == "inventario" and self.digital:
                self.indice_pista += 1 if evento.key == pygame.K_RIGHT else -1
                return True
            if evento.key == pygame.K_c and self.digital:
                self.modo = None if self.activo else "introduccion"
                return True
            if evento.key in (pygame.K_LEFT, pygame.K_RIGHT) and self.modo in ("eco", "eco_mensajes", "inventario"):
                self.indice_destino += 1 if evento.key == pygame.K_RIGHT else -1
                return True
            if evento.key == pygame.K_i:
                self.modo = None if self.modo == "inventario" else "inventario"
                return True
            if evento.key == pygame.K_m:
                self.abrir("introduccion")
                return True
            if evento.key == pygame.K_q and not self.activo and not self.digital:
                cliente.actuar("habilidad")
                return True
            if self.activo:
                return True
        if not self.activo or evento.type != pygame.MOUSEBUTTONDOWN or evento.button != 1:
            return False
        if self.modo == "expediente":
            for caso, rect in self.nodos_expediente.items():
                if rect.collidepoint(posicion):
                    self.caso_expediente = caso
                    self.prueba_expediente = 0
                    return True
        for clave, boton in self.botones.items():
            if not boton.fue_clickeado(posicion):
                continue
            if clave == "expediente_cerrar":
                self.modo = None
            elif clave == "expediente_prueba":
                self.prueba_expediente += 1
            elif clave.startswith("expediente:"):
                estado = self.caso.get("expediente") or {}
                pendiente = estado.get("pendiente")
                if pendiente:
                    cliente.actuar("expediente_paso", direccion=clave.split(":")[1],
                                   caso=pendiente["id"], revision=estado["revision"], paso=estado["paso"])
            elif clave in ("cerrar", "seguir"):
                if self.privado.get("tutorial", {}).get("estado") == "pendiente" and self.caso.get("ronda", 0) == 0:
                    cliente.actuar("iniciar_tutorial")
                self.modo = None
            elif clave in ("inventario", "eco_mensajes", "introduccion", "actividad", "poder"):
                self.abrir(clave)
            elif clave.startswith("recoger:"):
                material = next(m for m in self.caso["encargo"]["materiales"] if m["id"] == clave.split(":")[1])
                cliente.actuar("recoger_suministro", material=material["id"], objetivo=material["fuente"]["id"])
            elif clave in ("iniciar_tutorial", "saltar_tutorial"):
                cliente.actuar(clave)
                self.modo = None
            elif clave in ("habilidad", "pedir_pista", "sujetar", "trabajar", "recoger_suministro", "depositar", "continuar"):
                cliente.actuar(clave)
            elif clave.startswith("pista:"):
                self.indice_pista = int(clave.split(":")[1])
                self.modo = "inventario"
            elif clave == "pista_anterior":
                self.indice_pista -= 1
            elif clave == "pista_siguiente":
                self.indice_pista += 1
            elif clave == "destino_anterior":
                self.indice_destino -= 1
            elif clave == "destino_siguiente":
                self.indice_destino += 1
            elif clave == "entregar":
                pistas, destinos = self.privado.get("inventario", []), self.destinos_pista()
                if pistas and destinos:
                    cliente.actuar("entregar", pista=pistas[self.indice_pista % len(pistas)]["id"],
                                   destinatario=destinos[self.indice_destino % len(destinos)]["id"],
                                   medio="eco" if self.cerca_eco() else "directo")
            elif clave.startswith("eco:"):
                destinos = self.destinos_eco()
                cliente.actuar("eco", mensaje=int(clave.split(":")[1]),
                               destinatario=destinos[self.indice_destino % len(destinos)]["id"])
            elif clave.startswith("votar:"):
                cliente.actuar("votar", opcion=clave.split(":")[1])
            elif clave.startswith("presente_votar:"):
                cliente.actuar("presente_votar", opcion=clave.split(":")[1])
            elif clave == "clasificar_abrir":
                self.abrir("clasificar")
            elif clave.startswith("clasificar:"):
                cliente.actuar("presente_clasificar" if self.digital else "clasificar",
                               categoria=clave.split(":", 1)[1])
            elif clave == "caldero":
                self.abrir("caldero")
            elif clave == "analizar":
                cliente.actuar("presente_analizar")
            elif clave.startswith("terminal:"):
                terminal_nucleo.accion(self, clave, cliente)
            elif clave.startswith("analisis:"):
                analisis_manipulado.accion(self, clave, posicion, cliente)
            elif clave == "presente_siguiente":
                cliente.actuar("presente_siguiente")
            elif clave.startswith("viajar:"):
                self.vista.viajar(cliente, clave.split(":", 1)[1])
            elif clave == "cancelar_portal":
                cliente.actuar("cancelar_portal")
                self.modo = None
            elif clave == "rectificar":
                cliente.actuar("rectificar")
            break
        return True
