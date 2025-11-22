#!/usr/bin/env python3
"""
Rate limiting handler for Gemini API to manage quota limits
"""

import time
import logging
import random
from typing import Optional, Callable, Any
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RateLimitHandler:
    """
    Handles rate limiting for Gemini API calls
    """
    
    def __init__(self):
        # Free tier limits
        self.requests_per_minute = 15
        self.requests_per_day = 1500
        
        # Tracking
        self.request_times = []
        self.daily_requests = 0
        self.last_daily_reset = datetime.now().date()
        
        # Retry settings
        self.max_retries = 3
        self.base_delay = 35  # seconds (from API response)
        self.max_delay = 300  # 5 minutes max delay
        
    def can_make_request(self) -> bool:
        """Check if we can make a request without hitting rate limits"""
        now = datetime.now()
        
        # Reset daily counter if it's a new day
        if now.date() > self.last_daily_reset:
            self.daily_requests = 0
            self.last_daily_reset = now.date()
        
        # Check daily limit
        if self.daily_requests >= self.requests_per_day:
            logger.warning("Daily rate limit reached")
            return False
        
        # Check per-minute limit
        minute_ago = now - timedelta(minutes=1)
        recent_requests = [t for t in self.request_times if t > minute_ago]
        
        if len(recent_requests) >= self.requests_per_minute:
            logger.warning("Per-minute rate limit reached")
            return False
        
        return True
    
    def record_request(self):
        """Record a successful request"""
        now = datetime.now()
        self.request_times.append(now)
        self.daily_requests += 1
        
        # Clean up old request times (keep only last 2 minutes)
        two_minutes_ago = now - timedelta(minutes=2)
        self.request_times = [t for t in self.request_times if t > two_minutes_ago]
    
    def get_wait_time(self) -> int:
        """Calculate how long to wait before next request"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        recent_requests = [t for t in self.request_times if t > minute_ago]
        
        if recent_requests:
            # Wait until the oldest request is more than 1 minute old
            oldest_recent = min(recent_requests)
            wait_until = oldest_recent + timedelta(minutes=1)
            wait_seconds = max(0, (wait_until - now).total_seconds())
            return int(wait_seconds)
        
        return 0
    
    def exponential_backoff(self, attempt: int) -> int:
        """Calculate exponential backoff delay"""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        # Add jitter to prevent thundering herd
        jitter = random.uniform(0.8, 1.2)
        return int(delay * jitter)

def rate_limited(func: Callable) -> Callable:
    """
    Decorator to handle rate limiting for Gemini API calls
    """
    rate_handler = RateLimitHandler()
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        for attempt in range(rate_handler.max_retries + 1):
            try:
                # Check if we can make a request
                if not rate_handler.can_make_request():
                    wait_time = rate_handler.get_wait_time()
                    logger.info(f"Rate limit reached, waiting {wait_time} seconds")
                    time.sleep(wait_time)
                
                # Make the request
                result = func(*args, **kwargs)
                rate_handler.record_request()
                return result
                
            except Exception as e:
                error_str = str(e)
                
                # Check if it's a rate limit error
                if "429" in error_str and "quota" in error_str.lower():
                    if attempt < rate_handler.max_retries:
                        wait_time = rate_handler.exponential_backoff(attempt)
                        logger.warning(f"Rate limit error (attempt {attempt + 1}/{rate_handler.max_retries + 1}), waiting {wait_time} seconds")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error("Max retries reached for rate limit")
                        raise
                else:
                    # Not a rate limit error, re-raise
                    raise
        
        return None
    
    return wrapper

class GeminiRateLimiter:
    """
    Rate limiter specifically for Gemini API calls
    """
    
    def __init__(self):
        self.rate_handler = RateLimitHandler()
        self.request_queue = []
        self.processing = False
    
    @rate_limited
    def make_gemini_request(self, request_func: Callable, *args, **kwargs) -> Any:
        """
        Make a Gemini API request with rate limiting
        """
        return request_func(*args, **kwargs)
    
    def get_status(self) -> dict:
        """Get current rate limiting status"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        recent_requests = [t for t in self.rate_handler.request_times if t > minute_ago]
        
        return {
            'requests_last_minute': len(recent_requests),
            'requests_today': self.rate_handler.daily_requests,
            'can_make_request': self.rate_handler.can_make_request(),
            'wait_time_seconds': self.rate_handler.get_wait_time(),
            'daily_limit': self.rate_handler.requests_per_day,
            'minute_limit': self.rate_handler.requests_per_minute
        }

# Global rate limiter instance
gemini_rate_limiter = GeminiRateLimiter()

def apply_rate_limiting_to_gemini():
    """
    Apply rate limiting to Gemini API calls in the application
    """
    try:
        from gemini_utils import GeminiAnalyzer
        
        # Store original methods
        original_analyze_bookmark = GeminiAnalyzer.analyze_bookmark_content
        original_analyze_user_context = GeminiAnalyzer.analyze_user_context
        original_generate_reasoning = GeminiAnalyzer.generate_recommendation_reasoning
        original_rank_recommendations = GeminiAnalyzer.rank_recommendations
        
        # Apply rate limiting decorator
        GeminiAnalyzer.analyze_bookmark_content = rate_limited(original_analyze_bookmark)
        GeminiAnalyzer.analyze_user_context = rate_limited(original_analyze_user_context)
        GeminiAnalyzer.generate_recommendation_reasoning = rate_limited(original_generate_reasoning)
        GeminiAnalyzer.rank_recommendations = rate_limited(original_rank_recommendations)
        
        logger.info("Rate limiting applied to Gemini API methods")
        
    except ImportError:
        logger.warning("GeminiAnalyzer not available for rate limiting")

def create_rate_limit_config():
    """
    Create configuration for rate limiting
    """
    config_content = """# Rate Limiting Configuration for Gemini API

# Free Tier Limits
REQUESTS_PER_MINUTE = 15
REQUESTS_PER_DAY = 1500

# Retry Settings
MAX_RETRIES = 3
BASE_DELAY = 35  # seconds
MAX_DELAY = 300  # 5 minutes

# Fallback Settings
ENABLE_FALLBACK = True
FALLBACK_TO_UNIFIED_ENGINE = True

# Monitoring
LOG_RATE_LIMITS = True
ALERT_ON_QUOTA_REACHED = True
"""
    
    try:
        with open("rate_limit_config.py", 'w') as f:
            f.write(config_content)
        logger.info(" Created rate_limit_config.py")
        return True
    except Exception as e:
        logger.error(f" Failed to create rate limit config: {e}")
        return False

if __name__ == "__main__":
    # Test rate limiting
    print("Testing rate limiting functionality...")
    
    # Create config
    create_rate_limit_config()
    
    # Test status
    status = gemini_rate_limiter.get_status()
    print(f"Rate limiting status: {status}")
    
    print(" Rate limiting setup complete!") 