"""Ruta de luces sobre el suelo transitable y pequeñas celebraciones locales."""
import heapq
import math


def buscar_camino(colisiones, origen, destino, limite=10000):
    """A* con pasos de ocho píxeles, comprobando también el punto intermedio."""
    inicio = (round(origen[0]), round(origen[1]))
    def distancia(p):
        return math.hypot(p[0]-destino[0], p[1]-destino[1])
    cola = [(distancia(inicio), 0, inicio)]
    costes = {inicio: 0}
    anteriores = {}
    while cola and len(costes) < limite:
        _, coste, punto = heapq.heappop(cola)
        if coste != costes[punto]:
            continue
        if distancia(punto) <= 54:
            ruta = [punto]
            while ruta[-1] in anteriores:
                ruta.append(anteriores[ruta[-1]])
            return list(reversed(ruta))
        for dx, dy in ((8, 0), (-8, 0), (0, 8), (0, -8)):
            vecino = (punto[0]+dx, punto[1]+dy)
            nuevo = coste+8
            if nuevo >= costes.get(vecino, float("inf")):
                continue
            if colisiones.bloqueado(*vecino) or colisiones.bloqueado(punto[0]+dx/2, punto[1]+dy/2):
                continue
            costes[vecino] = nuevo
            anteriores[vecino] = punto
            heapq.heappush(cola, (nuevo+max(0, distancia(vecino)-54), nuevo, vecino))
    return []


def estrella(superficie, centro, radio, color):
    import pygame
    puntos = []
    for i in range(10):
        angulo = -math.pi/2+i*math.pi/5
        r = radio if i%2==0 else radio*.45
        puntos.append((centro[0]+math.cos(angulo)*r, centro[1]+math.sin(angulo)*r))
    pygame.draw.polygon(superficie, color, puntos)
