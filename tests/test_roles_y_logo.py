"""Elección de personaje (Kael y Tarek por defecto), textos del puente, icono y logo."""
import os
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from multijugador.campana import CASOS  # noqa: E402
from multijugador.dialogos import personajes_elegidos  # noqa: E402
from multijugador.movimiento import PartidaMovimiento  # noqa: E402
from multijugador.partida_local import ClienteCampanaLocal  # noqa: E402
from nucleo.rutas import RAIZ  # noqa: E402


def partida(aspirante=None, habitante=None):
    return PartidaMovimiento([dict(id="0", nombre="A", rol="aspirante", apariencia=aspirante),
                              dict(id="1", nombre="B", rol="habitante", apariencia=habitante),
                              dict(id="2", nombre="C", rol="guardian"), dict(id="3", nombre="D", rol="mensajero")], 0)


def nombres_npc(p):
    return {n["nombre"] for n in p.mision.dialogos.publico() if n["dimension"] == "la_copa"}


class Eleccion(unittest.TestCase):
    def test_sin_apariencia_son_kael_y_tarek(self):
        self.assertEqual(personajes_elegidos([dict(rol="aspirante"), dict(rol="habitante", apariencia=None)]), {"Kael", "Tarek"})

    def test_guardian_y_mensajero_no_eligen(self):
        self.assertEqual(personajes_elegidos([dict(rol="guardian", apariencia="mujer"), dict(rol="mensajero", apariencia="mujer")]), set())

    def test_el_que_no_se_elige_queda_como_npc_y_el_elegido_no_se_duplica(self):
        por_defecto = nombres_npc(partida())
        self.assertLessEqual({"Mira", "Luma"}, por_defecto)
        self.assertFalse({"Kael", "Tarek"} & por_defecto)
        eligieron = nombres_npc(partida("mujer", "mujer"))
        self.assertIn("Kael", eligieron)
        self.assertFalse({"Mira", "Luma"} & eligieron)

    def test_el_bot_aspirante_es_kael(self):
        self.assertEqual(ClienteCampanaLocal._nombre_bot("aspirante"), "Kael · Aspirante")


class Vista(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)

    def vista(self, *apariencias):
        from interfaz.partida_multijugador import VistaPartida
        p = partida(*apariencias)
        return VistaPartida("0", {"mundo": p.estado("0")})

    def test_el_gemelo_decorativo_no_se_dibuja(self):
        v = self.vista()
        personajes = {o.get("personaje") for o in v.decoraciones}
        self.assertLessEqual({"Kael", "Mira", "Luma"}, personajes)
        self.assertLessEqual({"Kael", "Tarek"}, v._npcs_gemelos())
        self.assertFalse({"Mira", "Luma"} & v._npcs_gemelos())
        self.assertLessEqual({"Mira", "Luma"}, self.vista("mujer", "mujer")._npcs_gemelos())

    def test_la_apariencia_solo_cambia_en_la_copa(self):
        v = self.vista("mujer")
        datos = dict(rol="aspirante", apariencia="mujer")
        self.assertEqual(v._clave_figura(datos), "aspirante_mujer")
        v.dimension = "presente"
        self.assertEqual(v._clave_figura(datos), "aspirante")


class Puente(unittest.TestCase):
    def test_textos_del_caso(self):
        caso = CASOS[0]
        self.assertEqual(caso[1], "¿Quién rompió el puente norte?")
        self.assertIn("Kael rompió el puente", caso[2])
        self.assertIn("no por Kael", caso[5])

    def test_el_resultado_correcto_no_culpa_a_kael(self):
        p = partida()
        publico = p.mision.publico(p.conectados)
        self.assertEqual(publico["titulo"].split(" · ", 1)[1], "¿Quién rompió el puente norte?")

    def test_la_regla_esta_en_claude_md(self):
        texto = (RAIZ / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("El Aspirante puede ser Kael (predeterminado) o Mira", texto)
        self.assertNotIn("Mira es la Aspirante controlable", texto)


class Logo(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)

    def test_icono_de_ventana(self):
        from nucleo.recursos import aplicar_icono_ventana
        self.assertEqual(aplicar_icono_ventana().get_size(), (32, 32))

    def test_el_icono_se_aplica_antes_de_cada_ventana(self):
        for archivo in ("interfaz/menu_pausa.py", "un_jugador/ventana.py", "editores/hitbox_editor.py",
                        "editores/personaje_editor.py", "editores/alineacion_editor.py"):
            texto = Path(RAIZ / archivo).read_text(encoding="utf-8")
            self.assertLess(texto.index("aplicar_icono_ventana()"), texto.index("display.set_mode"), archivo)

    def test_logo_dentro_del_panel_y_sin_tapar_botones(self):
        from interfaz.inicio import CENTRO_LOGO, MenuInicio
        menu = MenuInicio()
        menu.dibujar()
        panel, logo = pygame.Rect(240, 70, 480, 590), menu.logo.rect(CENTRO_LOGO)
        self.assertTrue(panel.contains(logo))
        for clave, boton in menu.botones.items():
            self.assertFalse(boton.rect.colliderect(logo), clave)

    def test_glitch_breve_cada_pocos_segundos_con_cuadros_precalculados(self):
        from interfaz.logo import LogoAnimado
        logo = LogoAnimado(semilla=1)
        conocidos = {id(c) for c in logo.brillos + logo.glitches}
        vistos_glitch, inicios, anterior = 0, [], False
        for ahora in range(0, 30000, 10):
            cuadro = logo.cuadro(ahora)
            self.assertIn(id(cuadro), conocidos)
            activo = any(cuadro is g for g in logo.glitches)
            vistos_glitch += activo
            if activo and not anterior:
                inicios.append(ahora)
            anterior = activo
        self.assertGreater(len(inicios), 3)
        self.assertLessEqual(vistos_glitch, len(inicios) * 16)
        for a, b in zip(inicios, inicios[1:]):
            self.assertTrue(3000 <= b - a <= 5200, b - a)


if __name__ == "__main__":
    unittest.main()
