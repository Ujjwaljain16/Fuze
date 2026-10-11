#!/bin/bash
# Startup script for Hugging Face Spaces / Docker environments
# Uses supervisord for process supervision

set -euo pipefail

ALEMBIC_INI="/app/alembic.ini"
[ -f "$ALEMBIC_INI" ] || ALEMBIC_INI="./alembic.ini"

# Never serve traffic on a schema older than the code: every query touching a newer
# column would 500, and security migrations (e.g. 0013's RLS lockdown) would be missing.
# Each revision runs in its own transaction, so a failure leaves the last good revision.
echo "Running database migrations ($ALEMBIC_INI)..."
if ! python -m alembic -c "$ALEMBIC_INI" upgrade head; then
    echo "FATAL: database migration failed; refusing to start." >&2
    exit 1
fi

echo "Starting Fuze processes via supervisord..."
CONF_PATH="/app/supervisord.conf"
if [ ! -f "$CONF_PATH" ]; then
    CONF_PATH="./supervisord.conf"
fi

exec supervisord -c "$CONF_PATH"
