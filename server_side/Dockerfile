# People Counting API - Backend Dockerfile
# Optimized for Google Cloud Run
# 
# Build context: server_side/
# The weights must be copied from edge_side/infra/weights to server_side/infra/weights before building

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    WEIGHTS_PATH=/app/weights/yolov11n_ncnn_model \
    OUTPUT_DIR=/app/tmp

# Install minimal system dependencies for opencv-headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/

# Copy weights from edge_side (must be in build context)
# Run: cp -r ../edge_side/infra/weights ./weights before building
COPY weights/ ./weights/

# Create directories for temporary files
RUN mkdir -p /app/tmp /app/csi_data

# Set working directory to backend
WORKDIR /app/backend

# Expose port
EXPOSE 8000

# Run the application
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT --timeout-keep-alive 300
