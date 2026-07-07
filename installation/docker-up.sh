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
#   ./docker-up.sh -d           # web mode, builds + starts, then exits without following logs
#   ./docker-up.sh --gpu        # force the NVIDIA GPU-accelerated build (auto-detected by default)
#   ./docker-up.sh --no-gpu     # force the CPU-only build even if an NVIDIA GPU is detected
#
# Web mode auto-detects an NVIDIA GPU on the host (via `nvidia-smi`) and, if
# found, builds/runs the GPU-accelerated image instead - this needs the
# NVIDIA Container Toolkit installed on the host so Docker can pass the GPU
# through. See the app-gpu service in docker-compose.yml.
#
# This script lives in installation/ alongside docker-compose.yml, but can be
# run from anywhere (e.g. `./installation/docker-up.sh` from the repo root) -
# it moves itself into its own folder first so `docker compose` reliably
# finds docker-compose.yml no matter where you called it from.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

# Move to the directory containing this script so docker compose finds
# docker-compose.yml regardless of the caller's current working directory.
cd "$SCRIPT_DIR"

if grep -q avx /proc/cpuinfo; then
    CHROME_ARG="false"
else
    echo "[INFO] AVX not detected on host CPU. Enabling compatibility mode."
    CHROME_ARG="true"
fi

DETACHED=false
GPU_MODE=""    # "" = auto-detect, "true" = force GPU, "false" = force CPU
EXTRA_ARGS=()

for arg in "$@"; do
    case "$arg" in
        -d|--detach)  DETACHED=true ;;
        --gpu)        GPU_MODE=true ;;
        --no-gpu)     GPU_MODE=false ;;
        --build)      ;;  # already always built below; avoid passing it twice
        *)            EXTRA_ARGS+=("$arg") ;;
    esac
done

# Auto-detect an NVIDIA GPU on the host unless --gpu/--no-gpu forced a choice.
# nvidia-smi only exists when the NVIDIA driver is installed on the host, so
# its presence is a solid enough signal that GPU passthrough will work
# (assuming the NVIDIA Container Toolkit is also installed - see the
# app-gpu service in docker-compose.yml for what that enables).
if [ -z "$GPU_MODE" ]; then
    if command -v nvidia-smi &>/dev/null && nvidia-smi -L 2>/dev/null | grep -q GPU; then
        GPU_MODE=true
    else
        GPU_MODE=false
    fi
fi

echo "Fetching latest repository updates from git..."
git -C "$REPO_ROOT" fetch --all --prune

echo "Updating repository from git before starting Docker..."
git -C "$REPO_ROOT" pull --ff-only


echo "======================================"
echo " Starting ReceiptVault (Web mode, Docker)"
echo "======================================"

if [ "$GPU_MODE" = true ]; then
    echo "[INFO] NVIDIA GPU detected - building the GPU-accelerated image."
    echo "       (Needs the NVIDIA Container Toolkit on the host. If the"
    echo "        container fails to start, re-run with --no-gpu.)"
    SERVICE="app-gpu"
    PROFILE_ARGS=(--profile gpu)
else
    SERVICE="app"
    PROFILE_ARGS=()
fi

# Build the image and start the web service in the background so we can
# inspect the port mapping before deciding whether to attach to logs.
docker compose "${PROFILE_ARGS[@]}" build --build-arg NO_AVX=$CHROME_ARG "$SERVICE"
docker compose "${PROFILE_ARGS[@]}" up -d "$SERVICE" "${EXTRA_ARGS[@]}"

# Ask Docker which host port it mapped to the container's port 7000.
# `docker compose port` prints e.g. "0.0.0.0:54827" – we just want the number.
MAPPING="$(docker compose "${PROFILE_ARGS[@]}" port "$SERVICE" 7000 2>/dev/null || true)"
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

echo "  Press Ctrl+C to stop ReceiptVault."
echo ""

# Trap Ctrl+C to gracefully shut down the container
trap_handler() {
    echo ""
    echo "Stopping ReceiptVault..."
    docker compose "${PROFILE_ARGS[@]}" down
    exit 0
}
trap trap_handler SIGINT SIGTERM

# Attach to logs so the experience matches `docker compose up` running in
# the foreground. Ctrl+C will trigger the trap above and stop the container.
docker compose logs -f "$SERVICE"