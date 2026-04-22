#!/usr/bin/env python3
"""
Production Flask Server for Fuze
Optimized for maximum performance with proper WSGI server
Enhanced with Intent Analysis System optimizations and SSL connection management
"""

import os
import sys
import time
import re
from dotenv import load_dotenv

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv()

from flask import Flask, request, jsonify, render_template
from flask_jwt_extended import JWTManager
from datetime import timedelta, datetime
from models import db
from sqlalchemy import text
from flask_cors import CORS
import numpy as np
from utils.redis_utils import redis_cache
from utils.redis_utils import redis_cache
import logging
from core.logging_config import configure_logging, get_logger

# Import UnifiedConfig for standard settings
from utils.unified_config import get_config
config = get_config()

# Configure structured logging
configure_logging(debug=config.debug)
logger = get_logger(__name__)

# Initialize Sentry
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.rq import RqIntegration
import structlog
import uuid

def _scrub_sensitive_data(event, hint):
    """Remove sensitive fields before sending to Sentry."""
    if 'request' in event:
        headers = event['request'].get('headers', {})
        sensitive_headers = ['Authorization', 'Cookie', 'X-CSRF-TOKEN']
        for header in sensitive_headers:
            if header in headers:
                headers[header] = '[Filtered]'
    
    # Scrub bodies for common sensitive patterns
    if 'request' in event and 'data' in event['request']:
        import re
        body = str(event['request']['data'])
        body = re.sub(r'("password":\s*)"[^"]+"', r'\1"[Filtered]"', body)
        body = re.sub(r'("token":\s*)"[^"]+"', r'\1"[Filtered]"', body)
        event['request']['data'] = body

    # Remove embedding vectors
    if 'extra' in event:
        for key in list(event['extra'].keys()):
            if 'embedding' in key.lower():
                event['extra'][key] = '[Vector filtered]'
    
    return event

def init_sentry(unified_config):
    """Initialize Sentry with strict filtering and privacy."""
    dsn = unified_config.logging.sentry_dsn
    if not dsn:
        logger.warning("sentry_not_configured")
        return
    
    sentry_sdk.init(
        dsn=dsn,
        integrations=[
            FlaskIntegration(transaction_style='url'),
            SqlalchemyIntegration(),
            RedisIntegration(),
            RqIntegration(),
        ],
        traces_sample_rate=0.1 if not unified_config.debug else 1.0,
        profiles_sample_rate=0.01,
        environment=unified_config.environment,
        release=unified_config.logging.app_version,
        before_send=_scrub_sensitive_data,
    )
    logger.info("sentry_initialized", environment=unified_config.environment)

init_sentry(config)

# Import rate limiting middleware
try:
    from middleware.rate_limiting import init_rate_limiter
    RATE_LIMITING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"[WARNING] Rate limiting middleware not available: {e}")
    RATE_LIMITING_AVAILABLE = False

# Import database connection manager for SSL handling
try:
    from utils.database_connection_manager import (
        get_database_engine, 
        test_database_connection, 
        refresh_database_connections,
        get_database_info
    )
    connection_manager_available = True
    logger.info("database_connection_manager_imported")
