FROM python:3.11-slim

# ── Environment ──────────────────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ── System dependencies ───────────────────────────────────────────────────────
# libgl1 / libglib2.0-0  → required by OpenCV / PaddleOCR
# libx11-6 / python3-tk  → required for customtkinter GUI mode
# sqlite3                → CLI tool (the Python module is built-in)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libgomp1 \
    libglib2.0-0 \
    libx11-6 \
    python3-tk \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# ── App ───────────────────────────────────────────────────────────────────────
# NOTE: this Dockerfile now lives in installation/, but it must still be built
# with the REPO ROOT as the build context (so COPY . . can see core/, gui/,
# web/, main.py, utils.py, etc). That means:
#   docker build -f installation/Dockerfile -t receipt-vault .
# docker-compose.yml (in this same folder) is already set up to do this for
# you via `context: .. / dockerfile: Dockerfile`, so `docker compose up` and
# ./docker-up.sh still work exactly as before without any extra flags.
WORKDIR /app

ARG NO_AVX=false

# GPU_SUPPORT controls which paddlepaddle build gets installed for OCR:
#   false (default) -> CPU-only paddlepaddle (works everywhere)
#   true             -> paddlepaddle-gpu (needs an NVIDIA GPU + drivers on
#                        the *host*, plus nvidia-container-toolkit so the
#                        container can see it - see docker-compose.yml's
#                        app-gpu service and docker-up.sh's auto-detection)
# paddlepaddle-gpu's pip wheel bundles the CUDA/cuDNN runtime itself, so no
# nvidia/cuda base image is needed here - the host driver is all that matters.
ARG GPU_SUPPORT=false

COPY installation/requirements.txt installation/gpu_setup.py ./installation/
RUN pip install --no-cache-dir -r installation/requirements.txt

RUN if [ "$GPU_SUPPORT" = "true" ]; then \
        python installation/gpu_setup.py --mode gpu; \
    else \
        python installation/gpu_setup.py --mode cpu; \
    fi

RUN if [ "$NO_AVX" = "true" ]; then \
        pip install onnxruntime rapidocr_onnxruntime; \ 
    fi

COPY . .

# Persist the database directory as a named volume mount point
VOLUME ["/app/data"]

ENV FLAGS_use_mkldnn=0

# Default: web mode on 0.0.0.0 so Docker port mapping works
# Override with:  docker run ... receipt-vault python main.py --gui
EXPOSE 7000
CMD ["python", "main.py", "--web", "--host", "0.0.0.0", "--no-browser"]