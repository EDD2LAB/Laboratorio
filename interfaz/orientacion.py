"""Siguiente acción e indicadores visuales: no decide ni revela soluciones."""
import math
import time

import pygame

from nucleo.recursos import cargar_imagen, cargar_fuente


def objetivo_nucleo(contexto, conocidas, npcs):
    objetivos = contexto.get("objetivos", [])
    tareas = contexto.get("tareas", [])
    def tarea(clave):
        return next((o for o in objetivos if o.get("tarea") == clave), None)
    def pista(clave):
        return next((n for n in npcs if n.get("dimension") == "futuro" and n.get("pista") == clave), None)
    if "conexiones" not in tareas:
        return tarea("conexiones")
    if "archivos" not in tareas:
        return (pista("guia_de_firmas") if "guia_de_firmas" not in conocidas else None) or tarea("archivos")
    if "llave" not in tareas:
        return (pista("llave_supervision") if "llave_supervision" not in conocidas else None) or tarea("llave")
    if "cuentas" not in tareas:
        return tarea("cuentas")
    if "firma_representante" not in conocidas:
        return pista("firma_representante")
    return next((o for o in objetivos if o.get("id") == "futuro:pantalla"), None)


def datos_votacion(contexto, jugadores, identificador):
    faltan = set(contexto.get("faltan_votar", []))
    nombres = [j["nombre"] for j in jugadores if j.get("id") in faltan]
    if contexto.get("empate"):
        return "Eligieron distinto. Hablen y cambien un voto para llegar a un acuerdo."
    if identificador in faltan:
        return "Te toca elegir. Lee las pistas antes de votar."
    if nombres:
        visibles = ", ".join(nombres[:2])
        return "Falta elegir: " + visibles + (" y otra persona." if len(nombres) > 2 else ".")
    pendientes = contexto.get("votantes", 0) - contexto.get("votos_emitidos", 0)
    if pendientes > 0:
        return f"Faltan {pendientes} personas por elegir."
    return "Elijan juntos usando sus pistas."


def aviso_analisis(contexto):
    analisis = contexto.get("analisis") or {}
    if contexto.get("completada") or not analisis or analisis.get("concluido"):
        return ""
    faltan = max(0, analisis.get("minimo", 0) - len(analisis.get("halladas", [])))
    return f"Antes de decidir: Analizar, faltan {faltan} marcas."


