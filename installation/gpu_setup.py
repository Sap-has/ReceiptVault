#!/usr/bin/env python3
"""
installation/gpu_setup.py - Installs the right PaddlePaddle build (GPU or CPU)
for ReceiptVault's OCR engine.

Why this exists:
  core/ocr_processor.py already asks PaddleOCR to run on the GPU whenever one
  is usable - but that only works if the *GPU-enabled* `paddlepaddle-gpu`
  wheel is what's actually installed. The plain `paddlepaddle` package on
  PyPI is CPU-only, even on a machine with a perfectly good NVIDIA card. This
  script is the piece that closes that gap, and it's used by every install
  path (native launcher scripts on Windows/macOS/Linux, and the Dockerfile).

What it does:
  1. Looks for an NVIDIA GPU via `nvidia-smi` (present on Linux/Windows/WSL
     whenever the NVIDIA driver is installed; never present on macOS, since
     no Mac hardware has a CUDA-capable GPU).
  2. If found, reads the driver's reported CUDA version and picks the newest
     published PaddlePaddle GPU wheel index the driver can run (cu118 / cu126
     / cu129 / cu130).
  3. pip-installs `paddlepaddle-gpu` from that index. If that install fails
     for any reason (offline, unsupported combo, etc.) it falls back to the
     plain CPU wheel so the app still works, just without acceleration.
  4. If no NVIDIA GPU is found, it just installs the CPU `paddlepaddle` wheel.

Usage:
    python gpu_setup.py                 # auto-detect (default)
    python gpu_setup.py --mode gpu      # force the GPU wheel
    python gpu_setup.py --mode cpu      # force the CPU wheel
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys

# CUDA runtime version (as reported by `nvidia-smi`) -> PaddlePaddle wheel
# index folder. Ordered highest to lowest; we use the newest index whose
# floor the detected driver satisfies.
_CUDA_INDEX_FLOORS = [
    (13.0, "cu130"),
    (12.9, "cu129"),
    (12.6, "cu126"),
    (11.8, "cu118"),
]
_DEFAULT_CUDA_INDEX = "cu118"  # broadest driver compatibility (>= 450.80.02)
_PADDLE_INDEX_BASE = "https://www.paddlepaddle.org.cn/packages/stable"


def _run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False)
    return proc.stdout or ""


def detect_nvidia_gpu() -> bool:
    """True if `nvidia-smi` is on PATH and actually reports a GPU."""
    if shutil.which("nvidia-smi") is None:
        return False
    try:
        out = _run(["nvidia-smi", "-L"])
        return "GPU" in out
    except (OSError, subprocess.SubprocessError):
        return False


def detect_cuda_index() -> str:
    """Best-guess PaddlePaddle GPU wheel index folder for the installed driver."""
    try:
        out = _run(["nvidia-smi"])
        m = re.search(r"CUDA Version:\s*([\d.]+)", out)
        if m:
            version = float(m.group(1))
            for floor, index in _CUDA_INDEX_FLOORS:
                if version >= floor:
                    return index
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return _DEFAULT_CUDA_INDEX


def _pip_install(*args: str) -> bool:
    cmd = [sys.executable, "-m", "pip", "install", "--no-cache-dir", *args]
    print(f"[gpu_setup] Running: {' '.join(cmd)}")
    return subprocess.run(cmd, check=False).returncode == 0


def install_cpu() -> bool:
    print("[gpu_setup] Installing CPU-only paddlepaddle...")
    return _pip_install("paddlepaddle")


def install_gpu() -> bool:
    cuda_index = detect_cuda_index()
    index_url = f"{_PADDLE_INDEX_BASE}/{cuda_index}/"
    print(f"[gpu_setup] NVIDIA GPU detected - installing paddlepaddle-gpu ({cuda_index})...")
    if _pip_install("paddlepaddle-gpu", "-i", index_url):
        return True
    print("[gpu_setup] paddlepaddle-gpu install failed - falling back to CPU paddlepaddle.")
    return install_cpu()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=["auto", "gpu", "cpu"], default="auto",
        help="Force the gpu or cpu wheel, or auto-detect (default).",
    )
    args = parser.parse_args()

    if args.mode == "cpu":
        ok = install_cpu()
    elif args.mode == "gpu":
        ok = install_gpu()
    else:
        has_gpu = detect_nvidia_gpu()
        print(f"[gpu_setup] NVIDIA GPU detected: {has_gpu}")
        ok = install_gpu() if has_gpu else install_cpu()

    if not ok:
        print("[gpu_setup] ERROR: could not install any paddlepaddle build.")
        return 1

    print("[gpu_setup] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())