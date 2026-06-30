#!/usr/bin/env bash
# ReceiptVault – cross-platform launcher (macOS / Linux / ChromeOS)
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# 0.  Detect OS and execution environment
# ─────────────────────────────────────────────────────────────────────────────
OS="$(uname -s)"          # Darwin | Linux
IS_CHROMEOS=false
IS_GUI_CAPABLE=false

# ChromeOS detection: /etc/os-release contains ID=chromeos or a cros_* kernel
if [ -f /etc/os-release ]; then
    if grep -qi "chromeos\|cros" /etc/os-release 2>/dev/null; then
        IS_CHROMEOS=true
    fi
fi
# Also check the kernel version string (common on Crostini)
if uname -r 2>/dev/null | grep -qi "cros"; then
    IS_CHROMEOS=true
fi

# GUI capable = macOS, or Linux with a live DISPLAY/WAYLAND_DISPLAY
if [ "$OS" = "Darwin" ]; then
    IS_GUI_CAPABLE=true
elif [ "$OS" = "Linux" ] && [ "$IS_CHROMEOS" = false ]; then
    if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
        IS_GUI_CAPABLE=true
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# 1.  Auto-update from GitHub
# ─────────────────────────────────────────────────────────────────────────────
echo "======================================"
echo " Checking for updates..."
echo "======================================"
if [ -d ".git" ]; then
    git pull origin main || echo "[WARN] Git pull failed - continuing with current version."
else
    echo "[INFO] Not a git repository - skipping auto-update."
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 2.  Resolve Python interpreter
# ─────────────────────────────────────────────────────────────────────────────
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        VER=$("$candidate" -c "import sys; print(sys.version_info >= (3,11))" 2>/dev/null || echo "False")
        if [ "$VER" = "True" ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "[ERROR] Python 3.11 or newer was not found."
    if [ "$OS" = "Darwin" ]; then
        echo "        Install via:  brew install python  OR  https://www.python.org/downloads/"
    elif [ "$IS_CHROMEOS" = true ]; then
        echo "        Run:  sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
    else
        echo "        Run:  sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
    fi
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# 3.  Virtual environment
# ─────────────────────────────────────────────────────────────────────────────
echo "======================================"
echo " Setting up virtual environment..."
echo "======================================"
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    "$PYTHON" -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

echo "Installing / verifying dependencies..."
pip install -r requirements.txt --quiet
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 4.  Mode selection
# ─────────────────────────────────────────────────────────────────────────────
echo "======================================"
echo " Starting ReceiptVault"
echo "======================================"

if [ "$IS_CHROMEOS" = true ]; then
    # ChromeOS: GUI (Tk) window management is unreliable inside Crostini
    echo "[ChromeOS] Running in Web mode (GUI mode is not supported on ChromeOS)."
    echo "           ReceiptVault will pick a free port automatically and open it for you."
    echo ""
    python3 main.py --web

elif [ "$IS_GUI_CAPABLE" = false ]; then
    # Headless Linux (server, WSL without display, etc.)
    echo "[Headless] No graphical display detected - running in Web mode."
    echo "           ReceiptVault will pick a free port automatically (the URL"
    echo "           to open will be printed below once the server starts)."
    echo ""
    python3 main.py --web --no-browser

else
    # macOS or Linux with a display – offer a choice
    echo "How would you like to run ReceiptVault?"
    echo ""
    echo "  [1] Web Mode  - opens in your browser (recommended)"
    echo "  [2] GUI Mode  - native desktop window"
    echo ""
    read -rp "Enter 1 or 2 (default 1): " MODE
    MODE="${MODE:-1}"

    if [ "$MODE" = "2" ]; then
        echo ""
        echo "Starting in GUI mode..."
        python3 main.py --gui
    else
        echo ""
        echo "Starting in Web mode..."
        python3 main.py --web
    fi
fi