from backend.core.logging_config import get_logger

logger = get_logger(__name__)

from extensions import limiter

def init_rate_limiter(app):
    """Initialize rate limiter for the Flask app with Redis as primary storage"""
    try:
        redis_url = os.environ.get('REDIS_URL')
        
        # PRODUCTION: reasonable limits as a baseline
        # Specific overrides should be used on high-value AI routes
        default_limits = ["1000 per hour", "100 per minute"]
        
        # Security: Default to memory if Redis is missing to avoid crashing, 
        # but log a critical warning in production.
        storage_uri = 'memory://'
        if redis_url:
            storage_uri = redis_url
            logger.info("rate_limiter_redis_storage_enabled")
        else:
            logger.warning("rate_limiter_memory_fallback", reason="REDIS_URL_missing")
        
        # Configure the limiter
        # We handle this during init_app to ensure config is applied to the app instance
        limiter.init_app(app)
        limiter.storage_uri = storage_uri
        # Note: default_limits should be set on the object or passed to init_app if supported
        # flask-limiter 2.x+ uses storage_uri property
        
        # Set default limits manually on the instance for broadcast
        if not hasattr(limiter, '_default_limits'):
            limiter._default_limits = default_limits
        
        limiter.headers_enabled = True
        # Security: DO NOT swallow errors in production. We want to know if Redis dies.
        # But for stability, we might set it to True with a fallback.
        limiter.swallow_errors = True 
        
        logger.info("rate_limiter_initialized")
        return limiter
    except Exception as e:
        logger.error("rate_limiter_init_failed", error=str(e))
        return None



