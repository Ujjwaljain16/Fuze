# Dockerfile for Hugging Face Spaces deployment
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
# Suppress pip root user warning (safe in Docker containers)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel --root-user-action=ignore && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt --root-user-action=ignore

# Install Scrapling browsers (required for Scrapling to work)
RUN camoufox fetch || echo "Camoufox fetch completed"

# Copy application code
COPY backend/ ./backend/
COPY wsgi.py .
COPY app.py .
COPY start.sh .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=wsgi:app
ENV PORT=7860

# Make startup script executable
RUN chmod +x start.sh

# Expose port (Hugging Face Spaces uses 7860)
EXPOSE 7860

# Health check (optional - Spaces handles this)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#     CMD python -c "import requests; requests.get('http://localhost:7860/api/health')" || exit 1

# Run the application
# Use startup script to run both web server and RQ worker
# 
# The startup script (start.sh) runs:
# 1. RQ worker in background (processes bookmark tasks)
# 2. Gunicorn web server in foreground (handles API requests)
#
# Gunicorn Configuration with Gevent Worker:
# - worker-class: gevent - Async worker that handles concurrent connections without blocking
#   Gevent automatically monkey-patches standard library for async I/O
# - workers: 1 - With gevent, 1 worker can handle 1000+ concurrent connections efficiently
# - worker-connections: 1000 - Max concurrent connections per worker (gevent can handle this)
# - timeout: 2000s - Long timeout for SSE streams (33 minutes max connection time)
# - keep-alive: 5s - Keep connections alive for better performance
#
# This configuration allows:
# ✅ Concurrent SSE streams + API calls without blocking
# ✅ Multiple users with simultaneous requests
# ✅ Long-lived SSE connections for real-time progress updates
# ✅ Efficient resource usage (1 worker handles many connections)
# ✅ Background job processing with RQ worker
CMD ["./start.sh"]

