"""Simula las reglas y COPY del Dockerfile del servidor y prueba el resultado.

No sustituye `docker build`: no prueba la imagen base, pip de Linux ni USER.
Admite las reglas glob usadas por este proyecto y COPY locales sin flags.
Rechaza sintaxis adicional para evitar afirmar que validó algo que no entiende.
"""
import argparse
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

RAIZ = Path(__file__).resolve().parent.parent


def coincide(patron, ruta):
    patron = patron.rstrip("/")
    trozos = patron.split("/")
    expresion = ""
    for i, trozo in enumerate(trozos):
        if trozo == "**":
            expresion += ".*" if i == len(trozos) - 1 else "(?:[^/]+/)*"
        else:
            if any(c in trozo for c in "[]\\"):
                raise ValueError("Patrón no admitido por la simulación: " + patron)
            expresion += re.escape(trozo).replace(r"\*", "[^/]*").replace(r"\?", "[^/]")
            if i < len(trozos) - 1:
                expresion += "/"
    # Una regla que coincide con un directorio se hereda por sus descendientes.
    return re.fullmatch(expresion + "(?:/.*)?", ruta) is not None


def permitido(ruta, reglas):
    incluir = True
    for regla in reglas:
        if coincide(regla.lstrip("!"), ruta):
            incluir = regla.startswith("!")
    return incluir


PRUEBA = '''
import json, sys
from pathlib import Path
from multijugador.servicio_internet import ServicioSalas
from multijugador.tiempo_real import crear_app
from multijugador.protocolo import VERSION, MAX_MENSAJE, codificar
import multijugador.servicio_internet as modulo
assert Path(modulo.__file__).resolve().is_relative_to(Path.cwd())
assert 'pygame' not in sys.modules
reloj = [0.0]
s = ServicioSalas(lambda: reloj[0])
jugadores = []
for i, rol in enumerate(('guardian', 'mensajero')):
    datos = {'version': VERSION, 'nombre': 'Prueba' + str(i)}
    if i: datos['codigo'] = jugadores[0]['codigo']
    j = s.ejecutar('POST', '/v1/crear' if not i else '/v1/unirse', datos)
    jugadores.append(j)
    for accion in ({'tipo': 'rol', 'rol': rol}, {'tipo': 'listo', 'listo': True}):
        s.ejecutar('POST', '/v1/accion', accion, j['token'])
s.ejecutar('POST', '/v1/accion', {'tipo': 'iniciar'}, jugadores[0]['token'])
sala = s.salas[jugadores[0]['codigo']]
for tick in range(200):
    reloj[0] = (tick + 1) * .05
    sala.partida.actualizar(reloj[0])
    sala.actualizar_bots(reloj[0])
estado = sala._estado(jugadores[0]['id'])
assert estado['fase'] == 'partida'
assert len(estado['mundo']['jugadores']) == 4
assert len(codificar(estado)) <= MAX_MENSAJE
assert 'pygame' not in sys.modules
print(json.dumps({'ok': True, 'protocolo': VERSION, 'humanos': 2, 'jugadores': 4,
                  'ticks': 200, 'casos': s.ejecutar('GET', '/health', {})['casos'],
                  'sin_pygame': True}))
'''


def verificar():
    reglas = [r.strip() for r in (RAIZ / "Dockerfile.multijugador.dockerignore").read_text(encoding="utf-8").splitlines()
              if r.strip() and not r.lstrip().startswith("#")]
    copias = []
    for linea in (RAIZ / "Dockerfile.multijugador").read_text(encoding="utf-8").splitlines():
        if not linea.startswith("COPY "):
            continue
        partes = shlex.split(linea)[1:]
        if any(p.startswith(("--", "[")) or "*" in p for p in partes):
            raise ValueError("COPY no admitido por esta simulación: " + linea)
        destino = partes[-1]
        if not destino.startswith("/app/") or ".." in Path(destino).parts:
            raise ValueError("Destino fuera de /app: " + destino)
        copias += [(origen, destino.removeprefix("/app/")) for origen in partes[:-1]]
    with tempfile.TemporaryDirectory(prefix="timeless-docker-") as nombre:
        contexto = Path(nombre)
        cantidad = 0
        for origen, destino in copias:
            fuente = RAIZ / origen
            archivos = list(fuente.rglob("*")) if fuente.is_dir() else [fuente]
            for archivo in archivos:
                if not archivo.is_file() or not permitido(archivo.relative_to(RAIZ).as_posix(), reglas):
                    continue
                relativo = archivo.relative_to(fuente) if fuente.is_dir() else Path(archivo.name)
                salida = contexto / destino / relativo
                salida.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(archivo, salida)
                cantidad += 1
        resultado = subprocess.run([sys.executable, "-c", PRUEBA], cwd=contexto,
                                   text=True, encoding="utf-8", capture_output=True, timeout=90)
        if resultado.returncode:
            raise RuntimeError(resultado.stderr or resultado.stdout)
        datos = json.loads(resultado.stdout.strip().splitlines()[-1])
        return dict(datos, archivos_copiados=cantidad, tipo="simulacion_contexto_no_build")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path)
    args = parser.parse_args()
    resultado = verificar()
    texto = json.dumps(resultado, ensure_ascii=False, indent=2)
    print(texto)
    if args.salida:
        args.salida.write_text(texto + "\n", encoding="utf-8")
