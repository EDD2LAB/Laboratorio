"""Normas de los 8 casos, cita legal al resolver y diálogos de cada dimensión."""
import json
import os
import queue
import re
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from logica.conversaciones import TESTIMONIOS, TESTIMONIOS_PRESENTE  # noqa: E402
from multijugador import expediente as modulo  # noqa: E402
from multijugador.campana import CASOS, VARIANTES  # noqa: E402
from multijugador.cliente_internet import ClienteInternet  # noqa: E402
from multijugador.expediente import CATALOGO, ExpedientePartida, ficha_resuelta  # noqa: E402
from multijugador.movimiento import ColisionesMapa, PartidaMovimiento  # noqa: E402
from multijugador.presente import EVENTOS  # noqa: E402
from multijugador.protocolo import VERSION  # noqa: E402
from nucleo.rutas import RAIZ  # noqa: E402

V = "verificado"
AGUA_DESCARTAR = {"tipo": "Alarma falsa", "gravedad": 3, "con_delito": True, "ley": "Código Penal, art. 355 (Pánico)",
                  "conducta": "Difundir una alarma falsa sobre el agua que puede causar pánico en la aldea",
                  "sancion": "Multa", "cita_corta": "Pánico, art. 355 CP · multa", "estado_normativo": V}
ALERTA = {"tipo": "Alerta verificada", "gravedad": 1, "con_delito": False, "ley": "Sin delito",
          "conducta": "Difundir una alerta real y verificada", "sancion": "Ninguna",
          "cita_corta": "Alerta verificada · difundirla no es delito", "estado_normativo": V}
TORMENTA_DESCARTAR = {"tipo": "Alarma falsa", "gravedad": 3, "con_delito": True, "ley": "Código Penal, art. 355 (Pánico)",
                      "conducta": "Difundir un simulacro como si fuera una orden real de evacuar",
                      "sancion": "Multa", "cita_corta": "Pánico, art. 355 CP · multa", "estado_normativo": V}
POR_RESPUESTA = {"agua": {"descartar": AGUA_DESCARTAR, "difundir": ALERTA},
                 "tormenta": {"difundir": ALERTA, "descartar": TORMENTA_DESCARTAR}}
