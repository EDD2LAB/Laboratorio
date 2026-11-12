"""Vista previa del combate: simulación local y arranque sin pantalla."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from nucleo.rutas import RAIZ


class Simulacion(unittest.TestCase):
    def setUp(self):
        from herramientas.vista_combate import Simulador
        from multijugador.dimensiones_red import cargar_datos
        from multijugador.movimiento import ColisionesMapa
        self.colisiones = ColisionesMapa(cargar_datos("futuro"))
        self.sim = Simulador(self.colisiones)

    def test_personajes_empiezan_en_suelo_caminable(self):
        for jugador in self.sim.jugadores:
            self.assertFalse(self.colisiones.bloqueado(jugador["x"], jugador["y"]))

    def test_ciclo_aviso_rayo_pausa(self):
        self.sim.tanda()
        self.assertEqual(self.sim.turno, "aviso")
        self.sim.paso(3.1)
        self.assertEqual(self.sim.turno, "rayo")
        self.assertLess(self.sim.integridad, 3)  # nadie se movió: el rayo los alcanza
        self.sim.paso(.8)
        self.assertEqual(self.sim.turno, "recarga")
        self.assertEqual(self.sim.derribados, set())

    def test_fase_roja_tiene_dos_descargas(self):
        self.sim.cambiar_fase()
        self.sim.tanda()
        self.sim.paso(2.6)
        self.sim.paso(.8)
        self.assertEqual((self.sim.turno, self.sim.oleada), ("aviso", 2))

    def test_disparo_gasta_municion_y_destruye_en_dos(self):
        self.sim.nuevo_mini()
        self.sim.tanda()
        libre = lambda a, b: True
        self.assertTrue(self.sim.disparar(libre))
        self.sim.paso(.7)
        self.assertTrue(self.sim.disparar(libre))
        self.assertEqual((self.sim.minis, self.sim.municion), ([], 11))

    def test_estado_tiene_la_forma_del_servidor(self):
        estado = self.sim.estado()
        self.assertEqual(set(estado["batalla"]), {"fase", "turno", "segundos", "oleada", "blancos", "derribados"})
        self.assertIn("minis_activos", estado["aventura"])

    def test_preparacion_vuelve_al_combate(self):
        for _ in range(8):
            self.sim.preparacion()
        self.assertEqual((self.sim.fase, self.sim.fabricado), ("activo", True))


class Arranque(unittest.TestCase):
    def test_abre_dibuja_y_guarda_captura(self):
        with tempfile.TemporaryDirectory() as carpeta:
            captura = Path(carpeta) / "vista.png"
            entorno = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
            resultado = subprocess.run(
                [sys.executable, "-m", "herramientas.vista_combate", "--cuadros", "40", "--captura", str(captura)],
                cwd=RAIZ, env=entorno, capture_output=True, text=True, timeout=120)
            self.assertEqual(resultado.returncode, 0, resultado.stderr)
            self.assertTrue(captura.is_file())


if __name__ == "__main__":
    unittest.main()
