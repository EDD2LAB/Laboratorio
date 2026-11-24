"""Modo Feria de los Ecos con QR (fase 1): votos, servidor, QR, pantalla y aislamiento."""
import json
import os
import re
import subprocess
import sys
import unittest
import urllib.error
import urllib.request

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from nucleo.rutas import RAIZ
from feria.casos import CASOS, DECISIONES, CATEGORIAS
from feria.sesion import SesionFeria, VotoInvalido

PUERTOS_PRUEBA = (18765, 18766, 18767)


class Sesion(unittest.TestCase):
    def setUp(self):
        self.s = SesionFeria()

    def test_un_voto_por_dispositivo_y_ronda(self):
        self.assertEqual(self.s.votar("celular-0001", 1, "verificar", "rumor_politico"), 1)
        with self.assertRaises(VotoInvalido):
            self.s.votar("celular-0001", 1, "compartir", "rumor_politico")
        self.s.cerrar_ronda()
        self.s.abrir_ronda()
        self.assertEqual(self.s.votar("celular-0001", 2, "detener", "acusacion_personal"), 1)
        self.assertEqual(len(self.s.participantes_unicos), 1)

    def test_rechaza_datos_invalidos_ronda_vieja_y_cerrada(self):
        for args in (("x", 1, "verificar", "rumor_politico"), (None, 1, "verificar", "rumor_politico"),
                     ("celular-0002", 1, "borrar", "rumor_politico"), ("celular-0002", 1, "verificar", "chisme"),
                     ("celular-0002", 7, "verificar", "rumor_politico"), ("celular-0002", "1", "verificar", "rumor_politico")):
            with self.subTest(args=args), self.assertRaises(VotoInvalido):
                self.s.votar(*args)
        self.s.cerrar_ronda()
        with self.assertRaises(VotoInvalido):
            self.s.votar("celular-0002", 1, "verificar", "rumor_politico")

    def test_resultado_colectivo_y_estados_del_caldero(self):
        for i in range(6):
            self.s.votar(f"celular-{i:04d}", 1, "verificar", "rumor_politico")
        for i in range(6, 10):
            self.s.votar(f"celular-{i:04d}", 1, "ignorar", "suceso_natural")
        r = self.s.cerrar_ronda()
        self.assertEqual((r["total"], r["responsables"], r["aciertos_categoria"], r["caldero"]), (10, 6, 6, "positivo"))
        self.s.abrir_ronda()
        for i in range(10):
            self.s.votar(f"celular-{i:04d}", 2, "compartir" if i < 5 else "ignorar", "suceso_natural")
        self.assertEqual(self.s.cerrar_ronda()["caldero"], "critico")
        self.s.abrir_ronda()
        for i, decision in enumerate(("verificar", "verificar", "ignorar", "ignorar", "compartir")):
            self.s.votar(f"celular-{i:04d}", 3, decision, "acusacion_personal")
        self.assertEqual(self.s.cerrar_ronda()["caldero"], "dudoso")
        self.assertEqual(len(self.s.historial), 3)

    def test_ronda_sin_votos_no_falla(self):
        r = self.s.cerrar_ronda()
        self.assertEqual((r["total"], r["caldero"]), (0, "dudoso"))

    def test_las_rondas_recorren_el_catalogo(self):
        vistos = []
        for _ in range(len(CASOS) + 1):
            vistos.append(self.s.caso_actual)
            self.s.cerrar_ronda()
            self.s.abrir_ronda()
        self.assertEqual(vistos[:len(CASOS)], [c["id"] for c in CASOS])
        self.assertEqual(vistos[-1], CASOS[0]["id"])

    def test_el_celular_no_recibe_respuestas_ni_votos_ajenos(self):
        self.s.votar("celular-0001", 1, "verificar", "rumor_politico")
        celular = json.dumps(self.s.para_celular(), ensure_ascii=False)
        for oculto in ("categoria\"", "verdad", "ensenanza", "mejor", "celular-0001"):
            self.assertNotIn(oculto, celular)
        pantalla = self.s.para_pantalla()
        self.assertEqual(pantalla["votos"], 1)
        self.assertIsNone(pantalla["resultado"])  # sin porcentajes hasta cerrar
        self.assertNotIn("celular-0001", json.dumps(pantalla, ensure_ascii=False))

    def test_catalogo_coherente_con_el_arbol_de_la_copa(self):
        from feria.casos import NOMBRE_CATEGORIA
        from logica.logica_juego import OPCIONES_CLASIFICACION as CATEGORIAS_ARBOL
        for caso in CASOS:
            self.assertIn(caso["mejor"], dict(DECISIONES))
            self.assertIn(NOMBRE_CATEGORIA[caso["categoria"]], CATEGORIAS_ARBOL)
        # Ningún caso deja a Kael o a Mira como culpables: la verdad los desmiente.
        for caso in CASOS:
            if re.search(r"(Kael|Mira)", caso["tablilla"]):  # «Mirador» no es Mira
                self.assertTrue(caso["verdad"].startswith("Falso"), caso["id"])


