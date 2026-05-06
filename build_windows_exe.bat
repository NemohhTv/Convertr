@echo off
REM Builds dist\Convertr\Convertr.exe using PyInstaller.
REM Requires that install_python_requirements.bat has been run.
setlocal
cd /d "%~dp0"

where pyinstaller >nul 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Run install_python_requirements.bat first.
    exit /b 1
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

pyinstaller --noconfirm Convertr.spec
if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

echo.
echo Build complete: dist\Convertr\Convertr.exe
endlocal
