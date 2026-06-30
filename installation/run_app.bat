@echo off
setlocal EnableDelayedExpansion

echo ======================================
echo  ReceiptVault - Windows Launcher
echo ======================================
echo.

:: ── Locate folders ─────────────────────────────────────────────────────────
:: This script lives in installation\. The actual app (main.py, gui\, web\,
:: core\, utils.py) lives one level up, at the repo root, so we resolve both
:: paths up front and cd between them as needed below.
set "INSTALL_DIR=%~dp0"
pushd "%INSTALL_DIR%.."
set "ROOT_DIR=%CD%"
popd

:: ── Auto-update (must run from the repo root, where .git lives) ───────────
cd /d "%ROOT_DIR%"
if exist ".git" (
    echo Checking for updates...
    git pull origin main
    echo.
) else (
    echo [INFO] Not a git repository - skipping auto-update.
    echo.
)

:: ── Virtual environment (created at repo root, so it's shared regardless
::    of how the app is launched) ────────────────────────────────────────────
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
pip install -r "%INSTALL_DIR%requirements.txt" --quiet
echo.

:: ── Mode selection ─────────────────────────────────────────────────────────
echo How would you like to run ReceiptVault?
echo.
echo   [1] Web Mode   - opens in your browser  (recommended for most users)
echo   [2] GUI Mode   - native desktop window
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
    python main.py --web
)

pause
endlocal