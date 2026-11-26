@echo off
title Actualizar Timeless Glitch
cd /d "%~dp0"
echo Trayendo lo ultimo de GitHub (rama multijugador)...
git checkout multijugador
if errorlevel 1 (
  echo.
  echo ERROR: no se pudo cambiar a la rama multijugador. Guarda o descarta tus cambios
  echo y vuelve a intentarlo. Copia el mensaje de arriba y pasaselo a Claude.
  pause
  exit /b 1
)
git pull origin multijugador
if errorlevel 1 (
  echo.
  echo ERROR al traer los cambios. Copia el mensaje de arriba y pasaselo a Claude.
  pause
  exit /b 1
)
echo.
echo Instalando dependencias nuevas en .venv...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo ERROR al instalar dependencias. Copia el mensaje de arriba y pasaselo a Claude.
  pause
  exit /b 1
)
echo.
echo Listo. Ya puedes jugar con Jugar.bat
pause
