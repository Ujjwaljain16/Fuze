#!/usr/bin/env python3
"""
Root-level WSGI entry point for Render deployment
This file imports the app from backend.wsgi to ensure compatibility
"""

# Import the app from backend.wsgi
from backend.wsgi import app

# Export for gunicorn
__all__ = ['app']

