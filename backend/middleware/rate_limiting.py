import os
from typing import List
from flask import jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from core.logging_config import get_logger

logger = get_logger(__name__)


def get_default_limits() -> List[str]:
    """Dynamically resolve rate limits based on environment at runtime."""
    app_env = os.environ.get('ENVIRONMENT', os.environ.get('APP_ENV', os.environ.get('FLASK_ENV', 'development'))).lower()
    is_development = app_env in ('development', 'dev', 'local', 'test')

    if is_development:
        return ["100000 per day", "10000 per hour", "1000 per minute"]
    return ["1000 per day", "200 per hour", "50 per minute"]


def get_user_rate_limit_key() -> str:
    """
    Rate limit key function: uses JWT identity if present, falls back to remote IP address.
    Uses specific exception handling to prevent swallowing configuration bugs.
    """
    try:
        from flask_jwt_extended import get_jwt_identity
        from flask_jwt_extended.exceptions import JWTExtendedException

        try:
            identity = get_jwt_identity()
            if identity:
                return f"user:{identity}"
        except JWTExtendedException:
            pass
    except (ImportError, RuntimeError):
        pass

    return get_remote_address()


# Singleton Limiter instance using explicit moving-window strategy
limiter = Limiter(
    key_func=get_user_rate_limit_key,
    default_limits=get_default_limits(),
    strategy="moving-window",
    headers_enabled=True,
)


def init_rate_limiter(app) -> Limiter:
    """
    Wire module-level limiter into the Flask app.
    Configures Redis storage, Werkzeug ProxyFix, storage socket timeouts,
    and custom 429 response handling.
    Fails fast in production if Redis storage is unavailable.
    """
    app_env = os.environ.get('ENVIRONMENT', os.environ.get('APP_ENV', os.environ.get('FLASK_ENV', 'development'))).lower()
    is_production = app_env in ('production', 'prod', 'staging')

    redis_url = os.environ.get('REDIS_URL')

    if not redis_url:
        if is_production:
            logger.error("rate_limiter_redis_missing_production", extra={"environment": app_env})
            raise RuntimeError("REDIS_URL is required for production rate limiting")
        else:
            logger.warning("rate_limiter_no_redis_dev_fallback", extra={"environment": app_env})
            storage_uri = 'memory://'
    else:
        # Convert redis:// to rediss:// for Upstash TLS if needed
        if 'upstash.io' in redis_url and redis_url.startswith('redis://'):
            redis_url = redis_url.replace('redis://', 'rediss://', 1)
        storage_uri = redis_url

    # Configure proxy headers fix for Nginx/ALB/Cloudflare IP extraction
    if not getattr(app, '_proxy_fix_applied', False):
        try:
            from werkzeug.middleware.proxy_fix import ProxyFix
            app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
            app._proxy_fix_applied = True
            logger.info("rate_limiter_proxy_fix_applied")
        except Exception as p_err:
            logger.warning("rate_limiter_proxy_fix_failed", extra={"error": str(p_err)})

    app.config["RATELIMIT_STORAGE_URI"] = storage_uri
    app.config["RATELIMIT_STORAGE_OPTIONS"] = {
        "socket_connect_timeout": 2,
        "socket_timeout": 2,
    }

    limiter.init_app(app)

    # Register custom 429 JSON response handler
    @app.errorhandler(429)
    def ratelimit_exceeded_handler(e):
        return jsonify({
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please slow down and try again later.",
            "retry_after": getattr(e, "description", None) or "60"
        }), 429

    logger.info("rate_limiter_initialized_successfully", extra={"storage_uri": storage_uri.split('@')[-1] if '@' in storage_uri else storage_uri})
    return limiter