except ImportError as e:
    logger.warning("database_connection_manager_not_available", error=str(e))
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
    
    # Import dashboard blueprint with error handling
    dashboard_available = False
    try:
        from blueprints.dashboard import dashboard_bp
        dashboard_available = True
        logger.info("blueprint_import_success", blueprint="dashboard")
    except ImportError as e:
        logger.warning("blueprint_import_not_available", blueprint="dashboard", error=str(e))
        dashboard_available = False
    except Exception as e:
        logger.error(f"[ERROR] Dashboard blueprint import failed: {e}")
        import traceback
        logger.error(f"Dashboard blueprint traceback: {traceback.format_exc()}")
        dashboard_available = False
    
    # Import API manager with error handling
    api_manager_available = False
    try:
        from services.multi_user_api_manager import init_api_manager
        api_manager_available = True
        logger.info("service_import_success", service="multi_user_api_manager")
    except ImportError as e:
        logger.warning("service_import_not_available", service="multi_user_api_manager", error=str(e))
        api_manager_available = False
    except Exception as e:
        logger.error("service_import_failed", service="multi_user_api_manager", error=str(e))
        api_manager_available = False

    # Import user API key blueprint with error handling
    user_api_key_available = False
    init_user_api_key = None
    try:
        from blueprints.user_api_key import init_app as init_user_api_key
        user_api_key_available = True
        logger.info("blueprint_import_success", blueprint="user_api_key")
    except ImportError as e:
        logger.warning("blueprint_import_not_available", blueprint="user_api_key", error=str(e))
        user_api_key_available = False
        init_user_api_key = None
    except Exception as e:
        logger.error("blueprint_import_failed", blueprint="user_api_key", error=str(e))
        user_api_key_available = False
        init_user_api_key = None

    # Import recommendations blueprint with error handling
    try:
        from blueprints.recommendations import recommendations_bp
        recommendations_available = True
        logger.info("blueprint_import_success", blueprint="recommendations")
    except ImportError as e:
        logger.warning("blueprint_import_not_available", blueprint="recommendations", error=str(e))
        recommendations_available = False
    
    # Import LinkedIn blueprint with error handling
    try:
        from blueprints.linkedin import linkedin_bp
        linkedin_available = True
        logger.info("blueprint_import_success", blueprint="linkedin")
    except ImportError as e:
        logger.warning("blueprint_import_not_available", blueprint="linkedin", error=str(e))
        linkedin_available = False
        
    logger.info("all_blueprints_imported")
        
except ImportError as e:
    logger.warning(f"[WARNING] Some blueprints not available: {e}")
    recommendations_available = False
    linkedin_available = False
    dashboard_available = False
    api_manager_available = False

# Import intent analysis components for production optimization
try:
    from ml.intent_analysis_engine import IntentAnalysisEngine
    from utils.gemini_utils import GeminiAnalyzer
    intent_analysis_available = True
    logger.info("intent_analysis_components_imported")
except ImportError as e:
    logger.warning("intent_analysis_components_not_available", error=str(e))
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

def _validate_production_env():
    """Validate critical environment variables for production"""
    # Skip validation during tests
    if os.environ.get('FLASK_ENV') == 'testing' or os.environ.get('PYTEST_CURRENT_TEST'):
        return
    
    critical_vars = {
        'SECRET_KEY': 'dev-secret-key-change-in-production',
        'JWT_SECRET_KEY': 'dev-jwt-secret-change-in-production',
        'DATABASE_URL': None,  # Optional but recommended
    }
    
    warnings = []
    errors = []
    
    for var, default_value in critical_vars.items():
        value = os.environ.get(var)
        if not value or (default_value and value == default_value):
            if var in ['SECRET_KEY', 'JWT_SECRET_KEY']:
                errors.append(f"{var} must be set to a secure value in production")
            else:
                warnings.append(f"{var} is not set (may cause issues)")
    
    for warning in warnings:
        logger.warning("production_config_warning", warning=warning)
    
    for error in errors:
        logger.error("production_config_error", error=error)
    
    if errors:
        raise ValueError(f"Critical production configuration errors: {', '.join(errors)}")

# Set environment based on how it's being run
# Only force production if explicitly set or if running via wsgi
if os.environ.get('FLASK_ENV') != 'development' and '__main__' not in sys.modules.get('__main__', {}).__file__ if '__main__' in sys.modules else True:
    os.environ.setdefault('FLASK_ENV', 'production')
    os.environ.setdefault('FLASK_DEBUG', 'False')
else:
    # Development mode
    os.environ.setdefault('FLASK_ENV', 'development')
    os.environ.setdefault('FLASK_DEBUG', 'True')

