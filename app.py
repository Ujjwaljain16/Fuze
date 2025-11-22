#!/usr/bin/env python3
"""
Hugging Face Spaces Entry Point
This file is required by Hugging Face Spaces for Docker deployments
It imports the Flask app from backend.wsgi
"""

# Import the app from backend.wsgi (wsgi.py at root imports from backend.wsgi)
from wsgi import app

# Hugging Face Spaces expects 'app' to be available
# The app is already created in backend/wsgi.py, exported via root wsgi.py
if __name__ == "__main__":
    # For local testing
    import os
    port = int(os.environ.get("PORT", 7860))
    app.run(host='0.0.0.0', port=port, debug=False)

