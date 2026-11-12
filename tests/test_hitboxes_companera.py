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
                extra = esperado.get('restauradas') or esperado.get('añadidas') or {'cantidad': 0, 'sha256': hashlib.sha256(b'[]').hexdigest()}
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


def _recorrido(colisiones, inicio, paso=6):
    """Celdas alcanzables a pie desde ``inicio`` con las mismas reglas del servidor."""
    a = (round(inicio[0]) // paso, round(inicio[1]) // paso)
    vistos, pila = {a}, [a]
    while pila:
        x, y = pila.pop()
        for p in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            o, d = (x * paso + 3, y * paso + 3), (p[0] * paso + 3, p[1] * paso + 3)
            if (p not in vistos and 0 <= p[0] < 960 // paso and 0 <= p[1] < 720 // paso
                    and not colisiones.bloqueado(*d) and colisiones.puede_pasar(o, d)):
                vistos.add(p)
                pila.append(p)
    return vistos


class RecorridosDelPresente(unittest.TestCase):
    """Sin caminar por paredes ni muebles y sin edificios aislados."""

    def test_desde_la_aparicion_se_llega_a_pie_a_los_cinco_edificios(self):
        from multijugador.dimensiones_red import cargar_datos, edificios_de
        from multijugador.movimiento import ColisionesMapa
        datos = cargar_datos('presente')
        s, (x, y, w, h) = datos['spawn']['default'], datos['rect_mapa']
        vistos = _recorrido(ColisionesMapa(datos), (x + (s['rx'] + s['rw'] / 2) * w, y + (s['ry'] + s['rh']) * h))
        for clave, puerta in edificios_de(datos).items():
            with self.subTest(edificio=clave):
                cx, cy = round(puerta['x']) // 6, round(puerta['y']) // 6
                self.assertTrue(any((cx + dx, cy + dy) in vistos for dx in range(-2, 3) for dy in range(-2, 3)))

    def test_interiores_solo_dejan_caminar_por_el_suelo_y_se_puede_salir(self):
        from multijugador.dimensiones_red import RADIO_SALIDA, cerca_de_rect
        from multijugador.movimiento import ColisionesMapa
        for clave in EDIFICIOS_PRESENTE:
            with self.subTest(edificio=clave):
                datos = cargar_interior(clave)
                colisiones = ColisionesMapa(datos)
                inicio = spawn_interior(datos)
                self.assertFalse(colisiones.bloqueado(*inicio))
                vistos = _recorrido(colisiones, inicio)
                # Con fugas por las paredes se recorría más de la mitad del cuadro.
                self.assertLess(len(vistos), (960 // 6) * (536 // 6) / 3)
                self.assertTrue(any(cerca_de_rect(a * 6 + 3, b * 6 + 3, rect_salida(datos), RADIO_SALIDA)
                                    for a, b in vistos))
