@echo off
title BHARAT FUTURES ENGINE - DASHBOARD
color 0B
cd /d "C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE"
echo ============================================================
echo   BHARAT FUTURES ENGINE v2.0 - DASHBOARD
echo   Port: 8600
echo ============================================================
echo.
echo  Opening dashboard at: http://localhost:8600
echo  Press Ctrl+C to stop.
echo.
python -m streamlit run app.py --server.port 8600 --browser.gatherUsageStats false
pause
