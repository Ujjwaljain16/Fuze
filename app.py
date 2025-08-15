#!/usr/bin/env python3
"""
Development Flask App for Fuze
This is the main application file for development and testing
"""

import os
from dotenv import load_dotenv
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from models import db
from redis_utils import redis_cache

# Load environment variables
load_dotenv()

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configuration
    app.config.from_object('config.DevelopmentConfig')
    
    # Initialize extensions
    db.init_app(app)
    jwt = JWTManager(app)
    
    # Optimized CORS configuration to reduce preflight requests
    CORS(app, 
         origins=['http://localhost:3000', 'http://localhost:5173', 'http://127.0.0.1:5173'],
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization', 'X-CSRF-TOKEN'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         # Add these optimizations:
         max_age=86400,  # Cache preflight for 24 hours
         expose_headers=['Content-Type', 'Authorization'],
         allow_credentials=True)
    
    # Import and register blueprints
    from blueprints.auth import auth_bp
    from blueprints.projects import projects_bp
    from blueprints.tasks import tasks_bp
    from blueprints.bookmarks import bookmarks_bp
    from blueprints.feedback import feedback_bp
    from blueprints.profile import profile_bp
    from blueprints.search import search_bp
    from blueprints.user_api_key import init_app
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(bookmarks_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(search_bp)
    
    # Try to register optional blueprints
    try:
        from blueprints.recommendations import recommendations_bp
        app.register_blueprint(recommendations_bp)
        print("✅ Recommendations blueprint registered")
    except ImportError as e:
        print(f"⚠️ Recommendations blueprint not available: {e}")
    
    try:
        from blueprints.linkedin import linkedin_bp
        app.register_blueprint(linkedin_bp)
        print("✅ LinkedIn blueprint registered")
    except ImportError as e:
        print(f"⚠️ LinkedIn blueprint not available: {e}")
    
    # Initialize user API key system
    init_app(app)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'message': 'Not found'}, 404
    
    @app.errorhandler(500)
    def internal_server_error(error):
        return {'message': 'Internal server error'}, 500
    
    return app

# Create the app instance
app = create_app()

if __name__ == "__main__":
    print("Starting Fuze Development Server...")
    print("Environment: DEVELOPMENT")
    print("Debug: ENABLED")
    print("=" * 50)
    
    # Test database connection
    with app.app_context():
        try:
            db.session.execute('SELECT 1')
            print("✅ Database connection successful")
        except Exception as e:
            print(f"⚠️ Database connection failed: {e}")
    
    # Start development server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )
