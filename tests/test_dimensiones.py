import contextlib
import io
import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from logica.dimensiones import (
    DIMENSION_FUTURO,
    DIMENSION_LA_COPA,
    DIMENSION_PRESENTE,
    EDIFICIOS_PRESENTE,
    GestorDimensiones,
)
from mundo.camara import (
    actualizar_camara_mundo,
    dibujar_escena_con_camara,
    posicion_mundo_a_pantalla,
    posicion_pantalla_a_mundo,
)
from mundo.colisiones import jugador_bloqueado
from mundo.creacion import crear_mundo
from mundo.grafo_aldea import buscar_ruta_transmision
from mundo.jugador import mover_jugador
from mundo.mapas import cargar_mapa_edificio, cargar_mapa_presente, cargar_mapa_principal
from mundo.npcs import actualizar_npcs_presentes
from mundo.personajes import cargar_personaje_periodista
from nucleo.config import ESCENA_DIALOGO, ESCENA_MAPA
from nucleo.recursos import cargar_spritesheet_frames
from un_jugador.codice import construir_contenido_codice
from un_jugador.hud import (
    celular_disponible,
    controles_hud,
    instrucciones_dimension,
    objetivo_mision_actual,
    rect_controles_hud,
    texto_tutorial_primer_evento,
)
from un_jugador.tablilla import iniciar_animacion_decision
from un_jugador.ventana import rect_lienzo_en_ventana
from logica.logica_juego import EstadoJuego
from logica.conversaciones import construir_conversacion
from logica.grafo_fisico import GrafoFisico


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

    def test_dimension_instructions_only_offer_phone_in_the_present(self):
        estado = EstadoJuego()
        self.assertFalse(celular_disponible(estado))
        _, instrucciones_pasado = instrucciones_dimension(DIMENSION_LA_COPA)
        self.assertFalse(any("celular" in linea.lower() or "C abre" in linea for linea in instrucciones_pasado))

        estado.dimension_actual = DIMENSION_PRESENTE
        self.assertTrue(celular_disponible(estado))
        _, instrucciones_presente = instrucciones_dimension(DIMENSION_PRESENTE)
        self.assertTrue(any("C abre el celular" in linea for linea in instrucciones_presente))

    def test_journal_shows_bridge_quest_clues_and_full_character_continuity(self):
        estado = EstadoJuego()
        mundo = {
            "reparacion_puentes": SimpleNamespace(
                estado="MATERIALS_PENDING",
                materiales_recogidos={"tablas"},
            )
        }
        misiones = construir_contenido_codice(estado, mundo, 0)
        self.assertTrue(any("Reconstruir el Puente Norte" in linea for linea in misiones))
        self.assertTrue(any("1/3 materiales" in linea for linea in misiones))

        estado.dimension_actual = DIMENSION_PRESENTE
        estado.iniciar_mision_presente()
        estado.registrar_pista_presente("fuente_ausente")
        informacion = construir_contenido_codice(
            estado,
            {"reparacion_puentes": None},
            1,
        )
        self.assertTrue(any("✓" in linea and "archivo original" in linea for linea in informacion))
        self.assertTrue(any("○" in linea for linea in informacion))

        continuidad = construir_contenido_codice(estado, {}, 2)
        for nombre in (
            "Elías Vega",
            "Ronaldo Vélez",
            "Darío Veraz",
            "Mateo Ríos",
            "Lía Nova",
            "Tomás Red",
        ):
            self.assertTrue(any(nombre in linea for linea in continuidad))

    def test_journal_secondary_selection_points_to_bridge_materials_then_bridge(self):
        estado = EstadoJuego()
        tablas = pygame.Rect(30, 40, 20, 20)
        puente = pygame.Rect(300, 400, 40, 40)
        reparacion = SimpleNamespace(
            estado="MATERIALS_PENDING",
            MATERIALES=("tablas", "cuerda", "herramientas"),
            PLATAFORMAS_MATERIALES={
                "plataforma_noreste": "tablas",
                "plataforma_suroeste": "cuerda",
                "plataforma_sureste": "herramientas",
            },
            materiales_recogidos=set(),
        )
        mundo = {
            "dimension": DIMENSION_LA_COPA,
            "reparacion_puentes": reparacion,
            "interacciones": [
                {
                    "accion": "recolectar_material",
                    "material": "tablas",
                    "rect": tablas,
                    "activo": True,
                },
                {
                    "accion": "reparar_puente",
                    "rect": puente,
                    "activo": True,
                },
            ],
        }
        self.assertIsNone(objetivo_mision_actual(estado, mundo, set()))
        self.assertEqual(
            objetivo_mision_actual(estado, mundo, set(), "secundaria"),
            (tablas.center, "Recoger tablas"),
        )

        reparacion.materiales_recogidos.update(reparacion.MATERIALES)
        reparacion.estado = "READY_TO_REPAIR"
        self.assertEqual(
            objetivo_mision_actual(estado, mundo, set(), "secundaria"),
            (puente.center, "Reconstruir Puente Norte"),
        )
        reparacion.estado = "REPAIRED"
        self.assertIsNone(
            objetivo_mision_actual(estado, mundo, set(), "secundaria")
        )

    def test_building_interior_objective_points_to_its_exit(self):
        estado = EstadoJuego()
        salida = pygame.Rect(300, 400, 40, 30)
        objetivo = objetivo_mision_actual(
            estado,
            {
                "edificio_interior": "centro_verificacion",
                "interacciones": [{
                    "accion": "salir_edificio",
                    "rect": salida,
                    "activo": True,
                }],
            },
            set(),
        )
        self.assertEqual(objetivo, (salida.center, "Salir del edificio"))

    def test_hud_key_labels_show_phone_only_in_present_dimension(self):
        estado = EstadoJuego()
        controles_pasado = dict(controles_hud(estado))
        self.assertNotIn("C", controles_pasado)
        self.assertIn("J", controles_pasado)
        self.assertIn("E", controles_pasado)
        hud = SimpleNamespace(objetivos={nombre: 0 for nombre in range(5)})
        self.assertEqual(rect_controles_hud(hud, estado).top, 283)

        estado.dimension_actual = DIMENSION_PRESENTE
        self.assertEqual(dict(controles_hud(estado))["C"], "Celular")

    def test_present_characters_only_talk_about_their_own_era(self):
        estado = EstadoJuego()
        for nombre, antepasado in (
            ("Darío Veraz", "Odran"),
            ("Ronaldo Vélez", "Kael"),
            ("Tomás Red", "Tarek"),
            ("Lía Nova", "Luma"),
            ("Mateo Ríos", "Mensajero de antes"),
        ):
            dialogo, _ = construir_conversacion(nombre, estado, set())
            self.assertNotIn(antepasado, dialogo["texto"])

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

    def test_present_image_classification_requires_evidence_and_changes_indicators(self):
        estado = EstadoJuego()
        estado.dimension_actual = DIMENSION_PRESENTE
        estado.iniciar_mision_presente()
        self.assertFalse(estado.resolver_mision_presente("clasificar_ia"))
        self.assertIsNone(estado.mision_presente["clasificacion"])

        for pista in estado.PISTAS_PARA_VERIFICAR:
            estado.registrar_pista_presente(pista)
        self.assertTrue(estado.resolver_mision_presente("clasificar_ia"))

        self.assertEqual(estado.mision_presente["clasificacion"], "generada_por_ia")
        self.assertTrue(estado.mision_presente["clasificacion_correcta"])
        self.assertEqual(estado.indicadores["sabiduria"], 58)
        self.assertEqual(estado.indicadores["confianza_consejo"], 53)
        self.assertEqual(estado.indicadores["desinformación"], 0)

        estado_error = EstadoJuego()
        estado_error.dimension_actual = DIMENSION_PRESENTE
        estado_error.iniciar_mision_presente()
        for pista in estado_error.PISTAS_PARA_VERIFICAR:
            estado_error.registrar_pista_presente(pista)
        self.assertTrue(estado_error.resolver_mision_presente("clasificar_real"))
        self.assertFalse(estado_error.mision_presente["clasificacion_correcta"])
        self.assertEqual(estado_error.indicadores["sabiduria"], 44)
        self.assertEqual(estado_error.indicadores["desinformación"], 6)

    def test_objective_arrow_only_marks_clear_destinations(self):
        estado = EstadoJuego()
        caldero = pygame.Rect(470, 340, 20, 20)
        portal = pygame.Rect(880, 270, 70, 100)
        mundo = {
            "dimension": DIMENSION_LA_COPA,
            "interacciones": [
                {"accion": "tablilla", "rect": caldero},
                {
                    "accion": "portal_temporal",
                    "rect": portal,
                    "activo": False,
                },
            ],
        }
        self.assertIsNone(objetivo_mision_actual(estado, mundo, set()))
        self.assertEqual(
            objetivo_mision_actual(estado, mundo, {"Kael"}),
            (caldero.center, "Caldero central"),
        )

        estado.terminado = True
        mundo["interacciones"][1]["activo"] = True
        self.assertEqual(
            objetivo_mision_actual(estado, mundo, set()),
            (portal.center, "Portal al presente"),
        )

        estado.dimension_actual = DIMENSION_PRESENTE
        estado.iniciar_mision_presente()
        pantalla = pygame.Rect(250, 300, 30, 30)
        mundo_presente = {
            "dimension": DIMENSION_PRESENTE,
            "interacciones": [{
                "accion": "examinar_publicacion",
                "rect": pantalla,
            }],
            "personajes": [],
        }
        self.assertEqual(
            objetivo_mision_actual(estado, mundo_presente, set()),
            (pantalla.center, "Publicación digital"),
        )
        estado.mision_presente["publicacion_examinada"] = True
        self.assertIsNone(objetivo_mision_actual(estado, mundo_presente, set()))
        for pista in estado.PISTAS_PARA_VERIFICAR:
            estado.registrar_pista_presente(pista)
        self.assertEqual(
            objetivo_mision_actual(estado, mundo_presente, set()),
            (pantalla.center, "Clasificar la publicación"),
        )

    def test_present_walking_sprite_rows_follow_requested_directions(self):
        pygame.display.init()
        pygame.display.set_mode((1, 1))
        try:
            personaje = cargar_personaje_periodista()
            for direccion, fila in (
                ("abajo", 2),
                ("derecha", 3),
                ("arriba", 4),
                ("izquierda", 5),
            ):
                frames_esperados = cargar_spritesheet_frames(
                    os.path.join(
                        "NPCS",
                        "NPC Mundo2",
                        f"NPC2-mundo2-Fila{fila}.png",
                    ),
                    8,
                )
                frame_esperado = pygame.transform.scale(
                    frames_esperados[0],
                    personaje["tamano"],
                )
                self.assertEqual(
                    pygame.image.tobytes(
                        personaje["frames_caminar"][direccion][0],
                        "RGBA",
                    ),
                    pygame.image.tobytes(frame_esperado, "RGBA"),
                )
        finally:
            pygame.quit()

    def test_potion_animation_has_separate_throw_splash_and_effect_phases(self):
        animacion = iniciar_animacion_decision("Quemar")
        self.assertGreater(animacion["duracion_lanzamiento"], 0)
        self.assertGreater(animacion["duracion_splash"], 0)
        self.assertEqual(
            animacion["duracion"],
            animacion["duracion_lanzamiento"]
            + animacion["duracion_splash"]
            + animacion["duracion_efecto"],
        )

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
        self.assertGreaterEqual(len(recursos["hitboxes"]), 35)
        interacciones_activas = [
            objeto for objeto in recursos["interacciones"]
            if objeto.get("activo", True)
        ]
        self.assertEqual(len(interacciones_activas), 8)
        entradas = [
            objeto for objeto in interacciones_activas
            if objeto["accion"] == "entrar_edificio"
        ]
        self.assertEqual(len(entradas), len(EDIFICIOS_PRESENTE))
        self.assertEqual(
            {objeto["edificio_id"] for objeto in entradas},
            set(EDIFICIOS_PRESENTE),
        )
        self.assertTrue(all(objeto["activo"] for objeto in entradas))
        self.assertTrue(any(
            objeto["accion"] == "examinar_publicacion"
            for objeto in recursos["interacciones"]
        ))
        for edificio_id, edificio in EDIFICIOS_PRESENTE.items():
            rx, ry = edificio["spawn_exterior"]
            spawn_puerta = pygame.Rect(0, 0, 12, 8)
            spawn_puerta.center = (
                recursos["rect_mapa"].x + round(rx * recursos["rect_mapa"].width),
                recursos["rect_mapa"].y + round(ry * recursos["rect_mapa"].height),
            )
            self.assertFalse(
                jugador_bloqueado(spawn_puerta, mundo),
                f"El spawn exterior de {edificio_id} debe quedar accesible.",
            )
            entrada = next(
                objeto for objeto in entradas
                if objeto["edificio_id"] == edificio_id
            )
            self.assertLess(
                pygame.Vector2(spawn_puerta.center).distance_to(entrada["rect"].center),
                58,
                f"El spawn exterior de {edificio_id} debe permitir pulsar E.",
            )
        self.assertEqual(jugador["id"], "periodista")
        self.assertEqual(jugador["rect"].size, (22, 30))
        self.assertEqual(jugador["rect"].midbottom, jugador["pies"].midbottom)
        self.assertTrue(jugador["frames_idle"]["abajo"])
        self.assertFalse(jugador["frames_hablar"])
        self.assertFalse(jugador["frames_eco"])
        self.assertEqual(jugador["nombre"], "Elías Vega")
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
            tamanos_npc["Ronaldo Vélez"],
            (24, 28),
        )
        self.assertEqual(tamanos_npc["Mateo Ríos"], (24, 28))
        self.assertEqual(tamanos_npc["Darío Veraz"], (29, 33))
        self.assertEqual(tamanos_npc["Tomás Red"], (29, 33))
        self.assertEqual(tamanos_npc["Lía Nova"], (29, 33))
        self.assertEqual(
            {actor["personaje"] for actor in mundo["personajes"]},
            {
                "Darío Veraz",
                "Ronaldo Vélez",
                "Tomás Red",
                "Lía Nova",
                "Mateo Ríos",
            },
        )
        self.assertEqual(recursos["spawn_dimension"], (480, 620))
        self.assertEqual(posicion_inicial, (480, 620))
        self.assertGreater(jugador["pies"].centerx, posicion_inicial[0])

    def test_present_building_interiors_load_editable_exit_hitboxes_and_spawn(self):
        pygame.display.init()
        pygame.display.set_mode((1, 1))
        try:
            for edificio_id in EDIFICIOS_PRESENTE:
                with self.subTest(edificio=edificio_id):
                    recursos = cargar_mapa_edificio(edificio_id)
                    recursos["jugador_presente"] = cargar_personaje_periodista()
                    salidas = [
                        objeto for objeto in recursos["interacciones"]
                        if objeto["accion"] == "salir_edificio"
                    ]
                    self.assertEqual(len(salidas), 1)
                    self.assertTrue(recursos["rect_mapa"].collidepoint(
                        recursos["spawn_dimension"]
                    ))
                    self.assertTrue(any(
                        hitbox.get("role") == "wall"
                        for hitbox in recursos["hitboxes"]
                    ))
                    recursos["dimension"] = DIMENSION_PRESENTE
                    mundo = crear_mundo(recursos)
                    self.assertFalse(
                        jugador_bloqueado(mundo["jugador"]["pies"], mundo),
                        f"El spawn interior de {edificio_id} debe quedar accesible.",
                    )
                    rect_salida = salidas[0]["rect"]
                    punto_cercano_salida = (
                        max(rect_salida.left, min(
                            mundo["jugador"]["pies"].centerx,
                            rect_salida.right,
                        )),
                        max(rect_salida.top, min(
                            mundo["jugador"]["pies"].centery,
                            rect_salida.bottom,
                        )),
                    )
                    self.assertLess(
                        pygame.Vector2(
                            mundo["jugador"]["pies"].center
                        ).distance_to(punto_cercano_salida),
                        58,
                        f"La salida de {edificio_id} debe quedar al alcance.",
                    )
        finally:
            pygame.quit()

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
        portal = next(
            interaccion for interaccion in interacciones
            if interaccion.get("accion") == "portal_temporal"
        )
        self.assertFalse(portal["activo"])
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
