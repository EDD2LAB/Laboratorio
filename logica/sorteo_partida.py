"""Una fuente de azar privada por partida. La semilla no viaja a los clientes."""
import random
import secrets


class SorteoPartida:
    def __init__(self, semilla=None):
        if semilla is not None and (type(semilla) is not int or not 0 <= semilla < 2**64):
            raise ValueError("La semilla debe ser un entero de 64 bits sin signo.")
        self.semilla = secrets.randbits(64) if semilla is None else semilla
        self.azar = random.Random(self.semilla)

    def elegir(self, opciones):
        return self.azar.choice(opciones)

    def vigencia(self, evento, rol):
        return random.Random(f"{self.semilla}:{evento}:{rol}").choice((90, 120, 150))

    def casos(self, originales, variantes):
        casos = [self.elegir((caso, variantes[caso[0]])) if caso[0] in variantes else caso for caso in originales]
        # Se sortea a quién menciona la acusación, nunca quién es culpable.
        # Las pruebas siguen demostrando retrasos, no apropiación de la ayuda.
        persona = self.elegir(("Mira", "Kael", "Luma", "Naira"))
        ayuda = list(casos[-1])
        ayuda[2] = ayuda[2].replace("Mira", persona)
        ayuda[4] = dict(ayuda[4])
        titulo, texto = ayuda[4]["aspirante"]
        ayuda[4]["aspirante"] = ("Inventario del reparto", texto)
        casos[-1] = tuple(ayuda)
        return tuple(casos)
