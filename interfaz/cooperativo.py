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
        for aviso in self.privado.get("avisos", []):
            if aviso["id"] > self.aviso_id:
                self.aviso_id = aviso["id"]
                self.notificar(aviso["texto"])
        resultado = self.caso.get("resultado")
        if resultado:
            clave = (resultado["opcion"], self.caso.get("rectificacion"))
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

    def dibujar(self, superficie):
        self.botones = {}
        if time.monotonic() < self.toast_hasta and not self.activo:
            fondo = pygame.Surface((900, 66), pygame.SRCALPHA)
            fondo.fill((10, 30, 23, 235))
            superficie.blit(fondo, (30, 574))
            self.texto_lineas(superficie, self.toast, 46, 586, 868, self.pequena, VERDE)
        if not self.activo:
            return
        velo = pygame.Surface((960, 720), pygame.SRCALPHA)
        velo.fill((2, 12, 8, 155))
        superficie.blit(velo, (0, 0))
        rect = pygame.Rect(165, 75, 630, 570)
        pygame.draw.rect(superficie, (17, 39, 29), rect, border_radius=16)
        pygame.draw.rect(superficie, ORO, rect, 3, border_radius=16)
        titulos = {"introduccion": "NUEVO CASO COOPERATIVO", "inventario": "MIS PRUEBAS", "caldero": "CONSEJO DEL CALDERO", "eco": "TRONCO DE LOS ECOS",
                   "eco_mensajes": "MENSAJES AL EQUIPO", "resultado": "RESULTADO DEL EQUIPO", "fuente": self.titulo}
        t = self.encabezado.render(titulos.get(self.modo, "INVESTIGACIÓN"), True, ORO)
        superficie.blit(t, t.get_rect(midtop=(480, 100)))
        inventario = self.privado.get("inventario", [])
        if self.modo == "introduccion":
            self.texto_lineas(superficie, self.caso.get("noticia", ""), 210, 175, color=ORO)
            self.texto_lineas(superficie, "Cada rol conoce una parte de la historia. Visita tu fuente con E, lee tu prueba con I y compártela con un compañero. Reúnan al menos dos pruebas y decidan juntos en el caldero.", 210, 280)
            self.texto_lineas(superficie, "Tu fuente: " + self.privado.get("objetivo", {}).get("nombre", ""), 210, 458, fuente=self.pequena, color=VERDE)
        elif self.modo == "fuente":
            self.texto_lineas(superficie, self.texto, 210, 175)
            self.boton(superficie, "inventario", "Leer mis pruebas", 480, 470)
        elif self.modo == "inventario":
            if not inventario:
                self.texto_lineas(superficie, "Todavía no tienes pruebas. Acércate a tu fuente y pulsa E.", 210, 185)
                self.texto_lineas(superficie, "Tu fuente: " + self.privado.get("objetivo", {}).get("nombre", ""), 210, 285, fuente=self.pequena, color=ORO)
            else:
                self.indice_pista %= len(inventario)
                pista = inventario[self.indice_pista]
                self.texto_lineas(superficie, pista["titulo"], 210, 160, color=ORO)
                self.texto_lineas(superficie, pista["texto"], 210, 201)
                self.boton(superficie, "pista_anterior", "<", 246, 329, 70)
                self.boton(superficie, "pista_siguiente", ">", 714, 329, 70)
                etiqueta = self.pequena.render(f"Prueba {self.indice_pista + 1} de {len(inventario)}", True, CREMA)
                superficie.blit(etiqueta, etiqueta.get_rect(center=(480, 329)))
                destinatarios = self.destinatarios()
                if destinatarios:
                    self.indice_destino %= len(destinatarios)
                    destino = destinatarios[self.indice_destino]
                    self.texto_lineas(superficie, "Para: " + destino["nombre"], 210, 377)
                    self.boton(superficie, "destino_anterior", "Anterior", 330, 430, 210)
                    self.boton(superficie, "destino_siguiente", "Siguiente", 630, 430, 210)
                    self.boton(superficie, "entregar", "Enviar por Eco" if self.cerca_eco() else "Entregar de cerca", 480, 492, 330)
                else:
                    self.texto_lineas(superficie, "No hay otro jugador conectado para recibirla.", 210, 390)
        elif self.modo == "eco":
            self.texto_lineas(superficie, self.texto or "Comparte pruebas y coordina al equipo a distancia.", 210, 175)
            self.boton(superficie, "inventario", "Enviar una prueba", 480, 350, 360)
            self.boton(superficie, "eco_mensajes", "Enviar mensaje breve", 480, 416, 360)
        elif self.modo == "eco_mensajes":
            self.texto_lineas(superficie, "Lo recibirán los jugadores conectados.", 210, 157, fuente=self.pequena)
            for i, mensaje in enumerate(self.caso.get("mensajes_eco", [])):
                self.boton(superficie, "eco:" + str(i), mensaje, 480, 235 + i * 66, 550)
        elif self.modo == "caldero":
            self.texto_lineas(superficie, self.caso.get("noticia", ""), 210, 157)
            self.texto_lineas(superficie, f"Investigadores: {self.caso.get('investigadores', 0)} (mín. 2) · Entregas: {self.caso.get('entregas', 0)}", 210, 252, fuente=self.pequena, color=ORO)
            self.texto_lineas(superficie, f"Tus pruebas: {len(inventario)} (mín. 2) · Votos: {self.caso.get('votos_emitidos', 0)}/{self.caso.get('votantes', 0)}", 210, 280, fuente=self.pequena)
            mensaje = ("Esperando al menos dos jugadores conectados para decidir." if self.caso.get("votantes", 0) < 2 else
                       "Empate: comparen las pruebas y cambien un voto." if self.caso.get("empate") else
                       "Cada votante necesita dos pruebas. Todos los conectados votan; se requiere mayoría.")
            self.texto_lineas(superficie, mensaje, 210, 310, fuente=self.pequena)
            if self.privado.get("voto"):
                self.texto_lineas(superficie, "Tu voto: " + self.caso.get("opciones", {}).get(self.privado["voto"], ""), 210, 349, fuente=self.pequena, color=VERDE)
            listo = self.caso.get("votantes", 0) >= 2 and self.caso.get("investigadores", 0) >= 2 and self.caso.get("entregas", 0) >= 1 and len(inventario) >= 2
            for i, (clave, texto) in enumerate(self.caso.get("opciones", {}).items()):
                self.boton(superficie, "votar:" + clave, texto, 480, 392 + i * 58, 430, listo and self.en_caldero())
        elif self.modo == "resultado":
            resultado = self.caso.get("resultado") or {}
            self.texto_lineas(superficie, resultado.get("texto", ""), 210, 175)
            for i, (nombre, valor) in enumerate(self.caso.get("indicadores", {}).items()):
                etiqueta = {"confianza": "Confianza", "armonia": "Armonía", "desinformacion": "Desinformación"}.get(nombre, nombre)
                self.texto_lineas(superficie, f"{etiqueta}: {valor}", 240, 346 + i * 31, color=VERDE if resultado.get("correcto") else ORO)
            if not resultado.get("correcto") and not self.caso.get("rectificacion"):
                self.boton(superficie, "rectificar", "Revisar decisión", 480, 493, 330, self.en_caldero())
                if not self.en_caldero():
                    self.texto_lineas(superficie, "Acércate al caldero para rectificar.", 210, 525, fuente=self.pequena)
        # Área separada para la confirmación; nunca tapa las pruebas ni botones.
        if time.monotonic() < self.toast_hasta and self.modo != "resultado":
            self.texto_lineas(superficie, self.toast, 195, 552, 570, self.pequena, VERDE)
        self.boton(superficie, "cerrar", "Investigar" if self.modo == "introduccion" else "Cerrar · Esc", 480, 614, 260)

    def en_caldero(self):
        return any(o["id"] == "caldero" and self.vista.cerca(o) for o in self.caso.get("objetivos", []))

    def destinatarios(self):
        jugadores = [j for j in self.vista.estado.get("mundo", {}).get("jugadores", [])
                     if j["id"] != self.vista.identificador and j.get("conectado", True)]
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
            if self.activo:
                return True
        if not self.activo or evento.type != pygame.MOUSEBUTTONDOWN or evento.button != 1:
            return False
        for clave, boton in self.botones.items():
            if not boton.fue_clickeado(posicion):
                continue
            if clave == "cerrar":
                self.modo = None
            elif clave in ("inventario", "eco_mensajes"):
                self.abrir(clave)
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
