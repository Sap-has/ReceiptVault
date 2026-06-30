#!/usr/bin/env bash
# ReceiptVault – Docker launcher
#
# Thin wrapper around `docker compose up` that also tells you which host
# port got assigned to the web UI (since the compose file lets Docker pick
# any free port rather than hardcoding 7000, in case something else on your
# machine is already using it).
#
# Usage:
#   ./docker-up.sh              # web mode (default), builds + starts + follows logs
#   ./docker-up.sh --gui        # GUI mode (Linux with X11 only)
#   ./docker-up.sh -d           # web mode, builds + starts, then exits without following logs
#
# This script lives in installation/ alongside docker-compose.yml, but can be
# run from anywhere (e.g. `./installation/docker-up.sh` from the repo root) -
# it moves itself into its own folder first so `docker compose` reliably
# finds docker-compose.yml no matter where you called it from.
set -euo pipefail

# Move to the directory containing this script so docker compose finds
# docker-compose.yml regardless of the caller's current working directory.
cd "$(dirname "$0")"

GUI_MODE=false
DETACHED=false
EXTRA_ARGS=()

for arg in "$@"; do
    case "$arg" in
        --gui)        GUI_MODE=true ;;
        -d|--detach)  DETACHED=true ;;
        --build)      ;;  # already always built below; avoid passing it twice
        *)            EXTRA_ARGS+=("$arg") ;;
    esac
done

if [ "$GUI_MODE" = true ]; then
    echo "Starting ReceiptVault in GUI mode (Docker, Linux/X11)..."
    xhost +local:docker 2>/dev/null || true
    exec docker compose --profile gui up "${EXTRA_ARGS[@]}"
fi

echo "======================================"
echo " Starting ReceiptVault (Web mode, Docker)"
echo "======================================"

# Build the image and start the web service in the background so we can
# inspect the port mapping before deciding whether to attach to logs.
docker compose up --build -d app "${EXTRA_ARGS[@]}"

# Ask Docker which host port it mapped to the container's port 7000.
# `docker compose port` prints e.g. "0.0.0.0:54827" – we just want the number.
MAPPING="$(docker compose port app 7000 2>/dev/null || true)"
HOST_PORT="${MAPPING##*:}"

echo ""
if [ -n "$HOST_PORT" ] && [ "$HOST_PORT" != "$MAPPING" ]; then
    echo "  ReceiptVault is running → http://localhost:${HOST_PORT}"
else
    echo "  ReceiptVault is running. Could not auto-detect the port; check it with:"
    echo "    docker compose ps"
fi

if [ "$DETACHED" = true ]; then
    echo "  Running in the background. Run 'docker compose down' to stop it."
    echo ""
    exit 0
fi

echo "  Press Ctrl+C to stop following logs (the container keeps running in the background)."
echo "  Run 'docker compose down' to stop it."
echo ""

# Attach to logs so the experience matches `docker compose up` running in
# the foreground. Ctrl+C here only detaches from logs; it does not stop
# the container (matching the message above).
exec docker compose logs -f app