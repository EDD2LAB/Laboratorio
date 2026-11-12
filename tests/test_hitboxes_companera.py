"""Paredes entregadas por el equipo y accesos conservados al integrarlas."""
import hashlib
import json
from pathlib import Path
import unittest

from bots.navegador_bot import NavegadorBot
from logica.dimensiones import EDIFICIOS_PRESENTE
from multijugador.dimensiones_red import spawn_interior, rect_salida, cargar_interior
from multijugador.movimiento import PartidaMovimiento

RAIZ = Path(__file__).resolve().parent.parent


class HitboxesIntegradas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = PartidaMovimiento([dict(id=r, nombre=r, rol=r) for r in
                                  ('guardian', 'mensajero', 'habitante', 'aspirante')], 0)

    def test_paredes_originales_sin_edicion_automatica(self):
        a = json.loads((RAIZ/'docs/auditoria_hitboxes_presente.json').read_text(encoding='utf8'))
        archivos = [(RAIZ/'Hitboxes/Mapas/Presente'/nombre, esperado) for nombre, esperado in a['paredes'].items()]
        archivos.append((RAIZ/'Hitboxes/Mapas/Pr_MañanaLumi_hitboxes.json', a['la_copa']))
        for ruta, esperado in archivos:
            with self.subTest(archivo=ruta.name):
                d = json.loads(ruta.read_text(encoding='utf8'))
                paredes = [b for b in d['hitboxes'] if b.get('role','wall') == 'wall']
                # Paredes añadidas con autorización van al final; las originales no se tocan.
                extra = esperado.get('restauradas', {'cantidad': 0, 'sha256': hashlib.sha256(b'[]').hexdigest()})
                self.assertEqual(len(paredes), esperado['cantidad'] + extra['cantidad'])
                originales, restauradas = paredes[:esperado['cantidad']], paredes[esperado['cantidad']:]
                self.assertEqual(hashlib.sha256(json.dumps(originales, sort_keys=True).encode()).hexdigest(), esperado['sha256'])
                self.assertEqual(hashlib.sha256(json.dumps(restauradas, sort_keys=True).encode()).hexdigest(), extra['sha256'])

    def test_interior_de_cliente_y_servidor_apunta_al_archivo_nuevo(self):
        for clave, config in EDIFICIOS_PRESENTE.items():
            self.assertTrue(config['interior_hitboxes'].startswith('Mapas/Presente/'))
            m = self.p.interiores[clave]
            self.assertEqual(m.datos, cargar_interior(clave))
            self.assertGreater(len(m.paredes), 50)

    def test_apariciones_pistas_y_consultas_en_el_mismo_recinto(self):
        mision = self.p.mision.presente
        puntos = [n for grupo in mision.personajes_evento for n in grupo]
        puntos += [o for o in self.p.mision.exploracion.objetivos if o['dimension']=='presente']
        for punto in puntos:
            m = self.p.interiores[punto['interior']]
            origen = spawn_interior(m.datos)
            self.assertFalse(m.bloqueado(*origen))
            self.assertTrue(NavegadorBot(m).buscar_ruta(origen, (punto['x'],punto['y']), radio=8), punto)

    def test_los_cuatro_pueden_entrar_y_salir_sin_aparecer_tras_una_pared(self):
        p = self.p
        for clave, m in p.interiores.items():
            puerta = p.mision.presente.edificios[clave]
            for j in p.jugadores.values():
                j.update(dimension='presente', interior=None, x=puerta['x'], y=puerta['y'])
            for identificador, j in p.jugadores.items():
                p.entrar_edificio(identificador, clave)
                self.assertFalse(m.bloqueado(j['x'],j['y']))
                self.assertTrue(NavegadorBot(m).buscar_ruta(spawn_interior(m.datos), (j['x'],j['y']), radio=8))
                x,y,w,h = rect_salida(m.datos)
                self.assertTrue(NavegadorBot(m).buscar_ruta((j['x'],j['y']), (x+w/2,y+h/2), radio=58))
