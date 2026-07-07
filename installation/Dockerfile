# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY installation/requirements.txt installation/gpu_setup.py ./installation/

# Install wheels into a local folder to easily copy over to final stage
RUN pip install --no-cache-dir --user -r installation/requirements.txt

ARG GPU_SUPPORT=false
RUN if [ "$GPU_SUPPORT" = "true" ]; then \
        python installation/gpu_setup.py --mode gpu; \
    else \
        python installation/gpu_setup.py --mode cpu; \
    fi

# ── Stage 2: Final Runtime ───────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLAGS_use_mkldnn=0

# System dependencies for OpenCV / PaddleOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libgomp1 \
    libglib2.0-0 \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy app code LAST so code modifications don't trigger full pip reinstallations
COPY . .

VOLUME ["/app/data"]
EXPOSE 7000

CMD ["python", "main.py", "--web", "--host", "0.0.0.0", "--no-browser"]