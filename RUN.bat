@echo off
title Scout - Development Mode
color 0A
echo.
echo  ========================================================
echo       SCOUT - DEV MODE (No compilation)
echo  ========================================================
echo.
echo  Checking Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] Python not found.
    pause
    goto :end
)
echo  [OK] Python detected
echo.
echo  Launching Scout...
echo.
python scout_gui.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Failed to launch. Check errors above.
    pause
)
:end
