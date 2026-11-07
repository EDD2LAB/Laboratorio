import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from logica.grafo_fisico import GrafoFisico
from juego import (
    cargar_mapa_principal,
    cargar_spritesheet_frames,
    colision_hitbox_mapa,
    crear_grafo_fisico,
    jugador_bloqueado,
)
from mundo.reparacion_puentes import SistemaReparacionPuente


ROOT = os.path.dirname(os.path.dirname(__file__))


def cargar_imagen(ruta):
    return pygame.image.load(os.path.join(ROOT, "Imagenes", ruta)).convert_alpha()


def crear_sistema(puente=None, grafo=None):
    if puente is None:
        puente = {
            "id": "puente_1",
            "rect": pygame.Rect(300, 300, 120, 70),
            "imagen": pygame.Surface((120, 70), pygame.SRCALPHA),
        }
    if grafo is None:
        grafo = GrafoFisico(
            (
                {"id": "origen", "posicion": [0.2, 0.5]},
                {"id": "destino", "posicion": [0.8, 0.5]},
                {"id": "plataforma_noreste", "posicion": [0.8, 0.2]},
                {"id": "plataforma_suroeste", "posicion": [0.2, 0.7]},
                {"id": "plataforma_sureste", "posicion": [0.8, 0.7]},
            ),
            ({
                "id": "puente_1",
                "origen": "origen",
                "destino": "destino",
            },),
        )
    recursos = {
        "puente_danado": cargar_imagen(os.path.join("Puentes", "Puente1Roto.png")),
        "puente_reparado": cargar_imagen(os.path.join("Puentes", "Puente1.png")),
        "efecto_reparacion": cargar_spritesheet_frames(
            os.path.join("Animaciones", "Efectos", "EfectoReparacion.png"),
            8,
        ),
        "indicador_normal": cargar_imagen(
            os.path.join("Indicadores Puente", "Indicador.png")
        ),
        "indicador_acierto": cargar_imagen(
            os.path.join("Indicadores Puente", "IndicadorAcierto.png")
        ),
        "indicador_error": cargar_imagen(
            os.path.join("Indicadores Puente", "IndicadorError.png")
        ),
        "materiales_spritesheet": cargar_imagen(
            os.path.join("Herramientas", "HerramientasReparación.png")
        ),
    }
    return puente, grafo, SistemaReparacionPuente(puente, grafo, recursos)


def posicionar_aguja_en_zona(sistema):
    angulo = sistema._angulo_objetivo()
    periodo = sistema.configuracion["duracion_recorrido_ms"]
    sistema.tiempo_aguja_ms = (angulo + math.pi) / math.pi * periodo


class ReparacionPuentesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_materials_can_only_be_collected_once(self):
        _, _, sistema = crear_sistema()
        self.assertEqual(len(sistema.objetos), 3)
        self.assertEqual(
            {objeto["tipo"] for objeto in sistema.objetos},
            set(sistema.MATERIALES),
        )
        self.assertEqual(
            {objeto["plataforma"] for objeto in sistema.objetos},
            set(sistema.PLATAFORMAS_MATERIALES),
        )
        puente = sistema.grafo.puentes["puente_1"]
        self.assertNotIn(
            puente["origen"],
            {objeto["plataforma"] for objeto in sistema.objetos},
        )
        self.assertNotIn(
            puente["destino"],
            {objeto["plataforma"] for objeto in sistema.objetos},
        )
        self.assertTrue(
            all(
                objeto["imagen"] is not None
                and not sistema.hitbox_puente.colliderect(objeto["rect"])
                for objeto in sistema.objetos
            )
        )
        for objeto in sistema.objetos:
            posicion_plataforma = sistema.grafo.plataformas[
                objeto["plataforma"]
            ]["posicion"]
            desplazamiento = sistema.DESPLAZAMIENTOS_SUELO[
                objeto["plataforma"]
            ]
            self.assertEqual(
                objeto["rect"].midbottom,
                (
                    round(posicion_plataforma[0] * 960) + desplazamiento[0],
                    round(posicion_plataforma[1] * 720) + desplazamiento[1],
                ),
            )
            evento = sistema.solicitar_recoleccion(objeto["id"])
            self.assertIsNotNone(evento)
            self.assertIsNone(sistema.solicitar_recoleccion(objeto["id"]))
        self.assertEqual(sistema.estado, "READY_TO_REPAIR")
        self.assertEqual(len(sistema.materiales_recogidos), 3)

    def test_material_spritesheet_is_cropped_into_three_individual_objects(self):
        spritesheet = cargar_imagen(
            os.path.join("Herramientas", "HerramientasReparación.png")
        )
        recortes = SistemaReparacionPuente.recortar_spritesheet_materiales(
            spritesheet
        )
        self.assertEqual(set(recortes), set(SistemaReparacionPuente.MATERIALES))
        self.assertEqual(
            [recortes[item].get_size() for item in SistemaReparacionPuente.MATERIALES],
            [(47, 48), (34, 37), (37, 41)],
        )

    def test_materials_are_on_clear_floor_areas_of_the_real_platforms(self):
        _, decoraciones, _, hitboxes, _, _ = cargar_mapa_principal()
        puente = next(
            decoracion
            for decoracion in decoraciones
            if decoracion.get("id") == "puente_1"
        )
        _, _, sistema = crear_sistema(
            puente,
            crear_grafo_fisico(decoraciones),
        )

        for objeto in sistema.objetos:
            with self.subTest(material=objeto["tipo"]):
                self.assertFalse(any(
                    hitbox.get("role") == "wall"
                    and colision_hitbox_mapa(objeto["rect"], hitbox)
                    for hitbox in hitboxes
                ))
                self.assertFalse(any(
                    decoracion.get("personaje")
                    and decoracion["hitbox"].colliderect(objeto["rect"])
                    for decoracion in decoraciones
                ))
                self.assertFalse(any(
                    decoracion.get("puente")
                    and decoracion["rect"].colliderect(objeto["rect"])
                    for decoracion in decoraciones
                ))

    def test_bridge_collision_blocks_crossing_until_repaired(self):
        puente, _, sistema = crear_sistema()
        mundo = {
            "reparacion_puentes": sistema,
            "hitboxes": [],
            "personajes": [],
        }
        jugador_en_puente = pygame.Rect(puente["rect"].center, (8, 8))
        self.assertTrue(jugador_bloqueado(jugador_en_puente, mundo))

        for objeto in sistema.objetos:
            if objeto["activo"]:
                sistema.solicitar_recoleccion(objeto["id"])
        sistema.iniciar_reparacion()
        for _ in range(sistema.configuracion["aciertos_necesarios"]):
            posicionar_aguja_en_zona(sistema)
            sistema.intentar_reparacion()
        sistema.actualizar(sistema.configuracion["duracion_animacion_ms"])
        self.assertFalse(sistema.bloquea_paso)
        self.assertFalse(jugador_bloqueado(jugador_en_puente, mundo))

    def test_repair_requires_materials_and_opens_minigame(self):
        _, _, sistema = crear_sistema()
        self.assertFalse(sistema.iniciar_reparacion())
        self.assertEqual(sistema.estado, "MATERIALS_PENDING")
        for objeto in sistema.objetos:
            sistema.solicitar_recoleccion(objeto["id"])
        self.assertTrue(sistema.iniciar_reparacion())
        self.assertTrue(sistema.minijuego_activo)

    def test_correct_zone_matches_green_arc_and_moves_after_each_hit(self):
        _, _, sistema = crear_sistema()
        for objeto in sistema.objetos:
            sistema.solicitar_recoleccion(objeto["id"])
        sistema.iniciar_reparacion()

        angulos_objetivo = []
        indicadores = []
        for progreso in range(sistema.configuracion["aciertos_necesarios"]):
            sistema.estado_indicador = "normal"
            angulos_objetivo.append(sistema._angulo_objetivo())
            indicador = sistema._indicador_actual()
            indicadores.append(indicador)
            objetivo = sistema._angulo_objetivo()
            tolerancia = sistema.configuracion["tolerancia_angulo"]
            self.assertTrue(sistema._dentro_de_zona_correcta(objetivo))
            self.assertFalse(
                sistema._dentro_de_zona_correcta(objetivo + tolerancia + 0.02)
            )
            muestra = (
                round(110 + 60 * math.cos(objetivo)),
                round(110 + 60 * math.sin(objetivo)),
            )
            rojo, verde, azul, _ = indicador.get_at(muestra)
            self.assertGreater(verde, rojo)
            self.assertGreater(verde, azul)

            posicionar_aguja_en_zona(sistema)
            resultado = sistema.intentar_reparacion()
            self.assertEqual(resultado["resultado"], "acierto")
            self.assertEqual(sistema.progreso, progreso + 1)

        self.assertAlmostEqual(
            math.degrees(angulos_objetivo[0]),
            -25,
            delta=0.1,
        )
        self.assertAlmostEqual(
            math.degrees(angulos_objetivo[1]),
            -85,
            delta=0.1,
        )
        self.assertAlmostEqual(
            math.degrees(angulos_objetivo[2]),
            -145,
            delta=0.1,
        )
        self.assertEqual(len({id(indicador) for indicador in indicadores}), 3)

    def test_errors_are_nonlethal_and_three_hits_restore_bridge_route(self):
        puente, grafo, sistema = crear_sistema()
        for objeto in sistema.objetos:
            sistema.solicitar_recoleccion(objeto["id"])
        sistema.iniciar_reparacion()

        error = sistema.intentar_reparacion()
        self.assertEqual(error["resultado"], "error")
        self.assertEqual(sistema.progreso, 0)
        self.assertEqual(grafo.puentes["puente_1"]["estado"], "bloqueado")

        for _ in range(sistema.configuracion["aciertos_necesarios"]):
            posicionar_aguja_en_zona(sistema)
            resultado = sistema.intentar_reparacion()
            self.assertEqual(resultado["resultado"], "acierto")
        self.assertEqual(sistema.estado, "REPAIR_ANIMATION")

        sistema.actualizar(sistema.configuracion["duracion_animacion_ms"])
        self.assertEqual(sistema.estado, "REPAIRED")
        self.assertEqual(grafo.puentes["puente_1"]["estado"], "normal")
        self.assertTrue(grafo.puentes["puente_1"]["transitable"])
        self.assertEqual(sistema.snapshot()["estado"], "REPAIRED")
        self.assertIs(puente["imagen"], sistema.imagen_reparada)
        self.assertEqual(puente["rect"], sistema.hitbox_puente)


if __name__ == "__main__":
    unittest.main()
