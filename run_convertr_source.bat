@echo off
setlocal
cd /d "%~dp0"

echo Starting Convertr from source...
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m pip install -r requirements.txt
  py -3 app.py
  exit /b %errorlevel%
)

where python >nul 2>nul
if %errorlevel%==0 (
  python -m pip install -r requirements.txt
  python app.py
  exit /b %errorlevel%
)

echo Python was not found. Install Python 3.11 or newer from https://www.python.org/downloads/
pause
exit /b 1