def tarea_actual(vista):
    mundo = vista.estado.get("mundo", {})
    caso, privado = mundo.get("caso", {}), mundo.get("privado", {})
    contexto = vista.contexto()
    objetivo = (privado.get("guia", {}).get("objetivo") if vista.dimension == "la_copa"
                else vista._objetivo_presente())
    titulo, detalle = vista._textos_objetivo(caso, privado, privado.get("guia", {}))
    final = contexto.get("desafio_final") or {}
    if vista.dimension == "futuro" and not vista.interior and final.get("fase") in ("preparacion", "activo", "reintento"):
        rol = getattr(vista, "final_rol_guia", None) or (vista.yo() or {}).get("rol", "guardian")
        titulo = {"guardian": "Compara las órdenes del consejo", "mensajero": "Lleva el módulo por las recargas",
                  "habitante": "Estabiliza y sostiene la estación", "aspirante": "Prepara la autorización humana"}[rol]
        if final["fase"] != "activo" or len(final.get("hechos", [])) == 4:
            titulo = "Ve a la pantalla central para " + ("recuperar la señal" if final["fase"] == "reintento" else "activar juntos" if final["fase"] == "activo" else "iniciar el final")
        aventura = final.get("aventura", {})
        if final["fase"] == "preparacion" and aventura.get("faltan"):
            titulo = "Vuelve por el portal: falta " + ", ".join(aventura["faltan"])
        elif final["fase"] == "preparacion" and not aventura.get("fabricado"):
            titulo = "Ayuda a la rebelión: recoge y entrega las piezas en el taller"
        elif len(final.get("hechos", [])) == 4:
            titulo = "Ve a tu consola y confirma con E"
        batalla = final.get("batalla", {})
        if final["fase"] == "activo" and batalla.get("turno") in ("aviso", "rayo"):
            titulo = "¡Sal de las marcas! NÚCLEO va a disparar"
        elif batalla.get("turno") == "recarga":
            titulo = "¡Está recargando! " + titulo
        return dict(titulo=titulo, detalle="Esquiva durante los ataques. Usa E en las estaciones durante la pausa.", objetivo=objetivo, tecla="E", logro=None)
    if vista.dimension == "futuro" and vista.interior:
        return {"titulo": "Consulta la mesa" if objetivo and objetivo["id"] != "salir" else "Vuelve a la ciudad",
                "detalle": "La visita es opcional. Pulsa E junto a la mesa; usa E en la puerta para salir.",
                "objetivo": objetivo, "tecla": "E", "logro": None}
    tecla = "E"
    logro = None
    if vista.dimension == "la_copa":
        guia = privado.get("guia", {})
        paso = guia.get("paso")
        if paso == "buscar" and objetivo:
            titulo = "Busca tu pista: " + objetivo.get("nombre", "sigue la luz")
            logro = "pista_" + (vista.yo() or {}).get("rol", "")
        elif paso == "compartir":
            titulo = "Comparte o pide una pista con I"
            tecla, logro = "I", "dos_pistas"
        elif paso == "tutorial":
            numero = (privado.get("tutorial") or {}).get("paso", 0)
            tecla = "W" if numero == 0 else "E"
            logro = "tutorial:" + str(numero + 1)
        elif paso == "decidir":
            titulo, logro = "Ve al caldero y elige con tu equipo", "resuelto"
    elif (vista.dimension == "presente" and contexto.get("completada")
          and not (privado.get("presente") or {}).get("clasificacion")):
        titulo, tecla, objetivo = "Abre C para clasificar lo que descubrieron", "C", None
    elif contexto.get("fin"):
        titulo, tecla = "¡Misión completa! Ve al portal", "E"
    elif contexto.get("completada"):
        titulo, tecla = "Abre C para clasificar y continuar", "C"
        objetivo = None
    elif vista.dimension == "presente":
        analisis = contexto.get("analisis") or {}
        if contexto.get("pistas", 0) < contexto.get("total_pistas", 3):
            if objetivo:
                if vista.interior and objetivo.get("id") == "salir":
                    titulo = "Sal del edificio para buscar la siguiente pista"
                elif not objetivo.get("puerta") and objetivo.get("interior") == vista.interior and objetivo.get("pista"):
                    titulo = "Habla con " + objetivo.get("nombre", "la persona marcada")
                else:
                    titulo = "Entra a " + objetivo.get("nombre", "la puerta marcada")
                logro = objetivo.get("pista")
        elif analisis and not analisis.get("concluido"):
            faltan = max(0, analisis.get("minimo", 0) - len(analisis.get("halladas", [])))
            titulo, tecla = f"Abre C: encuentra {faltan} marcas en Analizar", "C"
            objetivo = None  # no enviar a votar mientras la tarea es analizar
        else:
            titulo = "Ve a la pantalla pública y elige en C"
    elif objetivo:
        titulo = ("Habla con " if objetivo.get("pista") in ("llave_supervision", "firma_representante") else "Ve a ") + objetivo.get("nombre", "la señal")
        logro = objetivo.get("pista")
    if vista.dimension_completa() and tecla == "E":
        rect = vista.rect_portal()
        if rect and not (vista.dimension == "la_copa" and contexto.get("fase") != "final"):
            objetivo = {"id": "portal", "x": rect.centerx, "y": rect.centery}
    return {"titulo": titulo, "detalle": detalle, "objetivo": objetivo, "tecla": tecla, "logro": logro}


def logros_actuales(vista):
    mundo = vista.estado.get("mundo", {})
    caso, privado = mundo.get("caso", {}), mundo.get("privado", {})
    personal = privado if vista.dimension == "la_copa" else privado.get(vista.dimension) or {}
    logros = {p["id"] for p in personal.get("inventario", [])}
    if len(logros) >= 2:
        logros.add("dos_pistas")
    paso = (privado.get("tutorial") or {}).get("paso", 0)
    if vista.dimension == "la_copa":
        logros.update("tutorial:" + str(i) for i in range(1, paso + 1))
    else:
        logros.update(vista.contexto().get("tareas", []))
    if vista.contexto().get("resultado"):
        logros.add("resuelto")
    return logros


