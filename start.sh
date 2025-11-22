#!/bin/bash
# Startup script for Hugging Face Spaces
# Runs both the web server (Gunicorn) and RQ worker

set -e

echo "Starting Fuze backend services..."

# Start RQ worker in background
echo "Starting RQ worker..."
python backend/worker.py --queue default &
WORKER_PID=$!

# Function to cleanup on exit
cleanup() {
    echo "Shutting down services..."
    kill $WORKER_PID 2>/dev/null || true
    wait $WORKER_PID 2>/dev/null || true
    exit 0
}

# Trap signals to cleanup
trap cleanup SIGTERM SIGINT

# Start Gunicorn web server (foreground)
echo "Starting Gunicorn web server..."
exec gunicorn app:app \
    --bind 0.0.0.0:7860 \
    --workers 1 \
    --worker-class gevent \
    --worker-connections 1000 \
    --timeout 2000 \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile -

