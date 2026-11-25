<#
.SYNOPSIS
  Crea el ejecutable de Timeless Glitch para la feria (PyInstaller, --onedir).

.DESCRIPTION
  Ejecutar desde la raíz del proyecto:
      powershell -ExecutionPolicy Bypass -File herramientas\empaquetar.ps1
  Resultado: dist\TimelessGlitch\TimelessGlitch.exe y dist\TimelessGlitch.zip.

  -Diagnostico crea además dist\diagnostico\TimelessGlitchDiag (con consola, sin
  --windowed): recorre menú, campaña local y portales sin pantalla
  (herramientas\diagnostico_exe.py) e imprime cada paso.
#>
param([switch]$Diagnostico)

$ErrorActionPreference = "Stop"
$Raiz = Split-Path -Parent $PSScriptRoot
Set-Location $Raiz
$Python = Join-Path $Raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "No existe .venv. Crea el entorno: py -3.12 -m venv .venv e instala requirements.txt."
}

# 1. PyInstaller y Pillow solo en el .venv, con versiones fijas.
& $Python -m pip show pyinstaller pillow *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Instalando PyInstaller y Pillow en .venv..."
    & $Python -m pip install -r requirements-empaquetar.txt
    if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las herramientas de empaquetado." }
}

# Icono: el PNG del juego convertido a .ico (varios tamaños, vecino más cercano).
New-Item -ItemType Directory -Force "build" | Out-Null
$Icono = Join-Path $Raiz "build\TimelessGlitch.ico"
& $Python -c @"
from PIL import Image
imagen = Image.open(r'Imagenes/Iconos/Icono_juego.png').convert('RGBA')
imagen = imagen.crop(imagen.getbbox() or (0, 0, *imagen.size))
lado = max(imagen.size)
cuadro = Image.new('RGBA', (lado, lado), (0, 0, 0, 0))
cuadro.paste(imagen, ((lado - imagen.width) // 2, (lado - imagen.height) // 2))
cuadro.resize((256, 256), Image.NEAREST).save(r'$Icono', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
"@
if ($LASTEXITCODE -ne 0) { throw "No se pudo convertir el icono." }

# 2. Datos que el juego lee en tiempo de ejecución (todo relativo a nucleo.rutas.RAIZ).
#    Fuera de estas carpetas, el único archivo que no es .py es multijugador\configuracion.json.
$Datos = @()
foreach ($carpeta in "Imagenes", "Audios", "Fuentes", "Hitboxes", "datos") {
    $Datos += "--add-data"; $Datos += "$carpeta;$carpeta"
}
$Datos += "--add-data"; $Datos += "multijugador\configuracion.json;multijugador"
# Importados solo dentro de funciones (botones "Ver la batalla final" y "Feria de los Ecos QR", y audio).
$Ocultos = @("--hidden-import", "herramientas.vista_combate", "--hidden-import", "audio.audio_manager",
             "--hidden-import", "feria.pantalla", "--hidden-import", "feria.qr", "--hidden-import", "feria.remoto", "--hidden-import", "segno")

function Invoke-PyInstaller($Script, $Nombre, $Destino, $Extra) {
    & $Python -m PyInstaller $Script --name $Nombre --onedir --noconfirm --clean `
        --icon $Icono --distpath $Destino --workpath "build\$Nombre" `
        @Datos @Ocultos @Extra
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller falló ($Nombre)." }
}

Invoke-PyInstaller "juego.py" "TimelessGlitch" "dist" @("--windowed")
if ($Diagnostico) {
    Invoke-PyInstaller "herramientas\diagnostico_exe.py" "TimelessGlitchDiag" "dist\diagnostico" @()
}

$Juego = Join-Path $Raiz "dist\TimelessGlitch"
$Interno = Join-Path $Juego "_internal"

# Originales pesados de Gemini: el juego usa las versiones ya preparadas
# (herramientas\preparar_arte_esencial.py), así que no van en el ejecutable.
foreach ($Salida in $Juego, (Join-Path $Raiz "dist\diagnostico\TimelessGlitchDiag")) {
    $Originales = Join-Path $Salida "_internal\Imagenes\assets finales"
    if (Test-Path -LiteralPath $Originales) { Remove-Item -LiteralPath $Originales -Recurse -Force }
}

# 3. Preferencias de feria (claves reales de nucleo/preferencias.py), UTF-8 sin BOM.
$Preferencias = @"
{
  "modo_pantalla": "completa",
  "volumen_general": 0.8,
  "volumen_musica": 0.5,
  "volumen_ambiente": 0.4,
  "volumen_efectos": 0.7
}
"@
[System.IO.File]::WriteAllText((Join-Path $Interno "preferencias_usuario.json"), $Preferencias, (New-Object System.Text.UTF8Encoding($false)))

# 4. Archivos de feria junto al ejecutable.
foreach ($archivo in "Feria.bat", "LEEME_FERIA.txt", "preparar_pc_feria.ps1") {
    Copy-Item (Join-Path $Raiz "herramientas\feria\$archivo") $Juego -Force
}

# 5. Zip (con Python: conserva bien los nombres con tildes).
$Zip = Join-Path $Raiz "dist\TimelessGlitch.zip"
if (Test-Path $Zip) { Remove-Item $Zip -Force }
& $Python -c "import shutil; shutil.make_archive(r'dist\TimelessGlitch', 'zip', r'dist', 'TimelessGlitch')"
if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el zip." }

$Tamano = (Get-ChildItem $Juego -Recurse -File | Measure-Object Length -Sum).Sum
Write-Host ("Carpeta: {0}  ({1:N1} MB)" -f $Juego, ($Tamano / 1MB))
Write-Host ("Zip:     {0}  ({1:N1} MB)" -f $Zip, ((Get-Item $Zip).Length / 1MB))