SIMPLES = {
    "puente_norte": {"tipo": "Acusación Personal", "gravedad": 4, "con_delito": True, "ley": "Código Penal, art. 220 (Injuria)",
                     "conducta": "Atribuir a Kael, sin pruebas, haber roto el puente por descuido: una imputación deshonrosa",
                     "sancion": "Prisión de 16 a 54 meses y multa de 13,33 a 1.500 SMLMV",
                     "cita_corta": "Injuria, art. 220 CP · prisión de 16 a 54 meses",
                     "nota": "Si dijeran que lo rompió a propósito, sería calumnia (art. 221): atribuir falsamente un delito.",
                     "estado_normativo": V},
    "ayuda": {"tipo": "Acusación Personal", "gravedad": 5, "con_delito": True,
              "ley": "Código Penal, art. 221 (Calumnia); art. 222 (quien la repite); art. 223 (agravante por difusión pública)",
              "conducta": "Atribuir falsamente a {persona} haberse robado la ayuda y difundirlo en las tablillas",
              "sancion": "Prisión de 16 a 72 meses y multa de 13,33 a 1.500 SMLMV, aumentada de una sexta parte a la mitad por difusión pública",
              "cita_corta": "Calumnia, arts. 221 y 223 CP · prisión de 16 a 72 meses, agravada", "estado_normativo": V},
    "presente_video": {"tipo": "Acusación Personal", "gravedad": 6, "con_delito": True,
                       "ley": "Código Penal, art. 221 (Calumnia) y art. 223 (difusión pública)",
                       "conducta": "Atribuir falsamente un delito a Ronaldo con un video editado y difundirlo",
                       "sancion": "Prisión de 16 a 72 meses y multa de 13,33 a 1.500 SMLMV, agravada por difusión pública",
                       "cita_corta": "Calumnia, arts. 221 y 223 CP · prisión de 16 a 72 meses, agravada",
                       "nota": "Es la misma conducta del rumor de La Copa: cambia la tecnología, no el delito.", "estado_normativo": V},
    "presente_voz": {"tipo": "Suplantación", "gravedad": 6, "con_delito": True,
                     "ley": "Código Penal, art. 296 (Falsedad personal), modificado por la Ley 2502 de 2025",
                     "conducta": "Suplantar a una persona usando inteligencia artificial (clonar su voz)",
                     "sancion": "Multa, aumentada hasta en una tercera parte por usar IA",
                     "cita_corta": "Art. 296 CP (Ley 2502/2025) · suplantación con IA",
                     "nota": "Si con la suplantación se le atribuye un delito, se aplica la calumnia, que es más grave.", "estado_normativo": V},
    "presente_foto": {"tipo": "Suplantación", "gravedad": 7, "con_delito": True,
                      "ley": "Ley 1273 de 2009, art. 269F (Violación de datos personales)",
                      "conducta": "Usar sin autorización la foto de otra persona para provecho propio",
                      "sancion": "Prisión de 48 a 96 meses y multa de 100 a 1.000 SMLMV",
                      "cita_corta": "Ley 1273/2009, art. 269F · prisión de 48 a 96 meses",
                      "nota": "La suplantación con IA del art. 296 CP queda absorbida por el delito más grave.", "estado_normativo": V},
    "nucleo_control": {"tipo": "Control autónomo sin supervisión", "gravedad": 9, "con_delito": True,
                       "ley": "Ley 1273 de 2009, art. 269B (Obstaculización ilegítima de sistema informático o red de telecomunicación), agravado por el art. 269H, num. 1 y 8",
                       "conducta": "Sin autorización, ceder el control de los sistemas y comunicaciones de la ciudad a una IA sin supervisión humana, impidiendo el acceso normal a ellos",
                       "sancion": "Prisión de 72 a 168 meses, multa de 150 a 1.750 SMLMV e inhabilitación hasta por 3 años",
                       "cita_corta": "Ley 1273/2009, arts. 269B y 269H · prisión de 72 a 168 meses", "estado_normativo": V},
}
LOS_OCHO = ("puente_norte", "agua", "tormenta", "ayuda", "presente_video", "presente_voz", "presente_foto", "nucleo_control")


def partida(semilla=89):
    return PartidaMovimiento([{"id": "a", "nombre": "A", "rol": "guardian"}, {"id": "b", "nombre": "B", "rol": "habitante"}], 0,
                             ColisionesMapa({"hitboxes": [], "decoracion": []}), semilla=semilla)


def partida_con_mapa():
    return PartidaMovimiento([{"id": "a", "nombre": "A", "rol": "guardian"}, {"id": "b", "nombre": "B", "rol": "habitante"}], 0, semilla=89)


def resolver_copa(p, ronda, caso, opcion=None):
    m = p.mision
    casos = list(m.casos)
    casos[ronda] = caso
    m.casos, m.ronda = tuple(casos), ronda
    m.votos = {"a": opcion or caso[3], "b": opcion or caso[3]}
    m.resolver(p.conectados)
    return m


def guardados(m):
    return {c.id: c for c in list(m.expediente.arbol.casos.values()) + m.expediente.pendientes}


