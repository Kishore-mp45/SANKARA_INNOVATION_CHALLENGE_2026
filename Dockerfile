FROM python:3.11-slim

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy backend requirements and install (production-light, no OpenCV/YOLO)
COPY backend/requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy backend code
COPY backend/ ./backend/

# Copy ML models
COPY ml_models/ ./ml_models/

# Copy frontend (for static file serving)
COPY frontend/ ./frontend/

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Set working directory to backend
WORKDIR /app/backend

# Environment variables
ENV USE_SQLITE=true
ENV DEBUG=false
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose port
EXPOSE ${PORT}

# Start using the shell script (guaranteed to expand $PORT)
ENTRYPOINT ["/bin/bash", "/app/start.sh"]
