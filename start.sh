#!/bin/bash
# Startup script for Hugging Face Spaces / Docker environments
# Uses supervisord for process supervision

set -e

echo "Running automatic database migrations..."
if [ -f "/app/alembic.ini" ]; then
    python -m alembic -c /app/alembic.ini upgrade head || echo "Warning: Alembic migration auto-run failed, continuing startup..."
elif [ -f "./alembic.ini" ]; then
    python -m alembic -c ./alembic.ini upgrade head || echo "Warning: Alembic migration auto-run failed, continuing startup..."
elif [ -f "./backend/alembic.ini" ]; then
    python -m alembic -c ./backend/alembic.ini upgrade head || echo "Warning: Alembic migration auto-run failed, continuing startup..."
else
    python -m alembic upgrade head || echo "Warning: Alembic migration auto-run failed, continuing startup..."
fi

echo "Starting Fuze processes via supervisord..."
CONF_PATH="/app/supervisord.conf"
if [ ! -f "$CONF_PATH" ]; then
    CONF_PATH="./supervisord.conf"
fi

exec supervisord -c "$CONF_PATH"
