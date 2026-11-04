import contextlib
import io
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
    ESCENA_DIALOGO,
    ESCENA_MAPA,
    cargar_mapa_presente,
    cargar_mapa_principal,
    crear_mundo,
    dibujar_escena_con_camara,
    mover_jugador,
    posicion_mundo_a_pantalla,
    posicion_pantalla_a_mundo,
    rect_lienzo_en_ventana,
    actualizar_camara_mundo,
    actualizar_npcs_presentes,
    buscar_ruta_transmision,
    texto_tutorial_primer_evento,
)
from logica_juego import EstadoJuego
from conversaciones import construir_conversacion
from grafo_fisico import GrafoFisico


class GestorDimensionesTests(unittest.TestCase):
    def test_decision_transmission_without_open_route_does_not_raise(self):
        grafo = GrafoFisico(
            [
                {"id": "plataforma_a", "posicion": [0.2, 0.5]},
                {"id": "plataforma_b", "posicion": [0.8, 0.5]},
            ],
            [{
                "id": "puente_a_b",
                "origen": "plataforma_a",
                "destino": "plataforma_b",
                "estado": "bloqueado",
            }],
        )

        with contextlib.redirect_stdout(io.StringIO()):
            ruta = buscar_ruta_transmision(
                grafo,
                "plataforma_a",
                "plataforma_b",
            )

        self.assertIsNone(ruta)
        self.assertEqual(
            buscar_ruta_transmision(grafo, "plataforma_a", "plataforma_a"),
            (["plataforma_a"], []),
        )

    def test_first_event_tutorial_explains_talk_then_review_the_tablet(self):
        estado = EstadoJuego()
        mundo = {"dimension": DIMENSION_LA_COPA}

        texto_inicial = texto_tutorial_primer_evento(estado, mundo, set())
        self.assertIn("PRIMER EVENTO", texto_inicial)
        self.assertIn("Habla con alguien", texto_inicial)

        dialogo, clave = construir_conversacion("Kael", estado, set())
        self.assertIn("Caldero central", dialogo["texto"])
        texto_despues_de_hablar = texto_tutorial_primer_evento(
            estado,
            mundo,
            {clave},
        )
        self.assertIn("ve al Caldero central", texto_despues_de_hablar)

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
        self.assertEqual(jugador["rect"].size, (22, 30))
        self.assertEqual(jugador["rect"].midbottom, jugador["pies"].midbottom)
        self.assertTrue(jugador["frames_idle"]["abajo"])
        self.assertFalse(jugador["frames_hablar"])
        self.assertFalse(jugador["frames_eco"])
        self.assertEqual(mundo["habilidad"].personaje, "periodista")
        self.assertGreater(mundo["camara"]["zoom"], 1)
        self.assertLess(960 / mundo["camara"]["zoom"], 960)
        actualizar_camara_mundo(mundo, 10000)
        posicion_jugador_pantalla = posicion_mundo_a_pantalla(
            jugador["pies"].center,
            mundo,
        )
        self.assertGreater(posicion_jugador_pantalla[0], 325)
        self.assertLess(posicion_jugador_pantalla[0], 635)
        self.assertGreater(posicion_jugador_pantalla[1], 650)
        self.assertLess(posicion_jugador_pantalla[1], 720)
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
        actualizar_camara_mundo(mundo, 100)
        desplazamiento_camara = mundo["camara"]["x"] - x_camara_anterior
        self.assertGreater(desplazamiento_camara, 0)
        self.assertLess(desplazamiento_camara, 40)
        actualizar_camara_mundo(mundo, 1000)
        self.assertAlmostEqual(
            mundo["camara"]["x"],
            jugador["pies"].centerx - 960 / (2 * mundo["camara"]["zoom"]),
            delta=1,
        )
        self.assertEqual(mundo["camara"]["zoom"], 1.6)
        self.assertAlmostEqual(
            posicion_mundo_a_pantalla(jugador["pies"].center, mundo)[0],
            480,
            delta=1,
        )
        self.assertEqual(len(recursos["decoraciones"]), 5)
        self.assertTrue(
            all(
                objeto["hitbox"].width < objeto["rect"].width
                and objeto["hitbox"].height < objeto["rect"].height
                and objeto["hitbox"].midbottom == objeto["rect"].midbottom
                and objeto["frames_idle"]["abajo"].get_size()
                == objeto["rect"].size
                and objeto["frames_idle"]["abajo"]
                for objeto in recursos["decoraciones"]
            )
        )
        tamanos_npc = {
            objeto["personaje"]: objeto["rect"].size
            for objeto in recursos["decoraciones"]
        }
        self.assertEqual(
            tamanos_npc["Kael (aspirante a alcalde)"],
            (24, 28),
        )
        self.assertEqual(tamanos_npc["Mensajero urbano"], (24, 28))
        self.assertEqual(tamanos_npc["Agente de verificación"], (29, 33))
        self.assertEqual(tamanos_npc["Habitante conectada"], (29, 33))
        self.assertEqual(tamanos_npc["Influencer"], (29, 33))
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

    def test_mover_jugador_handles_partial_key_maps(self):
        pygame.display.init()
        pygame.display.set_mode((1, 1))
        try:
            config = GestorDimensiones().obtener_configuracion(DIMENSION_PRESENTE)
            recursos = cargar_mapa_presente(config)
            recursos["dimension"] = DIMENSION_PRESENTE
            mundo = crear_mundo(recursos)
            jugador = mundo["jugador"]

            mover_jugador(jugador, mundo, {pygame.K_d: True}, 100)
            self.assertGreater(jugador["posicion_x"], 0)
            self.assertEqual(jugador["direccion"], "derecha")
        finally:
            pygame.quit()

    def test_present_npcs_follow_routes_and_pause_during_dialogue(self):
        pygame.display.init()
        pygame.display.set_mode((1, 1))
        try:
            config = GestorDimensiones().obtener_configuracion(DIMENSION_PRESENTE)
            recursos = cargar_mapa_presente(config)
            recursos["dimension"] = DIMENSION_PRESENTE
            mundo = crear_mundo(recursos)
            mundo["escena_actual"] = ESCENA_MAPA
            patrullas = [
                actor for actor in mundo["personajes"]
                if actor.get("objeto", {}).get("ruta_npc")
            ]
            self.assertEqual(len(patrullas), 5)
            patrones = set()
            for actor in patrullas:
                objeto = actor["objeto"]
                ruta = objeto["ruta_npc"]
                patrones.add(ruta["pattern"])
                self.assertEqual(
                    objeto["rect"].midbottom,
                    ruta["points"][0],
                )
                for punto in ruta["points"]:
                    hitbox_ruta = objeto["hitbox"].copy()
                    hitbox_ruta.midbottom = punto
                    self.assertTrue(mundo["rect_mapa"].contains(hitbox_ruta))
                ancho_ruta = max(p[0] for p in ruta["points"]) - min(
                    p[0] for p in ruta["points"]
                )
                alto_ruta = max(p[1] for p in ruta["points"]) - min(
                    p[1] for p in ruta["points"]
                )
                self.assertGreaterEqual(max(ancho_ruta, alto_ruta), 24)
                self.assertEqual(
                    set(objeto["frames_caminar"]),
                    {"abajo", "arriba", "izquierda", "derecha"},
                )
                self.assertTrue(
                    all(objeto["frames_caminar"].values())
                )
            self.assertEqual(patrones, {"loop", "ping_pong"})

            actor = patrullas[0]
            objeto = actor["objeto"]
            objeto["estado_ruta"] = "WALKING"
            objeto["tiempo_estado_ms"] = 0
            objeto["velocidad_ruta"] = 38
            posicion_inicial = (
                objeto["posicion_ruta_x"],
                objeto["posicion_ruta_y"],
            )
            actualizar_npcs_presentes(mundo, 100)
            posicion_despues = (
                objeto["posicion_ruta_x"],
                objeto["posicion_ruta_y"],
            )
            self.assertNotEqual(posicion_despues, posicion_inicial)
            self.assertAlmostEqual(
                pygame.Vector2(posicion_despues).distance_to(posicion_inicial),
                3.8,
                delta=0.1,
            )
            actualizar_npcs_presentes(mundo, 60)
            self.assertEqual(objeto["indice_frame"], 1)
            posicion_despues = (
                objeto["posicion_ruta_x"],
                objeto["posicion_ruta_y"],
            )
            self.assertEqual(actor["rect"].midbottom, objeto["hitbox"].midbottom)

            mundo["npc_en_dialogo"] = actor["personaje"]
            mundo["escena_actual"] = ESCENA_DIALOGO
            actualizar_npcs_presentes(mundo, 500)
            self.assertEqual(objeto["estado_ruta"], "INTERACTING")
            self.assertEqual(
                (objeto["posicion_ruta_x"], objeto["posicion_ruta_y"]),
                posicion_despues,
            )
            mundo["escena_actual"] = ESCENA_MAPA
            actualizar_npcs_presentes(mundo, 100)
            self.assertEqual(objeto["estado_ruta"], "WAITING")
            self.assertEqual(
                (objeto["posicion_ruta_x"], objeto["posicion_ruta_y"]),
                posicion_despues,
            )
        finally:
            pygame.quit()

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
        habitantes = {
            personaje["personaje"]: personaje["rect"].size
            for personaje in mundo["personajes"]
        }
        self.assertEqual(habitantes["Tarek"], habitantes["Kael"])

    def test_present_camera_clamps_to_map_edges_without_revealing_canvas(self):
        pygame.display.init()
        pygame.display.set_mode((1, 1))
        try:
            config = GestorDimensiones().obtener_configuracion(DIMENSION_PRESENTE)
            recursos = cargar_mapa_presente(config)
            recursos["dimension"] = DIMENSION_PRESENTE
            mundo = crear_mundo(recursos)
            rect_mapa = recursos["rect_mapa"]
            posiciones = (
                rect_mapa.topleft,
                rect_mapa.topright,
                rect_mapa.bottomleft,
                rect_mapa.bottomright,
            )
            for posicion in posiciones:
                mundo["jugador"]["pies"].center = posicion
                actualizar_camara_mundo(mundo, inmediata=True)
                camara = mundo["camara"]
                self.assertGreaterEqual(camara["x"], rect_mapa.left)
                self.assertLessEqual(
                    camara["x"] + 960 / camara["zoom"],
                    rect_mapa.right,
                )
                self.assertGreaterEqual(camara["y"], rect_mapa.top)
                self.assertLessEqual(
                    camara["y"] + 720 / camara["zoom"],
                    rect_mapa.bottom,
                )
                frame = pygame.Surface((960, 720))
                dibujar_escena_con_camara(frame, recursos["mapa"], mundo)
                for punto in ((0, 0), (959, 0), (0, 719), (959, 719)):
                    self.assertNotEqual(
                        frame.get_at(punto)[:3],
                        (18, 27, 38),
                    )
        finally:
            pygame.quit()

    def test_window_viewport_uses_all_available_resolution(self):
        for size in ((1280, 720), (1366, 768), (1600, 900), (1920, 1080)):
            viewport = rect_lienzo_en_ventana(size)
            self.assertEqual(viewport.topleft, (0, 0))
            self.assertEqual(viewport.size, size)


if __name__ == "__main__":
    unittest.main()
