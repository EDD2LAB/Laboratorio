"""Estado temporal de una sesión de feria: solo en memoria, sin tocar el juego.

Lo usan a la vez el servidor web (votos de los celulares) y la pantalla grande,
desde hilos distintos: todo cambio pasa por un candado.
"""
import re
import secrets
import threading

from feria.casos import CASOS, CATEGORIAS, DECISIONES, NOMBRE_CATEGORIA, POR_ID, RESPONSABLES, RIESGOSAS, publico

LETRAS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # sin 0/O ni 1/I/L: se dictan sin confusión
DISPOSITIVO = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
MAX_VOTOS_RONDA = 2000
UMBRAL_POSITIVO, UMBRAL_CRITICO = .6, .4


def nuevo_codigo():
    return "".join(secrets.choice(LETRAS) for _ in range(6))


class VotoInvalido(ValueError):
    """El celular recibe este texto tal cual."""


class SesionFeria:
    def __init__(self, codigo=None, casos=CASOS):
        self.codigo_sesion = codigo or nuevo_codigo()
        self.token_anfitrion = secrets.token_urlsafe(24)
        self.casos = [caso["id"] for caso in casos]
        self.ronda_actual = 0          # cuántas rondas se han abierto (la primera es 1)
        self.caso_actual = None
        self.abierta = False
        self.respuestas = {}           # dispositivo -> (decision, categoria) de la ronda actual
        self.participantes_unicos = set()
        self.resultado = None
        self.historial = []            # resultados de rondas cerradas (resumen de la sesión)
        self._candado = threading.Lock()
        self.abrir_ronda()

    # --- Rondas --------------------------------------------------------------
    def abrir_ronda(self):
        with self._candado:
            self.ronda_actual += 1
            self.caso_actual = self.casos[(self.ronda_actual - 1) % len(self.casos)]
            self.respuestas = {}
            self.resultado = None
            self.abierta = True
            return self.ronda_actual

    def cerrar_ronda(self):
        with self._candado:
            if not self.abierta:
                return self.resultado
            self.abierta = False
            self.resultado = self._resultado()
            self.historial.append(self.resultado)
            return self.resultado

    # --- Votos ---------------------------------------------------------------
    def votar(self, dispositivo, ronda, decision, categoria):
        if type(dispositivo) is not str or not DISPOSITIVO.match(dispositivo):
            raise VotoInvalido("No se reconoce este celular. Recarga la página.")
        if decision not in dict(DECISIONES) or categoria not in dict(CATEGORIAS):
            raise VotoInvalido("Elige una decisión y una categoría.")
        with self._candado:
            if type(ronda) is not int or ronda != self.ronda_actual:
                raise VotoInvalido("Esta ronda ya terminó. Mira la pantalla grande.")
            if not self.abierta:
                raise VotoInvalido("La votación de esta ronda está cerrada.")
            if dispositivo in self.respuestas:
                raise VotoInvalido("Ya votaste en esta ronda. ¡Gracias!")
            if len(self.respuestas) >= MAX_VOTOS_RONDA:
                raise VotoInvalido("La ronda está llena. Espera la siguiente.")
            self.respuestas[dispositivo] = (decision, categoria)
            self.participantes_unicos.add(dispositivo)
            return len(self.respuestas)

    # --- Lecturas --------------------------------------------------------------
    def _resultado(self):
        caso = POR_ID[self.caso_actual]
        total = len(self.respuestas)
        decisiones = {clave: 0 for clave, _ in DECISIONES}
        categorias = {clave: 0 for clave, _ in CATEGORIAS}
        for decision, categoria in self.respuestas.values():
            decisiones[decision] += 1
            categorias[categoria] += 1
        responsables = sum(decisiones[d] for d in RESPONSABLES)
        riesgosas = sum(decisiones[d] for d in RIESGOSAS)
        indice = responsables / total if total else 0.0
        if total and indice >= UMBRAL_POSITIVO:
            caldero = "positivo"
        elif total and riesgosas / total >= UMBRAL_CRITICO:
            caldero = "critico"
        else:
            caldero = "dudoso"
        return {
            "ronda": self.ronda_actual, "caso": caso["id"], "total": total,
            "decisiones": decisiones, "categorias": categorias,
            "categoria_correcta": caso["categoria"], "nombre_categoria": NOMBRE_CATEGORIA[caso["categoria"]],
            "aciertos_categoria": categorias[caso["categoria"]],
            "responsables": responsables, "riesgosas": riesgosas, "indice_responsable": indice,
            "caldero": caldero, "verdad": caso["verdad"], "ensenanza": caso["ensenanza"],
        }

    def para_celular(self):
        """Ronda abierta y caso, sin respuestas correctas ni votos de otros."""
        with self._candado:
            return {"ronda": self.ronda_actual, "abierta": self.abierta,
                    "caso": publico(POR_ID[self.caso_actual]),
                    "decisiones": DECISIONES, "categorias": CATEGORIAS}

    def para_pantalla(self):
        """Lo que muestra la pantalla grande: el total mientras se vota y el
        resultado colectivo solo al cerrar (nunca votos individuales)."""
        with self._candado:
            return {"codigo": self.codigo_sesion, "ronda": self.ronda_actual, "abierta": self.abierta,
                    "caso": dict(POR_ID[self.caso_actual]), "votos": len(self.respuestas),
                    "participantes": len(self.participantes_unicos),
                    "resultado": dict(self.resultado) if self.resultado else None,
                    "rondas_cerradas": len(self.historial)}