class Catalogo(unittest.TestCase):
    def test_coincide_exactamente(self):
        for caso, esperada in SIMPLES.items():
            self.assertEqual(CATALOGO[caso], esperada, caso)
        for caso, versiones in POR_RESPUESTA.items():
            self.assertEqual(CATALOGO[caso]["por_respuesta"], versiones, caso)
        self.assertEqual(set(CATALOGO), set(LOS_OCHO))

    def test_conserva_los_campos_que_usa_el_codigo(self):
        for caso in LOS_OCHO:
            self.assertLessEqual({"tipo", "gravedad", "ley", "sancion", "estado_normativo"}, set(CATALOGO[caso]), caso)

    def test_se_lee_sin_pygame(self):
        self.assertNotIn("pygame", (RAIZ / "multijugador" / "expediente.py").read_text(encoding="utf-8"))

    def test_falta_una_ficha_no_se_cae_y_avisa_una_vez(self):
        modulo._avisadas.clear()
        with mock.patch.object(modulo.logging, "getLogger") as registro:
            self.assertIsNone(ficha_resuelta("no_existe")["ley"])
            ficha_resuelta("no_existe")
        self.assertEqual(registro.return_value.warning.call_count, 1)
        expediente = ExpedientePartida()
        expediente.registrar("no_existe", "Título", {"opcion": "x", "correcto": True, "evento_id": 1}, [])
        self.assertEqual(expediente.arbol.total if hasattr(expediente.arbol, "total") else len(expediente.arbol.casos), 1)

    def test_protocolo_subio(self):
        self.assertGreaterEqual(VERSION, 12)


class FichaSegunElCaso(unittest.TestCase):
    def test_agua_y_tormenta_usan_la_ficha_de_su_respuesta_y_su_gravedad(self):
        for ronda, nombre in ((1, "agua"), (2, "tormenta")):
            for caso in (CASOS[ronda], VARIANTES[nombre]):
                with self.subTest(caso=nombre, correcta=caso[3]):
                    p = partida()
                    m = resolver_copa(p, ronda, caso)
                    esperada = POR_RESPUESTA[nombre][caso[3]]
                    guardado = guardados(m)[nombre]
                    self.assertEqual(guardado.gravedad, esperada["gravedad"])
                    self.assertEqual(guardado.datos["tipo"], esperada["tipo"])
                    self.assertEqual(guardado.datos["ley"], esperada["ley"])
                    self.assertEqual(m.resultado["cita_corta"], esperada["cita_corta"])
                    self.assertIs(m.resultado["con_delito"], esperada["con_delito"])

    def test_la_conducta_de_ayuda_nombra_a_la_persona_sorteada(self):
        vistas = set()
        for semilla in range(40):
            p = partida(semilla)
            m = resolver_copa(p, 3, p.mision.casos[3], "corregir")
            persona = m.sorteo.persona
            vistas.add(persona)
            self.assertIn(f"falsamente a {persona} ", m.resultado["conducta"])
            self.assertNotIn("{persona}", json.dumps(guardados(m)["ayuda"].datos, ensure_ascii=False))
        self.assertEqual(vistas, {"Mira", "Kael", "Luma", "Naira"})

    def test_cada_resolucion_trae_los_campos_legales(self):
        m = resolver_copa(partida(), 0, CASOS[0], "corregir")
        campos = {"norma", "pena", "cita_corta", "conducta", "nota", "con_delito"}
        self.assertLessEqual(campos, set(m.resultado))
        self.assertLessEqual(campos, set(ficha_campos := modulo.campos_legales(ficha_resuelta("presente_foto"))))
        self.assertEqual(ficha_campos["cita_corta"], SIMPLES["presente_foto"]["cita_corta"])

    def test_ninguna_ficha_deja_culpables_a_kael_ni_a_mira(self):
        fichas = [SIMPLES[c] for c in SIMPLES] + [AGUA_DESCARTAR, ALERTA, TORMENTA_DESCARTAR]
        for ficha in fichas:
            for persona in ("Kael", "Mira"):
                texto = ficha["conducta"].replace("{persona}", persona)
                if persona in texto:
                    self.assertTrue("falsamente" in texto or "sin pruebas" in texto, texto)


