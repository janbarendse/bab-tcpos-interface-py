@echo off
REM BAB PrintHub Launcher - Ensures Python 3.13 is used
echo Starting BAB PrintHub with Python 3.13...
py -3.13 fiscal_printer_hub.py
if errorlevel 1 (
    echo.
    echo ERROR: Failed to start BAB PrintHub
    echo Make sure Python 3.13 is installed
    pause
)
