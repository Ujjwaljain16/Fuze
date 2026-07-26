#!/usr/bin/env python3
"""
Production Flask Server for Fuze
Optimized for maximum performance with proper WSGI server
Enhanced with Intent Analysis System optimizations, SSL connection management,
header sanitization, and comprehensive health monitoring endpoints.
"""

import os
import sys
import time
import re
import uuid
import hmac
import traceback
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv()

from core.logging_config import configure_logging, get_logger

configure_logging(debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
logger = get_logger(__name__)

# Initialize Sentry SDK for Backend Error Tracking if SENTRY_DSN configured
SENTRY_DSN = os.environ.get("SENTRY_DSN")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        def before_send_scrub_pii(event, hint):
            if "request" in event and "headers" in event["request"]:
                headers = event["request"]["headers"]
                for key in ["Authorization", "Cookie", "X-Api-Key"]:
                    if key in headers:
                        headers[key] = "[REDACTED]"
            return event

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[FlaskIntegration(), SqlalchemyIntegration()],
            traces_sample_rate=0.1,
            environment=os.environ.get("ENVIRONMENT", "development"),
            before_send=before_send_scrub_pii
        )
        logger.info("✅ Sentry backend error tracking initialized successfully")
    except Exception as sentry_err:
        logger.warning(f"⚠️ Could not initialize Sentry SDK: {sentry_err}")

from flask import Flask, request, jsonify, g
from flask_jwt_extended import JWTManager
from models import db
from sqlalchemy import text
from flask_cors import CORS
from utils.redis_utils import redis_cache

# Import Flask-Compress for response compression
try:
    from flask_compress import Compress
    COMPRESS_AVAILABLE = True
except ImportError:
    logger.warning("Flask-Compress not available")
    COMPRESS_AVAILABLE = False

# Import Redis exceptions for error handling
try:
    import redis.exceptions
except ImportError:
    class ConnectionError(Exception):
        pass
    class TimeoutError(Exception):
        pass
    redis = type('redis', (), {'exceptions': type('exceptions', (), {
        'ConnectionError': ConnectionError,
        'TimeoutError': TimeoutError,
        'RedisError': Exception
    })()})()

# Import rate limiting middleware
try:
    from middleware.rate_limiting import init_rate_limiter
    RATE_LIMITING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Rate limiting middleware not available: {e}")
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
    logger.info("Database connection manager imported successfully")
except ImportError as e:
    logger.warning(f"Database connection manager not available: {e}")
    connection_manager_available = False

# Import blueprints with error handling
recommendations_available = False
linkedin_available = False
dashboard_available = False
api_manager_available = False
user_api_key_available = False
init_user_api_key = None

try:
    from blueprints.auth import auth_bp
    from blueprints.projects import projects_bp
    from blueprints.tasks import tasks_bp
    from blueprints.bookmarks import bookmarks_bp
    from blueprints.feedback import feedback_bp
    from blueprints.profile import profile_bp
    from blueprints.search import search_bp
    
    try:
        from blueprints.dashboard import dashboard_bp
        dashboard_available = True
    except Exception as e:
        logger.warning(f"Dashboard blueprint not available: {e}")
        dashboard_available = False

    try:
        from services.multi_user_api_manager import init_api_manager
        api_manager_available = True
    except Exception as e:
        logger.warning(f"API manager not available: {e}")
        api_manager_available = False

    try:
        from blueprints.user_api_key import init_app as init_user_api_key
        user_api_key_available = True
    except Exception as e:
        logger.warning(f"User API key blueprint not available: {e}")
        user_api_key_available = False

    try:
        from blueprints.recommendations import recommendations_bp
        recommendations_available = True
    except Exception as e:
        logger.warning(f"Recommendations blueprint not available: {e}")
        recommendations_available = False

    try:
        from blueprints.linkedin import linkedin_bp
        linkedin_available = True
    except Exception as e:
        logger.warning(f"LinkedIn blueprint not available: {e}")
        linkedin_available = False

except ImportError as e:
    logger.warning(f"Some blueprints not available: {e}")

# Import intent analysis components
try:
    from ml.intent_analysis_engine import IntentAnalysisEngine
    from utils.gemini_utils import GeminiAnalyzer
    intent_analysis_available = True
except ImportError as e:
    logger.warning(f"Intent Analysis components not available: {e}")
    intent_analysis_available = False

SENSITIVE_HEADERS = {'authorization', 'cookie', 'x-api-key', 'x-csrf-token', 'jwt'}

def sanitize_headers(headers: dict) -> dict:
    """Redact sensitive authorization tokens from request headers prior to logging."""
    return {
        k: ('[REDACTED]' if k.lower() in SENSITIVE_HEADERS else v)
        for k, v in headers.items()
    }

