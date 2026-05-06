@echo off
REM Builds the user-facing installer EXE. Requires that:
REM   1. build_windows_exe.bat has been run (produces dist\Convertr)
REM   2. Inno Setup 6 is installed at the default location.
setlocal
cd /d "%~dp0"

if not exist "dist\Convertr\Convertr.exe" (
    echo Run build_windows_exe.bat first.
    exit /b 1
)

set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo Inno Setup 6 not found. Install from https://jrsoftware.org/isinfo.php
    exit /b 1
)

if not exist release mkdir release

"%ISCC%" installer\Convertr.iss
if errorlevel 1 (
    echo Installer build failed.
    exit /b 1
)

echo.
echo Installer built in release\
endlocal
