#!/usr/bin/env python3
"""
Production WSGI Entry Point for Fuze
Optimized for production deployment with Gunicorn
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the Flask app
# Use absolute import for compatibility with gunicorn
import sys
import os
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from backend.run_production import create_app

# Create the application instance
# This is called when Gunicorn imports this module
app = create_app()

# Log that app is ready (for debugging)
if os.environ.get('FLASK_ENV') == 'production':
    import logging
    logger = logging.getLogger(__name__)
    logger.info("✅ WSGI app created and ready for Gunicorn")

if __name__ == "__main__":
    # This is for development only
    # In production, use: gunicorn wsgi:app
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
