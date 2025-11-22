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

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=wsgi:app
ENV PORT=7860

# Expose port (Hugging Face Spaces uses 7860)
EXPOSE 7860

# Health check (optional - Spaces handles this)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#     CMD python -c "import requests; requests.get('http://localhost:7860/api/health')" || exit 1

# Run the application
# Use app.py as entry point for Hugging Face Spaces compatibility
# Use gevent worker for better handling of SSE streams and long-running connections
# Gevent handles concurrent connections efficiently without blocking
# Increased timeout to 2000s (33 minutes) to handle SSE streams with 30-minute max connection time
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:7860", "--workers", "1", "--worker-class", "gevent", "--worker-connections", "1000", "--timeout", "2000", "--keep-alive", "5", "--access-logfile", "-", "--error-logfile", "-"]