class Servidor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from feria.web import ServidorFeriaLocal
        cls.servidor = ServidorFeriaLocal(PUERTOS_PRUEBA, host="127.0.0.1").iniciar()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.detener()

    def setUp(self):
        self.sesion = self.servidor.registro.crear()
        self.url = self.servidor.url(self.sesion.codigo_sesion, "127.0.0.1")

    def tearDown(self):
        self.servidor.registro.cerrar(self.sesion.codigo_sesion)

    def votar(self, cuerpo):
        datos = cuerpo if isinstance(cuerpo, bytes) else json.dumps(cuerpo).encode()
        peticion = urllib.request.Request(self.url + "/voto", datos, {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(peticion, timeout=5) as respuesta:
                return respuesta.status, json.load(respuesta)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def test_pagina_ronda_y_voto_desde_un_celular(self):
        with urllib.request.urlopen(self.url, timeout=5) as respuesta:
            html = respuesta.read().decode("utf-8")
        self.assertIn("Feria de los Ecos", html)
        self.assertNotIn("http://", html.split("<script>")[0])  # sin recursos externos
        with urllib.request.urlopen(self.url + "/ronda", timeout=5) as respuesta:
            ronda = json.load(respuesta)
        self.assertEqual((ronda["ronda"], ronda["abierta"]), (1, True))
        voto = dict(dispositivo="celular-abc123", ronda=1, decision="verificar", categoria="rumor_politico")
        self.assertEqual(self.votar(voto)[0], 200)
        estado, cuerpo = self.votar(voto)
        self.assertEqual(estado, 409)
        self.assertIn("Ya votaste", cuerpo["mensaje"])
        self.assertEqual(self.sesion.para_pantalla()["votos"], 1)

    def test_solicitudes_malas_y_sesion_inexistente(self):
        self.assertEqual(self.votar(b"no es json")[0], 400)
        self.assertEqual(self.votar([1, 2])[0], 400)
        for codigo in ("ZZZZZZ", "abc", "../x"):
            with self.subTest(codigo=codigo), self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(self.url.replace(self.sesion.codigo_sesion, codigo) + "/ronda", timeout=5)
            self.assertEqual(error.exception.code, 404)

    def test_registro_caduca_y_tiene_limite(self):
        import feria.web as web
        registro = web.RegistroFerias()
        primera = registro.crear()
        registro.sesiones[primera.codigo_sesion] = (primera, -10 ** 9)  # muy vieja
        self.assertIsNone(registro.obtener(primera.codigo_sesion))
        for _ in range(web.MAX_SESIONES):
            registro.crear()
        with self.assertRaises(RuntimeError):
            registro.crear()


class Qr(unittest.TestCase):
    def test_qr_cuadrado_con_modulos_enteros_y_zona_blanca(self):
        import segno
        from feria.qr import ZONA_SILENCIO, superficie_qr
        pygame.init()
        url = "http://192.168.1.20:8080/feria/AB12CD"
        imagen = superficie_qr(url, 200)
        modulos = len(segno.make(url, error="m", micro=False).matrix) + 2 * ZONA_SILENCIO
        self.assertEqual(imagen.get_width(), imagen.get_height())
        self.assertEqual(imagen.get_width() % modulos, 0)
        self.assertLessEqual(imagen.get_width(), 200)
        self.assertEqual(tuple(imagen.get_at((0, 0)))[:3], (255, 255, 255))


class PantallaGrande(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((960, 720))

    def test_ronda_completa_y_al_salir_no_queda_sesion(self):
        from feria.pantalla import jugar_desde_menu
        from feria.web import ServidorFeriaLocal
        servidor = ServidorFeriaLocal(PUERTOS_PRUEBA, host="127.0.0.1").iniciar()
        vistas = {}

        def guion(pantalla, cuadro):
            sesion = pantalla.sesion
            vistas["sesion"] = sesion.codigo_sesion
            if cuadro < 6:
                sesion.votar(f"celular-{cuadro:04d}", sesion.ronda_actual, "verificar", "rumor_politico")
            elif cuadro == 6:
                pantalla.accionar("votar_aqui")
                pantalla.accionar("decision:detener")
                pantalla.accionar("categoria:rumor_politico")
                pantalla.accionar("enviar_pantalla")
            elif cuadro == 8:
                pantalla.tecla(pygame.K_SPACE)
            elif cuadro == 10:
                vistas["resultado"] = sesion.para_pantalla()["resultado"]
                pantalla.tecla(pygame.K_n)
            elif cuadro == 12:
                vistas["ronda"] = sesion.ronda_actual
        try:
            self.assertIsNone(jugar_desde_menu(pygame.Surface((960, 720)), servidor=servidor, cuadros=14, al_dibujar=guion))
            self.assertEqual(vistas["resultado"]["total"], 7)
            self.assertEqual(vistas["resultado"]["caldero"], "positivo")
            self.assertEqual(vistas["ronda"], 2)
            self.assertIsNone(servidor.registro.obtener(vistas["sesion"]))  # salir destruye los votos
        finally:
            servidor.detener()

    def test_un_error_dentro_de_la_feria_no_cierra_el_juego(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        import feria.pantalla as pantalla
        with tempfile.TemporaryDirectory() as tmp,                 mock.patch("nucleo.rutas.RAIZ", Path(tmp)),                 mock.patch.object(pantalla, "PantallaFeria", side_effect=RuntimeError("fallo de prueba")):
            from feria.web import ServidorFeriaLocal
            servidor = ServidorFeriaLocal(PUERTOS_PRUEBA, host="127.0.0.1").iniciar()
            try:
                pygame.event.clear()
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
                self.assertIsNone(pantalla.jugar_desde_menu(pygame.Surface((960, 720)), servidor=servidor))
            finally:
                servidor.detener()
            registro = (Path(tmp) / "cache" / "feria_error.log").read_text(encoding="utf-8")
            self.assertIn("fallo de prueba", registro)

    def test_sin_la_libreria_del_qr_no_se_abre_ningun_servidor(self):
        from unittest import mock
        import importlib.util
        import feria.pantalla as pantalla
        original = importlib.util.find_spec
        sin_segno = lambda nombre, *args, **kw: None if nombre == "segno" else original(nombre, *args, **kw)
        with mock.patch("importlib.util.find_spec", sin_segno),                 mock.patch("feria.web.ServidorFeriaLocal") as servidor:
            pygame.event.clear()
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
            self.assertIsNone(pantalla.jugar_desde_menu(pygame.Surface((960, 720))))
        servidor.assert_not_called()

    def test_errores_repetidos_no_dejan_puertos_ocupados(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        import feria.pantalla as pantalla
        import feria.web as web
        real = web.ServidorFeriaLocal
        creados = []

        def crear():
            creados.append(real(PUERTOS_PRUEBA[:1], host="127.0.0.1"))
            return creados[-1]
        with tempfile.TemporaryDirectory() as tmp, mock.patch("nucleo.rutas.RAIZ", Path(tmp)),                 mock.patch.object(web, "ServidorFeriaLocal", side_effect=crear),                 mock.patch.object(pantalla, "PantallaFeria", side_effect=RuntimeError("fallo de prueba")):
            for _ in range(6):  # con un solo puerto, una fuga haría fallar el segundo intento
                pygame.event.clear()
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
                self.assertIsNone(pantalla.jugar_desde_menu(pygame.Surface((960, 720))))
        self.assertEqual(len(creados), 6)
        self.assertTrue(all(s.puerto == PUERTOS_PRUEBA[0] and not s._hilo.is_alive() for s in creados))

    def test_menu_ofrece_la_feria_en_sus_dos_versiones(self):
        from interfaz.inicio import MenuInicio
        menu = MenuInicio()
        for feria in (False, True):
            menu.feria, menu.vista = feria, "principal"
            menu.dibujar()
            self.assertIn("feria_qr", menu.botones)
            rects = [b.rect for b in menu.botones.values()]
            self.assertTrue(all(r.collidelist(rects[i + 1:]) == -1 for i, r in enumerate(rects)))


class Aislamiento(unittest.TestCase):
    def test_la_feria_no_carga_el_juego_ni_arte_al_importarse(self):
        codigo = ("import sys, pygame, feria.casos, feria.sesion, feria.web, feria.movil, feria.qr, feria.pantalla\n"
                  "assert not pygame.display.get_init()\n"
                  "prohibidos = [m for m in sys.modules if m.startswith(('multijugador.campana', 'multijugador.movimiento',"
                  " 'multijugador.servidor', 'logica.expediente', 'bots', 'interfaz.partida_multijugador'))]\n"
                  "assert not prohibidos, prohibidos\n")
        resultado = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True, text=True)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)

    def test_una_sesion_no_escribe_archivos_ni_cambia_el_protocolo(self):
        from multijugador import protocolo
        version = protocolo.VERSION
        vigilados = [RAIZ / "preferencias_usuario.json", RAIZ / "datos" / "casos_expediente.json"]
        antes = {ruta: ruta.read_bytes() if ruta.exists() else None for ruta in vigilados}
        sesion = SesionFeria()
        for i in range(5):
            sesion.votar(f"celular-{i:04d}", 1, "verificar", "rumor_politico")
        sesion.cerrar_ronda()
        self.assertEqual({ruta: ruta.read_bytes() if ruta.exists() else None for ruta in vigilados}, antes)
        self.assertEqual(protocolo.VERSION, version)

    def test_la_campana_no_cambia_despues_de_jugar_feria(self):
        from multijugador.movimiento import PartidaMovimiento
        roles = [dict(id=r, nombre=r, rol=r) for r in ("guardian", "mensajero", "habitante", "aspirante")]
        antes = PartidaMovimiento(roles, 0).estado("guardian")["caso"]
        sesion = SesionFeria()
        sesion.votar("celular-0001", 1, "compartir", "rumor_politico")
        sesion.cerrar_ronda()
        despues = PartidaMovimiento(roles, 0).estado("guardian")["caso"]
        self.assertEqual(json.dumps(antes, sort_keys=True, default=str), json.dumps(despues, sort_keys=True, default=str))


if __name__ == "__main__":
    unittest.main()
