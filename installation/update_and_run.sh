#!/usr/bin/env bash
# ReceiptVault – cross-platform launcher (macOS / Linux / ChromeOS)
set -euo pipefail

# This script lives in installation/. The app itself (main.py, gui/, web/,
# core/, utils.py) lives one level up, at the repo root - move there so
# git pull, venv, and main.py all resolve correctly, regardless of where
# this script was invoked from.
INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$INSTALL_DIR/.."

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
pip install -r "$INSTALL_DIR/requirements.txt" --quiet
echo ""

echo "Checking for an NVIDIA GPU (for OCR acceleration)..."
python3 "$INSTALL_DIR/gpu_setup.py"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 4.  Mode selection
# ─────────────────────────────────────────────────────────────────────────────
echo "======================================"
echo " Starting ReceiptVault"
echo "======================================"

echo "Starting in Web mode..."
python3 main.py --web
