<#
.SYNOPSIS
  Prepara (o restaura con -Deshacer) la PC de la feria para Timeless Glitch.

.DESCRIPTION
  Ejecutar A MANO, como administrador, desde la carpeta del juego:
      powershell -ExecutionPolicy Bypass -File .\preparar_pc_feria.ps1
      powershell -ExecutionPolicy Bypass -File .\preparar_pc_feria.ps1 -Deshacer

  Cambia:
    - Atajos de accesibilidad: Teclas especiales (Shift x5), Teclas filtro y
      Teclas de alternancia dejan de saltar encima del juego.
    - Suspensión y apagado de pantalla con corriente: Nunca.
    - Acceso directo a Feria.bat (minimizado, con el icono del juego) en el
      escritorio y en la carpeta de Inicio del usuario.
    - Regla del firewall que permite TimelessGlitch.exe en redes privadas (LAN).
  Los valores anteriores se guardan en respaldo_feria.json para -Deshacer.
#>
param(
    [switch]$Deshacer,
    [string]$Carpeta = $PSScriptRoot
)

$ErrorActionPreference = "Stop"
$identidad = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $identidad.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Abre PowerShell como administrador y vuelve a ejecutar este script."
}

$Exe = Join-Path $Carpeta "TimelessGlitch.exe"
$Bat = Join-Path $Carpeta "Feria.bat"
$Respaldo = Join-Path $Carpeta "respaldo_feria.json"
$Regla = "Timeless Glitch (feria)"
$Accesos = @(
    (Join-Path ([Environment]::GetFolderPath("Desktop")) "Timeless Glitch - Feria.lnk"),
    (Join-Path ([Environment]::GetFolderPath("Startup")) "Timeless Glitch - Feria.lnk")
)
$Teclado = @{
    StickyKeys = "HKCU:\Control Panel\Accessibility\StickyKeys"
    FilterKeys = "HKCU:\Control Panel\Accessibility\Keyboard Response"
    ToggleKeys = "HKCU:\Control Panel\Accessibility\ToggleKeys"
}
# Flags sin el atajo de teclado (ni avisos) y con la función apagada.
$SinAtajo = @{ StickyKeys = "506"; FilterKeys = "122"; ToggleKeys = "58" }
$Energia = @(
    @{ Nombre = "Suspensión"; Grupo = "SUB_SLEEP"; Valor = "STANDBYIDLE" },
    @{ Nombre = "Apagar pantalla"; Grupo = "SUB_VIDEO"; Valor = "VIDEOIDLE" }
)

function Get-SegundosCorriente($Grupo, $Valor) {
    # Los dos últimos números 0x de la consulta son el valor con corriente (AC) y con batería (DC).
    $texto = (powercfg /query SCHEME_CURRENT $Grupo $Valor) -join "`n"
    $numeros = [regex]::Matches($texto, "0x[0-9a-fA-F]{8}")
    return [Convert]::ToInt32($numeros[$numeros.Count - 2].Value, 16)
}

function Set-SegundosCorriente($Grupo, $Valor, $Segundos) {
    powercfg /setacvalueindex SCHEME_CURRENT $Grupo $Valor $Segundos | Out-Null
    powercfg /setactive SCHEME_CURRENT | Out-Null
}

if ($Deshacer) {
    if (-not (Test-Path $Respaldo)) { throw "No hay respaldo_feria.json en ${Carpeta}: no hay nada que deshacer." }
    $previo = Get-Content $Respaldo -Raw | ConvertFrom-Json
    foreach ($clave in $Teclado.Keys) {
        Set-ItemProperty -Path $Teclado[$clave] -Name Flags -Value $previo.teclado.$clave
        Write-Host "Restaurado $clave (Flags = $($previo.teclado.$clave))"
    }
    foreach ($e in $Energia) {
        Set-SegundosCorriente $e.Grupo $e.Valor $previo.energia.($e.Valor)
        Write-Host "Restaurado $($e.Nombre) con corriente: $($previo.energia.($e.Valor)) s"
    }
    foreach ($acceso in $Accesos) {
        if (Test-Path $acceso) { Remove-Item $acceso -Force; Write-Host "Eliminado acceso directo $acceso" }
    }
    if (Get-NetFirewallRule -DisplayName $Regla -ErrorAction SilentlyContinue) {
        Remove-NetFirewallRule -DisplayName $Regla
        Write-Host "Eliminada la regla del firewall '$Regla'"
    }
    Remove-Item $Respaldo -Force
    Write-Host "Listo: la PC quedó como antes de la feria."
    return
}

if (-not (Test-Path $Exe)) { throw "No encuentro $Exe. Ejecuta el script desde la carpeta del juego o usa -Carpeta." }

# Guardar lo que había antes (solo la primera vez, para no pisar el respaldo original).
if (-not (Test-Path $Respaldo)) {
    $teclado = @{}
    foreach ($clave in $Teclado.Keys) { $teclado[$clave] = (Get-ItemProperty -Path $Teclado[$clave] -Name Flags).Flags }
    $energia = @{}
    foreach ($e in $Energia) { $energia[$e.Valor] = Get-SegundosCorriente $e.Grupo $e.Valor }
    @{ teclado = $teclado; energia = $energia } | ConvertTo-Json | Set-Content -Path $Respaldo -Encoding UTF8
    Write-Host "Respaldo guardado en $Respaldo"
}

foreach ($clave in $Teclado.Keys) {
    Set-ItemProperty -Path $Teclado[$clave] -Name Flags -Value $SinAtajo[$clave]
    Write-Host "Atajo de $clave desactivado (Flags = $($SinAtajo[$clave]))"
}
foreach ($e in $Energia) {
    Set-SegundosCorriente $e.Grupo $e.Valor 0
    Write-Host "$($e.Nombre) con corriente: Nunca"
}

$shell = New-Object -ComObject WScript.Shell
foreach ($acceso in $Accesos) {
    $lnk = $shell.CreateShortcut($acceso)
    $lnk.TargetPath = $Bat
    $lnk.WorkingDirectory = $Carpeta
    $lnk.WindowStyle = 7  # minimizado
    $lnk.IconLocation = "$Exe,0"
    $lnk.Save()
    Write-Host "Acceso directo creado: $acceso"
}

if (-not (Get-NetFirewallRule -DisplayName $Regla -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $Regla -Direction Inbound -Program $Exe -Action Allow -Profile Private | Out-Null
}
Write-Host "Firewall: TimelessGlitch.exe permitido en redes privadas ('$Regla')"
Write-Host "Listo. Al terminar la feria ejecuta: .\preparar_pc_feria.ps1 -Deshacer"
Write-Host "Nota: los atajos de accesibilidad se aplican al iniciar sesión de nuevo."
