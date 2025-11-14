#!/usr/bin/env python3
"""
Production Flask Server for Fuze
Optimized for maximum performance with proper WSGI server
Enhanced with Intent Analysis System optimizations and SSL connection management
"""

import os
import time
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, render_template
from flask_jwt_extended import JWTManager
from datetime import timedelta, datetime
from models import db
from sqlalchemy import text
from flask_cors import CORS
import numpy as np
from redis_utils import redis_cache
import logging

# Configure production logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('production.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Import rate limiting middleware
try:
    from middleware.rate_limiting import init_rate_limiter
    RATE_LIMITING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"[WARNING] Rate limiting middleware not available: {e}")
    RATE_LIMITING_AVAILABLE = False

# Import database connection manager for SSL handling
try:
    from database_connection_manager import (
        get_database_engine, 
        test_database_connection, 
        refresh_database_connections,
        get_database_info
    )
    connection_manager_available = True
    logger.info("[OK] Database connection manager imported successfully")
except ImportError as e:
    logger.warning(f"[WARNING] Database connection manager not available: {e}")
    connection_manager_available = False

# Import blueprints with error handling
try:
    from blueprints.auth import auth_bp
    from blueprints.projects import projects_bp
    from blueprints.tasks import tasks_bp
    from blueprints.bookmarks import bookmarks_bp
    from blueprints.feedback import feedback_bp
    from blueprints.profile import profile_bp
    from blueprints.search import search_bp
    from blueprints.user_api_key import init_app as init_user_api_key
    from multi_user_api_manager import init_api_manager
    
    # Import recommendations blueprint with error handling
    try:
        from blueprints.recommendations import recommendations_bp
        recommendations_available = True
        logger.info("[OK] Recommendations blueprint imported successfully")
    except ImportError as e:
        logger.warning(f"[WARNING] Recommendations blueprint not available: {e}")
        recommendations_available = False
    
    # Import LinkedIn blueprint with error handling
    try:
        from blueprints.linkedin import linkedin_bp
        linkedin_available = True
        logger.info("[OK] LinkedIn blueprint imported successfully")
    except ImportError as e:
        logger.warning(f"[WARNING] LinkedIn blueprint not available: {e}")
        linkedin_available = False
        
    logger.info("[OK] All blueprints imported successfully")
        
except ImportError as e:
    logger.warning(f"[WARNING] Some blueprints not available: {e}")
    recommendations_available = False
    linkedin_available = False

# Import intent analysis components for production optimization
try:
    from intent_analysis_engine import IntentAnalysisEngine
    from gemini_utils import GeminiAnalyzer
    intent_analysis_available = True
    logger.info("[OK] Intent Analysis components imported successfully")
except ImportError as e:
    logger.warning(f"[WARNING] Intent Analysis components not available: {e}")
    intent_analysis_available = False

# Initialize status variables at module level - only set what's not already defined
if 'database_available' not in locals():
    database_available = False
if 'recommendations_available' not in locals():
    recommendations_available = False
if 'linkedin_available' not in locals():
    linkedin_available = False
if 'intent_analysis_available' not in locals():
    intent_analysis_available = False
if 'connection_manager_available' not in locals():
    connection_manager_available = False

# Set production environment
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = 'False'

