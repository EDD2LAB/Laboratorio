"""Cierre compartido: el servidor elige la escena y el cliente solo la presenta."""
import json
import pygame
from nucleo.rutas import RAIZ
from nucleo.recursos import cargar_imagen, envolver_texto
from multijugador.aventura_final import RECONFIGURACION, EPILOGOS, CIERRE


class Desenlace:
    def __init__(self, panel):
        self.panel = panel
        from interfaz.presentacion_arte import AnimacionesNucleo
        self.nucleo = AnimacionesNucleo(128)
        self.fondos = {}
        respaldos = {"futuro": "Futuro/generado/MapaFuturo.png", "presente": "Fondos/Mapas/Presente/MapaPresente.png",
                     "la_copa": "Fondos/Mapas/Pr_MañanaLumi.png"}
        for era, respaldo in respaldos.items():
            self.fondos[era] = cargar_imagen("Finales/epilogo_" + ("copa" if era == "la_copa" else era) + ".png", (960, 720), requerido=False)
            if self.fondos[era] is None:
                self.fondos[era] = cargar_imagen(respaldo, (960, 720), requerido=False)
        self.creditos = []
        try:
            datos = json.loads((RAIZ / "datos/creditos.json").read_text(encoding="utf-8"))
            self.creditos = [str(p.get("nombre", "")) + " · " + str(p.get("rol", ""))
                             for p in datos.get("integrantes", []) if isinstance(p, dict) and p.get("nombre")]
        except (OSError, ValueError, TypeError):
            pass
        self.resultado = None
        self.informe_pedido = False

    def estado(self):
        from interfaz.final_cooperativo import estado
        return estado(self.panel.vista).get("aventura", {}).get("cierre", {})

    def actualizar(self, cliente):
        if self.estado().get("etapa") == "informe" and not self.informe_pedido:
            self.informe_pedido = True
            cliente.actuar("pedir_informe")

    def lineas(self, s, texto, y, fuente=None, color=(255, 243, 210)):
        fuente = fuente or self.panel.encabezado
        for linea in envolver_texto(texto, fuente, 800):
            imagen = fuente.render(linea, True, color)
            s.blit(imagen, imagen.get_rect(midtop=(480, y)))
            y += fuente.get_linesize() + 5

    def dibujar(self, s):
        p, c = self.panel, self.estado()
        etapa, indice = c.get("etapa"), c.get("indice", 0)
        fondo = self.fondos.get(EPILOGOS[indice][0] if etapa == "epilogo" else "futuro")
        s.fill((5, 18, 26))
        if fondo is not None:
            s.blit(fondo, (0, 0))
        velo = pygame.Surface((960, 720), pygame.SRCALPHA)
        velo.fill((3, 12, 20, 190))
        s.blit(velo, (0, 0))
        if etapa == "reconfiguracion":
            quien, texto = RECONFIGURACION[indice]
            self.lineas(s, "NÚCLEO BAJO SUPERVISIÓN HUMANA", 115)
            cuadro = self.nucleo.cuadro({"desafio_final": {"fase": "victoria"}}, pygame.time.get_ticks())
            if cuadro is not None:
                s.blit(cuadro, cuadro.get_rect(center=(480, 225)))
            self.lineas(s, quien, 300, color=(120, 240, 210))
            self.lineas(s, texto, 365)
        elif etapa == "epilogo":
            self.lineas(s, "EL REGRESO · " + str(indice + 1) + "/3", 115)
            self.lineas(s, EPILOGOS[indice][1], 390)
        elif etapa == "informe":
            if p.informe:
                from interfaz.informe_final import dibujar
                dibujar(p, s)
            else:
                self.lineas(s, "Abriendo la historia de los ocho casos…", 300)
        elif etapa == "pantalla":
            if self.resultado is None:
                from interfaz.finales import PantallaFinal
                jugadores = p.vista.estado.get("mundo", {}).get("jugadores", [])
                aspirante = next((j for j in jugadores if j.get("rol") == "aspirante"), {})
                lider = "Mira" if aspirante.get("apariencia") in ("mira", "mujer") else "Kael"
                expediente = p.caso.get("expediente", {})
                resueltos = (sum(bool(f.get("resuelto")) for f in p.informe.get("casos", [])) if p.informe
                             else expediente.get("total", 0) + expediente.get("pendientes", 0))
                self.resultado = PantallaFinal(p.caso.get("indicadores", {}), p.vista.etiquetas.get(p.dimension, p.vista.etiquetas["la_copa"]),
                                              p.encabezado, p.fuente, lider=lider, casos=resueltos)
            self.resultado.dibujar(s)
        elif etapa == "creditos":
            self.lineas(s, "TIMELESS GLITCH", 90)
            filas = ["Los Guardianes de la Memoria", "Estructuras de Datos 2", *self.creditos, CIERRE]
            area = pygame.Rect(50, 180, 860, 395)
            s.set_clip(area)
            for i, texto in enumerate(filas):
                self.lineas(s, texto, 480 + i * 60 - min(c.get("segundos", 0) * 22, len(filas) * 60 + 100), p.fuente)
            s.set_clip(None)
        p.boton(s, "desenlace:menu" if etapa == "creditos" else "desenlace:continuar",
                "Volver al menú" if etapa == "creditos" else "Continuar para el equipo", 690 if etapa == "informe" else 480, 660, 340)

    def manejar(self, evento, posicion, cliente):
        p = self.panel
        if self.estado().get("etapa") == "informe":
            from interfaz import informe_final
            if informe_final.manejar_desplazamiento(p, evento, posicion):
                return True
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                b = p.botones.get("informe_exportar")
                if b and b.fue_clickeado(posicion):
                    p.informe_exportado = str(informe_final.exportar(p.informe))
                    return True
        avanzar = evento.type == pygame.KEYDOWN and evento.key in (pygame.K_e, pygame.K_SPACE)
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            avanzar = any(b.fue_clickeado(posicion) for k, b in p.botones.items() if k.startswith("desenlace:"))
        if avanzar:
            if self.estado().get("etapa") == "creditos":
                p.vista.volver_menu = True
            else:
                from interfaz.final_cooperativo import estado
                cliente.actuar("final_accion", operacion="continuar", ronda_final=estado(p.vista)["ronda"],
                               revision_cierre=self.estado()["revision"])
        return True


def pantalla(panel):
    if not hasattr(panel, "desenlace"):
        panel.desenlace = Desenlace(panel)
    return panel.desenlace
