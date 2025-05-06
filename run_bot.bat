@echo off
echo Starting Telegram Bot at %time% on %date%
"C:\Users\raffa\AppData\Local\Programs\Python\Python312\python.exe" "run_telegram_bot.py"
if %ERRORLEVEL% NEQ 0 (
    echo Bot failed to start with error code %ERRORLEVEL%
    pause
)