def _validate_production_env():
    """Validate critical environment variables for production"""
    if os.environ.get('FLASK_ENV') == 'testing' or os.environ.get('PYTEST_CURRENT_TEST'):
        return
    
    critical_vars = {
        'SECRET_KEY': 'dev-secret-key-change-in-production',
        'JWT_SECRET_KEY': 'dev-jwt-secret-change-in-production',
    }
    errors = []
    for var, default_val in critical_vars.items():
        val = os.environ.get(var)
        if not val or val == default_val:
            errors.append(f"{var} must be set to a secure value in production")
    if errors:
        raise ValueError(f"Critical production configuration errors: {', '.join(errors)}")

def create_app(config_name: str = None) -> Flask:
    # Run startup integrity checks before booting the app
    if not os.environ.get('SKIP_STARTUP_VALIDATION'):
        try:
            from core.startup_validation import validate_startup_integrity
            validate_startup_integrity()
        except Exception as e:
            logger.critical("startup_validation_fatal_error", extra={"error": str(e)})
            import sys
            sys.exit(f"Startup failed: {e}")

    app = Flask(__name__)
    
    env = config_name or os.environ.get('FLASK_ENV', 'development')
    if env == 'production':
        app.config.from_object('config.ProductionConfig')
        _validate_production_env()
    elif env == 'testing':
        app.config.from_object('config.TestingConfig')
        app.config['RATELIMIT_ENABLED'] = False
        app.config['TESTING'] = True
    else:
        app.config.from_object('config.DevelopmentConfig')

    # Configure SQLALCHEMY_ENGINE_OPTIONS BEFORE db.init_app(app)
    db_url = app.config.get('SQLALCHEMY_DATABASE_URI', os.environ.get('DATABASE_URL', ''))
    if db_url and 'sqlite' in db_url:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
        }
    else:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'pool_size': 5,
            'max_overflow': 10,
            'pool_timeout': 30
        }

    # CORS setup using UnifiedConfig
    from utils.unified_config import UnifiedConfig
    import re
    cors_config = UnifiedConfig().cors
    cors_origins = cors_config.origins.copy()

    default_allowed = [
        'https://itsfuze.vercel.app',
        'http://localhost:3000',
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        re.compile(r"^https://.*\.vercel\.app$")
    ]
    for o in default_allowed:
        if o not in cors_origins:
            cors_origins.append(o)

    CORS(app, origins=cors_origins, supports_credentials=True)

    # Intercept OPTIONS preflight requests globally to enforce credentials
    @app.before_request
    def handle_global_cors_preflight():
        if request.method == 'OPTIONS':
            origin = request.headers.get('Origin')
            response = app.make_default_options_response()
            if origin:
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRF-TOKEN, X-Request-ID'
                response.headers['Access-Control-Max-Age'] = '86400'
            return response, 204

    # Initialize rate limiting
    if RATE_LIMITING_AVAILABLE:
        try:
            init_rate_limiter(app)
        except Exception as e:
            logger.warning(f"Rate limiting initialization failed: {e}")

    # Initialize response compression
    if COMPRESS_AVAILABLE:
        compress = Compress()
        compress.init_app(app)

    # Database initialization
    db.init_app(app)

    # JWT setup
    jwt = JWTManager(app)

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'message': 'Token has expired', 'error': 'token_expired'}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'message': 'Signature verification failed', 'error': 'invalid_token'}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'message': 'Access token required', 'error': 'authorization_required'}), 401

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload.get('jti')
        if not jti:
            return False
        try:
            if not redis_cache or not getattr(redis_cache, 'connected', False):
                return True
            return redis_cache.redis_client.exists(f"revoked_jti:{jti}") == 1
        except Exception:
            return True

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({'message': 'Token has been revoked', 'error': 'token_revoked'}), 401

    @app.before_request
    def set_correlation_id():
        g.correlation_id = request.headers.get('X-Request-ID') or uuid.uuid4().hex

    @app.before_request
    def handle_options_preflight():
        if request.method == 'OPTIONS':
            origin = request.headers.get('Origin')
            response = make_response('', 204)
            if origin:
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
                response.headers['Access-Control-Allow-Headers'] = request.headers.get('Access-Control-Request-Headers', 'Content-Type, Authorization, X-Requested-With, X-Request-ID, Accept')
                response.headers['Access-Control-Max-Age'] = '86400'
            return response

    @app.after_request
    def consolidate_response_headers(response):
        if hasattr(g, 'correlation_id'):
            response.headers['X-Request-ID'] = g.correlation_id

        origin = request.headers.get('Origin')
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'

        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    # Blueprint Registration
    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(bookmarks_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(search_bp)

    if dashboard_available:
        app.register_blueprint(dashboard_bp)
    if recommendations_available:
        app.register_blueprint(recommendations_bp)
    if linkedin_available:
        app.register_blueprint(linkedin_bp)
    if user_api_key_available and init_user_api_key:
        try:
            init_user_api_key(app)
        except Exception as e:
            logger.warning(f"Error registering user API key blueprint: {e}")

    with app.app_context():
        if api_manager_available:
            try:
                init_api_manager()
            except Exception as e:
                logger.error(f"Error initializing API manager: {e}")

    # Structured Request ID & Latency Logging Middleware
    @app.before_request
    def before_request_logging():
        g.start_time = time.time()
        g.request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())

    @app.after_request
    def after_request_logging(response):
        origin = request.headers.get('Origin')
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'

        response.headers['X-Request-ID'] = getattr(g, 'request_id', '')
        if hasattr(g, 'start_time'):
            latency_s = time.time() - g.start_time
            latency_ms = round(latency_s * 1000, 2)
            
            try:
                from core.metrics import http_request_duration
                # Record HTTP request duration in prometheus
                http_request_duration.labels(
                    method=request.method,
                    endpoint=request.endpoint or 'unknown',
                    status=response.status_code
                ).observe(latency_s)
            except Exception:
                pass
                
            if latency_ms > 1000:
                logger.warning(
                    f"Slow request: {request.method} {request.path}",
                    extra={
                        "latency_ms": latency_ms,
                        "method": request.method,
                        "path": request.path,
                        "status": response.status_code,
                    }
                )
        return response

    # Root Endpoint
    @app.route('/')
    def root():
        return jsonify({'status': 'ok', 'message': 'Fuze API is running'}), 200

    # Container Liveness Probe (Fast, 0ms latency)
    @app.route('/health/liveness')
    @app.route('/api/health/liveness')
    def liveness_probe():
        return jsonify({'status': 'alive', 'timestamp': datetime.utcnow().isoformat()}), 200

    # Container Readiness Probe (Validates DB & Redis readiness)
    @app.route('/health/readiness')
    @app.route('/api/health/readiness')
    def readiness_probe():
        db_ready = False
        try:
            with db.engine.connect() as conn:
                conn.execute(text('SELECT 1'))
            db_ready = True
        except Exception:
            db_ready = False

        redis_ready = getattr(redis_cache, 'connected', False)
        is_ready = db_ready and redis_ready

        return jsonify({
            'status': 'ready' if is_ready else 'not_ready',
            'database': 'ready' if db_ready else 'unhealthy',
            'redis': 'ready' if redis_ready else 'unhealthy'
        }), 200 if is_ready else 503

    # Prometheus Metrics Endpoint
    # Secured with METRICS_AUTH_TOKEN bearer token.
    # Configure Grafana Cloud agent to send Authorization: Bearer {METRICS_AUTH_TOKEN}
    @app.route('/metrics')
    def prometheus_metrics():
        from core.metrics import get_metrics_output, METRICS_ENABLED
        if not METRICS_ENABLED:
            return jsonify({'status': 'metrics_disabled'}), 404

        metrics_token = os.environ.get('METRICS_AUTH_TOKEN')
        if metrics_token:
            auth_header = request.headers.get('Authorization', '')
            provided = auth_header.removeprefix('Bearer ').strip()
            if not hmac.compare_digest(provided, metrics_token):
                return jsonify({'message': 'Unauthorized'}), 401

        output, content_type = get_metrics_output()
        if output is None:
            return jsonify({'status': 'prometheus_client_unavailable'}), 503

        from flask import Response
        return Response(output, mimetype=content_type)

    # RQ Queue Metrics Endpoint
    @app.route('/health/queue')
    @app.route('/api/health/queue')
    def queue_health():
        try:
            from services.task_queue import get_queue_stats
            stats = get_queue_stats('default')
            status_code = 200 if stats.get('status') == 'connected' else 503
            return jsonify(stats), status_code
        except Exception as e:
            return jsonify({'status': 'error', 'error': str(e)}), 500

    # Detailed Health Endpoint
    @app.route('/api/health/detailed')
    def detailed_health_check():
        internal_token = os.environ.get('INTERNAL_HEALTH_TOKEN')
        request_token = request.headers.get('X-Internal-Token')
        if not internal_token or not hmac.compare_digest(request_token or '', internal_token):
            return jsonify({'status': 'unauthorized', 'message': 'Provide valid X-Internal-Token header.'}), 403

        return jsonify({
            'status': 'healthy',
            'redis_connected': getattr(redis_cache, 'connected', False)
        }), 200

    # General Health Check
    @app.route('/api/health')
    def health_check():
        db_status = 'unavailable'
        try:
            if connection_manager_available:
                try:
                    if test_database_connection():
                        db_status = 'connected'
                    else:
                        db_status = 'degraded'
                except Exception as db_err:
                    db_status = f'error: {str(db_err)}'
            else:
                with db.engine.connect() as conn:
                    conn.execute(text('SELECT 1'))
                    db_status = 'connected'
        except Exception as e:
            db_status = f'error: {str(e)}'

        is_mock_redis = type(redis_cache).__name__ in ('MagicMock', 'Mock', 'NonCallableMagicMock')
        if hasattr(redis_cache, 'get_cache_stats') and not is_mock_redis:
            try:
                stats_val = redis_cache.get_cache_stats()
                is_mock_stats = type(stats_val).__name__ in ('MagicMock', 'Mock', 'NonCallableMagicMock')
                if isinstance(stats_val, dict) and not is_mock_stats:
                    redis_stats = stats_val
                else:
                    redis_stats = {'connected': bool(getattr(redis_cache, 'connected', False))}
            except Exception:
                redis_stats = {'connected': bool(getattr(redis_cache, 'connected', False))}
        else:
            redis_stats = {'connected': bool(getattr(redis_cache, 'connected', False))}

        overall_status = 'healthy' if (db_status == 'connected' and bool(redis_stats.get('connected'))) else 'degraded'

        return jsonify({
            'status': str(overall_status),
            'message': 'Fuze API is running',
            'version': '1.0.0',
            'environment': str(app.config.get('ENV', 'development')),
            'database': str(db_status),
            'redis': {
                'connected': bool(redis_stats.get('connected')) if isinstance(redis_stats, dict) else False,
                'keyspace_hits': int(redis_stats.get('keyspace_hits', 0)) if isinstance(redis_stats, dict) and isinstance(redis_stats.get('keyspace_hits'), (int, float)) else 0,
                'keyspace_misses': int(redis_stats.get('keyspace_misses', 0)) if isinstance(redis_stats, dict) and isinstance(redis_stats.get('keyspace_misses'), (int, float)) else 0,
            },
            'recommendations_available': bool(recommendations_available),
            'intent_analysis_available': bool(intent_analysis_available),
            'linkedin_available': bool(linkedin_available)
        }), 200 if overall_status in ['healthy', 'degraded'] else 500

    # Redis Health Check
    @app.route('/api/health/redis')
    def redis_health_check():
        if hasattr(redis_cache, 'get_cache_stats'):
            stats = redis_cache.get_cache_stats()
        else:
            stats = {'connected': getattr(redis_cache, 'connected', False)}
        return jsonify(stats), 200 if stats.get('connected') else 503

    # Database Health Check
    @app.route('/api/health/database')
    def database_health_check():
        try:
            if connection_manager_available:
                if test_database_connection():
                    return jsonify({'status': 'healthy', 'service': 'database', 'connection_info': get_database_info()}), 200
                elif refresh_database_connections():
                    return jsonify({'status': 'recovered', 'service': 'database'}), 200
                else:
                    return jsonify({'status': 'unhealthy', 'service': 'database'}), 500
            else:
                with db.engine.connect() as conn:
                    conn.execute(text('SELECT 1'))
                return jsonify({'status': 'healthy', 'service': 'database'}), 200
        except Exception as e:
            return jsonify({'status': 'unhealthy', 'service': 'database', 'error': str(e)}), 500

    # Intent Analysis Health Check
    @app.route('/api/health/intent-analysis')
    def intent_analysis_health_check():
        if not intent_analysis_available:
            return jsonify({'status': 'unavailable', 'service': 'intent_analysis'}), 503
        gemini_key = os.environ.get('GEMINI_API_KEY')
        if not gemini_key:
            return jsonify({'status': 'unhealthy', 'service': 'intent_analysis', 'error': 'GEMINI_API_KEY missing'}), 503
        try:
            GeminiAnalyzer(gemini_key)
            return jsonify({'status': 'healthy', 'service': 'intent_analysis'}), 200
        except Exception as e:
            return jsonify({'status': 'unhealthy', 'service': 'intent_analysis', 'error': str(e)}), 503

    # LinkedIn Health Check
    @app.route('/api/health/linkedin')
    def linkedin_health_check():
        if not linkedin_available:
            return jsonify({'status': 'unavailable', 'service': 'linkedin'}), 503
        return jsonify({'status': 'healthy', 'service': 'linkedin'}), 200

    # Standard Error Handlers
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
        return jsonify({'message': 'Method not allowed', 'error': 'method_not_allowed'}), 405

    @app.errorhandler(Exception)
    def handle_exception(e):
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return e

        clean_headers = sanitize_headers(dict(request.headers))
        logger.error(
            "unhandled_application_exception",
            extra={
                "error": str(e),
                "url": request.url,
                "method": request.method,
                "headers": clean_headers
            },
            exc_info=True
        )
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    logger.info("Starting Fuze Server...", extra={"port": port, "debug": debug_mode})
    app.run(host='0.0.0.0', port=port, debug=debug_mode)