"""Finales del equipo y efectos del mapa de La Copa."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from interfaz.finales import determinar_final  # noqa: E402
from multijugador.partida_local import ClienteCampanaLocal  # noqa: E402


class ReglaDelFinal(unittest.TestCase):
    def test_victoria_exige_positivos_altos_y_poco_ruido(self):
        bien = dict(sabiduria=60, confianza=60, armonia=60, susurros_falsos=20, desinformacion=20)
        self.assertEqual(determinar_final(bien), "victoria")
        self.assertEqual(determinar_final(dict(bien, sabiduria=30, confianza=30, armonia=30)), "game_over")
        self.assertEqual(determinar_final(dict(bien, susurros_falsos=50, desinformacion=50)), "game_over")


class ConPartida(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        from interfaz.partida_multijugador import VistaPartida
        self.cliente = ClienteCampanaLocal("Prueba", "guardian")
        self.vista = VistaPartida("local", self.cliente.eventos.get_nowait())

    def caso(self):
        return self.vista.estado["mundo"]["caso"]


class FinalDelEquipo(ConPartida):
    def test_aparece_una_vez_al_completar_las_tres_eras(self):
        self.caso().update(fase="final", presente={"completada": True, "fin": True}, indicadores=dict(sabiduria=90, confianza=90, armonia=90))
        self.vista._revisar_final()
        self.assertIsNone(self.vista.pantalla_final)  # falta Ciudad Núcleo
        self.caso()["futuro"] = {"completada": True, "fin": True}
        self.vista._revisar_final()
        final = self.vista.pantalla_final
        self.assertIsNotNone(final)
        self.assertEqual(final.resultado, "victoria")
        self.assertIsNotNone(final.imagen)
        final.dibujar(pygame.Surface((960, 720)))
        self.vista.manejar_evento(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(1, 1)), (1, 1), self.cliente)
        self.assertIsNone(self.vista.pantalla_final)
        self.vista._revisar_final()
        self.assertIsNone(self.vista.pantalla_final)

    def test_no_aparece_sin_terminar_distrito_conecta(self):
        self.caso().update(fase="final", presente={"completada": False})
        self.vista._revisar_final()
        self.assertIsNone(self.vista.pantalla_final)


class EfectosDelMapa(ConPartida):
    def estado(self, **caso):
        self.caso().update(caso)
        self.vista._lanzar_efectos(self.caso())

    def test_el_poder_se_ve_una_sola_vez(self):
        self.estado(habilidades_usadas=["local"])
        self.assertEqual([e[0] for e in self.vista.efectos_mapa.activos], ["poder"])
        self.estado(habilidades_usadas=["local"])
        self.assertEqual(len(self.vista.efectos_mapa.activos), 1)

    def test_rumor_y_correccion_cruzan_un_puente(self):
        self.estado(oleadas=1)
        self.estado(resultado={"correcto": True, "evento_id": 5})
        self.assertEqual([r[0] for r in self.vista.efectos_mapa.recorridos], ["rumor", "correccion"])
        self.estado(oleadas=1, resultado={"correcto": True, "evento_id": 5})
        self.assertEqual(len(self.vista.efectos_mapa.recorridos), 2)

    def test_lo_ocurrido_antes_de_unirse_no_se_repite(self):
        from interfaz.partida_multijugador import VistaPartida
        self.caso()["oleadas"] = 3
        otra = VistaPartida("local", self.vista.estado)
        otra._lanzar_efectos(self.caso())
        self.assertEqual(otra.efectos_mapa.recorridos, [])

    def test_los_efectos_tienen_tope(self):
        from interfaz.efectos_mapa import MAX_EFECTOS
        for _ in range(30):
            self.vista.efectos_mapa.lanzar("poder", 10, 10)
        self.assertEqual(len(self.vista.efectos_mapa.activos), MAX_EFECTOS)

    def test_todas_las_tiras_se_cargaron(self):
        from interfaz.efectos_mapa import TIRAS
        for nombre, (_, cantidad, _tam) in TIRAS.items():
            self.assertEqual(len(self.vista.efectos_mapa.cuadros[nombre]), cantidad, nombre)

    def test_barra_de_recarga_en_sus_tres_estados(self):
        recarga = self.vista._estado_recarga
        self.assertEqual(recarga({"habilidad_usada": True}, "guardian"), "vacia")
        self.assertEqual(recarga({"inventario": []}, "guardian"), "mitad")
        self.assertEqual(recarga({"inventario": [{"id": "pista_guardian"}]}, "guardian"), "llena")
        for estado in ("vacia", "mitad", "llena"):
            self.assertIsNotNone(self.vista.arte.barra_recarga[estado])


class MapaDeLaCopa(ConPartida):
    def test_el_caldero_tiene_una_fila_por_estado(self):
        for fila in range(1, 5):
            self.assertEqual(len(self.vista.cuadros_caldero[(2, fila)]), 4)
        self.assertIsNotNone(self.vista.rect_caldero)

    def test_cada_tronco_usa_solo_su_diseno(self):
        self.assertEqual(set(self.vista.variantes_eco), {1, 2, 3, 4})
        self.assertEqual(len(self.vista.variantes_eco[1]), 4)
        tamano = (30, 56)
        self.assertEqual(len(self.vista._frames_tronco(tamano, 3)), 4)
        self.assertIs(self.vista._frames_tronco(tamano, 3), self.vista._frames_tronco(tamano, 3))

    def test_el_puente_deteriorado_se_cargo(self):
        self.assertIsNotNone(self.vista.puente_det)
        self.assertIsNotNone(self.vista.puente_det_zoom)

    def test_usar_un_tronco_lanza_su_efecto(self):
        tronco = next(o for o in self.caso()["objetivos"] if o["tipo"] == "eco")
        self.vista.cerca = lambda objetivo, *r: objetivo is tronco or objetivo == tronco
        self.vista.panel.abrir("eco")
        self.assertEqual(self.vista.efectos_mapa.activos[0][0], "eco")

    def test_las_conversaciones_usan_el_marco_de_dialogo(self):
        self.vista.panel.modo, self.vista.panel.titulo, self.vista.panel.texto = "fuente", "Luma · testimonio", "Hola"
        self.vista.panel.dibujar(pygame.Surface((960, 720)))
        self.assertIn("cerrar", self.vista.panel.botones)
        self.assertIn("inventario", self.vista.panel.botones)


class Reposo(ConPartida):
    def test_los_npc_con_hojas_de_reposo_se_animan(self):
        animados = {o["personaje"] for o in self.vista.decoraciones_zoom if o.get("cuadros_reposo")}
        self.assertLessEqual({"Naira", "Darek", "Luma", "Mira"}, animados)
        for objeto in self.vista.decoraciones_zoom:
            if objeto.get("cuadros_reposo"):
                self.assertEqual(len(objeto["cuadros_reposo"]), 8)

    def test_mira_y_luma_no_se_deslizan_en_reposo(self):
        from mundo.personajes import _centro_pies, cuadros_reposo_de
        for sprite in ("NPCS/Aspirante mujer/MujerAspirante Fila 1 - 1.png", "NPCS/Habitante mujer/x.png"):
            for orientacion in ("abajo", "derecha", "arriba", "izquierda"):
                centros = [_centro_pies(c) for c in cuadros_reposo_de(sprite, orientacion)]
                self.assertLessEqual(max(centros) - min(centros), 1, (sprite, orientacion))

    def test_las_hojas_se_encuentran_con_cualquier_nombre(self):
        from mundo.personajes import archivos_reposo_de
        for sprite in ("NPCS/Naira/Naira_fila1-1.png", "NPCS/Mensajero urbano/Mensajero_urbano-Fila1.png",
                       "NPCS/Aspirante mujer/MujerAspirante Fila 1 - 1.png"):
            self.assertEqual(len(archivos_reposo_de(sprite)), 4, sprite)
        self.assertEqual(archivos_reposo_de("NPCS/Arel/Arel.png"), [])  # no tiene
        self.assertEqual(archivos_reposo_de("Animales/Pajaro.png"), [])

    def test_quieto_en_diagonal_sigue_animado(self):
        for rol, hojas in self.vista.personajes_zoom.items():
            self.assertGreater(len(hojas[("reposo", "arriba_derecha")]), 1, rol)

    def test_en_distrito_conecta_reposan_animados(self):
        from multijugador.dimensiones_red import PRESENTE
        self.vista._cargar_dimension(PRESENTE)
        escena = self.vista.escenas_zoom[PRESENTE]
        self.assertGreater(len(escena["personajes"]["mensajero"][("reposo", "abajo")]), 1)
        self.assertTrue(any(o.get("cuadros_reposo") for o in escena["decoraciones"]))


if __name__ == "__main__":
    unittest.main()
