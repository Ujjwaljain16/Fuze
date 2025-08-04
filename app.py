
import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager
from datetime import timedelta
from models import db
from sqlalchemy import text
from flask_cors import CORS
import numpy as np
from redis_utils import redis_cache

# Import blueprints
from blueprints.auth import auth_bp
from blueprints.projects import projects_bp
from blueprints.tasks import tasks_bp
from blueprints.bookmarks import bookmarks_bp
from blueprints.recommendations import recommendations_bp
from blueprints.feedback import feedback_bp
from blueprints.profile import profile_bp
from blueprints.search import search_bp


# Global embedding model
# embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# def get_embedding(text):
#     if not text:
#         return np.zeros(384)
#     return embedding_model.encode([text])[0]

def create_app():
    """Application factory pattern for better testing and modularity"""
    app = Flask(__name__)
    
    # Environment-based configuration
    env = os.environ.get('FLASK_ENV', 'development')
    if env == 'production':
        app.config.from_object('config.ProductionConfig')
    else:
        app.config.from_object('config.DevelopmentConfig')
    
    # Override with environment variables if needed
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 15))
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=app.config.get('JWT_REFRESH_TOKEN_EXPIRES', 14))
    
    # Configure CORS based on environment
    if app.config.get('DEBUG'):
        # Development: Allow all origins with credentials
        CORS(app, 
             origins=app.config.get('CORS_ORIGINS', ['http://localhost:3000', 'http://localhost:5173']), 
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-CSRF-TOKEN'],
             methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    else:
        # Production: Restrict to specific origins
        CORS(app, 
             origins=app.config.get('CORS_ORIGINS', []), 
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-CSRF-TOKEN'],
             methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    
    # Initialize extensions
    db.init_app(app)
    jwt = JWTManager(app)
    
    # JWT Error Handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'message': 'The token has expired',
            'error': 'token_expired'
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'message': 'Signature verification failed',
            'error': 'invalid_token'
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'message': 'Request does not contain an access token',
            'error': 'authorization_required'
        }), 401
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(bookmarks_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(search_bp)
    
    # Register user API key blueprint
    from blueprints.user_api_key import init_app as init_user_api_key
    init_user_api_key(app)
    
    # Initialize API manager
    from multi_user_api_manager import init_api_manager
    with app.app_context():
        init_api_manager()
    
    # Security headers middleware
    @app.after_request
    def add_security_headers(response):
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # HTTPS-only headers in production
        if app.config.get('HTTPS_ENABLED'):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    # Basic route
    @app.route('/')
    def index():
        return {
            'message': 'Fuze API running', 
            'version': '1.0.0',
            'environment': app.config.get('ENV', 'development'),
            'https_enabled': app.config.get('HTTPS_ENABLED', False),
            'csrf_enabled': app.config.get('CSRF_ENABLED', False)
        }
    
    # API Key Management Page
    @app.route('/api-key-management')
    def api_key_management():
        """API Key Management Page"""
        from flask import render_template
        return render_template('api_key_management.html')
    
    # Health check endpoint for Chrome extension
    @app.route('/api/health')
    def health_check():
        try:
            # Test database connection using proper SQLAlchemy syntax
            db.session.execute(text('SELECT 1'))
            db_status = 'connected'
        except Exception as e:
            db_status = f'error: {str(e)}'
        
        # Get Redis status
        redis_stats = redis_cache.get_cache_stats()
        
        return {
            'status': 'healthy' if db_status == 'connected' and redis_stats.get('connected', False) else 'degraded',
            'message': 'Fuze API is running',
            'version': '1.0.0',
            'environment': app.config.get('ENV', 'development'),
            'database': db_status,
            'redis': redis_stats
        }, 200 if db_status == 'connected' else 500
    
    # Redis health check endpoint
    @app.route('/api/health/redis')
    def redis_health_check():
        redis_stats = redis_cache.get_cache_stats()
        return jsonify(redis_stats), 200 if redis_stats.get('connected', False) else 503
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return {'message': 'Bad request'}, 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return {'message': 'Unauthorized'}, 401
    
    @app.errorhandler(404)
    def not_found(error):
        return {'message': 'Not found'}, 404
    
    @app.errorhandler(500)
    def internal_server_error(error):
        return {'message': 'Internal server error'}, 500
    
    return app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    # Use configuration-based debug mode
    debug_mode = app.config.get('DEBUG', False)
    host = '0.0.0.0' if app.config.get('ENV') == 'production' else 'localhost'
    port = int(os.environ.get('PORT', 5000))
    
    # SSL context for HTTPS in production
    ssl_context = None
    if app.config.get('HTTPS_ENABLED'):
        cert_path = os.environ.get('SSL_CERT_PATH')
        key_path = os.environ.get('SSL_KEY_PATH')
        if cert_path and key_path:
            ssl_context = (cert_path, key_path)
    
    app.run(
        host=host, 
        port=port, 
        debug=debug_mode,
        ssl_context=ssl_context
    ) 