"""Ruta de luces sobre el suelo transitable y pequeñas celebraciones locales."""
import heapq
import math


def buscar_camino(colisiones, origen, destino, limite=10000, radio=54, paso=8):
    """A* comprobando todo el segmento; paso fino para descansillos estrechos."""
    inicio = (round(origen[0]), round(origen[1]))
    def distancia(p):
        return math.hypot(p[0]-destino[0], p[1]-destino[1])
    def estimacion(p):
        # La ruta usa cuatro direcciones. Esta cota evita explorar media ciudad
        # con la cuadrícula fina y sigue admitiendo llegar al radio de uso.
        manhattan = abs(p[0]-destino[0]) + abs(p[1]-destino[1])
        return max(0, distancia(p)-radio, manhattan-radio*math.sqrt(2))
    cola = [(estimacion(inicio), 0, inicio)]
    costes = {inicio: 0}
    anteriores = {}
    while cola and len(costes) < limite:
        _, coste, punto = heapq.heappop(cola)
        if coste != costes[punto]:
            continue
        if distancia(punto) <= radio:
            ruta = [punto]
            while ruta[-1] in anteriores:
                ruta.append(anteriores[ruta[-1]])
            return list(reversed(ruta))
        for dx, dy in ((paso, 0), (-paso, 0), (0, paso), (0, -paso)):
            vecino = (punto[0]+dx, punto[1]+dy)
            nuevo = coste+paso
            if nuevo >= costes.get(vecino, float("inf")):
                continue
            if colisiones.bloqueado(*vecino) or not colisiones.trayecto_libre(punto, vecino):
                continue
            costes[vecino] = nuevo
            anteriores[vecino] = punto
            heapq.heappush(cola, (nuevo+estimacion(vecino), nuevo, vecino))
    return []


def siguiente_paso(colisiones, origen, ruta, distancia=48):
    """Mira hacia el próximo tramo visible, sin señalar a través de paredes.

    La ruta puede tener unos cuadros de antigüedad: empezar en el punto más
    cercano que aún se alcanza evita que la flecha pida volver hacia atrás.
    """
    candidatos = [(math.dist(origen, p), i) for i, p in enumerate(ruta)]
    for _, inicio in sorted(candidatos):
        if colisiones.trayecto_libre(origen, ruta[inicio]):
            break
    else:
        return None
    siguiente = ruta[inicio]
    for punto in ruta[inicio + 1:]:
        if not colisiones.trayecto_libre(origen, punto):
            break
        siguiente = punto
        if math.dist(origen, punto) >= distancia:
            break
    return siguiente if math.dist(origen, siguiente) >= 3 else None


def estrella(superficie, centro, radio, color):
    import pygame
    puntos = []
    for i in range(10):
        angulo = -math.pi/2+i*math.pi/5
        r = radio if i%2==0 else radio*.45
        puntos.append((centro[0]+math.cos(angulo)*r, centro[1]+math.sin(angulo)*r))
    pygame.draw.polygon(superficie, color, puntos)
