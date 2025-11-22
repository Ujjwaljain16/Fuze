#!/bin/bash
# Startup script for Hugging Face Spaces
# Runs both the web server (Gunicorn) and RQ worker

set -e

echo "Starting Fuze backend services..."

# Start RQ worker in background with output to stdout/stderr
echo "Starting RQ worker..."
cd /app
python backend/worker.py --queue default 2>&1 &
WORKER_PID=$!

# Wait a moment to see if worker starts successfully
sleep 3

# Check if worker is still running
if ! kill -0 $WORKER_PID 2>/dev/null; then
    echo "WARNING: RQ worker failed to start or crashed immediately!"
    echo "Background jobs will fall back to threading mode"
    echo "Check logs above for worker startup errors"
else
    echo "RQ worker started successfully (PID: $WORKER_PID)"
    echo "Worker is ready to process background jobs"
fi

# Function to cleanup on exit
cleanup() {
    echo "Shutting down services..."
    if kill -0 $WORKER_PID 2>/dev/null; then
        kill $WORKER_PID 2>/dev/null || true
        wait $WORKER_PID 2>/dev/null || true
    fi
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

