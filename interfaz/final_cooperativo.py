"""Cuatro minijuegos sobre un mismo panel, con controles y texto por código."""
import time
import pygame
from nucleo.recursos import cargar_imagen
from multijugador.final_cooperativo import ROLES

CREMA, ORO, VERDE = (255, 243, 210), (237, 185, 87), (130, 222, 158)
NOMBRES = dict(guardian="Guardián", mensajero="Mensajero", habitante="Habitante", aspirante="Aspirante")


def estado(vista):
    return (vista.estado.get("mundo", {}).get("caso", {}).get("futuro") or {}).get("desafio_final") or {}


def objetivo(vista, rol=None):
    final = estado(vista)
    if final.get("fase") in (None, "bloqueado", "victoria"):
        return None
    yo = vista.yo() or {}
    rol = rol or yo.get("rol", "guardian")
    puntos = final.get("puntos", {})
    aventura = final.get("aventura", {})
    nombre = "Final cooperativo · " + NOMBRES[rol]
    if final["fase"] == "preparacion" and aventura.get("faltan"):
        rect = vista.rect_portal()
        return dict(id="portal", nombre="Terminar las eras pendientes", x=rect.centerx, y=rect.centery) if rect else None
    if final["fase"] == "preparacion" and not aventura.get("fabricado") and not aventura.get("faltan"):
        if yo.get("id") in aventura.get("cargas", {}) or len(aventura.get("entregadas", [])) == 3:
            punto = aventura.get("taller")
            nombre = "Entregar la pieza en el taller" if yo.get("id") in aventura.get("cargas", {}) else "Fabricar el equipo en el taller"
        else:
            materiales = aventura.get("materiales", [])
            punto = next((m for m in materiales if m["id"] == getattr(vista, "_pieza_guia", None)), None)
            if punto is None and materiales:
                punto = min(materiales, key=lambda m: (m["x"]-yo.get("x", 0))**2 + (m["y"]-yo.get("y", 0))**2)
            vista._pieza_guia = punto["id"] if punto else None
            if punto:
                nombre = "Recoger " + punto.get("nombre", "la pieza")
    elif len(final.get("hechos", [])) == 4:
        if yo.get("id") in final.get("activaciones", []):
            return None
        rol = (vista.yo() or {}).get("rol", rol)
        punto = puntos.get(rol)
    elif final["fase"] in ("preparacion", "reintento"):
        punto = puntos.get("aspirante")
    elif rol in final.get("hechos", []):
        return None
    elif rol in ("mensajero", "aspirante") and final.get("batalla", {}).get("fase", 1) == 1:
        return None
    elif rol == "mensajero" and rol not in final.get("hechos", []):
        if final.get("portador") not in (None, yo.get("id")):
            return None
        ruta = final.get("ruta") or []
        punto = final.get("recogida") if final.get("portador") is None else ruta[min(final.get("tramo", 0), len(ruta) - 1)] if ruta else None
    else:
        punto = puntos.get(rol)
    return dict(punto, id="final:" + rol, nombre=nombre) if punto else None


