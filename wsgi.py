#!/usr/bin/env python3
"""
Production WSGI Entry Point for Fuze
Optimized for production deployment with Gunicorn
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the Flask app
from run_production import create_app

# Create the application instance
app = create_app()

if __name__ == "__main__":
    # This is for development only
    # In production, use: gunicorn wsgi:app
    app.run(host='0.0.0.0', port=5000)
