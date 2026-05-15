@echo off
title BHARAT FUTURES ENGINE - TRADING BOT
color 0A
chcp 65001 >nul
cd /d "C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE"
echo ============================================================
echo   BHARAT FUTURES ENGINE v2.0 - TRADING BOT
echo   BTC Perpetual Futures - SuperTrend Only
echo ============================================================
echo.
echo   Make sure secrets.txt is filled before running!
echo   Press Ctrl+C to stop the bot.
echo.
python main.py
pause