class ArteOrientacion:
    def __init__(self):
        self.fuente = cargar_fuente(20)
        self.tiras = {}
        for nombre, cuadros in (("exclamacion", 4), ("interrogacion", 4), ("check", 4)):
            self.tiras[nombre] = self._cargar(f"Indicadores/{nombre}_4f.png", cuadros, (28, 28))
        self.teclas = {}

    @staticmethod
    def _cargar(ruta, cuadros, tamano):
        imagen = cargar_imagen(ruta, requerido=False)
        if imagen is None or imagen.get_width() % cuadros or imagen.get_width() < cuadros:
            return []
        ancho = imagen.get_width() // cuadros
        return [pygame.transform.scale(imagen.subsurface((i * ancho, 0, ancho, imagen.get_height())), tamano)
                for i in range(cuadros)]

    def tecla(self, superficie, texto, centro, tamano=(42, 30)):
        clave = (texto, tamano)
        if clave not in self.teclas:
            cuadros = self._cargar(f"Indicadores/tecla_{texto}.png", 2, tamano)
            if not cuadros:
                imagen = pygame.Surface(tamano, pygame.SRCALPHA)
                rect = imagen.get_rect()
                pygame.draw.rect(imagen, (17, 40, 33), rect, border_radius=5)
                pygame.draw.rect(imagen, (237, 185, 87), rect, 2, border_radius=5)
                render = self.fuente.render(texto, True, (255, 243, 210))
                if render.get_width() > rect.width - 8:
                    render = pygame.transform.scale(render, (rect.width - 8, render.get_height()))
                imagen.blit(render, render.get_rect(center=rect.center))
                cuadros = [imagen]
            self.teclas[clave] = cuadros
        cuadros = self.teclas[clave]
        rect = pygame.Rect(0, 0, *tamano)
        rect.center = centro
        superficie.blit(cuadros[(pygame.time.get_ticks() // 450) % len(cuadros)], rect)
        return rect

    def indicador(self, superficie, nombre, centro):
        cuadros = self.tiras[nombre]
        centro = (round(centro[0]), round(centro[1]))
        if cuadros:
            superficie.blit(cuadros[(pygame.time.get_ticks() // 180) % len(cuadros)], cuadros[0].get_rect(center=centro))
        else:
            color = (130, 222, 158) if nombre == "check" else (237, 185, 87)
            pygame.draw.circle(superficie, (13, 35, 28), centro, 15)
            pygame.draw.circle(superficie, color, centro, 15, 2)
            if nombre == "check":
                x, y = centro
                pygame.draw.lines(superficie, color, False, [(x - 7, y), (x - 2, y + 5), (x + 8, y - 7)], 3)
            else:
                render = self.fuente.render("!" if nombre == "exclamacion" else "?", True, color)
                superficie.blit(render, render.get_rect(center=centro))


class OrientacionMapa:
    def __init__(self):
        self.arte = ArteOrientacion()
        self.anterior = None
        self.celebracion = None

    def dibujar(self, vista, superficie):
        if vista.panel.activo or not vista.mostrar_hud:
            return
        tarea = tarea_actual(vista)
        logros = logros_actuales(vista)
        contexto = vista.contexto()
        clave = (vista.dimension, vista.interior, contexto.get("ronda"), (contexto.get("evento") or {}).get("id"))
        if self.anterior:
            anterior, antes, era = self.anterior
            if era == clave and anterior.get("logro") in logros - antes and anterior.get("objetivo"):
                hasta = max(time.monotonic(), getattr(vista.panel, "toast_hasta", 0)) + 1.8
                self.celebracion = (anterior["objetivo"], hasta, clave)
        self.anterior = (tarea, logros, clave)
        objetivo = tarea.get("objetivo")

        def dibujar(objeto, simbolo, tecla=None):
            x, y = vista.a_pantalla(objeto["x"], objeto["y"])
            if not superficie.get_rect().inflate(-20, -120).collidepoint(x, y):
                return
            y -= 80 if vista.dimension == "la_copa" else 65
            y += math.sin(pygame.time.get_ticks() / 220) * 2
            self.arte.indicador(superficie, simbolo, (x, y))
            if tecla:
                self.arte.tecla(superficie, tecla, (round(x + 34), round(y)), (28, 27))

        # Solo quien realmente tiene una pista nueva en la escena actual.
        mundo = vista.estado.get("mundo", {})
        for npc in mundo.get("caso", {}).get("npcs", []):
            if (npc.get("dimension") == vista.dimension and npc.get("interior") == vista.interior
                    and npc.get("pista") and npc["pista"] not in logros
                    and (not objetivo or npc.get("id") != objetivo.get("id"))):
                dibujar(npc, "interrogacion")
        if objetivo:
            cerca = any(math.hypot(c["x"] - objetivo["x"], c["y"] - objetivo["y"]) < 25 for c in vista.candidatos())
            dibujar(objetivo, "exclamacion", tarea["tecla"] if cerca else None)
        if self.celebracion:
            objeto, hasta, era = self.celebracion
            if era == clave and time.monotonic() < hasta:
                dibujar(objeto, "check")
            else:
                self.celebracion = None