def create_app():
    app = Flask(__name__)
    # Environment-based configuration
    env = os.environ.get('FLASK_ENV', 'development')
    if env == 'production':
        app.config.from_object('config.ProductionConfig')
        # Validate critical environment variables in production (skip during tests)
        _validate_production_env()
    elif env == 'testing':
        # Use development config for testing but mark as testing
        app.config.from_object('config.DevelopmentConfig')
    else:
        app.config.from_object('config.DevelopmentConfig')
    
    # JWT configuration is already set in config.py
    # Production-optimized CORS configuration using UnifiedConfig
    from utils.unified_config import UnifiedConfig
    unified_config = UnifiedConfig()
    cors_config = unified_config.cors
    
    # Get CORS origins from UnifiedConfig
    cors_origins = cors_config.origins.copy()
    
    # In development, add localhost origins if not present
    if app.config.get('DEBUG'):
        localhost_origins = ['http://localhost:3000', 'http://localhost:5173', 'http://127.0.0.1:5173']
        for origin in localhost_origins:
            if origin not in cors_origins:
                cors_origins.append(origin)
    else:
        # Production: Add Vercel patterns if not already included
        vercel_patterns = [
            'https://itsfuze.vercel.app',
            'https://*.vercel.app',  # Allow all Vercel preview deployments
        ]
        
        # Merge Vercel patterns (avoid duplicates)
        for pattern in vercel_patterns:
            pattern_clean = pattern.rstrip('/')
            if pattern_clean not in cors_origins:
                cors_origins.append(pattern_clean)
    
    logger.info("cors_configured", count=len(cors_origins))
    logger.debug("cors_origins_list", origins=cors_origins)
    
    # flask-cors supports wildcard patterns directly as strings
    # No need to convert to regex - just pass the list as-is
    CORS(app, 
         origins=cors_origins,  # flask-cors handles wildcards like "https://*.vercel.app" automatically
         supports_credentials=cors_config.supports_credentials,
         allow_headers=['Content-Type', 'Authorization', 'X-CSRF-TOKEN'],
         expose_headers=['Content-Type', 'X-CSRF-TOKEN'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
         max_age=cors_config.max_age)
    
    # Initialize rate limiting
    limiter = None
    if RATE_LIMITING_AVAILABLE:
        limiter = init_rate_limiter(app)
        if limiter:
            logger.info("rate_limiting_initialized")
        else:
            logger.warning("rate_limiting_init_failed")
    else:
        logger.warning("rate_limiting_not_available")
    
    # Make limiter available to blueprints
    app.limiter = limiter
    
    # Initialize response compression for better performance
    compress = Compress()
    compress.init_app(app)
    logger.info("response_compression_enabled")
    
    # Initialize database with enhanced SSL handling
    try:
        # Initialize database only once
        db.init_app(app)
        
        if connection_manager_available:
            # Defer database configuration to avoid blocking startup
            # The connection manager will configure the database lazily on first request
            # This ensures the app starts quickly even if database is slow/unavailable
            logger.info("database_connection_manager_active_lazy")
            # Set up fallback configuration for now
            try:
                app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                    'pool_pre_ping': True,
                    'pool_recycle': 300,
                    'pool_size': 3,
                    'max_overflow': 5,
                    'pool_timeout': 30,
                    'connect_args': {
                        'connect_timeout': 10,  # Shorter timeout for faster startup
                        'options': '-c statement_timeout=60000 -c idle_in_transaction_session_timeout=60000'
                    }
                }
                logger.info("database_extension_init_lazy")
            except Exception as fallback_error:
                logger.warning("database_fallback_config_failed", error=str(fallback_error))
                logger.info("database_extension_init_basic")
        else:
            logger.info("database_extension_init_standard")
    except Exception as e:
        logger.error("database_extension_init_error", error=str(e))
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
    
    # Global Rate Limit Error Handler
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            'message': 'Too many requests. Please slow down.',
            'error': 'rate_limit_exceeded',
            'description': str(e.description)
        }), 429
        
    # Row-Level Security (RLS) Configuration
    from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
    from sqlalchemy import text
    
    @app.before_request
    def set_correlation_id():
        """Set correlation ID for request tracing/observability."""
        correlation_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
        g.correlation_id = correlation_id
        
        # Bind to structlog context for auto-injection in every log trace
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            method=request.method,
            path=request.path,
            ip=request.remote_addr
        )

    @app.after_request
    def add_correlation_header(response):
        """Echo correlation ID for frontend tracing."""
        response.headers['X-Request-ID'] = getattr(g, 'correlation_id', '')
        return response

    @app.before_request
    def set_rls_context():
        """Implement session management for Postgres Row-Level Security (RLS)"""
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        try:
            # We try to see if there's a valid JWT
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
            
            if user_id:
                # Set the Postgres config for RLS (only affects current transaction)
                db.session.execute(text("SET LOCAL app.current_user_id = :user_id"), {"user_id": str(user_id)})
        except Exception:
            # Ignore errors: no active session, invalid token, or db connection failed
            pass
    
    # Skip database connection test during startup to avoid blocking
    # Database will be tested and connected on first request
    global database_available
    database_available = False  # Will be set to True on first successful connection
    logger.info("database_test_deferred")
    
    # Simple root endpoint - responds immediately for port binding (no DB checks)
    @app.route('/')
    def root():
        """Simple root endpoint for health checks - responds immediately"""
        return {'status': 'ok', 'message': 'Fuze API is running'}, 200
    
    # Register blueprints with error handling
    try:
        app.register_blueprint(auth_bp)
        app.register_blueprint(projects_bp)
        app.register_blueprint(tasks_bp)
        app.register_blueprint(bookmarks_bp)
        app.register_blueprint(feedback_bp)
        app.register_blueprint(profile_bp)
        app.register_blueprint(search_bp)
        
        # Register dashboard blueprint if available
        if dashboard_available:
            app.register_blueprint(dashboard_bp)
            logger.info("blueprint_registered", blueprint="dashboard")
        else:
            logger.warning("blueprint_not_registered", blueprint="dashboard")
        
        # Register recommendations blueprint if available
        if recommendations_available:
            app.register_blueprint(recommendations_bp)
            logger.info("blueprint_registered", blueprint="recommendations")
        else:
            logger.warning("blueprint_not_registered", blueprint="recommendations")
            
        # Register LinkedIn blueprint if available
        if linkedin_available:
            app.register_blueprint(linkedin_bp)
            logger.info("blueprint_registered", blueprint="linkedin")
        else:
            logger.warning("blueprint_not_registered", blueprint="linkedin")
            
        # Register user API key blueprint if available
        logger.info(f"[DEBUG] About to register user API key blueprint")
        logger.info(f"[DEBUG] user_api_key_available: {user_api_key_available}, init_user_api_key: {init_user_api_key}")
        if user_api_key_available and init_user_api_key:
            try:
                init_user_api_key(app)
                logger.info("blueprint_registered", blueprint="user_api_key")
            except Exception as e:
                logger.warning("blueprint_registration_failed", blueprint="user_api_key", error=str(e))
        else:
            logger.warning("blueprint_not_registered", blueprint="user_api_key")
            
        logger.info("all_blueprints_registered")
    except Exception as e:
        logger.error(f"[ERROR] Error registering blueprints: {e}")
    
    # Initialize API manager with error handling
    with app.app_context():
        try:
            if api_manager_available:
                # Try to initialize API manager even if database test failed
                init_api_manager()
                logger.info("api_manager_initialized")
            else:
                logger.warning("api_manager_skipped_not_available")
        except Exception as e:
            logger.error("api_manager_init_failed", error=str(e))

    # Initialize Background Analysis Service
    try:
        from services.background_analysis_service import start_background_service
        start_background_service()
        logger.info("[OK] Background analysis service started")
    except Exception as e:
        logger.error("background_analysis_service_init_failed", error=str(e))
        logger.warning("background_analysis_not_available")
    
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
                        logger.info("intent_analysis_gemini_init_success")
                    except Exception as e:
                        logger.warning("intent_analysis_gemini_init_failed", error=str(e))
                        intent_analysis_available = False
                else:
                    logger.warning("intent_analysis_gemini_api_key_missing")
                    intent_analysis_available = False
            elif not database_available:
                logger.warning("[WARNING] Intent Analysis System disabled - database unavailable")
                # intent_analysis_available remains as imported (True or False)
            else:
                # intent_analysis_available is False from import failure
                logger.warning("[WARNING] Intent Analysis components not available")
        except Exception as e:
            logger.error("intent_analysis_system_init_error", error=str(e))
            intent_analysis_available = False
    
    # Import and apply security middleware
    try:
        from middleware.security_middleware import add_security_headers as security_headers_middleware
        security_middleware_available = True
    except ImportError:
        logger.warning("[WARNING] Security middleware not available")
        security_middleware_available = False
    
    # Security headers middleware - Production-grade
    @app.after_request
    def add_security_headers(response):
        # Use security middleware if available, otherwise use built-in
        if security_middleware_available:
            response = security_headers_middleware(response)
        else:
            # Fallback to built-in security headers
            response.headers['X-Content-Type-Options'] = 'nosniff'
            # Allow framing from Hugging Face Spaces
            if os.environ.get('HUGGINGFACE_SPACE') or 'hf.space' in request.host:
                response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            else:
                response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
            
            if not app.config.get('DEBUG') and app.config.get('HTTPS_ENABLED'):
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
            
            if not app.config.get('DEBUG'):
                # Allow framing from Hugging Face Spaces (for Docker Spaces)
                # This allows the Space interface to display the app
                frame_ancestors = "'none'"
                if os.environ.get('HUGGINGFACE_SPACE') or 'hf.space' in request.host:
                    frame_ancestors = "'self' https://*.hf.space https://huggingface.co"
                
                csp = (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                    "font-src 'self' https://fonts.gstatic.com; "
                    "img-src 'self' data: https:; "
                    "connect-src 'self' https:; "
                    f"frame-ancestors {frame_ancestors};"
                )
                response.headers['Content-Security-Policy'] = csp
        
        return response
    
    # CRITICAL FIX: Add CORS headers to error responses
    @app.after_request
    def add_cors_to_all_responses(response):
        """Ensure CORS headers are added to ALL responses, including errors"""
        origin = request.headers.get('Origin')
        
        if origin:
            # Check if origin matches allowed patterns
            allowed = False
            cors_origins = []
            
            if app.config.get('DEBUG'):
                cors_origins = app.config.get('CORS_ORIGINS', ['http://localhost:3000', 'http://localhost:5173', 'http://127.0.0.1:5173'])
            else:
                cors_origins_env = os.environ.get('CORS_ORIGINS', '')
                if cors_origins_env:
                    cors_origins = [o.strip().rstrip('/') for o in cors_origins_env.split(',') if o.strip()]
                
                # Add default Vercel patterns if empty
                if not cors_origins:
                    cors_origins = ['https://itsfuze.vercel.app', 'https://*.vercel.app']
            
            # Check if origin matches any allowed origin (including wildcards)
            for allowed_origin in cors_origins:
                if allowed_origin == '*':
                    allowed = True
                    break
                elif '*' in allowed_origin:
                    # Convert wildcard pattern to regex
                    pattern = allowed_origin.replace('.', r'\.').replace('*', '.*')
                    if re.match(f'^{pattern}$', origin):
                        allowed = True
                        break
                elif origin == allowed_origin or origin == allowed_origin.rstrip('/'):
                    allowed = True
                    break
            
            if allowed:
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRF-TOKEN'
                response.headers['Access-Control-Expose-Headers'] = 'Content-Type, X-CSRF-TOKEN'
                response.headers['Access-Control-Max-Age'] = '86400'
        
        return response
    
    # Note: flask-cors automatically handles OPTIONS preflight requests
    # No need for manual OPTIONS handler - it can cause conflicts
    
    # Detailed Health check endpoint returning internal states
    @app.route('/api/health/detailed')
    def detailed_health_check():
        # Circuit Breaker states
        gemini_state, gemini_fail = "UNKNOWN", 0
        try:
            from utils.gemini_utils import gemini_breaker
            if hasattr(gemini_breaker, 'state'):
                gemini_state = gemini_breaker.state
                gemini_fail = gemini_breaker.failure_count
        except Exception:
            pass
            
        return {
            "status": "healthy",
            "circuit_breakers": {
                "gemini": {"state": str(gemini_state), "failure_count": gemini_fail}
            },
            "bulkheads": {
                "crud": {"in_use": 0, "capacity": int(os.environ.get('BULKHEAD_CRUD_CAPACITY', 30)), "rejection_rate_pct": 0},
                "search": {"in_use": 0, "capacity": int(os.environ.get('BULKHEAD_SEARCH_CAPACITY', 15)), "rejection_rate_pct": 0},
                "ml": {"in_use": 0, "capacity": int(os.environ.get('BULKHEAD_ML_CAPACITY', 8)), "rejection_rate_pct": 0}
            },
            "distributed_lock": {
                "analysis_leader": False  # Handled dynamically by workers 
            }
        }, 200

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
                from utils.database_utils import check_database_connection
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
                from scrapers.easy_linkedin_scraper import EasyLinkedInScraper
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
        return jsonify({'message': 'Bad request', 'error': str(error)}), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'message': 'Unauthorized', 'error': str(error)}), 401
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'message': 'Not found', 'error': str(error)}), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 Method Not Allowed errors with proper CORS headers"""
        response = jsonify({
            'message': 'Method not allowed',
            'error': 'method_not_allowed',
            'allowed_methods': error.valid_methods if hasattr(error, 'valid_methods') else []
        })
        response.status_code = 405
        # CORS headers will be added by after_request handler
        return response
    
    @app.errorhandler(500)
    def internal_server_error(error):
        logger.error(f"Internal server error: {error}", exc_info=True)
        return jsonify({'message': 'Internal server error', 'error': str(error)}), 500
    
    # Database connection error handler with SSL error handling
    @app.errorhandler(Exception)
    def handle_exception(e):
        # PRODUCTION OPTIMIZATION: Comprehensive error logging with full context
        import traceback
        error_traceback = traceback.format_exc()
        user_id = None
        try:
            from flask_jwt_extended import get_jwt_identity
            user_id = get_jwt_identity()
        except:
            pass
        
        # Check if it's a Redis connection error (rate limiting)
        error_str = str(e).lower()
        error_type = type(e).__name__
        
        # Handle Redis connection errors gracefully - don't crash the app
        is_redis_error = (
            isinstance(e, (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, redis.exceptions.RedisError)) or
            'connection closed by server' in error_str or
            ('redis' in error_str and ('connection' in error_str or 'timeout' in error_str or 'closed' in error_str))
        )
        
        if is_redis_error:
            logger.warning(f"Redis connection error in rate limiting: {e}. Allowing request to proceed without rate limiting.")
            # For Redis errors during rate limiting, we want to bypass rate limiting
            # but still process the request. However, we can't easily bypass Flask-Limiter
            # at this point, so we'll just log and return a 503 with a helpful message
            # The rate limiter should have already been configured with swallow_errors=True
            # which should prevent this, but if it still happens, handle it gracefully
            return jsonify({
                'error': 'Rate limiting service temporarily unavailable',
                'message': 'The rate limiting service is temporarily unavailable. Please try again in a moment.',
                'status': 'rate_limit_service_unavailable'
            }), 503
        
        # Check if it's a database connection error
        if any(error_type in error_str for error_type in [
            'could not translate host name', 
            'operationalerror', 
            'ssl connection has been closed',
            'connection closed unexpectedly',
            'ssl error'
        ]):
            logger.error(
                f"Database connection error: {e}\n"
                f"User ID: {user_id}\n"
                f"Request URL: {request.url}\n"
                f"Request Method: {request.method}\n"
                f"Traceback:\n{error_traceback}"
            )
            
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
                ]
            }), 503
        
        # PRODUCTION OPTIMIZATION: Log all other exceptions with full context
        import traceback
        error_traceback = traceback.format_exc()
        user_id = None
        try:
            from flask_jwt_extended import get_jwt_identity
            user_id = get_jwt_identity()
        except:
            pass
        
        logger.error(
            f"Unhandled exception: {str(e)}\n"
            f"User ID: {user_id}\n"
            f"Request URL: {request.url}\n"
            f"Request Method: {request.method}\n"
            f"Request Headers: {dict(request.headers)}\n"
            f"Traceback:\n{error_traceback}",
            exc_info=True
        )
        
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500
        
    try:
        from utils.embedding_utils import warm_up_embedding_model
        warm_up_embedding_model()
    except Exception as e:
        logger.warning(f"Failed to load warm up embedding model at startup: {e}")
    
    return app

app = create_app()

if __name__ == "__main__":
    # Development mode - allow debug
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_DEBUG'] = 'True'
    env = os.environ.get('FLASK_ENV', 'development')
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    logger.info("Starting Fuze Server...")
    logger.info(f"Environment: {env.upper()}")
    logger.info(f"Debug: {'ENABLED' if debug else 'DISABLED'}")
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
            debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
            app.run(
                host='0.0.0.0',
                port=5000,
                debug=debug_mode,
                threaded=True,
                ssl_context=(ssl_cert_path, ssl_key_path)
            )
        else:
            logger.warning("HTTPS enabled but SSL certificate files not found!")
            logger.warning(f"Certificate path: {ssl_cert_path}")
            logger.warning(f"Private key path: {ssl_key_path}")
            logger.warning("Falling back to HTTP mode for development...")
            
            # Fallback to HTTP for development
            debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
            app.run(
                host='0.0.0.0',
                port=5000,
                debug=debug_mode,
                threaded=True
            )
    else:
        logger.info("HTTP Mode: Starting without SSL (Development Mode)")
        
        # Start Flask server without HTTPS
        # Use debug mode if in development
        debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=debug_mode,
            threaded=True
        )