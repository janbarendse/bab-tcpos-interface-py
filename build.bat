@echo off
REM BAB PrintHub - Build Script
REM Compiles the application into a standalone executable

echo ========================================
echo BAB PrintHub - Build Script
echo ========================================
echo.

REM Check if Python 3.13 is available
py -3.13 --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.13 is not installed
    echo Please install Python 3.13 to build this application
    pause
    exit /b 1
)

echo Using Python 3.13
py -3.13 --version

REM Check if PyInstaller is installed
py -3.13 -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    py -3.13 -m pip install pyinstaller
)

echo.
echo Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

echo.
echo Building BAB PrintHub executable...
echo This may take a few minutes...
echo.

py -3.13 -m PyInstaller --onefile ^
    --noconsole ^
    --name "BAB_PrintHub" ^
    --icon=logo.png ^
    --add-data "logo.png;." ^
    --add-data "config.json;." ^
    --hidden-import=pywebview ^
    --hidden-import=pywebview.platforms.winforms ^
    --hidden-import=clr ^
    --hidden-import=pythonnet ^
    --collect-all pywebview ^
    --collect-all bottle ^
    fiscal_printer_hub.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Executable location: dist\BAB_PrintHub.exe
echo.
echo Note: Copy config.json to the same folder as the executable before running.
echo.
pause
