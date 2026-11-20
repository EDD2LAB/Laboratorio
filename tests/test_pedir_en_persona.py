"""E sobre un compañero, bots que se quedan en su zona y la flecha hacia el final."""
import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

from multijugador.dimensiones_red import FUTURO, LA_COPA, PRESENTE  # noqa: E402
from multijugador.mision import MENSAJES  # noqa: E402
from multijugador.partida_local import ClienteCampanaLocal  # noqa: E402
from interfaz.orientacion import AVISO_FINAL, tarea_actual, tres_eras_completas  # noqa: E402

TAREK = "bot_habitante"


def ultimo_acuse(cliente):
    return [e for e in list(cliente.eventos.queue) if e.get("tipo") == "acuse"][-1]


class PedirEnPersona(unittest.TestCase):
    def preparar(self, era):
        self.cliente = ClienteCampanaLocal("Prueba", "guardian", semilla=3, era=era)
        self.partida = self.cliente._partida
        self.yo = self.partida.jugadores["local"]
        tarek = self.partida.jugadores[TAREK]
        tarek["interior"] = None
        self.yo.update(x=tarek["x"] + 30, y=tarek["y"], interior=None)

    def test_e_sobre_un_companero_abre_el_menu_en_las_tres_eras(self):
        for era in (LA_COPA, PRESENTE, FUTURO):
            self.preparar(era)
            self.cliente.actuar("interactuar", objetivo="jugador:" + TAREK)
            acuse = ultimo_acuse(self.cliente)
            self.assertTrue(acuse["ok"], (era, acuse))
            self.assertEqual((acuse["vista"], acuse["destinatario"]), ("compartir", TAREK))

    def test_se_le_pide_lo_mismo_que_por_un_tronco_sin_tronco(self):
        for era in (LA_COPA, PRESENTE, FUTURO):
            self.preparar(era)
            self.cliente._ahora += 3
            self.cliente.actuar("eco", mensaje=0, destinatario=TAREK)
            self.assertTrue(ultimo_acuse(self.cliente)["ok"], era)
            avisos = [a for a in self.partida.mision.privado(TAREK)["avisos"] if a["tipo"] == "eco"]
            self.assertIn(MENSAJES[0], avisos[-1]["texto"])

    def test_lejos_del_companero_y_del_tronco_se_rechaza(self):
        self.preparar(LA_COPA)
        self.yo.update(x=self.yo["x"] + 300)
        self.cliente._ahora += 3
        self.cliente.actuar("eco", mensaje=0, destinatario=TAREK)
        self.assertFalse(ultimo_acuse(self.cliente)["ok"])


class BotsEnSuZona(unittest.TestCase):
    def test_ningun_bot_sigue_a_la_persona_en_ninguna_era(self):
        for era in (LA_COPA, PRESENTE, FUTURO):
            cliente = ClienteCampanaLocal("Prueba", "guardian", semilla=3, era=era)
            p = cliente._partida
            for _ in range(200):
                cliente.actualizar(.15)
            antes = {i: (p.jugadores[i]["x"], p.jugadores[i]["y"]) for i in cliente._bots.bots}
            cliente.mover(1, 0)
            for _ in range(40):
                cliente.actualizar(.15)
            for i, (x, y) in antes.items():
                self.assertLess(math.hypot(p.jugadores[i]["x"] - x, p.jugadores[i]["y"] - y), 1, (era, i))

    def test_si_se_lo_pides_acude_y_luego_vuelve_a_su_zona(self):
        cliente = ClienteCampanaLocal("Prueba", "guardian", semilla=3)
        p = cliente._partida
        for _ in range(200):
            cliente.actualizar(.15)
        yo, tarek = p.jugadores["local"], p.jugadores[TAREK]
        zona = (tarek["x"], tarek["y"])
        yo.update(x=tarek["x"] + 30, y=tarek["y"])
        cliente._ahora += 3
        cliente.actuar("eco", mensaje=0, destinatario=TAREK)
        mensajero = p.jugadores["bot_mensajero"]
        yo.update(x=mensajero["x"], y=mensajero["y"] + 40)  # se aleja: el bot va hasta allí
        cercania = []
        for _ in range(200):
            cliente.actualizar(.15)
            cercania.append(math.hypot(tarek["x"] - yo["x"], tarek["y"] - yo["y"]))
        self.assertLessEqual(min(cercania), 60)
        self.assertLess(math.hypot(tarek["x"] - zona[0], tarek["y"] - zona[1]), 45)


class VistaFalsa:
    def __init__(self, dimension, caso):
        self.dimension, self.interior = dimension, None
        self.estado = {"mundo": {"caso": caso}}

    def rect_portal(self):
        return pygame.Rect(100, 100, 40, 60)


class FlechaAlFinal(unittest.TestCase):
    LISTO = {"fase": "final", "presente": {"fin": True}, "futuro": {"desafio_final": {"fase": "preparacion"}}}

    def test_solo_cuando_las_tres_eras_terminaron(self):
        self.assertTrue(tres_eras_completas(VistaFalsa(LA_COPA, self.LISTO)))
        self.assertFalse(tres_eras_completas(VistaFalsa(LA_COPA, dict(self.LISTO, presente={"fin": False}))))
        self.assertFalse(tres_eras_completas(VistaFalsa(LA_COPA, dict(self.LISTO, fase="investigacion"))))

    def test_desde_otra_era_la_flecha_va_al_portal(self):
        for era in (LA_COPA, PRESENTE):
            tarea = tarea_actual(VistaFalsa(era, self.LISTO))
            self.assertEqual(tarea["objetivo"]["id"], "portal")
            self.assertTrue(tarea["titulo"].startswith(AVISO_FINAL))


if __name__ == "__main__":
    unittest.main()
