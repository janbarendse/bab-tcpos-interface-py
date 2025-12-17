@echo off
REM BAB PrintHub - Setup Script for Installation
REM Installs the application on a new machine

echo ========================================
echo BAB PrintHub - Installation Setup
echo ========================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if errorlevel 1 (
    echo WARNING: Not running as administrator.
    echo Some operations may fail if you don't have proper permissions.
    echo.
    pause
)

REM Default installation directory
set "INSTALL_DIR=%ProgramFiles%\BAB PrintHub"

echo This script will install BAB PrintHub to:
echo %INSTALL_DIR%
echo.
set /p "CUSTOM_DIR=Press ENTER to use default, or type a custom path: "

if not "%CUSTOM_DIR%"=="" (
    set "INSTALL_DIR=%CUSTOM_DIR%"
)

echo.
echo Installation directory: %INSTALL_DIR%
echo.

REM Create installation directory
if not exist "%INSTALL_DIR%" (
    echo Creating installation directory...
    mkdir "%INSTALL_DIR%"
    if errorlevel 1 (
        echo ERROR: Failed to create directory. Run as administrator or choose a different location.
        pause
        exit /b 1
    )
)

REM Check if executable exists
if not exist "BAB_PrintHub.exe" (
    echo ERROR: BAB_PrintHub.exe not found in current directory!
    echo Please run build.bat first or ensure the executable is in this folder.
    pause
    exit /b 1
)

echo.
echo Installing files...

REM Copy executable
copy /Y "BAB_PrintHub.exe" "%INSTALL_DIR%\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy executable
    pause
    exit /b 1
)
echo [OK] BAB_PrintHub.exe

REM Copy logo
if exist "logo.png" (
    copy /Y "logo.png" "%INSTALL_DIR%\" >nul
    echo [OK] logo.png
)

REM Copy or create config.json
if exist "config.json" (
    if not exist "%INSTALL_DIR%\config.json" (
        copy /Y "config.json" "%INSTALL_DIR%\" >nul
        echo [OK] config.json ^(new^)
    ) else (
        echo [SKIP] config.json ^(already exists, preserving existing configuration^)
    )
) else (
    echo [WARN] config.json not found - you'll need to create it manually
)

echo.
echo Creating startup shortcut...

REM Create desktop shortcut
set "SHORTCUT=%USERPROFILE%\Desktop\BAB PrintHub.lnk"
powershell -Command "$WS = New-Object -ComObject WScript.Shell; $SC = $WS.CreateShortcut('%SHORTCUT%'); $SC.TargetPath = '%INSTALL_DIR%\BAB_PrintHub.exe'; $SC.WorkingDirectory = '%INSTALL_DIR%'; $SC.IconLocation = '%INSTALL_DIR%\logo.png'; $SC.Description = 'BAB Fiscal PrintHub'; $SC.Save()" >nul 2>&1
if errorlevel 1 (
    echo [WARN] Failed to create desktop shortcut
) else (
    echo [OK] Desktop shortcut created
)

REM Create Start Menu shortcut
set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
if not exist "%STARTMENU%\BAB PrintHub" mkdir "%STARTMENU%\BAB PrintHub"
set "STARTSHORTCUT=%STARTMENU%\BAB PrintHub\BAB PrintHub.lnk"
powershell -Command "$WS = New-Object -ComObject WScript.Shell; $SC = $WS.CreateShortcut('%STARTSHORTCUT%'); $SC.TargetPath = '%INSTALL_DIR%\BAB_PrintHub.exe'; $SC.WorkingDirectory = '%INSTALL_DIR%'; $SC.IconLocation = '%INSTALL_DIR%\logo.png'; $SC.Description = 'BAB Fiscal PrintHub'; $SC.Save()" >nul 2>&1
if errorlevel 1 (
    echo [WARN] Failed to create Start Menu shortcut
) else (
    echo [OK] Start Menu shortcut created
)

echo.
echo ========================================
echo Installation completed successfully!
echo ========================================
echo.
echo Installation location: %INSTALL_DIR%
echo.
echo Desktop shortcut: %USERPROFILE%\Desktop\BAB PrintHub.lnk
echo Start Menu: Programs ^> BAB PrintHub
echo.
echo IMPORTANT: Before first run:
echo 1. Edit config.json in the installation folder
echo 2. Set the correct transactions_folder path
echo 3. Ensure the fiscal printer is connected
echo.
echo You can now run BAB PrintHub from the desktop or Start Menu.
echo.
pause
