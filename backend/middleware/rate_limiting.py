"""
Rate limiting middleware for production
"""
import os
import logging
from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)

def init_rate_limiter(app):
    """Initialize rate limiter for the Flask app"""
    try:
        redis_url = os.environ.get('REDIS_URL')
        
        # Use Redis if available, otherwise use memory storage
        if redis_url:
            storage_uri = redis_url
            logger.info("Rate limiter using Redis storage")
        else:
            storage_uri = 'memory://'
            logger.warning("Rate limiter using memory storage (not recommended for production)")
        
        # Use more lenient limits for development, stricter for production
        is_development = os.environ.get('FLASK_ENV', 'development') == 'development'
        
        if is_development:
            # Development: Higher limits to avoid hitting rate limits during testing
            default_limits = ["1000 per day", "200 per hour", "50 per minute"]
        else:
            # Production: Increased limits for better user experience
            default_limits = ["1000 per day", "200 per hour", "50 per minute"]
        
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,  # Use default key function
            default_limits=default_limits,
            storage_uri=storage_uri,
            headers_enabled=True
        )
        # Note: OPTIONS requests will use the same rate limits, but limits are high enough
        # (50 per minute) that preflight requests won't be an issue
        
        logger.info("Rate limiter initialized successfully")
        return limiter
    except Exception as e:
        logger.error(f"Failed to initialize rate limiter: {e}")
        # Return None if rate limiting fails - app should still work
        return None



