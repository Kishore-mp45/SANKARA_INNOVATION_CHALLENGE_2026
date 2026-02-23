#!/bin/bash
# PatientPath AI - Startup Script
# Reads PORT from environment (Railway sets this) and starts uvicorn

# Default to 8000 if PORT is not set
PORT="${PORT:-8000}"

echo "=========================================="
echo "PatientPath AI - Starting Server"
echo "PORT: $PORT"
echo "USE_SQLITE: $USE_SQLITE"
echo "DEBUG: $DEBUG"
echo "Working Dir: $(pwd)"
echo "=========================================="

# Start uvicorn with the resolved port
exec python -m uvicorn main:app --host 0.0.0.0 --port "$PORT" --log-level info
