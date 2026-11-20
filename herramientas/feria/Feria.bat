@echo off
rem Timeless Glitch en la feria: abre el juego en modo feria y lo reabre si se cierra.
rem Para salir de verdad: cierra primero ESTA ventana y despues el juego.
title Timeless Glitch - Feria
cd /d "%~dp0"
set TG_MODO_FERIA=1
:bucle
echo Abriendo Timeless Glitch...  (cierra esta ventana para dejar de reabrirlo)
start "" /wait "%~dp0TimelessGlitch.exe"
timeout /t 2 /nobreak >nul
goto bucle
