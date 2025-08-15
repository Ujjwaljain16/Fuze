#!/bin/bash
# Production Startup Script for Fuze Backend

echo "🚀 Starting Fuze Production Server..."

# Activate virtual environment (if using one)
# source venv/bin/activate

# Install production dependencies
echo "📦 Installing production dependencies..."
pip install -r requirements.production.txt

# Set production environment
export FLASK_ENV=production
export FLASK_DEBUG=False

# Start with Gunicorn (production WSGI server)
echo "🔥 Starting Gunicorn production server..."
gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 4 \
    --worker-class sync \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 30 \
    --keep-alive 2 \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    wsgi:app

echo "✅ Production server started successfully!"
