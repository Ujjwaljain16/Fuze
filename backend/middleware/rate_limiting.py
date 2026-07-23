"""
Rate limiting middleware for production.
Exposes a module-level `limiter` singleton so blueprints can apply
@limiter.limit(...) decorators at definition time rather than creating
decorated inner functions per-request (which breaks across workers).
"""
import os
import logging
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singleton — import and decorate routes with this
# ---------------------------------------------------------------------------
is_development = os.environ.get('FLASK_ENV', 'development') == 'development'
default_limits = (
    ["100000 per day", "10000 per hour", "1000 per minute"]
    if is_development
    else ["1000 per day", "200 per hour", "50 per minute"]
)
def get_user_rate_limit_key():
    """
    Rate limit key function: uses JWT identity if available, falls back to remote IP address.
    """
    try:
        from flask_jwt_extended import get_jwt_identity
        identity = get_jwt_identity()
        if identity:
            return f"user:{identity}"
    except Exception:
        pass
    return get_remote_address()

limiter = Limiter(
    key_func=get_user_rate_limit_key,
    default_limits=default_limits,
    headers_enabled=True,
    swallow_errors=is_development
)

def init_rate_limiter(app) -> Limiter:
    """
    Wire the module-level limiter into the Flask app.
    Tries Redis first; falls back to in-memory if Redis is unavailable.
    Returns the configured Limiter instance.
    """
    try:
        redis_url = os.environ.get('REDIS_URL')
        storage_uri = 'memory://'
        if redis_url:
            try:
                import redis
                test_client = redis.from_url(
                    redis_url, socket_connect_timeout=2, socket_timeout=2
                )
                test_client.ping()
                test_client.close()
                storage_uri = redis_url
                logger.info("Rate limiter: using Redis storage")
            except Exception as redis_error:
                logger.warning(
                    f"Redis unavailable for rate limiting ({redis_error}), "
                    "falling back to memory storage"
                )
        else:
            logger.warning("Rate limiter: no REDIS_URL configured, using memory storage")
            
        app.config["RATELIMIT_STORAGE_URI"] = storage_uri

        limiter.init_app(app)
        logger.info("Rate limiter initialised successfully")
        return limiter

    except Exception as e:
        logger.error(f"Failed to initialise rate limiter: {e}")
        raise
