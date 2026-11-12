"""Geometría propia: paredes originales, rutas reales y correspondencia visual."""
import hashlib
import json
import os
from pathlib import Path
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from bots.navegador_bot import NavegadorBot
from logica.dimensiones import DIMENSIONES, EDIFICIOS_FUTURO
from multijugador.dimensiones_red import spawn_interior, spawn_presente, rect_salida, rect_portal
from multijugador.movimiento import PartidaMovimiento
from multijugador.final_cooperativo import ROLES

RAIZ = Path(__file__).resolve().parent.parent


class MapaNuevo(unittest.TestCase):
    def setUp(self):
        self.p = PartidaMovimiento([dict(id=r, nombre=r, rol=r) for r in ROLES], 0)

    def test_generador_provisional_no_sobrescribe_la_geometria_instalada(self):
        from unittest.mock import patch
        from herramientas import generar_futuro
        ruta = generar_futuro.HITBOXES_DESTINO
        original = ruta.read_bytes()
        with patch.object(generar_futuro.pygame.image, "save") as guardar:
            generar_futuro.main()
        guardar.assert_not_called()
        self.assertEqual(ruta.read_bytes(), original)

    def test_paredes_coinciden_con_la_auditoria_y_los_ajustes_autorizados(self):
        auditoria = json.loads((RAIZ / "docs/auditoria_mapa_futuro.json").read_text(encoding="utf-8"))
        for nombre, esperado in auditoria["paredes"].items():
            datos = json.loads((RAIZ / "Hitboxes/Mapas/Futuro" / nombre).read_text(encoding="utf-8"))
            paredes = [h for h in datos["hitboxes"] if h.get("role", "wall") == "wall"]
            self.assertEqual(len(paredes), esperado["cantidad"])
            self.assertEqual(hashlib.sha256(json.dumps(paredes, sort_keys=True).encode()).hexdigest(), esperado["sha256"])

    def test_cuatro_apariciones_sin_islas_aisladas(self):
        m = self.p.colisiones_de("futuro")
        origen = m.inicio_libre(*spawn_presente(m.datos))
        self.p._viajar_equipo("la_copa", "futuro")
        for j in self.p.jugadores.values():
            self.assertFalse(m.bloqueado(j["x"], j["y"]))
            self.assertTrue(NavegadorBot(m).buscar_ruta(origen, (j["x"], j["y"]), radio=8), j["id"])

    def test_terminales_npcs_puertas_y_portal_alcanzables(self):
        m = self.p.colisiones_de("futuro")
        origen = m.inicio_libre(*spawn_presente(m.datos))
        f = self.p.mision.futuro
        for punto in f.objetivos + f.npcs + list(f.edificios.values()):
            self.assertTrue(NavegadorBot(m).buscar_ruta(origen, (punto["x"], punto["y"]), radio=8), punto["id"])
        x, y, w, h = rect_portal("futuro", m.datos)
        self.assertTrue(NavegadorBot(m).buscar_ruta(origen, (x+w/2, y+h/2), radio=40))

    def test_cinco_interiores_con_consulta_y_regreso_a_la_salida(self):
        for edificio, m in self.p.interiores_futuro.items():
            origen = spawn_interior(m.datos)
            self.assertFalse(m.bloqueado(*origen), edificio)
            consulta = next(o for o in self.p.mision.exploracion.objetivos if o["dimension"] == "futuro" and o["interior"] == edificio)
            self.assertTrue(NavegadorBot(m).buscar_ruta(origen, (consulta["x"], consulta["y"]), radio=8), edificio)
            x, y, w, h = rect_salida(m.datos)
            self.assertTrue(NavegadorBot(m).buscar_ruta((consulta["x"], consulta["y"]), (x+w/2, y+h/2), radio=50), edificio)

    def test_cliente_y_servidor_usan_el_mismo_interior_y_paredes(self):
        import pygame
        from mundo.mapas import cargar_mapa_edificio
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        self.assertEqual(DIMENSIONES["futuro"]["mapa"], "Fondos/Mapas/Futuro/MapaFuturo.png")
        for edificio, m in self.p.interiores_futuro.items():
            self.assertTrue(EDIFICIOS_FUTURO[edificio]["interior_hitboxes"].startswith("Mapas/Futuro/"))
            vista = cargar_mapa_edificio(edificio, "futuro")
            self.assertEqual(tuple(vista["rect_mapa"]), tuple(m.datos["rect_mapa"]))
            paredes = [h for h in vista["hitboxes"] if h.get("role", "wall") == "wall"]
            self.assertEqual(len(paredes), len(m.paredes))
            for a, b in zip(paredes, m.paredes):
                self.assertEqual(set(a), set(b))
                for campo in a:
                    if isinstance(a[campo], float):
                        self.assertAlmostEqual(a[campo], b[campo], places=10)
                    else:
                        self.assertEqual(a[campo], b[campo])

    def test_cuatro_personas_entran_en_cada_edificio_sin_cruzar_paredes(self):
        self.p._viajar_equipo("la_copa", "futuro")
        f = self.p.mision.futuro
        f.tareas["conexiones"] = "guardian"
        for edificio, puerta in f.edificios.items():
            mapa = self.p.interiores_futuro[edificio]
            origen = spawn_interior(mapa.datos)
            for i, jugador in self.p.jugadores.items():
                jugador.update(interior=None, x=puerta["x"], y=puerta["y"])
                self.p.entrar_edificio(i, edificio)
                self.assertFalse(mapa.bloqueado(jugador["x"], jugador["y"]))
                self.assertTrue(NavegadorBot(mapa).buscar_ruta(origen, (jugador["x"], jugador["y"]), radio=8), (edificio, i))
