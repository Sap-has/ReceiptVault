@echo off
setlocal EnableDelayedExpansion

echo ======================================
echo  ReceiptVault – Windows Launcher
echo ======================================
echo.

:: ── Auto-update ────────────────────────────────────────────────────────────
if exist ".git" (
    echo Checking for updates...
    git pull origin main
    echo.
) else (
    echo [INFO] Not a git repository – skipping auto-update.
    echo.
)

:: ── Virtual environment ────────────────────────────────────────────────────
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Could not create virtual environment.
        echo         Make sure Python 3.11+ is installed and on PATH.
        echo         Download: https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat

echo Installing / verifying dependencies...
pip install -r requirements.txt --quiet
echo.

:: ── Mode selection ─────────────────────────────────────────────────────────
echo How would you like to run ReceiptVault?
echo.
echo   [1] Web Mode   – opens in your browser  (recommended for most users)
echo   [2] GUI Mode   – native desktop window
echo.
set /p MODE="Enter 1 or 2 (default 1): "

if "%MODE%"=="" set MODE=1

if "%MODE%"=="2" (
    echo.
    echo Starting in GUI mode...
    python main.py --gui
) else (
    echo.
    echo Starting in Web mode...
    start "" http://127.0.0.1:7000
    python main.py --web
)

pause
endlocal