"""Los tres casos de contenido manipulado de Distrito Conecta."""
import json
import os
import unittest
import uuid
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from bots.gestor_bots import GestorBots  # noqa: E402
from multijugador.dimensiones_red import LA_COPA, PRESENTE  # noqa: E402
from multijugador.movimiento import PartidaMovimiento  # noqa: E402
from multijugador.presente import EVENTOS, MARCAS  # noqa: E402
from multijugador.protocolo import ROLES  # noqa: E402
from nucleo.rutas import RAIZ  # noqa: E402

PROCESADO = RAIZ / "Imagenes" / "Manipulado" / "procesado"
# Un punto de cada marca, en el orden del JSON.
PUNTOS = {
    "presente_video": [{"frame": 0}, {"frame": 5}, {"frame": 6}, {"frame": 7}],
    "presente_voz": [{"segundo": 2.3}, {"zona": "saturacion"}, {"segundo": 3}],
    "presente_foto": [{"x": .1, "y": .1}, {"x": .9, "y": .3}, {"x": .5, "y": .2}, {"x": .2, "y": .71}, {"x": .5, "y": .45}],
}
CORRECTAS = {"presente_video": "Contenido manipulado", "presente_voz": "Suplantación", "presente_foto": "Suplantación"}


def partida(humanos=1, bots=False):
    jugadores = [dict(id=str(i), nombre="J" + str(i), rol=ROLES[i]) for i in range(humanos)]
    if bots:
        jugadores += [dict(id="bot_" + r, nombre=r, rol=r, controlador="bot") for r in ROLES[humanos:]]
    p = PartidaMovimiento(jugadores, 0)
    p.colisiones_de(PRESENTE)
    p._viajar_equipo(LA_COPA, PRESENTE)
    p.actualizar(.05)
    return p


def accion(p, i, nombre, **datos):
    return p.actuar(i, dict(accion=nombre, id_solicitud=uuid.uuid4().hex, ronda=p.mision.ronda, **datos), p.ultima)


def reunir_pistas(p, i="0"):
    for npc in [n for n in p.mision.dialogos.publico() if n["dimension"] == "presente" and n.get("pista")]:
        p.jugadores[i].update(x=npc["x"], y=npc["y"], interior=npc.get("interior"))
        assert accion(p, i, "hablar_npc", npc=npc["id"])["ok"]
    p.jugadores[i]["interior"] = None


def votar(p, i="0", opcion="verificar"):
    pantalla = p.mision.presente.pantalla
    p.jugadores[i].update(x=pantalla["x"], y=pantalla["y"])
    return accion(p, i, "presente_votar", opcion=opcion)


def resolver_caso(p, marcas=None):
    m = p.mision.presente
    evento = m.evento["id"]
    reunir_pistas(p)
    assert accion(p, "0", "presente_analizar")["ok"]
    for punto in PUNTOS[evento][:marcas or m.evento["minimo"]]:
        assert accion(p, "0", "presente_marcar", **punto)["ok"]
    assert votar(p)["ok"]
    assert accion(p, "0", "presente_clasificar", categoria=CORRECTAS[evento])["ok"]


