@echo off
REM Installs Python dependencies for running and building Convertr.
setlocal

where python >nul 2>nul
if errorlevel 1 (
    echo Python not found on PATH. Install Python 3.11+ from https://python.org
    exit /b 1
)

python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
echo.
echo Dependencies installed. Run run_convertr_source.bat to launch.
endlocal
