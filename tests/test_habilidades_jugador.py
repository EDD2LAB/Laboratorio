import unittest

from logica.habilidades_jugador import HabilidadJugador


class HabilidadJugadorTests(unittest.TestCase):
    def test_guardian_impulse_has_a_timed_boost_and_cooldown(self):
        habilidad = HabilidadJugador("guardian")
        self.assertTrue(habilidad.activar())
        self.assertEqual(habilidad.multiplicador_movimiento, 2.2)
        self.assertFalse(habilidad.disponible)
        self.assertFalse(habilidad.activar())

        habilidad.actualizar(850)
        self.assertEqual(habilidad.multiplicador_movimiento, 1.0)
        habilidad.actualizar(5150)
        self.assertTrue(habilidad.disponible)

    def test_journalist_public_communication_is_single_use(self):
        habilidad = HabilidadJugador("periodista")
        self.assertTrue(habilidad.disponible)
        self.assertTrue(habilidad.activar())
        self.assertFalse(habilidad.disponible)
        habilidad.actualizar(60000)
        self.assertFalse(habilidad.disponible)

    def test_unknown_character_does_not_get_a_silent_fallback(self):
        with self.assertRaises(ValueError):
            HabilidadJugador("personaje_desconocido")


if __name__ == "__main__":
    unittest.main()
