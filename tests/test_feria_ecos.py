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
os.environ["COPA_FERIA_SERVIDOR"] = ""   # las pruebas nunca salen a internet
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
        registro.sesiones[primera.codigo_sesion][1] = -10 ** 9  # muy vieja
        self.assertIsNone(registro.obtener(primera.codigo_sesion))
        for _ in range(web.MAX_SESIONES):
            registro.crear()
        with self.assertRaises(RuntimeError):
            registro.crear()


    def pedir(self, ruta, datos=None, token=None):
        cabeceras = {"Content-Type": "application/json"}
        if token:
            cabeceras["Authorization"] = "Bearer " + token
        cuerpo = None if datos is None else json.dumps(datos).encode()
        peticion = urllib.request.Request(f"http://127.0.0.1:{self.servidor.puerto}{ruta}", cuerpo, cabeceras)
        try:
            with urllib.request.urlopen(peticion, timeout=5) as respuesta:
                return respuesta.status, json.load(respuesta)
        except urllib.error.HTTPError as error:
            return error.code, None

    def test_la_pantalla_por_internet_controla_su_sesion_solo_con_su_clave(self):
        estado, nueva = self.pedir("/feria/nueva", {})
        self.assertEqual(estado, 200)
        codigo, token = nueva["codigo"], nueva["token"]
        self.assertEqual(nueva["estado"]["ronda"], 1)
        base = f"/feria/{codigo}"
        self.assertEqual(self.pedir(base + "/estado")[0], 403)
        self.assertEqual(self.pedir(base + "/estado", token="otra-clave")[0], 403)
        self.assertEqual(self.pedir(base + "/control", {"accion": "cerrar"}, "otra-clave")[0], 403)
        self.assertEqual(self.pedir(base + "/control", {"accion": "borrar_todo"}, token)[0], 400)
        voto = dict(dispositivo="celular-remoto1", ronda=1, decision="detener", categoria="rumor_politico")
        self.assertEqual(self.pedir(base + "/voto", voto)[0], 200)
        self.assertEqual(self.pedir(base + "/estado", token=token)[1]["votos"], 1)
        estado, cerrada = self.pedir(base + "/control", {"accion": "cerrar"}, token)
        self.assertEqual((estado, cerrada["abierta"], cerrada["resultado"]["total"]), (200, False, 1))
        self.assertEqual(self.pedir(base + "/control", {"accion": "abrir"}, token)[1]["ronda"], 2)
        # El celular sigue sin ver la clave ni las respuestas.
        self.assertNotIn(token, json.dumps(self.pedir(base + "/ronda")[1]))
        self.assertEqual(self.pedir(base + "/control", {"accion": "terminar"}, token)[0], 200)
        self.assertIsNone(self.servidor.registro.obtener(codigo))

    def test_una_sesion_de_internet_sin_pantalla_caduca(self):
        import feria.web as web
        registro = web.RegistroFerias()
        remota, local = registro.crear(remota=True), registro.crear()
        for entrada in registro.sesiones.values():
            entrada[2] -= web.SIN_ANFITRION + 1   # nadie preguntó en 10 minutos
        self.assertIsNone(registro.obtener(remota.codigo_sesion))
        self.assertIs(registro.obtener(local.codigo_sesion), local)  # la local la controla su pantalla

    def test_sesion_remota_vota_cierra_abre_y_termina(self):
        import time
        from feria.remoto import SesionRemota
        remota = SesionRemota.crear(f"http://127.0.0.1:{self.servidor.puerto}", timeout=5)
        try:
            servidora = self.servidor.registro.obtener(remota.codigo_sesion)
            self.assertTrue(remota.url.endswith("/feria/" + remota.codigo_sesion))
            remota.votar("pantalla-0001", remota.ronda_actual, "verificar", "rumor_politico")
            servidora.votar("celular-xyz789", 1, "compartir", "rumor_politico")
            remota.cerrar_ronda()
            self.assertFalse(remota.abierta)   # la pantalla reacciona sin esperar a la red
            limite = time.monotonic() + 8
            while (remota.para_pantalla()["resultado"] or {}).get("total") != 2 and time.monotonic() < limite:
                time.sleep(.05)
            self.assertEqual(remota.para_pantalla()["resultado"]["total"], 2)
            remota.abrir_ronda()
            while remota.ronda_actual != 2 and time.monotonic() < limite:
                time.sleep(.05)
            self.assertEqual((remota.ronda_actual, remota.abierta, remota.problema), (2, True, ""))
        finally:
            remota.terminar()
        self.assertIsNone(self.servidor.registro.obtener(remota.codigo_sesion))
        self.assertFalse(remota._hilo.is_alive())


