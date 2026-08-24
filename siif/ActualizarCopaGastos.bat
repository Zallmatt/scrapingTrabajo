@echo off
chcp 65001 >nul
title Actualizar Copa Gastos SIIF
color 0A

REM Raíz del repo = carpeta padre de siif\
cd /d "%~dp0.."
if errorlevel 1 (
    echo No se pudo ubicar la carpeta del proyecto.
    pause
    exit /b 1
)

echo ============================================================
echo   Actualizar Copa Gastos SIIF
echo ============================================================
echo.
echo   Reportes: rf604m + rf610m + rf610mfte
echo   Flujo:    descarga -^> transform -^> UPSERT a base
echo.
echo   1. Se abrira Chrome con el login de SIIF.
echo   2. Completa el captcha y hace clic en Ingresar.
echo   3. Despues no hace falta tocar nada.
echo      (puede tardar varias horas; no cierres esta ventana)
echo.
echo   Proyecto: %CD%
echo ============================================================
echo.

where py >nul 2>&1
if errorlevel 1 (
    echo ERROR: No se encontro el comando "py".
    echo Instala Python desde python.org e incluye el launcher "py".
    echo.
    pause
    exit /b 1
)

py -3 -u siif\run_all_gastos.py
set EXITCODE=%ERRORLEVEL%

echo.
echo ============================================================
if %EXITCODE%==0 (
    echo   Proceso finalizado correctamente.
) else (
    echo   Proceso finalizado con errores ^(codigo %EXITCODE%^).
)
echo ============================================================
echo.
pause
exit /b %EXITCODE%
