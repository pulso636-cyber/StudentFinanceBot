@echo off
REM Скрипт для запуска Filkin Bot
echo ====================================
echo    Filkin Bot Starter
echo ====================================
echo.

REM 1. Убить все процессы Python
echo [1/4] Stopping all Python processes...
taskkill /F /IM python.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python processes stopped
) else (
    echo [INFO] No Python processes found
)
echo.

REM 2. Подождать 10 секунд
echo [2/4] Waiting 10 seconds for Telegram to release connection...
timeout /t 10 /nobreak >nul
echo [OK] Ready to start
echo.

REM 3. Проверить .env
echo [3/4] Checking .env file...
if exist .env (
    echo [OK] .env file found
) else (
    echo [ERROR] .env file not found!
    pause
    exit /b 1
)
echo.

REM 4. Запустить бота
echo [4/4] Starting bot...
echo ====================================
echo.
python bot.py

pause
