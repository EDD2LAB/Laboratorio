@echo off
rem Arma de nuevo el .exe con los ultimos cambios y lo copia a C:\TimelessGlitch
rem (sin borrar respaldo_feria.json ni nada que ya este alli).
title Actualizar Timeless Glitch .exe
cd /d "%~dp0"
echo Armando el .exe con los ultimos cambios (tarda unos minutos)...
powershell -NoProfile -ExecutionPolicy Bypass -File herramientas\empaquetar.ps1
if errorlevel 1 (
  echo.
  echo ERROR: no se pudo armar el .exe. Revisa los mensajes de arriba.
  pause
  exit /b 1
)
echo Copiando a C:\TimelessGlitch ...
robocopy "dist\TimelessGlitch" "C:\TimelessGlitch" /E /NFL /NDL /NJH /NP
if errorlevel 8 (
  echo ERROR al copiar. Cierra el juego si esta abierto y vuelve a intentarlo.
  pause
  exit /b 1
)
echo.
echo Listo: C:\TimelessGlitch\TimelessGlitch.exe ya tiene tus ultimos cambios.
pause
