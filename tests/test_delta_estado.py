"""El estado por diferencias reconstruye exactamente lo mismo que un snapshot."""
import json
import unittest
import uuid

from multijugador.delta import CodificadorEstado, DecodificadorEstado, aplicar, diferencia, exponer, preparar
from multijugador.dimensiones_red import LA_COPA, PRESENTE
from multijugador.movimiento import PartidaMovimiento
from multijugador.protocolo import ROLES


def partida(cantidad=4):
    return PartidaMovimiento([dict(id=str(i), nombre="J" + str(i), rol=ROLES[i]) for i in range(cantidad)], 0)


def estado(p, i):
    return {"tipo": "estado", "revision": 1, "fase": "partida", "mundo": p.estado(i)}


def mover(p, i, paso):
    p.recibir(i, {"dx": 1 if paso % 20 < 10 else -1, "dy": 0, "seq": paso, "correr": False}, p.ultima)
    p.actualizar(p.ultima + .05)


class Diferencias(unittest.TestCase):
    def test_aplicar_reconstruye(self):
        antes = {"a": 1, "b": {"c": 2, "d": [1]}, "e": 5}
        despues = {"a": 1, "b": {"c": 3, "d": [1, 2]}, "f": {"g": 1}}
        self.assertEqual(aplicar(antes, diferencia(antes, despues)), despues)

    def test_lo_que_no_cambia_no_viaja(self):
        self.assertEqual(diferencia({"a": {"b": 1}}, {"a": {"b": 1}}), {})

    def test_aplicar_no_modifica_el_estado_anterior(self):
        antes = {"a": {"b": 1}}
        aplicar(antes, {"a": {"b": 2}})
        self.assertEqual(antes, {"a": {"b": 1}})


class Reconstruccion(unittest.TestCase):
    def test_los_deltas_dan_el_mismo_estado_que_un_snapshot(self):
        p = partida()
        cod, dec = CodificadorEstado("0"), DecodificadorEstado()
        for paso in range(120):
            mover(p, "0", paso)
            mensaje = json.loads(json.dumps(cod.codificar(estado(p, "0"))))
            recibido = dec.recibir(mensaje)
            esperado, _ = preparar(estado(p, "0"), "0")
            self.assertEqual({k: v for k, v in recibido.items() if k != "seq"}, {k: v for k, v in exponer(esperado).items() if k != "seq"}, paso)

    def test_los_deltas_ocupan_mucho_menos(self):
        p = partida()
        cod = CodificadorEstado("0")
        snapshot = len(json.dumps(cod.codificar(estado(p, "0"))))
        mover(p, "0", 1)
        self.assertLess(len(json.dumps(cod.codificar(estado(p, "0")))), snapshot / 10)


class Snapshots(unittest.TestCase):
    def test_primer_mensaje_es_snapshot(self):
        mensaje = CodificadorEstado("0").codificar(estado(partida(), "0"))
        self.assertEqual(mensaje["tipo"], "estado")
        self.assertIsInstance(mensaje["mundo"]["jugadores"], list)

    def test_quien_se_une_tarde_o_reconecta_queda_igual_que_los_demas(self):
        p = partida()
        cod, dec = CodificadorEstado("0"), DecodificadorEstado()
        for paso in range(30):
            mover(p, "0", paso)
            dec.recibir(cod.codificar(estado(p, "0")))
        continuo = dec.recibir(cod.codificar(estado(p, "0")))
        tarde = DecodificadorEstado().recibir(CodificadorEstado("0").codificar(estado(p, "0")))
        self.assertEqual({k: v for k, v in continuo.items() if k != "seq"}, {k: v for k, v in tarde.items() if k != "seq"})

    def test_cambiar_de_dimension_envia_snapshot(self):
        p = partida()
        cod = CodificadorEstado("0")
        cod.codificar(estado(p, "0"))
        p._viajar_equipo(LA_COPA, PRESENTE)
        self.assertEqual(cod.codificar(estado(p, "0"))["tipo"], "estado")

    def test_entrar_a_un_edificio_envia_snapshot(self):
        p = partida()
        p._viajar_equipo(LA_COPA, PRESENTE)
        cod = CodificadorEstado("0")
        cod.codificar(estado(p, "0"))
        puerta = p.mision.presente.edificios["sede_aspirante"]
        p.jugadores["0"].update(x=float(puerta["x"]), y=float(puerta["y"]))
        p.actuar("0", dict(accion="entrar_edificio", edificio="sede_aspirante", id_solicitud=uuid.uuid4().hex, ronda=0), p.ultima)
        self.assertEqual(cod.codificar(estado(p, "0"))["tipo"], "estado")

    def test_una_base_perdida_pide_snapshot_una_sola_vez(self):
        p = partida()
        cod, dec = CodificadorEstado("0"), DecodificadorEstado()
        dec.recibir(cod.codificar(estado(p, "0")))
        mover(p, "0", 1)
        cod.codificar(estado(p, "0"))  # este delta se pierde
        mover(p, "0", 2)
        self.assertIsNone(dec.recibir(cod.codificar(estado(p, "0"))))
        self.assertTrue(dec.tomar_peticion())
        self.assertFalse(dec.tomar_peticion())
        cod.forzar_snapshot = True
        mover(p, "0", 3)
        self.assertIsNotNone(dec.recibir(cod.codificar(estado(p, "0"))))


class Interes(unittest.TestCase):
    def test_de_otra_dimension_solo_llega_lo_minimo(self):
        p = partida(2)
        p.jugadores["1"]["dimension"] = PRESENTE
        forma, lugar = preparar(estado(p, "0"), "0")
        self.assertEqual(lugar, (LA_COPA, None))
        self.assertIn("x", forma["mundo"]["jugadores"]["0"])
        self.assertNotIn("x", forma["mundo"]["jugadores"]["1"])

    def test_de_otro_edificio_solo_llega_lo_minimo(self):
        p = partida(2)
        p._viajar_equipo(LA_COPA, PRESENTE)
        p.jugadores["1"]["interior"] = "sede_aspirante"
        forma, _ = preparar(estado(p, "0"), "0")
        self.assertNotIn("x", forma["mundo"]["jugadores"]["1"])

    def test_la_mision_de_otra_era_llega_resumida(self):
        forma, _ = preparar(estado(partida(2), "0"), "0")
        self.assertNotIn("objetivos", forma["mundo"]["caso"]["futuro"])
        self.assertIn("fin", forma["mundo"]["caso"]["futuro"])
        self.assertIn("objetivos", forma["mundo"]["caso"])

    def test_posiciones_enteras(self):
        p = partida(1)
        p.jugadores["0"].update(x=100.6, y=200.4)
        forma, _ = preparar(estado(p, "0"), "0")
        self.assertEqual((forma["mundo"]["jugadores"]["0"]["x"], forma["mundo"]["jugadores"]["0"]["y"]), (101, 200))


if __name__ == "__main__":
    unittest.main()
