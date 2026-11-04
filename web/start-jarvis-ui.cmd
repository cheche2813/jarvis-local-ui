@echo off
setlocal
cd /d "%~dp0"
title JARVIS - Local Node
"%~dp0..\src\.venv\Scripts\python.exe" "%~dp0server.py"
echo.
echo El servidor de Jarvis se detuvo. Pulsa una tecla para cerrar.
pause >nul
