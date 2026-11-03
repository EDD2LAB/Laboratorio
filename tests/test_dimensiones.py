import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from dimensiones import (
    DIMENSION_FUTURO,
    DIMENSION_LA_COPA,
    DIMENSION_PRESENTE,
    GestorDimensiones,
)
from juego import (
    cargar_mapa_presente,
    cargar_mapa_principal,
    crear_mundo,
    mover_jugador,
    posicion_mundo_a_pantalla,
    posicion_pantalla_a_mundo,
    actualizar_camara_mundo,
)
from logica_juego import EstadoJuego


class GestorDimensionesTests(unittest.TestCase):
    def test_transition_is_serializable_and_only_runs_once(self):
        gestor = GestorDimensiones()
        self.assertNotIn(DIMENSION_PRESENTE, gestor.desbloqueadas)
        with self.assertRaises(ValueError):
            gestor.iniciar_transicion(DIMENSION_FUTURO)

        gestor.desbloquear_dimension(DIMENSION_PRESENTE)
        evento = gestor.iniciar_transicion(DIMENSION_PRESENTE)
        self.assertEqual(evento, {
            "tipo": "cambio_dimension",
            "origen": DIMENSION_LA_COPA,
            "destino": DIMENSION_PRESENTE,
            "spawn": "spawn_presente",
        })
        self.assertIsNone(gestor.iniciar_transicion(DIMENSION_PRESENTE))
        gestor.activar_dimension(DIMENSION_PRESENTE)

        self.assertTrue(gestor.transicion_presente_realizada)
        self.assertEqual(gestor.dimension_anterior, DIMENSION_LA_COPA)
        self.assertIsNone(gestor.iniciar_transicion(DIMENSION_PRESENTE))

    def test_present_mission_keeps_shared_progress(self):
        estado = EstadoJuego()
        estado.indicadores["sabiduria"] = 63
        estado.gestor_dimensiones.desbloquear_dimension(DIMENSION_PRESENTE)
        estado.gestor_dimensiones.iniciar_transicion(DIMENSION_PRESENTE)
        estado.gestor_dimensiones.activar_dimension(DIMENSION_PRESENTE)
        estado.iniciar_mision_presente()

        estado.resolver_mision_presente("revisar_fuente")
        estado.resolver_mision_presente("comparar_evidencia")
        estado.registrar_pista_presente("respuesta_kael")
        estado.resolver_mision_presente("verificar")

        self.assertEqual(estado.indicadores["sabiduria"], 68)
        self.assertEqual(estado.indicadores["confianza_consejo"], 53)
        self.assertEqual(estado.mision_presente["estado"], "completada")
        self.assertIn("fuente_ausente", estado.historial_evidencias)
        self.assertIn("publicacion_aspirante", estado.mensajes_verificados)
        self.assertTrue(estado.progreso_dimensiones[DIMENSION_PRESENTE]["completada"])
        self.assertEqual(estado.dimension_actual, DIMENSION_PRESENTE)

    def test_present_verification_requires_source_context_and_kael_response(self):
        estado = EstadoJuego()
        estado.gestor_dimensiones.desbloquear_dimension(DIMENSION_PRESENTE)
        estado.gestor_dimensiones.iniciar_transicion(DIMENSION_PRESENTE)
        estado.gestor_dimensiones.activar_dimension(DIMENSION_PRESENTE)
        estado.iniciar_mision_presente()

        self.assertFalse(estado.resolver_mision_presente("verificar"))
        self.assertEqual(estado.mision_presente["estado"], "activa")
        for pista in estado.PISTAS_PARA_VERIFICAR:
            estado.registrar_pista_presente(pista)
        self.assertTrue(estado.resolver_mision_presente("verificar"))

    def test_present_map_loads_without_authored_hitboxes(self):
        pygame.display.init()
        pygame.display.set_mode((1, 1))
        try:
            config = GestorDimensiones().obtener_configuracion(DIMENSION_PRESENTE)
            recursos = cargar_mapa_presente(config)
            recursos["dimension"] = DIMENSION_PRESENTE
            mundo = crear_mundo(recursos)
            jugador = mundo["jugador"]
            posicion_inicial = jugador["pies"].center

            class TeclasDerecha:
                def __getitem__(self, tecla):
                    return tecla in (pygame.K_d, pygame.K_RIGHT)

            mover_jugador(jugador, mundo, TeclasDerecha(), 100)
        finally:
            pygame.quit()

        self.assertIsNotNone(recursos)
        self.assertEqual(recursos["mapa"].get_size(), (960, 720))
        proporcion_original = 998 / 576
        proporcion_escalada = (
            recursos["rect_mapa"].width / recursos["rect_mapa"].height
        )
        self.assertAlmostEqual(proporcion_escalada, proporcion_original, places=2)
        self.assertEqual(len(recursos["hitboxes"]), 1)
        self.assertEqual(len(recursos["interacciones"]), 1)
        self.assertEqual(
            recursos["interacciones"][0]["accion"],
            "examinar_publicacion",
        )
        self.assertEqual(jugador["id"], "periodista")
        self.assertEqual(mundo["habilidad"].personaje, "periodista")
        self.assertGreater(mundo["camara"]["zoom"], 1)
        self.assertLess(960 / mundo["camara"]["zoom"], 960)
        actualizar_camara_mundo(mundo, 10000)
        posicion_jugador_pantalla = posicion_mundo_a_pantalla(
            jugador["pies"].center,
            mundo,
        )
        self.assertAlmostEqual(posicion_jugador_pantalla[0], 480, delta=1)
        self.assertAlmostEqual(posicion_jugador_pantalla[1], 360, delta=1)
        posicion_mouse = (260, 410)
        posicion_mundo = posicion_pantalla_a_mundo(posicion_mouse, mundo)
        posicion_mouse_reconvertida = posicion_mundo_a_pantalla(
            posicion_mundo,
            mundo,
        )
        self.assertAlmostEqual(
            posicion_mouse_reconvertida[0],
            posicion_mouse[0],
            delta=1,
        )
        self.assertAlmostEqual(
            posicion_mouse_reconvertida[1],
            posicion_mouse[1],
            delta=1,
        )
        jugador["pies"].x += 40
        x_camara_anterior = mundo["camara"]["x"]
        actualizar_camara_mundo(mundo, 10000)
        self.assertAlmostEqual(
            posicion_mundo_a_pantalla(jugador["pies"].center, mundo)[0],
            480,
            delta=1,
        )
        self.assertGreater(mundo["camara"]["x"], x_camara_anterior)
        self.assertEqual(len(recursos["decoraciones"]), 5)
        self.assertEqual(
            {actor["personaje"] for actor in mundo["personajes"]},
            {
                "Agente de verificación",
                "Kael (aspirante a alcalde)",
                "Habitante conectada",
                "Influencer",
                "Mensajero urbano",
            },
        )
        self.assertEqual(recursos["spawn_dimension"], (480, 620))
        self.assertEqual(posicion_inicial, (480, 620))
        self.assertGreater(jugador["pies"].centerx, posicion_inicial[0])

    def test_copa_still_uses_its_original_map_and_hitboxes(self):
        pygame.display.init()
        pygame.display.set_mode((1, 1))
        try:
            mapa, decoraciones, interacciones, hitboxes, guardian, mapas_dia = (
                cargar_mapa_principal()
            )
            recursos = {
                "mapa": mapa,
                "mapas_dia": mapas_dia,
                "decoraciones": decoraciones,
                "interacciones": interacciones,
                "hitboxes": hitboxes,
                "guardian": guardian,
                "dimension": DIMENSION_LA_COPA,
            }
            mundo = crear_mundo(recursos)
        finally:
            pygame.quit()

        self.assertEqual(len(mapas_dia), 3)
        self.assertTrue(hitboxes)
        self.assertTrue(mundo["hitboxes"])
        self.assertEqual(mundo["dimension"], DIMENSION_LA_COPA)
        self.assertEqual(mundo["habilidad"].personaje, "guardian")
        self.assertIsNone(mundo["camara"])


if __name__ == "__main__":
    unittest.main()
