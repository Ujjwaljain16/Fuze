#!/usr/bin/env python3
"""
Production Flask Server for Fuze
Optimized for maximum performance
"""

import os
from app import create_app

# Set production environment
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = 'False'

# Create the app
app = create_app()

if __name__ == "__main__":
    print("🚀 Starting Fuze Production Server...")
    print("⚡ Performance Optimized Mode")
    print("🔧 Debug: DISABLED")
    print("🌐 Environment: PRODUCTION")
    print("=" * 50)
    
    # Run with production settings
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,  # Critical for performance
        threaded=True,  # Enable threading
        use_reloader=False  # Disable auto-reloader
    ) 