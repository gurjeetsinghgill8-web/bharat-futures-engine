@echo off
echo ============================================================
echo   BHARAT FUTURES ENGINE - VPS UPDATE + AVAX EMERGENCY FIX
echo ============================================================
echo.

set VPS_IP=157.49.187.4
set VPS_USER=root
set VPS_PASS=U4CJs4HKbMMJ
set VPS_PATH=/root/bharat-futures

echo [1] Uploading fixed main.py to VPS...
echo y | .\pscp.exe -pw "%VPS_PASS%" "main.py" %VPS_USER%@%VPS_IP%:%VPS_PATH%/main.py
if %errorlevel% neq 0 (
    echo FAILED to upload main.py
    goto :error
)
echo     OK: main.py uploaded.

echo.
echo [2] Uploading emergency close script...
echo y | .\pscp.exe -pw "%VPS_PASS%" "emergency_close_avax.py" %VPS_USER%@%VPS_IP%:%VPS_PATH%/emergency_close_avax.py
if %errorlevel% neq 0 (
    echo FAILED to upload emergency_close_avax.py
    goto :error
)
echo     OK: emergency_close_avax.py uploaded.

echo.
echo [3] Stopping the bot on VPS...
echo y | .\plink.exe -ssh %VPS_USER%@%VPS_IP% -pw "%VPS_PASS%" "pkill -f 'python.*main.py' 2>/dev/null; echo Bot stopped"

echo.
echo [4] Running EMERGENCY CLOSE for AVAXUSD on VPS...
echo y | .\plink.exe -ssh %VPS_USER%@%VPS_IP% -pw "%VPS_PASS%" "cd %VPS_PATH% && python3 emergency_close_avax.py"

echo.
echo [5] Restarting bot on VPS with fixed code...
echo y | .\plink.exe -ssh %VPS_USER%@%VPS_IP% -pw "%VPS_PASS%" "cd %VPS_PATH% && pkill -f 'python.*main.py' 2>/dev/null; sleep 2; nohup python3 main.py > logs/bot.log 2>&1 &amp; echo Bot restarted"

echo.
echo ============================================================
echo   DONE! Bot restarted with fixed code.
echo   - AVAXUSD position closed
echo   - Duplicate lots bug FIXED
echo   - Check Telegram for confirmation
echo ============================================================
goto :end

:error
echo.
echo ERROR: VPS connection failed. Try again or check VPS status.

:end
pause
