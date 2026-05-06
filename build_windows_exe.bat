@echo off
setlocal
cd /d "%~dp0"

echo Building Convertr.exe...
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m PyInstaller --noconfirm --clean --onefile --windowed --name Convertr app.py

if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)

echo Build complete. Check the dist folder for Convertr.exe.
pause
