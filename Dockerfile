FROM python:3.11-slim

# Set environment variables to ensure Python doesn't buffer output and handles paths correctly
ENV PYTHONDONTRIES=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDELAY_IMPORT=0

# Install system dependencies required for OpenCV, PaddlePaddle, and SQLite3
# 'libgl1-mesa-glx' and 'libglib2.0-0' are essential for PaddleOCR/OpenCV on slim images
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libx11-6 \
    sqlite3 \
    python3-tk \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Command to run your application (replace with your entry point)
CMD ["python", "main.py"]