class Render(unittest.TestCase):
    def test_el_servidor_de_internet_ofrece_la_feria_sin_tocar_sus_rutas(self):
        from multijugador.tiempo_real import crear_app
        rutas = {r.resource.canonical for r in crear_app().router.routes()}
        for ruta in ("/v1/juego", "/health", "/v1/estado", "/v1/crear", "/feria/nueva", "/feria/{codigo}/voto",
                     "/feria/{codigo}/estado", "/feria/{codigo}/control"):
            self.assertIn(ruta, rutas)

    def test_la_imagen_de_docker_incluye_la_feria_sin_pygame(self):
        dockerfile = (RAIZ / "Dockerfile.multijugador").read_text(encoding="utf-8")
        ignorados = (RAIZ / "Dockerfile.multijugador.dockerignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("COPY feria/ /app/feria/", dockerfile)
        for modulo in ("__init__", "casos", "sesion", "movil", "web"):
            self.assertIn(f"!feria/{modulo}.py", ignorados)
            codigo = (RAIZ / "feria" / f"{modulo}.py").read_text(encoding="utf-8")
            self.assertNotRegex(codigo, r"(?m)^\s*(import|from) pygame")

    def test_sin_internet_la_espera_pasa_a_la_red_local(self):
        from feria.pantalla import _conectar_remoto
        pygame.init()
        pygame.event.clear()
        sesion, aviso = _conectar_remoto(pygame.Surface((960, 720)), "http://127.0.0.1:1", limite=.5)
        self.assertIsNone(sesion)
        self.assertIn("misma Wi-Fi", aviso)

    def test_render_sin_desplegar_la_feria_pasa_a_la_red_local_sin_esperar(self):
        import threading
        import time
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from feria.pantalla import _conectar_remoto

        class Viejo(BaseHTTPRequestHandler):   # servidor de salas sin las rutas /feria
            def do_POST(self):
                self.send_error(404)

            def log_message(self, *args):
                pass
        viejo = HTTPServer(("127.0.0.1", 0), Viejo)
        threading.Thread(target=viejo.serve_forever, daemon=True).start()
        try:
            pygame.init()
            pygame.event.clear()
            inicio = time.monotonic()
            sesion, aviso = _conectar_remoto(pygame.Surface((960, 720)), f"http://127.0.0.1:{viejo.server_port}")
            self.assertLess(time.monotonic() - inicio, 5)
            self.assertIsNone(sesion)
            self.assertIn("aún no tiene la feria", aviso)
        finally:
            viejo.shutdown()
            viejo.server_close()


class Redes(unittest.TestCase):
    def test_prefiere_la_zona_movil_del_computador_y_descarta_ips_sin_red(self):
        from unittest import mock
        import feria.web as web
        respuestas = [(2, 1, 6, "", (ip, 0)) for ip in ("169.254.41.200", "192.168.128.30", "192.168.137.1", "127.0.0.1")]
        with mock.patch.object(web.socket, "getaddrinfo", return_value=respuestas),                 mock.patch.object(web, "ip_local", return_value="192.168.128.30"):
            self.assertEqual(web.ips_locales(), ["192.168.137.1", "192.168.128.30"])
        with mock.patch.object(web.socket, "getaddrinfo", side_effect=OSError),                 mock.patch.object(web, "ip_local", return_value="127.0.0.1"):
            self.assertEqual(web.ips_locales(), ["127.0.0.1"])


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

    def test_pantalla_por_internet_y_al_salir_se_borra_la_sesion(self):
        import time
        from unittest import mock
        from feria.pantalla import jugar_desde_menu
        from feria.web import ServidorFeriaLocal
        nube = ServidorFeriaLocal(PUERTOS_PRUEBA, host="127.0.0.1").iniciar()   # hace de Render
        vistas = {}

        def guion(pantalla, cuadro):
            if cuadro == 0:
                vistas["url"], vistas["codigo"] = pantalla.url, pantalla.sesion.codigo_sesion
                pantalla.accionar("votar_aqui")
                pantalla.accionar("decision:verificar")
                pantalla.accionar("categoria:suceso_natural")
                pantalla.accionar("enviar_pantalla")
            elif cuadro == 2:
                sesion = nube.registro.obtener(vistas["codigo"])
                limite = time.monotonic() + 5
                while sesion.para_pantalla()["votos"] < 1 and time.monotonic() < limite:
                    time.sleep(.05)
                vistas["votos"] = sesion.para_pantalla()["votos"]
        try:
            with mock.patch.dict(os.environ, {"COPA_FERIA_SERVIDOR": f"http://127.0.0.1:{nube.puerto}"}), \
                    mock.patch("feria.web.ServidorFeriaLocal") as local:
                self.assertIsNone(jugar_desde_menu(pygame.Surface((960, 720)), cuadros=4, al_dibujar=guion))
            local.assert_not_called()   # con internet no se abre ningún puerto en el computador
            self.assertEqual(vistas["url"], f"http://127.0.0.1:{nube.puerto}/feria/{vistas['codigo']}")
            self.assertEqual(vistas["votos"], 1)
            self.assertIsNone(nube.registro.obtener(vistas["codigo"]))
        finally:
            nube.detener()

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

    def test_el_texto_de_cada_caso_cabe_en_el_pergamino_y_la_tecla_i_cambia_de_red(self):
        from feria.pantalla import PantallaFeria
        sesion = SesionFeria()
        pantalla = PantallaFeria(sesion, ["http://192.168.137.1:8080/feria/AB12CD", "http://10.0.0.5:8080/feria/AB12CD"])
        instruccion = "Escanea el código con tu celular y decide qué hacer con este mensaje."
        ancho = pantalla.hueco_qr.right - pantalla.hueco_qr.x - 10 - pantalla.qr.get_width() - 46
        for caso in CASOS:
            with self.subTest(caso=caso["id"]):
                self.assertLessEqual(pantalla._alto_bloque(caso, instruccion, ancho, 16, 14), pantalla.hueco_qr.height - 14)
        superficie = pygame.Surface((960, 720))
        for _ in CASOS:
            pantalla.dibujar(superficie, (0, 0), 0)
            sesion.cerrar_ronda()
            sesion.abrir_ronda()
        pantalla.tecla(pygame.K_i)
        self.assertEqual(pantalla.url, "http://10.0.0.5:8080/feria/AB12CD")

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
