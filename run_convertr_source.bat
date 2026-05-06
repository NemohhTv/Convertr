@echo off
REM Runs Convertr directly from source (no PyInstaller bundle needed).
REM Uses pythonw so no console window flashes up.
setlocal
cd /d "%~dp0"
where pythonw >nul 2>nul
if errorlevel 1 (
    python app.py
) else (
    pythonw app.py
)
endlocal
