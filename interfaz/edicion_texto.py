"""Edición de los campos de texto: cursor, selección, copiar, cortar y pegar."""
import pygame

from nucleo import portapapeles


class EditorCampos:
    """Lleva el cursor de cada campo; el texto sigue en el diccionario ``campos``."""

    def __init__(self, campos, limites, filtros=None, solo_lectura=()):
        self.campos = campos
        self.limites = limites
        self.filtros = filtros or {}
        self.solo_lectura = set(solo_lectura)
        self._cursores = {}  # campo -> [cursor, ancla]

    def posiciones(self, clave):
        """(cursor, ancla) válidos aunque el texto haya cambiado desde fuera."""
        largo = len(self.campos[clave])
        cursor, ancla = self._cursores.get(clave, (largo, largo))
        return min(cursor, largo), min(ancla, largo)

    def seleccion(self, clave):
        cursor, ancla = self.posiciones(clave)
        return min(cursor, ancla), max(cursor, ancla)

    def colocar(self, clave, cursor, extender=False):
        cursor = max(0, min(cursor, len(self.campos[clave])))
        ancla = self.posiciones(clave)[1] if extender else cursor
        self._cursores[clave] = [cursor, ancla]

    def seleccionar_todo(self, clave):
        self._cursores[clave] = [len(self.campos[clave]), 0]

    def texto_seleccionado(self, clave):
        inicio, fin = self.seleccion(clave)
        return self.campos[clave][inicio:fin]

    def insertar(self, clave, nuevo):
        """Escribe (o pega) reemplazando la selección y respetando el campo."""
        if clave in self.solo_lectura:
            return
        filtro = self.filtros.get(clave)
        nuevo = "".join(c for c in (filtro(nuevo) if filtro else nuevo) if c.isprintable())
        inicio, fin = self.seleccion(clave)
        texto = self.campos[clave]
        nuevo = nuevo[:max(0, self.limites[clave] - (len(texto) - (fin - inicio)))]
        self.campos[clave] = texto[:inicio] + nuevo + texto[fin:]
        self.colocar(clave, inicio + len(nuevo))

    def borrar(self, clave, adelante=False):
        if clave in self.solo_lectura:
            return
        inicio, fin = self.seleccion(clave)
        if inicio == fin:
            if adelante:
                fin = min(fin + 1, len(self.campos[clave]))
            else:
                inicio = max(inicio - 1, 0)
        self.campos[clave] = self.campos[clave][:inicio] + self.campos[clave][fin:]
        self.colocar(clave, inicio)

    def _palabra(self, clave, cursor, paso):
        texto = self.campos[clave]
        i = cursor
        while 0 <= i + (paso if paso < 0 else 0) < len(texto) and texto[i + (paso if paso < 0 else 0)].isspace():
            i += paso
        while 0 <= i + (paso if paso < 0 else 0) < len(texto) and not texto[i + (paso if paso < 0 else 0)].isspace():
            i += paso
        return i

    def manejar_tecla(self, evento, clave):
        """True si la tecla era de edición (flechas, Inicio, Ctrl+C...)."""
        control = bool(evento.mod & pygame.KMOD_CTRL)
        extender = bool(evento.mod & pygame.KMOD_SHIFT)
        cursor, ancla = self.posiciones(clave)
        inicio, fin = self.seleccion(clave)
        if control and evento.key == pygame.K_a:
            self.seleccionar_todo(clave)
        elif control and evento.key in (pygame.K_c, pygame.K_x):
            if inicio != fin:
                portapapeles.copiar(self.campos[clave][inicio:fin])
                if evento.key == pygame.K_x:
                    self.borrar(clave)
        elif control and evento.key == pygame.K_v:
            self.insertar(clave, portapapeles.pegar().replace("\r", " ").replace("\n", " ").strip())
        elif evento.key == pygame.K_BACKSPACE:
            self.borrar(clave)
        elif evento.key == pygame.K_DELETE:
            self.borrar(clave, adelante=True)
        elif evento.key in (pygame.K_LEFT, pygame.K_RIGHT):
            paso = -1 if evento.key == pygame.K_LEFT else 1
            if inicio != fin and not extender and not control:
                self.colocar(clave, inicio if paso < 0 else fin)
            else:
                self.colocar(clave, self._palabra(clave, cursor, paso) if control else cursor + paso, extender)
        elif evento.key == pygame.K_HOME:
            self.colocar(clave, 0, extender)
        elif evento.key == pygame.K_END:
            self.colocar(clave, len(self.campos[clave]), extender)
        else:
            return False
        return True

    def indice_en(self, clave, x, fuente):
        """Letra del campo más cercana a ``x`` (píxeles desde el inicio del texto)."""
        texto = self.campos[clave]
        return min(range(len(texto) + 1), key=lambda i: abs(fuente.size(texto[:i])[0] - x))
