"""Cada era habla de lo suyo: nombres, lugares y objetos no se cruzan entre eras.

También comprueba que los números que se muestran (casos y estrellas) salen de
los datos, que la historia del puente no se contradice y que los créditos están.
"""
import json
import os
import re
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import test_leyes_penas as leyes  # noqa: E402  (solo su expresión COPA; no se copian sus pruebas)

from logica.conversaciones import REACCIONES, TESTIMONIOS, TESTIMONIOS_PRESENTE  # noqa: E402
from multijugador import campana, mision, nucleo, presente  # noqa: E402
from multijugador.aventura_final import EPILOGOS, RECONFIGURACION  # noqa: E402
from multijugador.clasificacion import CATEGORIA_EVENTO  # noqa: E402
from multijugador.dialogos import PERSONAJE_DE_ROL, PERSONAJE_FUTURO_DE_ROL, nombre_visible  # noqa: E402
from multijugador.exploracion import CONTENIDOS  # noqa: E402
from multijugador.expediente import CATALOGO  # noqa: E402
from multijugador.partida_local import ClienteCampanaLocal  # noqa: E402
from multijugador.presentacion import ETIQUETAS, INDICADORES_INICIALES, total_casos  # noqa: E402
from multijugador.protocolo import ROLES  # noqa: E402
from multijugador.suministros import ENCARGOS  # noqa: E402
from nucleo.rutas import RAIZ  # noqa: E402

# La expresión COPA de test_leyes_penas, ampliada con los objetos de La Copa.
COPA = re.compile(leyes.DialogosPorDimension.COPA + r"|(?i:\b(caldero|tronco|poción|pocion|tablilla)s?\b)")
# "Mira" también es un verbo ("Mira quién lo firma"): no es el personaje.
VERBO_MIRA = re.compile(r"\bMira (?=primero|quién)")
OTRAS_ERAS = re.compile(leyes.DialogosPorDimension.PRESENTE + "|" + "|".join(leyes.DialogosPorDimension.FUTUROS)
                        + r"|NÚCLEO|\bMateo\b|\bTomás\b")
PUENTE_ABIERTO = re.compile(r"abierto hoy|está abierto|sin problemas", re.IGNORECASE)
NOMBRE_VIEJO = "torm" + "enta"  # partido para que este archivo no se encuentre a sí mismo


def textos(valor):
    """Todas las cadenas dentro de tuplas, listas y diccionarios (también sus claves)."""
    if isinstance(valor, str):
        yield valor
    elif isinstance(valor, dict):
        for clave, dato in valor.items():
            yield from textos(clave)
            yield from textos(dato)
    elif isinstance(valor, (tuple, list, set)):
        for dato in valor:
            yield from textos(dato)


def paginas_ayuda():
    from interfaz.menu_pausa import PAGINAS_COMO_JUGAR
    return dict(PAGINAS_COMO_JUGAR)


def bots(dimension):
    return [nombre_visible({"nombre": ClienteCampanaLocal._nombre_bot(rol), "rol": rol, "controlador": "bot"}, dimension)
            for rol in ROLES]