class PantallaFinal:
    def __init__(self, panel):
        self.panel = panel
        self.fondo = cargar_imagen("FinalCooperativo/ConsolaSupervision.png", (900, 675), requerido=False)
        self.rol = (panel.vista.yo() or {}).get("rol", "guardian")
        self.manteniendo = False
        self.ultimo_envio = 0

    def texto(self, superficie, texto, y, color=CREMA, x=110, ancho=740):
        return self.panel.texto_lineas(superficie, texto, x, y, ancho, self.panel.fuente, color)

    def boton(self, superficie, clave, texto, x, y, ancho=240, activo=True):
        self.panel.boton(superficie, "final:" + clave, texto, x, y, ancho, activo)

    def dibujar(self, superficie):
        p, f = self.panel, estado(self.panel.vista)
        velo = pygame.Surface((960, 720), pygame.SRCALPHA)
        velo.fill((3, 12, 20, 220))
        superficie.blit(velo, (0, 0))
        if self.fondo is not None:
            superficie.blit(self.fondo, (30, 20))
        else:
            pygame.draw.rect(superficie, (10, 31, 38), (30, 20, 900, 675), border_radius=14)
            pygame.draw.rect(superficie, ORO, (30, 20, 900, 675), 3, border_radius=14)
        self.texto(superficie, "RECUPERAR EL CONTROL", 155, ORO)
        self.texto(superficie, "Señal: " + str(f.get("integridad", 3)) + "/3", 155, VERDE, x=740, ancho=145)
        batalla = f.get("batalla", {})
        if f.get("fase") == "activo" and batalla.get("turno") == "recarga":
            import math
            etiqueta = p.pequena.render("Pausa: " + str(math.ceil(batalla.get("segundos", 0))) + " s", True, ORO)
            superficie.blit(etiqueta, (540, 158))
        for i, rol in enumerate(ROLES):
            self.boton(superficie, "rol:" + rol, NOMBRES[rol] + (" · listo" if rol in f.get("hechos", []) else ""), 200 + i * 185, 215, 175)
            if rol == self.rol:
                rect = p.botones["final:rol:" + rol].rect
                pygame.draw.line(superficie, VERDE, (rect.left + 12, rect.bottom - 5), (rect.right - 12, rect.bottom - 5), 2)
        fase = f.get("fase", "bloqueado")
        aventura = f.get("aventura", {})
        if fase == "preparacion" and aventura.get("faltan"):
            self.texto(superficie, "Antes de ayudar a la rebelión, terminen:", 290, ORO)
            self.texto(superficie, ", ".join(aventura["faltan"]), 365)
            self.texto(superficie, "Vuelvan por el portal. Sus pruebas nos permitirán recuperar el control.", 440)
        elif fase == "preparacion" and not aventura.get("fabricado"):
            self.texto(superficie, "AYUDA A LA REBELIÓN", 270, VERDE)
            self.texto(superficie, "Recojan tres piezas y llévenlas al taller del Corredor de Datos.", 320)
            self.texto(superficie, "Construiremos el módulo y blásteres para detener los mini-núcleos.", 365)
            self.texto(superficie, "Piezas entregadas: " + str(len(aventura.get("entregadas", []))) + "/3", 420)
            self.texto(superficie, "Sigue la luz del mapa y pulsa E cerca de cada pieza.", 465)
            yo = (p.vista.yo() or {}).get("id")
            if yo in aventura.get("cargas", {}):
                self.boton(superficie, "depositar", "Entregar en el taller", 480, 525, 340, p.vista.cerca(aventura["taller"]))
            elif len(aventura.get("entregadas", [])) == 3:
                self.boton(superficie, "fabricar", "Fabricar equipo", 480, 525, 340, p.vista.cerca(aventura["taller"]))
            else:
                for i, pieza in enumerate(aventura.get("materiales", [])):
                    self.boton(superficie, "material:" + pieza["id"], "Recoger " + pieza["nombre"], 220 + i * 260, 525, 245, p.vista.cerca(pieza))
        elif fase == "preparacion":
            self.texto(superficie, "Esquiven las marcas. Durante las pausas, usen sus estaciones.", 270)
            for i, rol in enumerate(ROLES):
                self.texto(superficie, NOMBRES[rol] + ": " + dict(guardian="compara las órdenes.", mensajero="lleva el módulo sin perder la señal.",
                           habitante="ajusta la estación para apagar el escudo.", aspirante="prepara la autorización del consejo.")[rol], 340 + i * 42)
            self.boton(superficie, "iniciar", "Iniciar juntos", 480, 550)
        elif fase == "reintento":
            self.texto(superficie, "LA SEÑAL SE CORTÓ", 290, ORO)
            self.texto(superficie, "Vuelvan a la pantalla central. Conservan los casos investigados y las tareas completadas.", 350)
            self.boton(superficie, "reintentar", "Recuperar la señal", 480, 530, 340)
        elif fase == "victoria":
            self.texto(superficie, "¡LO LOGRARON ENTRE TODOS!", 295, VERDE)
            self.texto(superficie, "NÚCLEO vuelve a ayudar. Sus decisiones se revisan y necesitan autorización humana.", 355)
            self.texto(superficie, "Investigar, compartir y colaborar permitió recuperar la ciudad.", 435)
            self.boton(superficie, "informe", "Ver nuestro informe", 480, 540, 340)
        elif fase == "activo":
            privados = p.privado.get("final_cooperativo", {})
            datos = privados.get(self.rol)
            if len(f.get("hechos", [])) == 4:
                self.texto(superficie, "Las cuatro tareas están listas. Cada participante vuelve a su estación.", 300, VERDE)
                self.texto(superficie, "Activen sus propias consolas con E. No hay límite de tiempo.", 365)
                self.texto(superficie, "Confirmaciones: " + str(len(f.get("activaciones", []))), 435)
                self.boton(superficie, "activar", "Confirmar activación", 480, 540, 340)
            elif f.get("batalla", {}).get("turno") != "recarga":
                self.texto(superficie, "¡NÚCLEO está atacando! Vuelve al mapa y sal de las marcas.", 310, ORO)
                self.texto(superficie, "Los minijuegos continúan durante su próxima recarga.", 380)
            elif f.get("batalla", {}).get("fase") == 1 and self.rol in ("mensajero", "aspirante"):
                self.texto(superficie, "Guardián y Habitante están apagando el escudo.", 310)
                self.texto(superficie, "Esquiva las marcas. Tu tarea empieza en la fase roja.", 380)
            elif datos is None:
                self.texto(superficie, "Esta misión la realiza tu compañero " + NOMBRES[self.rol] + ".", 310)
                self.texto(superficie, "Puedes seguir su progreso arriba. Elige tu rol para realizar tu tarea.", 380)
            elif self.rol in f.get("hechos", []):
                self.texto(superficie, "¡Tu tarea está lista! El equipo conserva este avance.", 310, VERDE)
                self.texto(superficie, "Vuelve al mapa, esquiva las marcas y ayuda a tus compañeros con E.", 380)
            elif self.rol == "guardian":
                self.texto(superficie, "Compara las dos tarjetas. ¿Qué dato cambió sin autorización?", 260)
                for x, clave, titulo in ((110, "registro", "Registro del consejo"), (515, "orden", "Orden recibida")):
                    pygame.draw.rect(superficie, (18, 48, 57), (x - 8, 305, 350, 160), border_radius=8)
                    self.texto(superficie, titulo, 315, ORO, x=x, ancho=330)
                    for i, campo in enumerate(("firma", "fecha", "permiso")):
                        self.texto(superficie, campo.capitalize() + ": " + datos.get(clave, {}).get(campo, ""), 355 + i * 32, x=x, ancho=330)
                for i, campo in enumerate(("firma", "fecha", "permiso")):
                    self.boton(superficie, "comparar:" + campo, campo.capitalize(), 245 + i * 235, 515, 210, "guardian" not in f.get("hechos", []))
            elif self.rol == "habitante":
                self.texto(superficie, "Pon cada indicador en verde. Después mantén E o Espacio durante 2 segundos.", 260)
                for i, (valor, meta) in enumerate(zip(datos.get("valores", []), datos.get("metas", []))):
                    y = 335 + i * 65
                    self.texto(superficie, "Circuito " + str(i + 1), y - 12, x=115, ancho=180)
                    self.boton(superficie, "ajustar:" + str(i) + ":-1", "-", 300, y, 60)
                    for n in range(7):
                        rect = pygame.Rect(350 + n * 42, y - 14, 35, 28)
                        pygame.draw.rect(superficie, VERDE if n == meta else (47, 80, 88), rect, border_radius=3)
                        if n == valor:
                            pygame.draw.rect(superficie, CREMA, rect.inflate(4, 4), 3, border_radius=3)
                    self.boton(superficie, "ajustar:" + str(i) + ":1", "+", 705, y, 60)
                self.texto(superficie, f"Carga: {f.get('carga', 0):.1f}/2 s · " + ("Estación activa" if f.get("estacion_activa") else "Mantén E para cargarla"), 535, VERDE)
            elif self.rol == "mensajero":
                self.texto(superficie, "Espera la orden verificada, recoge el módulo y recorre las recargas del mapa.", 270)
                self.texto(superficie, "Módulo: " + str(f.get("modulo") or "pendiente de verificar"), 345, ORO)
                self.texto(superficie, "Recargas: " + str(f.get("tramo", 0)) + "/2. Los pulsos rojos cortan la señal; puedes recuperar la carga.", 395)
                self.texto(superficie, "El escudo ya está apagado. Entrega el módulo en la última estación.", 455)
                self.boton(superficie, "recargar" if f.get("portador") else "recoger", "Recargar / entregar" if f.get("portador") else "Recoger módulo", 480, 540, 320,
                           "guardian" in f.get("hechos", []) and "mensajero" not in f.get("hechos", []))
            else:
                self.texto(superficie, "Arma la propuesta: prueba, conexión y límite del sistema.", 260)
                for i, (campo, opciones) in enumerate(datos.get("opciones", {}).items()):
                    for j, (valor, etiqueta) in enumerate(opciones):
                        elegido = datos.get("propuesta", {}).get(campo) == valor
                        self.boton(superficie, "elegir:" + campo + ":" + valor, ("> " if elegido else "") + etiqueta,
                                   290 + j * 380, 330 + i * 65, 350)
                self.boton(superficie, "autorizar", "Presentar al consejo", 480, 540, 320)
        self.boton(superficie, "mapa", "Volver al mapa", 480, 625, 320)
        from nucleo.recursos import envolver_texto
        aviso = p.toast if p.toast and time.monotonic() < p.toast_hasta else f.get("aviso", "")
        for i, linea in enumerate(envolver_texto(aviso, p.pequena, 770)[:2]):
            superficie.blit(p.pequena.render(linea, True, ORO), (95, 568 + i * 18))

    def actualizar(self, cliente):
        p = self.panel
        if p.modo != "final_cooperativo" or self.rol != "habitante" or not pygame.key.get_focused():
            self.manteniendo = False
            return
        if estado(p.vista).get("batalla", {}).get("turno") != "recarga":
            self.manteniendo = False
            return
        datos = p.privado.get("final_cooperativo", {}).get(self.rol, {})
        if self.manteniendo and "valores" in datos and datos.get("valores") == datos.get("metas") and time.monotonic() - self.ultimo_envio >= .4:
            self.ultimo_envio = time.monotonic()
            cliente.actuar("final_accion", operacion="mantener", rol=self.rol, ronda_final=estado(p.vista).get("ronda"))

    def manejar(self, evento, posicion, cliente):
        if evento.type in (pygame.KEYDOWN, pygame.KEYUP) and evento.key in (pygame.K_e, pygame.K_SPACE):
            self.manteniendo = evento.type == pygame.KEYDOWN
            return True
        if evento.type != pygame.MOUSEBUTTONDOWN or evento.button != 1:
            return False
        for clave, boton in self.panel.botones.items():
            if not clave.startswith("final:") or not boton.fue_clickeado(posicion):
                continue
            partes = clave.split(":")[1:]
            operacion = partes[0]
            if operacion == "rol":
                self.rol = partes[1]
            elif operacion == "mapa":
                self.panel.modo = None
                self.manteniendo = False
            elif operacion == "informe":
                cliente.actuar("pedir_informe")
            else:
                datos = dict(operacion=operacion, rol=self.rol, ronda_final=estado(self.panel.vista).get("ronda"))
                if operacion == "material":
                    datos["pieza"] = partes[1]
                elif operacion == "comparar":
                    datos["campo"] = partes[1]
                elif operacion == "ajustar":
                    datos.update(indice=int(partes[1]), delta=int(partes[2]))
                elif operacion == "elegir":
                    datos.update(campo=partes[1], valor=partes[2])
                cliente.actuar("final_accion", **datos)
            return True
        return False


def pantalla(panel):
    if not hasattr(panel, "pantalla_final_coop"):
        panel.pantalla_final_coop = PantallaFinal(panel)
    return panel.pantalla_final_coop
