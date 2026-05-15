@echo off
title BHARAT FUTURES ENGINE - AUTO RESTART LOOP
color 0A

:START
echo ================================================
echo   BHARAT FUTURES ENGINE - LIVE TRADING BOT
echo   Auto-restarts if it crashes
echo ================================================
echo.

cd /d "c:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE"

echo Starting bot at %TIME%...
"C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.12_3.12.2800.0_x64__qbz5n2kfra8p0\python3.12.exe" main.py

echo.
echo Bot stopped at %TIME%. Restarting in 5 seconds...
echo (Close this window to stop permanently)
timeout /t 5 /nobreak >nul
goto START