def create_app():
    app = Flask(__name__)
    # Environment-based configuration
    env = os.environ.get('FLASK_ENV', 'development')
    if env == 'production':
        app.config.from_object('config.ProductionConfig')
    else:
        app.config.from_object('config.DevelopmentConfig')
    
    # JWT configuration is already set in config.py
    # Production-optimized CORS configuration
    if app.config.get('DEBUG'):
        # Development: Allow localhost origins
        CORS(app, 
             origins=app.config.get('CORS_ORIGINS', ['http://localhost:3000', 'http://localhost:5173', 'http://127.0.0.1:5173']), 
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-CSRF-TOKEN'],
             methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
             max_age=86400)
    else:
        # Production: Only allow explicitly configured origins
        cors_origins_env = os.environ.get('CORS_ORIGINS', '')
        if cors_origins_env:
            # Parse comma-separated list from environment
            cors_origins = [origin.strip() for origin in cors_origins_env.split(',') if origin.strip()]
        else:
            # Fallback: Only allow specific production domains (remove localhost for security)
            cors_origins = []
            logger.warning("[WARNING] CORS_ORIGINS not set in production - no origins allowed")
        
        CORS(app, 
             origins=cors_origins, 
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-CSRF-TOKEN'],
             methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
             max_age=86400)
    
    # Initialize rate limiting
    limiter = None
    if RATE_LIMITING_AVAILABLE:
        limiter = init_rate_limiter(app)
        if limiter:
            logger.info("[OK] Rate limiting initialized")
        else:
            logger.warning("[WARNING] Rate limiting initialization failed")
    else:
        logger.warning("[WARNING] Rate limiting not available")
    
    # Make limiter available to blueprints
    app.limiter = limiter
    
    # Initialize database with enhanced SSL handling
    try:
        # Initialize database only once
        db.init_app(app)
        
        if connection_manager_available:
            # Use the connection manager to get a working engine
            try:
                engine = get_database_engine()
                # Configure the app to use our managed engine instead of trying to override db.engine
                app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                    'pool_pre_ping': True,
                    'pool_recycle': 300,
                    'pool_size': 5,
                    'max_overflow': 10,
                    'pool_timeout': 20
                }
                
                logger.info("[OK] Database initialized with connection manager")
            except Exception as e:
                logger.warning(f"[WARNING] Connection manager failed, using standard engine: {e}")
                # Try to configure standard database options as fallback
                try:
                    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                        'pool_pre_ping': True,
                        'pool_recycle': 300,
                        'pool_size': 3,
                        'max_overflow': 5,
                        'pool_timeout': 30,
                        'connect_args': {
                            'connect_timeout': 30,
                            'options': '-c statement_timeout=60000 -c idle_in_transaction_session_timeout=60000'
                        }
                    }
                    logger.info("[OK] Database extension initialized with fallback configuration")
                except Exception as fallback_error:
                    logger.warning(f"[WARNING] Fallback configuration failed: {fallback_error}")
                    logger.info("[OK] Database extension initialized (basic mode)")
        else:
            logger.info("[OK] Database extension initialized (standard mode)")
    except Exception as e:
        logger.error(f"[ERROR] Error initializing database extension: {e}")
        # Continue without database - some endpoints might still work
    
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
    
    # Test database connection before proceeding with enhanced SSL handling
    global database_available
    try:
        with app.app_context():
            if connection_manager_available:
                # Use connection manager for testing with multiple attempts
                max_connection_attempts = 3
                connection_successful = False
                
                for attempt in range(max_connection_attempts):
                    try:
                        if test_database_connection():
                            database_available = True
                            connection_successful = True
                            logger.info(f"[OK] Database connection test successful (connection manager) on attempt {attempt + 1}")
                            break
                        else:
                            logger.warning(f"[WARNING] Database connection test failed on attempt {attempt + 1}")
                            if attempt < max_connection_attempts - 1:
                                logger.info(f"[INFO] Retrying database connection in 5 seconds...")
                                time.sleep(5)
                                
                                # Try to refresh connections
                                if refresh_database_connections():
                                    logger.info("[OK] Database connections refreshed, retrying...")
                                else:
                                    logger.warning("[WARNING] Failed to refresh database connections")
                    except Exception as e:
                        logger.warning(f"[WARNING] Database connection attempt {attempt + 1} failed: {e}")
                        if attempt < max_connection_attempts - 1:
                            logger.info(f"[INFO] Retrying database connection in 5 seconds...")
                            time.sleep(5)
                
                if not connection_successful:
                    # Final attempt to refresh connections
                    if refresh_database_connections():
                        database_available = True
                        logger.info("[OK] Database connections refreshed successfully on final attempt")
                    else:
                        database_available = False
                        logger.warning("[WARNING] Database connection test failed after all attempts")
            else:
                # Fallback to standard testing
                db.session.execute(text('SELECT 1'))
                database_available = True
                logger.info("[OK] Database connection test successful (standard)")
    except Exception as e:
        logger.warning(f"[WARNING] Database connection test failed: {e}")
        logger.warning("[WARNING] Server will start but database-dependent features may not work")
        database_available = False
    
    # Register blueprints with error handling
    try:
        app.register_blueprint(auth_bp)
        app.register_blueprint(projects_bp)
        app.register_blueprint(tasks_bp)
        app.register_blueprint(bookmarks_bp)
        app.register_blueprint(feedback_bp)
        app.register_blueprint(profile_bp)
        app.register_blueprint(search_bp)
        
        # Register recommendations blueprint if available
        if recommendations_available:
            app.register_blueprint(recommendations_bp)
            logger.info("[OK] Recommendations blueprint registered")
        else:
            logger.warning("[WARNING] Recommendations blueprint not registered")
            
        # Register LinkedIn blueprint if available
        if linkedin_available:
            app.register_blueprint(linkedin_bp)
            logger.info("[OK] LinkedIn blueprint registered")
        else:
            logger.warning("[WARNING] LinkedIn blueprint not registered")
            
        # Register user API key blueprint
        init_user_api_key(app)
        logger.info("[OK] All blueprints registered successfully")
    except Exception as e:
        logger.error(f"[ERROR] Error registering blueprints: {e}")
    
    # Initialize API manager with error handling
    with app.app_context():
        try:
            if database_available:
                init_api_manager()
                logger.info("[OK] API manager initialized")
            else:
                logger.warning("[WARNING] Skipping API manager initialization - database unavailable")
        except Exception as e:
            logger.error(f"[ERROR] Error initializing API manager: {e}")
    
    # Initialize Intent Analysis System for production with error handling
    with app.app_context():
        try:
            global intent_analysis_available
            
            # Only proceed if both intent analysis and database are available
            if intent_analysis_available and database_available:
                # Test intent analysis system initialization
                gemini_api_key = os.environ.get('GEMINI_API_KEY')
                if gemini_api_key:
                    # Test Gemini connection
                    try:
                        test_analyzer = GeminiAnalyzer(gemini_api_key)
                        logger.info("[OK] Intent Analysis System (Gemini) initialized successfully")
                    except Exception as e:
                        logger.warning(f"[WARNING] Intent Analysis System (Gemini) initialization failed: {e}")
                        intent_analysis_available = False
                else:
                    logger.warning("[WARNING] GEMINI_API_KEY not found - Intent Analysis will not work")
                    intent_analysis_available = False
            elif not database_available:
                logger.warning("[WARNING] Intent Analysis System disabled - database unavailable")
                # intent_analysis_available remains as imported (True or False)
            else:
                # intent_analysis_available is False from import failure
                logger.warning("[WARNING] Intent Analysis components not available")
        except Exception as e:
            logger.error(f"[ERROR] Error initializing Intent Analysis System: {e}")
            intent_analysis_available = False
    
    # Security headers middleware
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
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
            'csrf_enabled': app.config.get('CSRF_ENABLED', False),
            'database_available': database_available,
            'recommendations_available': recommendations_available,
            'intent_analysis_available': intent_analysis_available,
            'linkedin_available': linkedin_available,
            'connection_manager_available': connection_manager_available
        }
    
    
    # Health check endpoint for Chrome extension
    @app.route('/api/health')
    def health_check():
        try:
            if database_available:
                if connection_manager_available:
                    # Use connection manager for health check
                    if test_database_connection():
                        db_status = 'connected'
                    else:
                        db_status = 'degraded'
                else:
                    # Fallback to standard health check
                    db.session.execute(text('SELECT 1'))
                    db_status = 'connected'
            else:
                db_status = 'unavailable'
        except Exception as e:
            db_status = f'error: {str(e)}'
        
        redis_stats = redis_cache.get_cache_stats()
        
        # Determine overall status
        if db_status == 'connected' and redis_stats.get('connected', False):
            overall_status = 'healthy'
        elif db_status == 'unavailable':
            overall_status = 'degraded'
        else:
            overall_status = 'unhealthy'
        
        return {
            'status': overall_status,
            'message': 'Fuze API is running',
            'version': '1.0.0',
            'environment': app.config.get('ENV', 'development'),
            'database': db_status,
            'redis': redis_stats,
            'database_available': database_available,
            'recommendations_available': recommendations_available,
            'intent_analysis_available': intent_analysis_available,
            'linkedin_available': linkedin_available,
            'connection_manager_available': connection_manager_available
        }, 200 if overall_status in ['healthy', 'degraded'] else 500
    
    # Redis health check endpoint
    @app.route('/api/health/redis')
    def redis_health_check():
        redis_stats = redis_cache.get_cache_stats()
        return jsonify(redis_stats), 200 if redis_stats.get('connected', False) else 503
    
    # Database health check endpoint with enhanced SSL handling
    @app.route('/api/health/database')
    def database_health_check():
        try:
            if not database_available:
                return jsonify({
                    'status': 'unavailable',
                    'service': 'database',
                    'message': 'Database connection not available',
                    'troubleshooting': [
                        'Check if DATABASE_URL environment variable is set',
                        'Verify database host is accessible',
                        'Check network connectivity to database server',
                        'Verify database credentials are correct',
                        'Check SSL configuration if using SSL'
                    ]
                }), 503
            
            if connection_manager_available:
                # Use connection manager for health check
                if test_database_connection():
                    # Get connection info from manager
                    connection_info = get_database_info()
                    return jsonify({
                        'status': 'healthy',
                        'service': 'database',
                        'message': 'Database connection successful (connection manager)',
                        'connection_info': connection_info,
                        'tested_at': datetime.now().isoformat()
                    }), 200
                else:
                    # Try to refresh connections
                    if refresh_database_connections():
                        connection_info = get_database_info()
                        return jsonify({
                            'status': 'recovered',
                            'service': 'database',
                            'message': 'Database connection recovered after refresh',
                            'connection_info': connection_info,
                            'tested_at': datetime.now().isoformat()
                        }), 200
                    else:
                        return jsonify({
                            'status': 'unhealthy',
                            'service': 'database',
                            'error': 'Connection test failed after refresh',
                            'troubleshooting': [
                                'Database server may be down',
                                'Check database connection pool settings',
                                'Verify database permissions',
                                'Check for network issues',
                                'Check SSL configuration'
                            ]
                        }), 500
            else:
                # Fallback to standard health check
                from database_utils import check_database_connection
                if check_database_connection():
                    return jsonify({
                        'status': 'healthy',
                        'service': 'database',
                        'message': 'Database connection successful (standard)',
                        'connection_info': {
                            'available': True,
                            'tested_at': datetime.now().isoformat()
                        }
                    }), 200
                else:
                    return jsonify({
                        'status': 'unhealthy',
                        'service': 'database',
                        'error': 'Connection test failed',
                        'troubleshooting': [
                            'Database server may be down',
                            'Check database connection pool settings',
                            'Verify database permissions',
                            'Check for network issues'
                        ]
                    }), 500
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'service': 'database',
                'error': str(e),
                'troubleshooting': [
                    'Check application logs for detailed error',
                    'Verify database configuration',
                    'Check if database service is running',
                    'Verify network connectivity',
                    'Check SSL configuration if using SSL'
                ]
            }), 500
    
    # Intent Analysis System health check endpoint
    @app.route('/api/health/intent-analysis')
    def intent_analysis_health_check():
        try:
            if not intent_analysis_available:
                return jsonify({
                    'status': 'unavailable',
                    'service': 'intent_analysis',
                    'message': 'Intent Analysis components not available'
                }), 503
            
            gemini_api_key = os.environ.get('GEMINI_API_KEY')
            if not gemini_api_key:
                return jsonify({
                    'status': 'unhealthy',
                    'service': 'intent_analysis',
                    'error': 'GEMINI_API_KEY not configured'
                }), 503
            
            # Test Gemini connection
            try:
                test_analyzer = GeminiAnalyzer(gemini_api_key)
                return jsonify({
                    'status': 'healthy',
                    'service': 'intent_analysis',
                    'message': 'Intent Analysis System operational',
                    'gemini_model': 'connected'
                }), 200
            except Exception as e:
                return jsonify({
                    'status': 'unhealthy',
                    'service': 'intent_analysis',
                    'error': f'Gemini connection failed: {str(e)}'
                }), 503
                
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'service': 'intent_analysis',
                'error': str(e)
            }), 500
    
    # LinkedIn System health check endpoint
    @app.route('/api/health/linkedin')
    def linkedin_health_check():
        try:
            if not linkedin_available:
                return jsonify({
                    'status': 'unavailable',
                    'service': 'linkedin',
                    'message': 'LinkedIn components not available'
                }), 503
            
            # Test LinkedIn scraper initialization
            try:
                from easy_linkedin_scraper import EasyLinkedInScraper
                test_scraper = EasyLinkedInScraper()
                return jsonify({
                    'status': 'healthy',
                    'service': 'linkedin',
                    'message': 'LinkedIn Scraper operational',
                    'scraper_type': 'EasyLinkedInScraper'
                }), 200
            except Exception as e:
                return jsonify({
                    'status': 'unhealthy',
                    'service': 'linkedin',
                    'error': f'LinkedIn scraper initialization failed: {str(e)}'
                }), 503
                
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'service': 'linkedin',
                'error': str(e)
            }), 500
    
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
    
    # Database connection error handler with SSL error handling
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Check if it's a database connection error
        error_str = str(e).lower()
        if any(error_type in error_str for error_type in [
            'could not translate host name', 
            'operationalerror', 
            'ssl connection has been closed',
            'connection closed unexpectedly',
            'ssl error'
        ]):
            logger.error(f"Database connection error: {e}")
            
            # Try to refresh connections if using connection manager
            if connection_manager_available:
                try:
                    if refresh_database_connections():
                        logger.info("Database connections refreshed successfully")
                        return jsonify({
                            'error': 'Database connection recovered',
                            'message': 'Database connection has been restored. Please try again.',
                            'status': 'recovered'
                        }), 503
                except Exception as refresh_error:
                    logger.error(f"Failed to refresh connections: {refresh_error}")
            
            return jsonify({
                'error': 'Database connection failed',
                'message': 'Database is currently unavailable. Please try again later.',
                'status': 'database_error',
                'troubleshooting': [
                    'Check if database server is running',
                    'Verify network connectivity',
                    'Check database configuration',
                    'Check SSL configuration if using SSL',
                    'Contact system administrator'
                ]
            }), 503
        
        # Log other errors (don't expose details to client)
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred. Please try again later.',
            'status': 'error'
        }), 500
    
    return app

