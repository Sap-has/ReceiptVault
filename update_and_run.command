#!/usr/bin/env bash
# ReceiptVault – macOS launcher  (double-click this file in Finder)
# On first run macOS may prompt "Allow access" – click OK.
set -euo pipefail

# Move to the directory containing this script so relative paths work
cd "$(dirname "$0")"

# ─────────────────────────────────────────────────────────────────────────────
# 1.  Auto-update
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
# 2.  Python check
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
    echo "[ERROR] Python 3.11+ not found."
    echo "        Install via: https://www.python.org/downloads/  or  brew install python"
    read -rp "Press Enter to exit..."
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# 3.  Virtual environment & dependencies
# ─────────────────────────────────────────────────────────────────────────────
echo "======================================"
echo " Setting up environment..."
echo "======================================"
if [ ! -d "venv" ]; then
    echo "Creating virtual environment (first run only)..."
    "$PYTHON" -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate
echo "Installing / verifying dependencies..."
pip install -r requirements.txt --quiet
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 4.  Mode selection  (macOS supports both Web and GUI)
# ─────────────────────────────────────────────────────────────────────────────
echo "======================================"
echo " How would you like to run ReceiptVault?"
echo "======================================"
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