class ElPresenteYElFuturoNoHablanDeLaCopa(unittest.TestCase):
    def revisar(self, origen, valor):
        for texto in textos(valor):
            with self.subTest(origen=origen, texto=texto):
                self.assertIsNone(COPA.search(VERBO_MIRA.sub("", texto)))

    def test_distrito_conecta(self):
        from interfaz.partida_multijugador import AVISO_SIN_OBJETIVO
        self.revisar("eventos y pistas", presente.EVENTOS)
        self.revisar("opciones", presente.OPCIONES)
        self.revisar("testimonios", {n: TESTIMONIOS_PRESENTE[n] for n in PERSONAJE_DE_ROL.values() if n in TESTIMONIOS_PRESENTE})
        self.revisar("testimonios de otros", {n: TESTIMONIOS_PRESENTE[n] for n in ("Darío Veraz", "Lía Nova")})
        self.revisar("ayuda", paginas_ayuda()["Distrito Conecta"])
        self.revisar("etiquetas", ETIQUETAS["presente"])
        self.revisar("epílogo", [t for era, t in EPILOGOS if era == "presente"])
        self.revisar("interiores", CONTENIDOS)
        self.revisar("aviso de E", AVISO_SIN_OBJETIVO["presente"])
        self.revisar("bots", bots("presente"))

    def test_ciudad_nucleo(self):
        from interfaz.partida_multijugador import AVISO_SIN_OBJETIVO
        self.revisar("textos de nucleo.py", [nucleo.TITULO, nucleo.NOTICIA, nucleo.OPCIONES, nucleo.TEXTOS, nucleo.REGISTROS,
                                             nucleo.TERMINALES, nucleo.TEXTO_LLAVE, nucleo.TEXTOS_PISTA, nucleo.CUENTAS,
                                             nucleo.HABILIDADES_FUTURO])
        self.revisar("testimonios", {n: TESTIMONIOS_PRESENTE[n] for n in PERSONAJE_FUTURO_DE_ROL.values()})
        self.revisar("ayuda", paginas_ayuda()["Ciudad Núcleo"])
        self.revisar("etiquetas", ETIQUETAS["futuro"])
        self.revisar("reconfiguración y epílogo", [RECONFIGURACION, [t for era, t in EPILOGOS if era == "futuro"]])
        self.revisar("aviso de E", AVISO_SIN_OBJETIVO["futuro"])
        self.revisar("bots", bots("futuro"))

    def test_el_futuro_usa_el_centro_de_supervision(self):
        for texto in (nucleo.TEXTO_LLAVE, *TESTIMONIOS_PRESENTE["Corredor de Datos"], *paginas_ayuda()["Ciudad Núcleo"]):
            self.assertNotIn("Centro de Verificación", texto)
        self.assertIn("Centro de Supervisión", nucleo.TEXTO_LLAVE)


class LaCopaNoNombraOtrasEras(unittest.TestCase):
    def test_textos_de_la_copa(self):
        from interfaz.partida_multijugador import AVISO_SIN_OBJETIVO
        fuentes = {"casos": campana.CASOS, "variantes": campana.VARIANTES, "habilidades": campana.HABILIDADES,
                   "avisos": campana.AVISOS_RECIENTES, "pruebas": mision.PRUEBAS, "opciones": mision.OPCIONES,
                   "mensajes": mision.MENSAJES, "testimonios": TESTIMONIOS, "reacciones": REACCIONES,
                   "encargos": ENCARGOS, "ayuda": paginas_ayuda()["La Copa"], "etiquetas": ETIQUETAS["la_copa"],
                   "epílogo": [t for era, t in EPILOGOS if era == "la_copa"], "aviso de E": AVISO_SIN_OBJETIVO["la_copa"],
                   "bots": bots("la_copa")}
        for origen, valor in fuentes.items():
            for texto in textos(valor):
                with self.subTest(origen=origen, texto=texto):
                    self.assertIsNone(OTRAS_ERAS.search(texto))

    def test_el_bot_mensajero_de_la_copa_no_es_mateo(self):
        self.assertEqual(ClienteCampanaLocal._nombre_bot("mensajero"), "Mensajero")

    def test_la_habilidad_del_habitante_no_nombra_a_luma(self):
        self.assertNotIn("Luma", " ".join(campana.HABILIDADES["habitante"]))


class EtiquetasPorEra(unittest.TestCase):
    def test_las_tres_eras_con_las_mismas_claves(self):
        self.assertEqual(set(ETIQUETAS), {"la_copa", "presente", "futuro"})
        for era, etiquetas in ETIQUETAS.items():
            self.assertEqual(set(etiquetas), set(INDICADORES_INICIALES), era)

    def test_el_futuro_no_hereda_las_de_la_copa(self):
        for clave in ("confianza", "susurros_falsos"):
            self.assertNotEqual(ETIQUETAS["futuro"][clave], ETIQUETAS["la_copa"][clave])


class NumerosDesdeLosDatos(unittest.TestCase):
    def test_el_total_de_casos_coincide_con_el_catalogo(self):
        ids = [c[0] for c in campana.CASOS] + [e["id"] for e in presente.EVENTOS] + [nucleo.CASO]
        self.assertEqual(total_casos(), len(ids))
        self.assertEqual(set(CATALOGO), set(ids))

    def test_el_total_de_estrellas_es_el_que_se_puede_ganar(self):
        # Por caso: acertar y que todos reúnan dos pistas; y una por cada encargo.
        self.assertEqual(campana.ESTRELLAS_TOTALES, 2 * len(campana.CASOS) + min(len(campana.CASOS), len(ENCARGOS)))

    def test_no_quedan_numeros_escritos_a_mano(self):
        prohibidos = re.compile(r"[Oo]cho casos|de 8\"|casos=8|'estrellas_total', 11|\"estrellas_total\", 11")
        for archivo in ("interfaz/expediente.py", "interfaz/desenlace.py", "interfaz/finales.py",
                        "interfaz/cooperativo.py", "interfaz/partida_multijugador.py"):
            with self.subTest(archivo=archivo):
                self.assertIsNone(prohibidos.search((RAIZ / archivo).read_text(encoding="utf-8")))