class Material(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((64, 64))
        self.addCleanup(pygame.quit)

    def test_procesados_con_transparencia_y_videos_iguales(self):
        for nombre in ("foto_original", "foto_manipulada", "video_original", "video_manipulado"):
            imagen = pygame.image.load(str(PROCESADO / (nombre + ".png")))
            self.assertTrue(imagen.get_flags() & pygame.SRCALPHA, nombre)
        for nombre in ("video_original", "video_manipulado"):
            imagen = pygame.image.load(str(PROCESADO / (nombre + ".png"))).convert_alpha()
            self.assertEqual(imagen.get_size(), (296 * 8, 288), nombre)
            self.assertEqual(imagen.get_at((0, 0)).a, 0, nombre)

    def test_las_marcas_caen_dentro_de_su_imagen_o_duracion(self):
        for marca in MARCAS["foto_manipulada"]["marcas"]:
            x, y, ancho, alto = marca["rect"]
            self.assertTrue(0 <= x and x + ancho <= 1 and 0 <= y and y + alto <= 1, marca["id"])
        for marca in MARCAS["video_manipulado"]["marcas"]:
            self.assertTrue(all(0 <= f < 8 for f in marca["frames"]), marca["id"])
        for marca in MARCAS["audio_suplantado"]["marcas"]:
            if "rango" in marca:
                self.assertTrue(0 <= marca["rango"][0] < marca["rango"][1] <= MARCAS["audio_suplantado"]["duracion"], marca["id"])

    def test_el_json_es_el_que_usa_el_servidor(self):
        datos = json.loads((RAIZ / "datos" / "marcas_manipulacion.json").read_text(encoding="utf-8"))
        self.assertEqual(datos, MARCAS)


class Analisis(unittest.TestCase):
    def setUp(self):
        self.p = partida()
        self.m = self.p.mision.presente

    def test_rechaza_marcar_sin_abrir_el_analisis(self):
        reunir_pistas(self.p)
        self.assertFalse(accion(self.p, "0", "presente_marcar", frame=0)["ok"])

    def test_rechaza_analizar_sin_la_pista_del_original(self):
        self.assertFalse(accion(self.p, "0", "presente_analizar")["ok"])

    def test_rechaza_marcar_fuera_de_la_dimension(self):
        reunir_pistas(self.p)
        accion(self.p, "0", "presente_analizar")
        self.p.jugadores["0"]["dimension"] = LA_COPA
        self.assertFalse(accion(self.p, "0", "presente_marcar", frame=0)["ok"])
        self.assertEqual(self.m.marcas, {})

    def test_no_duplica_marcas(self):
        reunir_pistas(self.p)
        accion(self.p, "0", "presente_analizar")
        accion(self.p, "0", "presente_marcar", frame=0)
        accion(self.p, "0", "presente_marcar", frame=3)  # la misma marca (cuadros 0 a 4)
        self.assertEqual(list(self.m.marcas), ["orden_invertido"])

    def test_concluye_con_el_minimo_y_no_antes(self):
        for minimo in (2, 2, 3):
            evento = self.m.evento
            self.assertEqual(evento["minimo"], minimo)
            reunir_pistas(self.p)
            accion(self.p, "0", "presente_analizar")
            for punto in PUNTOS[evento["id"]][:minimo - 1]:
                accion(self.p, "0", "presente_marcar", **punto)
            self.assertFalse(self.m.concluido, evento["id"])
            self.assertEqual(self.m.publico({"0"})["etiqueta"], "sin_fuente")
            accion(self.p, "0", "presente_marcar", **PUNTOS[evento["id"]][minimo - 1])
            self.assertTrue(self.m.concluido, evento["id"])
            self.assertEqual(self.m.publico({"0"})["etiqueta"], evento["etiqueta"])
            if evento["id"] != "presente_foto":
                votar(self.p)
                accion(self.p, "0", "presente_clasificar", categoria=CORRECTAS[evento["id"]])
                accion(self.p, "0", "presente_siguiente")

    def test_marcar_lejos_de_toda_marca_no_cuenta(self):
        self.m.indice = 2
        reunir_pistas(self.p)
        accion(self.p, "0", "presente_analizar")
        self.assertTrue(accion(self.p, "0", "presente_marcar", x=.2, y=.95)["ok"])
        self.assertEqual(self.m.marcas, {})

    def test_la_conclusion_tiene_un_solo_id(self):
        reunir_pistas(self.p)
        accion(self.p, "0", "presente_analizar")
        accion(self.p, "0", "presente_marcar", frame=0)
        accion(self.p, "0", "presente_marcar", frame=5)
        primera = self.m.conclusion_id
        self.assertIsNotNone(primera)
        accion(self.p, "0", "presente_marcar", frame=6)
        self.assertEqual(self.m.conclusion_id, primera)

    def test_decidir_sin_concluir_se_permite_pero_es_mala_decision(self):
        reunir_pistas(self.p)
        self.assertTrue(votar(self.p)["ok"])
        self.assertTrue(self.m.completada)
        self.assertFalse(self.m.resultado["correcto"])
        self.assertLess(self.m.resultado["efectos"]["confianza"], 0)


class Campana(unittest.TestCase):
    def test_la_nota_de_voz_se_desbloquea_al_resolver_el_video(self):
        p = partida()
        m = p.mision.presente
        self.assertEqual(m.evento["id"], "presente_video")
        self.assertFalse(accion(p, "0", "presente_siguiente")["ok"])
        resolver_caso(p)
        self.assertEqual(m.evento["id"], "presente_video")
        accion(p, "0", "presente_siguiente")
        p.actualizar(p.ultima + .05)
        self.assertEqual(m.evento["id"], "presente_voz")
        self.assertEqual([n["pista"] for n in m.npcs if n.get("pista")], ["audio_original"])
        self.assertEqual(m.publico({"0"})["analisis"]["halladas"], [])

    def test_cada_evento_guarda_su_caso_en_el_expediente(self):
        p = partida()
        m = p.mision.presente
        for numero, evento in enumerate(EVENTOS):
            resolver_caso(p)
            if numero < len(EVENTOS) - 1:
                self.assertTrue(accion(p, "0", "presente_siguiente")["ok"])
        self.assertTrue(m.fin)
        expediente = p.mision.expediente
        casos = {c.id: c for c in list(expediente.arbol.casos.values()) + expediente.pendientes}
        self.assertEqual({c: casos[c].gravedad for c in casos}, {"presente_video": 6, "presente_voz": 6, "presente_foto": 7})
        for caso in casos.values():  # las leyes las agrega después el equipo
            self.assertIsNone(caso.datos["ley"])
            self.assertIsNone(caso.datos["sancion"])

    def test_con_bots_que_ayudan_a_marcar_el_caso_llega_al_expediente(self):
        p = partida(1, bots=True)
        gestor = GestorBots(p, {"0"})
        m = p.mision.presente
        reunir_pistas(p)
        original = p.actuar
        vistas = []
        p.actuar = lambda i, s, a: vistas.append((i, s["accion"])) or original(i, s, a)
        ahora = p.ultima
        for _ in range(400):
            ahora += .15
            p.actualizar(ahora)
            gestor.actualizar(ahora, .15)
            if m.marcas:
                break
        self.assertTrue(any(i.startswith("bot_") and a == "presente_marcar" for i, a in vistas), vistas[-5:])
        self.assertEqual(len(m.marcas), 1)  # la última marca queda para las personas
        p.actuar = original
        accion(p, "0", "presente_analizar")
        punto = next(q for q in PUNTOS["presente_video"] if q["frame"] != next(
            f for mk in MARCAS["video_manipulado"]["marcas"] if mk["id"] in m.marcas for f in mk["frames"][:1]))
        accion(p, "0", "presente_marcar", **punto)
        self.assertTrue(m.concluido)
        self.assertTrue(votar(p)["ok"])
        expediente = p.mision.expediente
        self.assertIn("presente_video", {c.id for c in list(expediente.arbol.casos.values()) + expediente.pendientes})


class Pantallas(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        from interfaz.partida_multijugador import VistaPartida
        self.p = partida()
        self.vista = VistaPartida("0", {"mundo": self.p.estado("0")})
        self.vista._cargar_dimension(PRESENTE)
        self.vista.dimension = PRESENTE
        self.panel = self.vista.panel

    def refrescar(self):
        self.vista.estado["mundo"] = self.p.estado("0")

    def test_el_sello_sale_una_vez_por_evento(self):
        ui = self.vista.celular.ui
        self.assertTrue(ui.lanzar_conclusion(41, "manipulado"))
        self.assertFalse(ui.lanzar_conclusion(41, "manipulado"))
        self.assertTrue(ui.lanzar_conclusion(42, "suplantacion"))
        self.assertTrue(ui.sellos["suplantacion"])

    def test_el_material_real_llega_a_las_pantallas(self):
        ui = self.vista.celular.ui
        self.assertEqual(len(ui.video_original), 8)
        self.assertEqual(ui.video_original[0].get_size(), ui.video_manipulado[0].get_size())
        self.assertAlmostEqual(ui.audios["original"].duracion, 4.47, 1)
        self.assertEqual(ui.audios["suplantado"].pico, 32768)
        self.assertLess(ui.audios["original"].pico, 32768)

    def test_el_comparador_avanza_y_marca_el_cuadro_visible(self):
        from interfaz.analisis_manipulado import tecla
        reunir_pistas(self.p)
        self.refrescar()
        cliente = mock.Mock()
        self.panel.modo = "analizar"
        ui = self.vista.celular.ui
        ui.video.ir_a(4)
        self.assertTrue(tecla(self.panel, pygame.K_RIGHT, cliente))
        self.assertEqual(ui.video.frame(), 5)
        tecla(self.panel, pygame.K_e, cliente)
        cliente.actuar.assert_called_once_with("presente_marcar", frame=5)

    def test_la_lupa_envia_coordenadas_normalizadas(self):
        from interfaz.analisis_manipulado import FOTO_MANIPULADA, accion as accion_ui
        cliente = mock.Mock()
        accion_ui(self.panel, "analisis:foto", (FOTO_MANIPULADA.x + 136, FOTO_MANIPULADA.y + 68), cliente)
        cliente.actuar.assert_called_once_with("presente_marcar", x=.5, y=.25)

    def test_cada_caso_se_dibuja_con_su_analisis(self):
        lienzo = pygame.Surface((960, 720))
        m = self.p.mision.presente
        for numero, evento in enumerate(EVENTOS):
            resolver_caso(self.p, marcas=len(PUNTOS[evento["id"]]))
            self.refrescar()
            for modo in ("analizar", "introduccion", "resultado", "caldero"):
                self.panel.modo = modo
                self.panel.dibujar(lienzo)
            if numero < len(EVENTOS) - 1:
                accion(self.p, "0", "presente_siguiente")
        self.assertTrue(m.fin)


if __name__ == "__main__":
    unittest.main()