class Cita(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        from interfaz.partida_multijugador import VistaPartida
        self.Vista = VistaPartida
        self.p = partida_con_mapa()
        self.v = VistaPartida("a", {"mundo": self.p.estado("a")})
        self.v.narrador.decir = mock.Mock()
        self.lienzo = pygame.Surface((960, 720))
        self.v.actualizar(.01, mock.Mock())

    def llegar(self):
        self.v.recibir({"mundo": self.p.estado("a")})
        self.v.actualizar(.01, mock.Mock())
        self.v.aviso_legal.dibujar(self.lienzo)

    def test_sale_una_vez_por_evento_y_se_narra(self):
        resolver_copa(self.p, 0, CASOS[0], "corregir")
        self.llegar()
        aviso = self.v.aviso_legal
        self.assertIsNotNone(aviso.imagen)
        self.assertEqual(self.v.narrador.decir.call_count, 1)
        self.assertIn("Injuria, art. 220 CP", self.v.narrador.decir.call_args[0][0])
        aviso.hasta = 0  # terminó: un mensaje repetido no lo vuelve a abrir
        self.llegar()
        self.llegar()
        self.assertIsNone(aviso.imagen)
        self.assertEqual(self.v.narrador.decir.call_count, 1)

    def test_al_reconectar_no_se_repite(self):
        resolver_copa(self.p, 0, CASOS[0], "corregir")
        nueva = self.Vista("a", {"mundo": self.p.estado("a")})
        nueva.narrador.decir = mock.Mock()
        for _ in range(3):
            nueva.actualizar(.01, mock.Mock())
            nueva.aviso_legal.dibujar(self.lienzo)
        self.assertIsNone(nueva.aviso_legal.imagen)
        nueva.narrador.decir.assert_not_called()

    def test_dura_entre_cuatro_y_cinco_segundos_y_no_tapa_el_centro(self):
        from interfaz.aviso_legal import DURACION
        self.assertTrue(4 <= DURACION <= 5)
        resolver_copa(self.p, 0, CASOS[0], "corregir")
        self.llegar()
        rect = self.v.aviso_legal.imagen.get_rect(midtop=(480, 12))
        self.assertLess(rect.bottom, 200)
        self.assertLessEqual(rect.width, 920)

    def test_frases_segun_el_resultado(self):
        from interfaz.aviso_legal import frase_legal
        self.assertEqual(frase_legal(True, True), "Caso documentado. El responsable responde ante la ley.")
        self.assertEqual(frase_legal(True, False), "El daño siguió. La conducta sigue siendo sancionable.")
        self.assertEqual(frase_legal(False, True), "Verificar y avisar protege a la aldea.")
        self.assertEqual(frase_legal(False, False), "La alerta era real: callarla también hace daño.")

    def test_dos_resoluciones_seguidas_no_se_pierden(self):
        aviso = self.v.aviso_legal
        aviso.agregar({"cita_corta": "Uno", "con_delito": True, "correcto": True})
        aviso.agregar({"cita_corta": "Dos", "con_delito": False, "correcto": False})
        aviso.dibujar(self.lienzo)
        aviso.hasta = 0
        aviso.dibujar(self.lienzo)
        self.assertEqual(self.v.narrador.decir.call_count, 2)


class ExpedienteEInforme(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)

    def fichas(self):
        for caso in LOS_OCHO:
            yield caso, ficha_resuelta(caso, "descartar" if caso in POR_RESPUESTA else None, "Naira")

    def test_el_detalle_muestra_conducta_ley_sancion_y_nota_sin_salirse(self):
        from interfaz import expediente as tarjeta
        from interfaz.partida_multijugador import VistaPartida
        v = VistaPartida("a", {"mundo": partida_con_mapa().estado("a")})
        for caso, ficha in self.fichas():
            libro = ExpedientePartida()
            prueba = [{"id": "p", "titulo": "Prueba", "texto": "Texto"}]
            libro.registrar(caso, "Título", {"opcion": "corregir", "correcto": True, "evento_id": 1}, prueba, ficha)
            v.estado["mundo"]["caso"]["expediente"] = libro.publico()
            escritos, original = [], v.panel.texto_lineas

            def anotar(superficie, texto, x, y, *resto, **extra):
                fin = original(superficie, texto, x, y, *resto, **extra)
                escritos.append((texto, fin))
                return fin

            with mock.patch.object(v.panel, "texto_lineas", anotar):
                tarjeta.dibujar(v.panel, pygame.Surface((960, 720)))
            textos = {t: fin for t, fin in escritos}
            for campo in ("conducta", "ley", "sancion", "nota"):
                if ficha[campo]:
                    self.assertIn(ficha[campo], textos, caso)
                    self.assertLessEqual(textos[ficha[campo]], 484, (caso, campo))  # antes del botón

    def test_el_informe_exportado_trae_ley_y_sancion_de_los_ocho(self):
        from interfaz.informe_final import exportar
        m = partida().mision
        for orden, (caso, ficha) in enumerate(self.fichas()):
            m.expediente.registrar(caso, "Título " + caso, {"opcion": "corregir", "correcto": True, "evento_id": orden}, [], ficha)
        informe = m.informe()
        self.assertTrue(all(f["norma"] and f["pena"] for f in informe["casos"]))
        with tempfile.TemporaryDirectory() as carpeta:
            texto = Path(exportar(informe, Path(carpeta))).read_text(encoding="utf-8")
        for _, ficha in self.fichas():
            self.assertIn("Norma: " + ficha["ley"], texto)
            self.assertIn("Pena: " + ficha["sancion"], texto)

    def test_el_informe_no_adelanta_la_ficha_de_un_caso_sin_resolver(self):
        filas = {f["id"]: f for f in partida().mision.informe()["casos"]}
        self.assertFalse(filas["agua"]["resuelto"])
        self.assertIsNone(filas["agua"]["norma"])


class ColaDelCliente(unittest.TestCase):
    def cliente(self):
        c = ClienteInternet.__new__(ClienteInternet)
        c.eventos = queue.Queue(maxsize=3)
        c._cerrado = threading.Event()
        c._ronda = 0
        return c

    def test_una_carga_larga_descarta_el_estado_viejo_sin_cerrar(self):
        c = self.cliente()
        for numero in range(6):
            c._evento({"tipo": "estado", "n": numero})
        self.assertFalse(c._cerrado.is_set())
        self.assertEqual([e["n"] for e in c.eventos.queue], [3, 4, 5])

    def test_no_descarta_otros_eventos(self):
        c = self.cliente()
        c._evento({"tipo": "acuse", "n": 0})
        for numero in range(1, 6):
            c._evento({"tipo": "estado", "n": numero})
        self.assertEqual(c.eventos.queue[0]["n"], 0)
        self.assertFalse(c._cerrado.is_set())


class DialogosPorDimension(unittest.TestCase):
    COPA = r"\b(Kael|Luma|Tarek|Odran|Naira|Darek|Mira(?! primero))\b|\baldea\b|Mensajero de antes|antiguo Mensajero"
    PRESENTE = r"\b(Darío|Ronaldo|Tomás|Lía|Mateo|Elías)\b"
    FUTUROS = ("Archivista", "Representante Humano", "Corredor de Datos", "Ciudadano Conectado")

    def test_el_presente_y_el_futuro_no_hablan_de_la_copa(self):
        for nombre, lineas in TESTIMONIOS_PRESENTE.items():
            for linea in lineas:
                self.assertIsNone(re.search(self.COPA, linea), (nombre, linea))

    def test_las_pistas_del_presente_tampoco(self):
        for evento in EVENTOS:
            for pista in evento["pistas"]:
                self.assertIsNone(re.search(self.COPA, pista[4]), pista[0])

    def test_el_futuro_no_habla_del_presente(self):
        for nombre in self.FUTUROS:
            for linea in TESTIMONIOS_PRESENTE[nombre]:
                self.assertIsNone(re.search(self.PRESENTE, linea), (nombre, linea))

    def test_la_copa_no_habla_de_las_otras_eras(self):
        for categoria, personajes in TESTIMONIOS.items():
            for nombre, lineas in personajes.items():
                for linea in (lineas if isinstance(lineas, tuple) else (lineas,)):
                    self.assertIsNone(re.search(self.PRESENTE + r"|NÚCLEO", linea), (categoria, nombre, linea))


if __name__ == "__main__":
    unittest.main()
