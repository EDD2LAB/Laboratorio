"""La campaña con bots puede empezar directamente en cualquiera de las tres eras."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from multijugador.dimensiones_red import FUTURO, LA_COPA, PRESENTE
from multijugador.partida_local import ClienteCampanaLocal


class InicioPorEra(unittest.TestCase):
    def test_todo_el_equipo_empieza_en_la_era_elegida(self):
        for era in (LA_COPA, PRESENTE, FUTURO):
            cliente = ClienteCampanaLocal("Prueba", "guardian", semilla=7, era=era)
            for _ in range(120):  # los bots juegan unos segundos sin fallar
                cliente.actualizar(1 / 30)
            dimensiones = {j["dimension"] for j in cliente._partida.jugadores.values()}
            self.assertEqual(dimensiones, {era}, era)

    def test_era_desconocida(self):
        with self.assertRaises(ValueError):
            ClienteCampanaLocal("Prueba", "guardian", era="edad_media")


if __name__ == "__main__":
    unittest.main()
