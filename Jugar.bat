@echo off
rem Abre el juego desde el codigo: siempre la version mas reciente, sin armar el .exe.
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" juego.py
