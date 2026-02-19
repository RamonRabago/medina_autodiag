@echo off
cd /d "%~dp0\.."
REM Ejecuta reset_bd_cero.py usando DATABASE_URL que pegues al inicio.
REM La URI no se guarda en ningun archivo.
echo.
echo === RESET BD contra Aiven ===
echo Pega la Service URI completa (mysql://user:pass@host:port/db^) y presiona Enter:
set /p DATABASE_URL=
if "%DATABASE_URL%"=="" (
    echo ERROR: No pegaste nada. Vuelve a ejecutar y pega la URI.
    pause
    exit /b 1
)
echo.
echo Conectando y ejecutando reset...
call venv\Scripts\activate.bat
python scripts/reset_bd_cero.py --yes
pause
