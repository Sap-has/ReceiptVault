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
    libglib2.0-0 \
    libx11-6 \
    python3-tk \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# ── App ───────────────────────────────────────────────────────────────────────
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persist the database directory as a named volume mount point
VOLUME ["/app/data"]

# Default: web mode on 0.0.0.0 so Docker port mapping works
# Override with:  docker run ... receipt-vault python main.py --gui
EXPOSE 7000
CMD ["python", "main.py", "--web", "--host", "0.0.0.0", "--no-browser"]