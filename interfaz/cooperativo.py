"""Paneles de investigación y cooperación sobre el mapa compartido."""
import math
import time

import pygame
from interfaz.boton import Boton

ORO = (237, 185, 87)
CREMA = (255, 243, 210)
VERDE = (130, 222, 158)


class PanelCooperativo:
    def __init__(self, vista):
        import juego
        self.vista = vista
        self.modo = "introduccion"
        self.titulo = ""
        self.texto = ""
        self.indice_pista = self.indice_destino = 0
        self.destino_fijo = None
        self.botones = {}
        self.fuente = juego.cargar_fuente(18)
        self.pequena = juego.cargar_fuente(14)
        self.encabezado = juego.cargar_fuente(24)
        self.toast = ""
        self.toast_hasta = 0
        self.aviso_id = 0
        self.resultado_visto = None
        self.ronda_vista = None
        self.estrellas_vistas = None
        self.tutorial_visto = None
        self.celebrar_hasta = 0

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
        if resultado:
            clave = (ronda, resultado["opcion"], self.caso.get("rectificacion"))
            if clave != self.resultado_visto:
                self.resultado_visto = clave
                self.abrir("resultado")

    def notificar(self, texto):
        self.toast, self.toast_hasta = texto, time.monotonic() + 6

    def recibir(self, acuse):
        self.notificar(acuse.get("mensaje", "Acción confirmada."))
        if acuse.get("ok") and acuse.get("vista"):
            self.abrir("inventario" if acuse["vista"] == "compartir" else acuse["vista"])
            self.titulo = acuse.get("titulo", "Testimonio")
            self.texto = acuse.get("mensaje", "")
            self.destino_fijo = acuse.get("destinatario")
            self.indice_destino = 0

    def cerca_eco(self):
        return any(o["tipo"] == "eco" and self.vista.cerca(o) for o in self.caso.get("objetivos", []))

    def texto_lineas(self, superficie, texto, x, y, ancho=535, fuente=None, color=CREMA):
        import juego
        fuente = fuente or self.fuente
        for linea in juego.envolver_texto(texto, fuente, ancho):
            superficie.blit(fuente.render(linea, True, color), (x, y))
            y += fuente.get_linesize() + 4
        return y

    def boton(self, superficie, clave, texto, x, y, ancho=280, activo=True):
        b = Boton(texto, centro=(x, y), fuente=self.fuente, tamano=(ancho, 42), desactivado=not activo)
        b.dibujar(superficie, self.vista.mouse)
        self.botones[clave] = b

    def retrato(self, superficie, nombre, x=170, y=175):
        imagen = None
        clave = nombre.lower().split(" · ")[0].split(":")[0]
        for o in self.vista.decoraciones:
            ruta = o.get("nombre", "").lower()
            if ("naira" in clave and "naira" in ruta) or ("luma" in clave and "habitante mujer" in ruta) or ("mira" in clave and "aspirante mujer" in ruta):
                imagen = o.get("imagen")
                break
        if imagen is None:
            yo = next((j for j in self.vista.estado.get("mundo", {}).get("jugadores", []) if j["id"] == self.vista.identificador), {})
            imagen = self.vista.personajes.get(yo.get("rol"), {}).get(("reposo", "abajo"), [None])[0]
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

    def dibujar(self, superficie):
        self.botones = {}
        if not self.activo:
            if time.monotonic() < self.toast_hasta:
                pygame.draw.rect(superficie, (10, 30, 23), (25, 572, 910, 72), border_radius=8)
                self.texto_lineas(superficie, self.toast, 42, 582, 870, self.fuente, VERDE)
            return
        velo = pygame.Surface((960, 720), pygame.SRCALPHA)
        velo.fill((2, 12, 8, 150)); superficie.blit(velo, (0, 0))
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
        inventario = self.privado.get("inventario", [])
        guia = self.privado.get("guia", {})
        tutorial = self.privado.get("tutorial", {})
        if self.modo == "introduccion":
            if tutorial.get("estado") == "pendiente" and self.caso.get("ronda", 0) == 0:
                self.retrato(superficie, "guía")
                self.texto_lineas(superficie, "¡Hola, detectives! La aldea necesita su ayuda.", 290, 180, 495)
                self.texto_lineas(superficie, "Aprendamos a caminar, hablar y llevar un farol. Será una misión corta, sin reloj.", 290, 265, 495)
                self.boton(superficie, "iniciar_tutorial", "Aprender jugando", 480, 420, 430)
                self.boton(superficie, "saltar_tutorial", "Ya sé jugar", 480, 480, 330)
            elif self.caso.get("fase") == "preparacion":
                self.dibujar_encargo(superficie)
            elif self.caso.get("fase") == "final":
                self.texto_lineas(superficie, "¡Gracias por ayudar a la aldea!", 165, 180, 630, color=ORO)
                self.texto_lineas(superficie, f"Estrellas del equipo: {self.caso.get('estrellas', 0)} de {self.caso.get('estrellas_total', 11)}", 165, 237, 630)
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
                self.boton(superficie, "pista_anterior", "<", 205, 353, 70)
                self.boton(superficie, "pista_siguiente", ">", 755, 353, 70)
                self.texto_lineas(superficie, f"Pista {self.indice_pista+1} de {len(inventario)}", 390, 343, 250, self.pequena)
                destinatarios = self.destinatarios()
                if destinatarios:
                    self.indice_destino %= len(destinatarios)
                    destino = destinatarios[self.indice_destino]
                    self.texto_lineas(superficie, "Para: " + destino["nombre"], 165, 400, 630)
                    self.boton(superficie, "destino_anterior", "< Persona", 330, 450, 235)
                    self.boton(superficie, "destino_siguiente", "Persona >", 630, 450, 235)
                    cerca = self.cerca_eco() or self.vista.cerca(destino, 64)
                    self.boton(superficie, "entregar", "Enviar mi pista" if self.cerca_eco() else "Dar mi pista", 480, 506, 420, cerca)
                    if not cerca:
                        self.texto_lineas(superficie, "Acércate a esa persona o a un tronco para enviarla.", 165, 538, 630, self.pequena, ORO)
            if len(inventario) < 2:
                self.boton(superficie, "pedir_pista", "Me falta una pista: pedir ayuda", 480, 582, 530)
        elif self.modo == "caldero":
            self.texto_lineas(superficie, self.caso.get("noticia", ""), 165, 175, 630)
            falta = self.falta_para_elegir()
            mensaje = falta or ("Eligieron distinto. Hablen y prueben otra vez." if self.caso.get("empate") else "Lee tus pistas. ¿Qué crees que pasó?")
            self.texto_lineas(superficie, mensaje, 165, 265, 630, color=ORO)
            self.texto_lineas(superficie, f"Tus pistas: {len(inventario)} · Ya eligieron {self.caso.get('votos_emitidos', 0)} de {self.caso.get('votantes', 0)}", 165, 325, 630, self.pequena)
            if len(inventario) < 2:
                self.boton(superficie, "pedir_pista", "Pedir la pista que me falta", 480, 375, 500)
            elif self.privado.get("voto"):
                self.texto_lineas(superficie, "Tu elección: " + self.caso["opciones"][self.privado["voto"]], 165, 365, 630, self.pequena, VERDE)
            for i, (clave, texto) in enumerate(self.caso.get("opciones", {}).items()):
                self.boton(superficie, "votar:"+clave, texto, 480, 435+i*62, 580, not falta)
        elif self.modo == "eco":
            self.texto_lineas(superficie, "Este tronco puede llevar tus pistas y mensajes a todo el mapa.", 165, 180, 630)
            self.boton(superficie, "inventario", "Enviar una pista", 480, 355, 440)
            self.boton(superficie, "eco_mensajes", "Enviar un mensaje", 480, 420, 440)
        elif self.modo == "eco_mensajes":
            for i, mensaje in enumerate(self.caso.get("mensajes_eco", [])):
                self.boton(superficie, "eco:"+str(i), mensaje, 480, 225+i*75, 620)
        elif self.modo == "actividad":
            self.dibujar_actividad(superficie)
        elif self.modo == "poder":
            self.texto_lineas(superficie, self.privado.get("habilidad", "Mi poder"), 165, 185, 630, color=ORO)
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
            self.texto_lineas(superficie, "Quédate junto al puesto." if cerca else "Acércate al círculo verde del puesto.", 165, 570, 630, self.pequena, ORO)

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

    def manejar(self, evento, posicion, cliente):
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_ESCAPE and self.activo:
                self.modo = None
                return True
            if evento.key == pygame.K_i:
                self.modo = None if self.modo == "inventario" else "inventario"
                return True
            if evento.key == pygame.K_m:
                self.abrir("introduccion")
                return True
            if evento.key == pygame.K_q and not self.activo:
                cliente.actuar("habilidad")
                return True
            if self.activo:
                return True
        if not self.activo or evento.type != pygame.MOUSEBUTTONDOWN or evento.button != 1:
            return False
        for clave, boton in self.botones.items():
            if not boton.fue_clickeado(posicion):
                continue
            if clave in ("cerrar", "seguir"):
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
            elif clave == "pista_anterior":
                self.indice_pista -= 1
            elif clave == "pista_siguiente":
                self.indice_pista += 1
            elif clave == "destino_anterior":
                self.indice_destino -= 1
            elif clave == "destino_siguiente":
                self.indice_destino += 1
            elif clave == "entregar":
                pistas, destinos = self.privado.get("inventario", []), self.destinatarios()
                if pistas and destinos:
                    cliente.actuar("entregar", pista=pistas[self.indice_pista % len(pistas)]["id"],
                                   destinatario=destinos[self.indice_destino % len(destinos)]["id"],
                                   medio="eco" if self.cerca_eco() else "directo")
            elif clave.startswith("eco:"):
                cliente.actuar("eco", mensaje=int(clave.split(":")[1]))
            elif clave.startswith("votar:"):
                cliente.actuar("votar", opcion=clave.split(":")[1])
            elif clave == "rectificar":
                cliente.actuar("rectificar")
            break
        return True
