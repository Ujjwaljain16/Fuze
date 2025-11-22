"""
Rate limiting middleware for production
"""
import os
import logging
from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis.exceptions

logger = logging.getLogger(__name__)

def init_rate_limiter(app):
    """Initialize rate limiter for the Flask app with Redis fallback"""
    try:
        redis_url = os.environ.get('REDIS_URL')
        
        # Use more lenient limits for development, stricter for production
        is_development = os.environ.get('FLASK_ENV', 'development') == 'development'
        
        if is_development:
            # Development: Higher limits to avoid hitting rate limits during testing
            default_limits = ["1000 per day", "200 per hour", "50 per minute"]
        else:
            # Production: Increased limits for better user experience
            default_limits = ["1000 per day", "200 per hour", "50 per minute"]
        
        # Try Redis first, fallback to memory if Redis is unavailable
        limiter = None
        if redis_url:
            try:
                # Test Redis connection first
                import redis
                from urllib.parse import urlparse
                parsed = urlparse(redis_url)
                
                # Create a test connection
                test_redis = redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
                test_redis.ping()
                test_redis.close()
                
                # Redis is available, use it
                limiter = Limiter(
                    app=app,
                    key_func=get_remote_address,
                    default_limits=default_limits,
                    storage_uri=redis_url,
                    headers_enabled=True,
                    swallow_errors=True,  # Don't crash on rate limit errors
                    on_breach=lambda request, endpoint, limits: logger.warning(
                        f"Rate limit breached: {endpoint} by {get_remote_address()}"
                    )
                )
                logger.info("Rate limiter using Redis storage")
            except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, 
                    redis.exceptions.RedisError, Exception) as redis_error:
                logger.warning(f"Redis unavailable for rate limiting ({redis_error}), falling back to memory storage")
                # Fall back to memory storage
                limiter = Limiter(
                    app=app,
                    key_func=get_remote_address,
                    default_limits=default_limits,
                    storage_uri='memory://',
                    headers_enabled=True,
                    swallow_errors=True
                )
                logger.warning("Rate limiter using memory storage (Redis unavailable)")
        else:
            # No Redis URL configured, use memory
            limiter = Limiter(
                app=app,
                key_func=get_remote_address,
                default_limits=default_limits,
                storage_uri='memory://',
                headers_enabled=True,
                swallow_errors=True
            )
            logger.warning("Rate limiter using memory storage (no Redis URL configured)")
        
        logger.info("Rate limiter initialized successfully")
        return limiter
    except Exception as e:
        logger.error(f"Failed to initialize rate limiter: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        # Return None if rate limiting fails - app should still work
        return None



