"""Iconos y señales del encargo, dibujados con píxeles y formas simples."""
import pygame


def dibujar_carga(superficie, material, centro):
    x, y = centro
    pygame.draw.rect(superficie, (15, 35, 27), (x-16, y-15, 32, 30), border_radius=4)
    if material == "farol":
        pygame.draw.circle(superficie, (255, 226, 116), (x, y), 10)
        pygame.draw.rect(superficie, (186, 123, 57), (x-9, y-12, 18, 5))
        pygame.draw.rect(superficie, (186, 123, 57), (x-9, y+8, 18, 5))
    elif material == "tablas":
        for dy in (-9, -2, 5):
            pygame.draw.rect(superficie, (179, 120, 65), (x-12, y+dy, 24, 5))
            pygame.draw.line(superficie, (95, 62, 39), (x-9, y+dy+2), (x+9, y+dy+2))
    elif material == "cuerdas":
        for radio in (11, 7, 3):
            pygame.draw.circle(superficie, (223, 189, 116), (x, y), radio, 2)
    elif material == "pergaminos":
        pygame.draw.rect(superficie, (242, 224, 175), (x-9, y-11, 18, 22))
        for dy in (-5, 0, 5):
            pygame.draw.line(superficie, (145, 101, 64), (x-5, y+dy), (x+5, y+dy))
    elif material == "provisiones":
        pygame.draw.ellipse(superficie, (169, 120, 67), (x-11, y-6, 22, 18))
        pygame.draw.rect(superficie, (218, 185, 111), (x-5, y-10, 10, 5))
    else:
        color = (90, 193, 233) if material == "agua" else (175, 117, 219)
        pygame.draw.rect(superficie, color, (x-8, y-7, 16, 18), border_radius=3)
        pygame.draw.rect(superficie, (228, 213, 168), (x-4, y-12, 8, 5))


def dibujar_encargos(superficie, caso, fuente):
    encargo = caso.get("encargo")
    if encargo:
        for material in encargo["materiales"]:
            o = material["fuente"]
            x, y = o["x"] + 23, o["y"] - 22
            dibujar_carga(superficie, material["id"], (x, y))
            texto = fuente.render(material["nombre"] + (": listo" if material["entregado"] else " · E"), True, (255, 239, 191))
            caja = texto.get_rect(midtop=(x, y+17))
            caja.clamp_ip(superficie.get_rect().inflate(-10, -10))
            pygame.draw.rect(superficie, (15, 35, 27), caja.inflate(6, 4))
            superficie.blit(texto, caja)
        d = encargo["destino"]
        pygame.draw.circle(superficie, (128, 238, 180), (d["x"], d["y"]), 24, 3)
        progreso = encargo.get("actividad", {}).get("progreso", 0)
        if encargo.get("materiales_listos"):
            for i in range(3):
                x, y = d["x"]-27+i*19, d["y"]-25
                color = (246, 202, 105) if i < progreso else (48, 74, 51)
                pygame.draw.rect(superficie, color, (x, y, 15, 8), border_radius=2)
        etiqueta = fuente.render(("AYUDAR JUNTOS · E" if encargo.get("materiales_listos") else "ENTREGAR · E") if not encargo["completo"] else "¡GRACIAS, EQUIPO!", True, (128, 238, 180))
        superficie.blit(etiqueta, etiqueta.get_rect(midtop=(d["x"], d["y"]+28)))
    for obra in caso.get("obras", []) + ([encargo] if encargo and encargo["completo"] else []):
        d = obra["destino"]
        x, y = d["x"]-22, d["y"]-36
        pygame.draw.line(superficie, (225, 189, 105), (x, y), (x, y+28), 3)
        pygame.draw.polygon(superficie, (100, 223, 152), ((x, y), (x+18, y+6), (x, y+12)))
        texto = fuente.render(obra["efecto"], True, (128, 238, 180))
        caja = texto.get_rect(midtop=(d["x"], d["y"]+46))
        caja.clamp_ip(superficie.get_rect().inflate(-10, -10))
        pygame.draw.rect(superficie, (15, 35, 27), caja.inflate(6, 4))
        superficie.blit(texto, caja)
