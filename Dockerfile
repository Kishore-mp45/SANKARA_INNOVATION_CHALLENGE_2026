FROM python:3.11-slim

# Install system dependencies for OpenCV and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy backend requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy ML models
COPY ml_models/ ./ml_models/

# Copy frontend (for static file serving)
COPY frontend/ ./frontend/

# Set working directory to backend
WORKDIR /app/backend

# Environment variables
ENV USE_SQLITE=true
ENV DEBUG=false
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Start the server
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
