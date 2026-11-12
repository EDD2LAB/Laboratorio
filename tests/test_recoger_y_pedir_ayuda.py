"""Encargo: recoger un objeto junto a un personaje, verlo resaltado y pedir ayuda a un bot."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

from multijugador.mision import MENSAJES, ORDENES_ECO, TODOS  # noqa: E402
from multijugador.partida_local import ClienteCampanaLocal  # noqa: E402


def a_preparacion(mision):
    mision.resultado = {"opcion": "corregir", "correcto": True, "texto": ""}
    assert mision.fase == "preparacion"


class Base(unittest.TestCase):
    def setUp(self):
        self.cliente = ClienteCampanaLocal("Prueba", "habitante", semilla=72)
        self.addCleanup(self.cliente.cerrar)
        self.partida = self.cliente._partida
        self.mision = self.partida.mision
        self.bots = set(self.cliente._bots.bots)
        a_preparacion(self.mision)

    def ultimo_estado(self):
        estado = None
        while not self.cliente.eventos.empty():
            evento = self.cliente.eventos.get_nowait()
            if "mundo" in evento:
                estado = evento
        return estado

    def avanzar_hasta(self, condicion, descripcion, limite=900):
        for _ in range(limite):
            if condicion():
                return
            self.cliente.actualizar(0.15)
        self.fail("No ocurrió: " + descripcion)


class RecogerJuntoAPersonaje(Base):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((960, 720))

    def vista_junto_a_la_cuerda(self):
        from interfaz.partida_multijugador import VistaPartida
        fuente = self.mision.encargo.fuente("cuerdas")  # archivo de Mira: hay un personaje al lado
        self.partida.jugadores["local"].update(x=fuente["x"] + 10, y=fuente["y"])
        self.cliente.actualizar(0.01)
        vista = VistaPartida("local", self.ultimo_estado())
        vista.panel.modo = None
        return vista, fuente

    def test_la_e_ofrece_recoger_aunque_haya_un_personaje_al_lado(self):
        vista, fuente = self.vista_junto_a_la_cuerda()
        opciones = vista.candidatos()
        recoger = next((o for o in opciones if o["id"] == fuente["id"]), None)
        self.assertIsNotNone(recoger, [o["id"] for o in opciones])
        self.assertEqual(recoger["nombre"], "Recoger Cuerda")
        self.assertEqual(opciones[0]["id"], fuente["id"])  # va antes que hablar con el personaje

    def test_el_objeto_elegido_se_resalta_en_dorado(self):
        vista, fuente = self.vista_junto_a_la_cuerda()
        objetivo = vista._calcular_resaltado()
        self.assertEqual((objetivo["tipo"], objetivo["clave"]), ("material", "cuerdas"))
        vista.dibujar(pygame.display.get_surface(), "LOCAL")
        self.assertTrue(vista._resaltado_hecho)

    def test_pulsar_e_recoge_el_objeto(self):
        vista, fuente = self.vista_junto_a_la_cuerda()
        evento = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, mod=0, unicode="e", scancode=0)
        vista.manejar_evento(evento, (0, 0), self.cliente)
        self.assertEqual(self.mision.encargo.cargas.get("local"), "cuerdas")


class PedirAyuda(Base):
    def test_pedir_ayuda_hace_que_un_bot_meta_un_objeto(self):
        self.cliente.actuar("pedir_ayuda")
        self.avanzar_hasta(lambda: self.mision.encargo.entregados, "un bot mete un objeto en el cesto")
        self.cliente.actualizar(0.15)
        self.assertEqual(len(self.mision.encargo.entregados), 1)  # uno por pedido
        self.assertTrue(set(self.mision.encargo.entregados.values()) <= self.bots)
        for _ in range(200):
            self.cliente.actualizar(0.15)
        self.assertEqual(len(self.mision.encargo.entregados), 1)  # sin pedir más, no siguen

    def test_el_eco_a_todos_lo_atiende_un_solo_bot(self):
        eco = next(o for o in self.mision.objetivos if o["tipo"] == "eco")
        self.partida.jugadores["local"].update(x=eco["x"], y=eco["y"])
        self.cliente.actuar("eco", mensaje=ORDENES_ECO.index("encargo"), destinatario=TODOS)
        self.avanzar_hasta(lambda: self.mision.encargo.entregados, "un bot mete un objeto en el cesto")
        for _ in range(200):
            self.cliente.actualizar(0.15)
        self.assertEqual(len(self.mision.encargo.entregados), 1)

    def test_la_guia_ofrece_el_boton_de_ayuda(self):
        self.assertTrue(self.mision.privado("local")["guia"].get("ayuda"))

    def test_hay_un_mensaje_por_orden(self):
        self.assertEqual(len(MENSAJES), len(ORDENES_ECO))


if __name__ == "__main__":
    unittest.main()


class BanderasDeObras(unittest.TestCase):
    def test_cada_obra_terminada_deja_su_bandera_en_su_sitio(self):
        pygame.init()
        from interfaz.suministros import dibujar_encargos
        from multijugador.suministros import ENCARGOS, EncargoSuministros
        mision = ClienteCampanaLocal("Prueba", "guardian", semilla=72)._partida.mision
        sitios = [EncargoSuministros(r, mision.objetivos).publico()["sitio"] for r in range(len(ENCARGOS))]
        self.assertEqual([s["id"] for s in sitios], ["puente_1", "testigo", "archivo"])
        obras = [EncargoSuministros(r, mision.objetivos).publico() for r in range(len(ENCARGOS))]
        superficie = pygame.Surface((960, 720))
        dibujar_encargos(superficie, {"obras": obras, "encargo": None}, pygame.font.Font(None, 16))
        for sitio in sitios:  # el asta dorada de cada bandera
            with self.subTest(sitio=sitio["id"]):
                self.assertEqual(tuple(superficie.get_at((sitio["x"] - 22, sitio["y"] - 20)))[:3], (225, 189, 105))
