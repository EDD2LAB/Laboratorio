"""Tandas anunciadas y pausas: reloj y colisiones exclusivamente del servidor."""
import math


class BatallaCooperativa:
    def __init__(self):
        self.fase = 1
        self.turno = "aviso"
        self.restante = 3.0
        self.blancos = []
        self.derribados = set()
        self.oleada = 1

    def reiniciar(self, hechos):
        self.fase = 2 if {"guardian", "habitante"} <= hechos else 1
        self.turno, self.restante = "aviso", 3.0
        self.blancos = []
        self.derribados.clear()
        self.oleada = 1

    def actualizar(self, dt, jugadores, presentes, hechos):
        nueva = 2 if {"guardian", "habitante"} <= hechos else 1
        if len(hechos) == 4:
            self.turno, self.blancos = "terminado", []
            self.derribados.clear()
            return []
        if nueva != self.fase:
            self.reiniciar(hechos)
        activos = {i: j for i, j in jugadores.items() if i in presentes
                   and j.get("dimension") == "futuro" and not j.get("interior")}
        self.derribados.intersection_update(activos)
        if self.turno == "aviso" and not self.blancos:
            self.blancos = [[round(j["x"]), round(j["y"])] for i, j in activos.items()
                            if i not in self.derribados][:4]
        self.restante = max(0, self.restante - dt)
        if self.restante > 0:
            return []
        if self.turno == "aviso":
            self.turno, self.restante = "rayo", .7
            radio = 22 if self.fase == 1 else 30
            golpes = [i for i, j in activos.items() if i not in self.derribados
                      and any(math.hypot(j["x"] - x, j["y"] - y) <= radio for x, y in self.blancos)]
            self.derribados.update(golpes)
            return golpes
        if self.turno == "rayo":
            if self.fase == 2 and self.oleada == 1:
                self.oleada = 2
                self.turno, self.restante, self.blancos = "aviso", 2.5, []
                return []
            self.turno, self.restante, self.blancos = "recarga", 26.0 if self.fase == 1 else 22.0, []
            # Nadie queda bloqueado sin compañero: la pausa recupera a los caídos.
            self.derribados.clear()
        else:
            self.turno, self.restante, self.blancos = "aviso", 3.0 if self.fase == 1 else 2.5, []
            self.oleada = 1
        return []

    def publico(self):
        return dict(fase=self.fase, turno=self.turno, segundos=round(self.restante, 1), oleada=self.oleada,
                    blancos=self.blancos, derribados=sorted(self.derribados))
