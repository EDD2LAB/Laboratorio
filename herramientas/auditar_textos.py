"""Lista candidatos a texto visible, sin cambiar textos del juego.

Es una auditoría estática: incluye avisos de error y ayudas, puede incluir
etiquetas internas y no reconstruye todos los textos compuestos en ejecución.
Las propuestas del informe requieren revisión humana antes de aplicarse.
"""
import ast
import csv
from pathlib import Path
import re

RAIZ = Path(__file__).resolve().parent.parent


def palabras(texto):
    return len(re.findall(r"\b[\wÁÉÍÓÚÜÑáéíóúüñ]+\b", texto))


def candidatos():
    filas = []
    for paquete in ("interfaz", "multijugador", "logica"):
        for archivo in sorted((RAIZ / paquete).glob("*.py")):
            fuente = archivo.read_text(encoding="utf-8-sig")
            arbol = ast.parse(fuente)
            padres = {hijo: padre for padre in ast.walk(arbol) for hijo in ast.iter_child_nodes(padre)}
            docstrings = set()
            for nodo in ast.walk(arbol):
                if isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    if nodo.body and isinstance(nodo.body[0], ast.Expr) and isinstance(nodo.body[0].value, ast.Constant):
                        docstrings.add(nodo.body[0].value)
            for nodo in ast.walk(arbol):
                if nodo in docstrings:
                    continue
                if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str) and not isinstance(padres.get(nodo), ast.JoinedStr):
                    texto = nodo.value.strip()
                elif isinstance(nodo, ast.JoinedStr):
                    texto = "".join(v.value if isinstance(v, ast.Constant) else "{dato}" for v in nodo.values)
                else:
                    continue
                if palabras(texto) < 3 or re.search(r"\.(png|jpg|json|py|mp3|wav|ttf)\b|https?://", texto, re.I):
                    continue
                filas.append((archivo.relative_to(RAIZ).as_posix(), nodo.lineno, palabras(texto), texto))
    return sorted(set(filas))


def main():
    filas = candidatos()
    with (RAIZ / "docs/textos.csv").open("w", encoding="utf-8-sig", newline="") as salida:
        escritor = csv.writer(salida)
        escritor.writerow(("archivo", "linea", "palabras", "texto"))
        escritor.writerows(filas)
    largas = sorted((f for f in filas if f[2] > 20), key=lambda f: (-f[2], f[0], f[1]))
    lineas = ["# Textos: inventario y propuestas pendientes de revisión", "",
              "Generado por `python herramientas/auditar_textos.py`. No modifica el juego.",
              f"Se encontraron {len(filas)} candidatos de tres o más palabras; {len(largas)} superan 20 palabras.",
              "El listado completo con archivo, línea, conteo y texto está en `textos.csv`.", "",
              "## Alcance", "",
              "Auditoría estática de interfaz, multijugador y lógica. Excluye docstrings, rutas y",
              "textos de menos de tres palabras. Los valores interpolados aparecen como {dato}.",
              "Puede incluir mensajes técnicos; no garantiza capturar cada texto construido en ejecución.",
              "Las leyes y sanciones del catálogo JSON no se recortan con esta herramienta.", "",
              "## Candidatos largos para revisar primero", "",
              "| Ubicación | Palabras | Texto actual |", "| --- | --- | --- |"]
    for archivo, numero, cantidad, texto in largas[:35]:
        texto = texto.replace("|", "/").replace("\n", " ")
        lineas.append(f"| `{archivo}:{numero}` | {cantidad} | {texto} |")
    propuestas = [
        ("Pista del agua: fecha del informe", "El informe habla de un depósito cerrado hace diez años."),
        ("Pista del agua: sustitución", "El depósito antiguo fue desconectado. El agua actual viene del manantial nuevo."),
        ("Pista del video original", "El video original muestra a Ronaldo poniendo monedas. Compáralo en Analizar."),
        ("Pista de la llave de supervisión", "El Corredor te dio la llave. Llévala al Centro de Verificación."),
        ("Pista sobre firmas de registros", "Revisa quién firma y cuándo. La firma debe ser de alguien autorizado."),
        ("Entrega del farol en el tutorial", "Lleva el farol al tronco brillante. Pulsa E para entregarlo."),
        ("Solicitud de una segunda pista", "Pide otra pista con I. Comparte también la tuya."),
    ]
    lineas += ["", "## Propuestas que todavía NO se aplican", "",
               "Objetivo de lectura: hasta 20 palabras por tarjeta. Revisar el contexto completo",
               "y el mensaje educativo antes de aprobar cada propuesta; no son sustituciones automáticas.",
               "Los avisos breves deberían caber en dos líneas. Las pruebas y normas completas deben",
               "seguir disponibles en el expediente aunque se aprueben resúmenes.", "",
               "| Tarjeta / finalidad | Propuesta | Palabras |", "| --- | --- | --- |"]
    for nombre, texto in propuestas:
        lineas.append(f"| {nombre} | {texto} | {palabras(texto)} |")
    (RAIZ / "docs/textos.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"Auditoría: {len(filas)} candidatos, {len(largas)} con más de 20 palabras; propuestas sin aplicar.")


if __name__ == "__main__":
    main()
