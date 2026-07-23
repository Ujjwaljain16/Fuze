#!/bin/bash
# Startup script for Hugging Face Spaces / Docker environments
# Uses supervisord for process supervision

set -e

echo "Starting Fuze processes via supervisord..."
CONF_PATH="/app/supervisord.conf"
if [ ! -f "$CONF_PATH" ]; then
    CONF_PATH="./supervisord.conf"
fi

exec supervisord -c "$CONF_PATH"
