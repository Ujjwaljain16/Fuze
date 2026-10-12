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
from datetime import datetime
from dotenv import load_dotenv

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv()

from core.logging_config import configure_logging, get_logger

configure_logging(debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
logger = get_logger(__name__)

# Error tracking, before Flask is imported so its integration hooks in. A no-op without
# SENTRY_DSN; the RQ worker initialises it first with its own component tag.
from core.sentry_setup import init_sentry

init_sentry(component='web')

from flask import Flask, request, jsonify, g, make_response
from core.http_errors import error_response, rate_limit_response, DEFAULT_CODES
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
    from blueprints.events import events_bp
    from blueprints.account import account_bp
    from blueprints.ask import ask_bp
    
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
    from ml.intent_engine.intent import resolve_intent  # noqa: F401  (availability check)
    intent_analysis_available = True
except ImportError as e:
    logger.warning(f"Intent Analysis components not available: {e}")
    intent_analysis_available = False

_REQUEST_ID = re.compile(r'[A-Za-z0-9._-]{1,64}')

SENSITIVE_HEADERS = {'authorization', 'cookie', 'x-api-key', 'x-csrf-token', 'jwt'}

def sanitize_headers(headers: dict) -> dict:
    """Redact sensitive authorization tokens from request headers prior to logging."""
    return {
        k: ('[REDACTED]' if k.lower() in SENSITIVE_HEADERS else v)
        for k, v in headers.items()
    }

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
    
    # Bigger bodies are refused with 413 before any handler parses them.
    app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_REQUEST_BYTES', 5 * 1024 * 1024))

    from core.app_env import app_env, require_secrets
    env = config_name or app_env()
    if env == 'production':
        app.config.from_object('config.ProductionConfig')
        require_secrets()
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
        # One source of truth for pool sizes, TLS, keepalives and timeouts (DB_* environment vars).
        from utils.unified_config import get_config
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = get_config().get_flask_config()['SQLALCHEMY_ENGINE_OPTIONS']

    # CORS setup - allowlist is shared with utils/cors_utils.is_allowed_origin(),
    # which any manual Access-Control-Allow-Origin header setter (below, and in
    # blueprints/events.py's SSE response) MUST validate against instead of
    # echoing the request's Origin verbatim.
    from utils.cors_utils import get_allowed_cors_origins, is_allowed_origin as _is_allowed_origin
    cors_origins = get_allowed_cors_origins()

    CORS(app, origins=cors_origins, supports_credentials=True)

    # Initialize rate limiting
    if RATE_LIMITING_AVAILABLE:
        try:
            init_rate_limiter(app)
        except Exception as e:
            # Without rate limits a deployed app is open to brute force and cost abuse: refuse
            # to start rather than log and carry on (init_rate_limiter's fail-fast was swallowed).
            from core.app_env import is_production
            if is_production():
                raise
            logger.warning(f"Rate limiting initialization failed: {e}")

    # Initialize response compression
    if COMPRESS_AVAILABLE:
        compress = Compress()
        compress.init_app(app)

    # Database initialization
    db.init_app(app)
    with app.app_context():
        if db.engine.dialect.name == 'postgresql':
            from sqlalchemy import event
            from utils.unified_config import get_config
            statement_timeout_ms = get_config().database.statement_timeout_ms

            if get_config().database.pool_pre_ping:
                from utils.db_pool import install_idle_ping
                install_idle_ping(db.engine, get_config().database.ping_idle_seconds)

            @event.listens_for(db.engine, 'connect')
            def _limit_statement_time(dbapi_connection, _record):
                # Set per connection, not as a startup option, so it also works through Supabase's
                # pooler. Migrations use their own engine and lift the limit.
                with dbapi_connection.cursor() as cursor:
                    cursor.execute(f"SET statement_timeout = {int(statement_timeout_ms)}")
                dbapi_connection.commit()

    # NOTE: migrations are applied exactly once by start.sh ("alembic upgrade head")
    # before supervisord launches gunicorn + the RQ workers. create_app() runs in
    # all three of those processes (each RQ worker also calls create_app()), so
    # auto-migrating here would run "alembic upgrade head" 3+ times concurrently
    # against the same database on every boot -- a real race (alembic_version
    # lock contention / duplicate-DDL errors), not just wasted startup time.
    # If this app is run standalone outside start.sh (e.g. local `flask run`),
    # apply migrations manually first: `alembic upgrade head`.
    if os.environ.get('AUTO_MIGRATE_ON_BOOT', '').lower() == 'true':
        with app.app_context():
            try:
                from alembic.config import Config
                from alembic import command
                alembic_ini_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'alembic.ini'))
                if not os.path.exists(alembic_ini_path):
                    alembic_ini_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'alembic.ini'))
                if os.path.exists(alembic_ini_path):
                    alembic_cfg = Config(alembic_ini_path)
                    command.upgrade(alembic_cfg, "head")
                    logger.info("alembic_auto_migration_completed_successfully")
                else:
                    logger.error("alembic_ini_not_found_schema_not_migrated")
            except Exception as mig_err:
                logger.warning(f"auto_migration_warning: {mig_err}")

    # JWT setup
    jwt = JWTManager(app)

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return error_response('token_expired', 'Token has expired', 401)

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return error_response('invalid_token', 'Signature verification failed', 401)

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return error_response('authorization_required', 'Access token required', 401)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload.get('jti')
        if not jti:
            return False
        # Fail OPEN (not revoked) when Redis is unreachable or the lookup
        # throws, rather than fail closed. This loader only runs after the
        # JWT's signature and expiry have already validated successfully --
        # the blocklist is a secondary, best-effort revocation check on top
        # of that, not the primary auth mechanism. Failing closed here means
        # a transient Redis blip (or, concretely, the shared connection pool
        # being exhausted under concurrent load -- confirmed via load testing:
        # 75 concurrent users caused ~38% of authenticated requests to receive
        # 401 UNAUTHORIZED, "Token has been revoked", for tokens that were
        # never revoked, purely because the .exists() call intermittently
        # raised under pool pressure) turns "cache/rate-limiter degraded" into
        # "every active user gets logged out simultaneously" -- a vastly
        # worse outage than briefly under-enforcing revocation.
        try:
            if not redis_cache or not getattr(redis_cache, 'connected', False):
                return False
            from core.sessions import is_family_revoked
            client = redis_cache.redis_client
            return (client.exists(f"revoked_jti:{jti}") == 1
                    or is_family_revoked(client, jwt_payload.get('family_id')))
        except Exception:
            return False

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return error_response('token_revoked', 'Token has been revoked', 401)

    @app.before_request
    def set_correlation_id():
        # One id per request, from the caller's X-Request-ID when it is sane, bound into every
        # log line written while handling the request (it used to reach no log at all, and a
        # second hook generated a different id for the response header).
        from core.logging_config import bind_request_context
        incoming = request.headers.get('X-Request-ID', '')
        request_id = incoming if _REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex
        g.correlation_id = g.request_id = request_id
        bind_request_context(correlation_id=request_id, method=request.method, path=request.path)

    @app.teardown_request
    def clear_correlation_id(_exc):
        from core.logging_config import clear_request_context
        clear_request_context()

    @app.before_request
    def handle_options_preflight():
        if request.method == 'OPTIONS':
            origin = request.headers.get('Origin')
            response = make_response('', 204)
            if _is_allowed_origin(origin):
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
                response.headers['Access-Control-Allow-Headers'] = request.headers.get(
                    'Access-Control-Request-Headers',
                    'Content-Type, Authorization, X-Requested-With, X-Request-ID, Accept'
                )
                response.headers['Access-Control-Max-Age'] = '86400'
            return response

    @app.after_request
    def consolidate_response_headers(response):
        if hasattr(g, 'correlation_id'):
            response.headers['X-Request-ID'] = g.correlation_id

        origin = request.headers.get('Origin')
        if _is_allowed_origin(origin):
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRF-TOKEN, X-Request-ID, Accept'

        from middleware.security_middleware import add_security_headers
        return add_security_headers(response)

    # Blueprint Registration
    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(bookmarks_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(ask_bp)

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

    @app.after_request
    def after_request_logging(response):
        origin = request.headers.get('Origin')
        if _is_allowed_origin(origin):
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
        from core.schema_version import schema_status
        db_ready = False
        schema_ready = False
        try:
            with db.engine.connect() as conn:
                # Code running against an older schema 500s on every query that touches new columns.
                schema_ready = schema_status(conn)['up_to_date']
            db_ready = True
        except Exception:
            db_ready = False

        redis_ready = getattr(redis_cache, 'connected', False)
        is_ready = db_ready and schema_ready and redis_ready

        body = {
            'status': 'ready' if is_ready else 'not_ready',
            'database': 'ready' if db_ready else 'unhealthy',
            'schema': 'current' if schema_ready else 'outdated',
            'redis': 'ready' if redis_ready else 'unhealthy'
        }
        if is_ready:
            return jsonify(body), 200
        return error_response('not_ready', 'Service is not ready', 503, **body)

    # Prometheus Metrics Endpoint
    # Secured with METRICS_AUTH_TOKEN bearer token.
    # Configure Grafana Cloud agent to send Authorization: Bearer {METRICS_AUTH_TOKEN}
    @app.route('/metrics')
    def prometheus_metrics():
        from core.metrics import get_metrics_output, METRICS_ENABLED
        if not METRICS_ENABLED:
            return error_response('metrics_disabled', 'Metrics are disabled', 404, status='metrics_disabled')

        # Closed unless a scrape token is configured: metrics expose route names, queue depth and errors.
        metrics_token = os.environ.get('METRICS_AUTH_TOKEN')
        if not metrics_token:
            return error_response('not_found', 'Not found', 404)
        auth_header = request.headers.get('Authorization', '')
        provided = auth_header.removeprefix('Bearer ').strip()
        if not hmac.compare_digest(provided, metrics_token):
            return error_response('unauthorized', 'Unauthorized', 401)

        output, content_type = get_metrics_output()
        if output is None:
            return error_response('metrics_unavailable', 'Prometheus client is unavailable', 503,
                                  status='prometheus_client_unavailable')

        from flask import Response
        return Response(output, mimetype=content_type)

    def _internal_caller() -> bool:
        """Operational detail (queue depth, cache stats) only for callers holding INTERNAL_HEALTH_TOKEN."""
        internal_token = os.environ.get('INTERNAL_HEALTH_TOKEN')
        return bool(internal_token) and hmac.compare_digest(request.headers.get('X-Internal-Token', ''), internal_token)

    def _database_ok() -> bool:
        try:
            with db.engine.connect() as conn:
                conn.execute(text('SELECT 1'))
            return True
        except Exception as e:
            logger.warning("health_database_check_failed", extra={"error": str(e)})
            return False

    # Public health endpoints report up/down only: no hostnames, DSNs, versions or error text,
    # and no side effects (the old database check could reset the connection pool on demand).
    @app.route('/api/health')
    def health_check():
        db_ok = _database_ok()
        redis_ok = bool(getattr(redis_cache, 'connected', False))
        return jsonify({
            'status': 'healthy' if db_ok and redis_ok else 'degraded',
            'database': 'connected' if db_ok else 'unavailable',
            'redis': {'connected': redis_ok},
        }), 200

    @app.route('/api/health/database')
    def database_health_check():
        healthy = _database_ok()
        if not healthy:
            return error_response('database_unavailable', 'Database is unavailable', 503,
                                  status='unhealthy', service='database')
        return jsonify({'status': 'healthy', 'service': 'database'}), 200

    @app.route('/api/health/redis')
    def redis_health_check():
        connected = bool(getattr(redis_cache, 'connected', False))
        if not connected:
            return error_response('redis_unavailable', 'Redis is unavailable', 503, connected=False)
        return jsonify({'connected': True}), 200

    @app.route('/health/queue')
    @app.route('/api/health/queue')
    def queue_health():
        if not _internal_caller():
            return error_response('not_found', 'Not found', 404)
        try:
            from services.task_queue import get_queue_stats
            stats = get_queue_stats('default')
            if stats.get('status') == 'connected':
                return jsonify(stats), 200
            extra = {k: v for k, v in stats.items() if k not in ('error', 'message')}
            return error_response('queue_unavailable', 'Task queue is unavailable', 503, **extra)
        except Exception:
            logger.exception("queue_health_failed")
            return error_response('internal_error', 'Queue health check failed', 500, status='error')

    @app.route('/api/health/detailed')
    def detailed_health_check():
        if not _internal_caller():
            return error_response('not_found', 'Not found', 404)
        stats = redis_cache.get_cache_stats() if hasattr(redis_cache, 'get_cache_stats') else {}
        return jsonify({
            'status': 'healthy',
            'database': _database_ok(),
            'redis': stats,
            'recommendations_available': bool(recommendations_available),
            'intent_analysis_available': bool(intent_analysis_available),
            'linkedin_available': bool(linkedin_available),
        }), 200

    # Standard Error Handlers: every error body is {"error": <code>, "message": <sentence>}.
    @app.errorhandler(400)
    def bad_request(error):
        return error_response('bad_request', 'Bad request', 400)

    @app.errorhandler(401)
    def unauthorized(error):
        return error_response('unauthorized', 'Unauthorized', 401)

    @app.errorhandler(404)
    def not_found(error):
        return error_response('not_found', 'Not found', 404)

    @app.errorhandler(405)
    def method_not_allowed(error):
        return error_response('method_not_allowed', 'Method not allowed', 405)

    @app.errorhandler(413)
    def payload_too_large(error):
        return error_response('payload_too_large', 'Request body is too large', 413)

    # init_rate_limiter registers the same handler; registering it here as well covers apps whose
    # limiter failed to start or was built after the first request.
    app.register_error_handler(429, rate_limit_response)

    @app.errorhandler(Exception)
    def handle_exception(e):
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            # Any other HTTP error (415, 501, ...) gets the envelope instead of Werkzeug's HTML page.
            if e.code is not None and e.code >= 400:
                return error_response(DEFAULT_CODES.get(e.code, 'http_error'), e.name, e.code)
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
        return error_response('internal_error', 'An unexpected error occurred', 500)

    return app


def __getattr__(name):
    # `from run_production import app` (scripts, the background service) builds the app on first
    # use. Building it at import time made every process that only imported create_app -- gunicorn
    # via wsgi.py, the RQ worker -- construct the whole app twice.
    if name == 'app':
        global app
        app = create_app()
        return app
    raise AttributeError(name)


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    logger.info("Starting Fuze Server...", extra={"port": port, "debug": debug_mode})
    app.run(host='0.0.0.0', port=port, debug=debug_mode)