class HistoriaDelPuente(unittest.TestCase):
    def test_ningun_texto_dice_que_hoy_esta_abierto(self):
        caso = next(c for c in campana.CASOS if c[0] == "puente_norte")
        fuentes = [caso, mision.PRUEBAS, TESTIMONIOS["Rumor Politico"], REACCIONES["Rumor Politico"],
                   (RAIZ / "multijugador/mision.py").read_text(encoding="utf-8")]
        for texto in textos(fuentes):
            self.assertIsNone(PUENTE_ABIERTO.search(texto), texto[:120])

    def test_kael_no_es_culpable_y_la_ficha_es_un_rumor_politico(self):
        self.assertIn("no por Kael", campana.CASOS[0][5])
        self.assertEqual(CATALOGO["puente_norte"]["tipo"], "Rumor Político")
        self.assertEqual(CATEGORIA_EVENTO["puente_norte"][0], "Rumor Politico")


class SinCasosViejos(unittest.TestCase):
    def test_los_datos_solo_tienen_los_casos_vigentes(self):
        for nombre, datos in (("clasificación", CATEGORIA_EVENTO), ("expediente", CATALOGO),
                              ("avisos", campana.AVISOS_RECIENTES), ("variantes", campana.VARIANTES)):
            with self.subTest(datos=nombre):
                self.assertNotIn(NOMBRE_VIEJO, datos)
                self.assertNotIn("ayuda", datos)
        self.assertEqual(set(TESTIMONIOS), set(REACCIONES))
        self.assertEqual(set(TESTIMONIOS), {CATEGORIA_EVENTO[c[0]][0] for c in campana.CASOS})

    def test_ningun_archivo_fuera_de_legado_los_menciona(self):
        propio = os.path.abspath(__file__)
        excluidas = {"legado", ".venv", ".venv2", "build", "dist", "cache", "informes", "__pycache__", ".git", "Claude outputs"}
        for carpeta, subcarpetas, archivos in os.walk(RAIZ):
            subcarpetas[:] = [s for s in subcarpetas if s not in excluidas]
            for archivo in archivos:
                ruta = os.path.join(carpeta, archivo)
                if not archivo.endswith((".py", ".json")) or os.path.abspath(ruta) == propio:
                    continue
                with open(ruta, encoding="utf-8", errors="ignore") as entrada:
                    contenido = entrada.read()
                with self.subTest(archivo=os.path.relpath(ruta, RAIZ)):
                    self.assertNotIn(NOMBRE_VIEJO, contenido.lower())
                    # «ayuda» es palabra común: solo se busca como id de caso.
                    self.assertIsNone(re.search(r"(caso|evento|casos)\s*[=:]\s*[\"']ayuda[\"']|[\"']ayuda[\"']\s*:\s*\(", contenido))


class Creditos(unittest.TestCase):
    def test_equipo_profesora_e_integrantes(self):
        datos = json.loads((RAIZ / "datos/creditos.json").read_text(encoding="utf-8"))
        self.assertEqual(datos["equipo"], "Glitch Hunters")
        self.assertTrue(datos["profesora"])
        self.assertEqual(len(datos["integrantes"]), 4)
        self.assertTrue(all(p.get("nombre") for p in datos["integrantes"]))

    def test_los_creditos_muestran_todo_y_la_fuente(self):
        from interfaz.desenlace import filas_creditos
        filas = filas_creditos()
        self.assertEqual(filas[0], "Glitch Hunters")
        self.assertIn("Dirigido por: Katherine Ospino", filas)
        self.assertTrue(any("Determination" in f and "CC BY 3.0" in f for f in filas))
        self.assertTrue(any(f.startswith("Sebastian Ariza · ") for f in filas))
        self.assertFalse(any("Guardianes de la Memoria" in f for f in filas))


if __name__ == "__main__":
    unittest.main()
