#!/bin/bash
# Startup script for Hugging Face Spaces
# Uses supervisord for process supervision

set -e

echo "Starting Fuze processes via supervisord..."
exec supervisord -c /app/supervisord.conf