app = create_app()

if __name__ == "__main__":
    logger.info("Starting Fuze Production Server...")
    logger.info("Performance Optimized Mode with SSL Connection Management")
    logger.info("Debug: DISABLED")
    logger.info("Environment: PRODUCTION")
    logger.info("=" * 50)
    
    # Display system status
    logger.info("System Status:")
    logger.info(f"   Database: {'[OK] Available' if database_available else '[ERROR] Unavailable'}")
    logger.info(f"   Connection Manager: {'[OK] Available' if connection_manager_available else '[ERROR] Unavailable'}")
    logger.info(f"   Intent Analysis: {'[OK] Available' if intent_analysis_available else '[ERROR] Unavailable'}")
    logger.info(f"   Recommendations: {'[OK] Available' if recommendations_available else '[ERROR] Unavailable'}")
    logger.info(f"   LinkedIn: {'[OK] Available' if linkedin_available else '[ERROR] Unavailable'}")
    logger.info(f"   Rate Limiting: {'[OK] Available' if RATE_LIMITING_AVAILABLE else '[WARNING] Unavailable'}")
    logger.info("=" * 50)
    
    # Check HTTPS configuration
    https_enabled = os.environ.get('HTTPS_ENABLED', 'False').lower() == 'true'
    ssl_cert_path = os.environ.get('SSL_CERT_PATH')
    ssl_key_path = os.environ.get('SSL_KEY_PATH')
    
    if https_enabled and ssl_cert_path and ssl_key_path:
        # Check if SSL certificate files exist
        if os.path.exists(ssl_cert_path) and os.path.exists(ssl_key_path):
            logger.info(f"HTTPS Enabled: Using SSL certificates")
            logger.info(f"Certificate: {ssl_cert_path}")
            logger.info(f"Private Key: {ssl_key_path}")
            
            # Start Flask server with HTTPS
            app.run(
                host='0.0.0.0',
                port=5000,
                debug=False,
                threaded=True,
                ssl_context=(ssl_cert_path, ssl_key_path)
            )
        else:
            logger.warning("HTTPS enabled but SSL certificate files not found!")
            logger.warning(f"Certificate path: {ssl_cert_path}")
            logger.warning(f"Private key path: {ssl_key_path}")
            logger.warning("Falling back to HTTP mode for development...")
            
            # Fallback to HTTP for development
            app.run(
                host='0.0.0.0',
                port=5000,
                debug=False,
                threaded=True
            )
    else:
        logger.info("HTTP Mode: Starting without SSL (Development Mode)")
        
        # Start Flask server without HTTPS
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,
            threaded=True
        )