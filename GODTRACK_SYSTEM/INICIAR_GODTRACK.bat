@echo off
setlocal
title GODTRACK SYSTEM LAUNCHER

echo ========================================================
echo        INICIANDO SISTEMA GODTRACK - POR FAVOR ESPERE
echo ========================================================
echo.

:: Change to the backend directory
cd /d "%~dp0backend"

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] No se detecto Python instalado.
    echo Por favor instala Python para ejecutar este sistema.
    pause
    exit /b
)

:: Run the application
echo Iniciando servidor y abriendo navegador...
python main.py

:: If python crashes, keep window open
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] El sistema se cerro inesperadamente.
    pause
)
