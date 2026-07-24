#!/usr/bin/env python3
"""
Rate Limiting Handler for Gemini API
Manages global rate limiting for Gemini API calls across threads and multi-worker processes
using shared Redis counters or thread-safe atomic memory tracking.
"""

import time
import random
import threading
from typing import Optional, Callable, Any, Dict
from functools import wraps
from datetime import datetime, timezone, timedelta
from core.logging_config import get_logger
from utils.redis_utils import RedisCache, redis_cache

logger = get_logger(__name__)


class RateLimitExceededException(Exception):
    """Raised when rate limits are exceeded and blocking sleep is disabled."""

    def __init__(self, message: str, wait_seconds: int = 60):
        super().__init__(message)
        self.wait_seconds = wait_seconds


class RateLimitHandler:
    """
    Handles global rate limiting for Gemini API calls with Redis persistence and thread locking.
    """

    def __init__(self, redis_client=None):
        self.requests_per_minute = 15
        self.requests_per_day = 1500
        self.max_retries = 3
        self.base_delay = 35
        self.max_delay = 300

        self.lock = threading.RLock()
        self.redis = redis_client or redis_cache
        self.request_times = []
        self.daily_requests = 0
        self.last_daily_reset = datetime.now(timezone.utc).date()

    def can_make_request(self) -> bool:
        """Check if request can be made without exceeding limits."""
        try:
            if self.redis and getattr(self.redis, 'connected', False):
                min_key = "fuze:gemini:rpm"
                day_key = "fuze:gemini:rpd"

                c_min = int(self.redis.get_cache(min_key) or 0)
                c_day = int(self.redis.get_cache(day_key) or 0)

                if c_min >= self.requests_per_minute or c_day >= self.requests_per_day:
                    logger.warning("gemini_rate_limit_reached_redis", extra={"min_count": c_min, "day_count": c_day})
                    return False
                return True

            # Thread-safe in-memory fallback
            now = datetime.now(timezone.utc)
            with self.lock:
                if now.date() > self.last_daily_reset:
                    self.daily_requests = 0
                    self.last_daily_reset = now.date()

                if self.daily_requests >= self.requests_per_day:
                    logger.warning("gemini_daily_limit_reached_memory")
                    return False

                minute_ago = now - timedelta(minutes=1)
                self.request_times = [t for t in self.request_times if t > minute_ago]

                if len(self.request_times) >= self.requests_per_minute:
                    logger.warning("gemini_minute_limit_reached_memory")
                    return False

                return True

        except Exception as e:
            logger.error("can_make_request_failed", extra={"error": str(e)})
            return True

    def record_request(self):
        """Record an API request attempt."""
        try:
            if self.redis and getattr(self.redis, 'connected', False):
                min_key = "fuze:gemini:rpm"
                day_key = "fuze:gemini:rpd"

                c_min = int(self.redis.get_cache(min_key) or 0) + 1
                self.redis.set_cache(min_key, c_min, ttl=60)

                c_day = int(self.redis.get_cache(day_key) or 0) + 1
                self.redis.set_cache(day_key, c_day, ttl=86400)
                return

            now = datetime.now(timezone.utc)
            with self.lock:
                self.request_times.append(now)
                self.daily_requests += 1
                minute_ago = now - timedelta(minutes=1)
                self.request_times = [t for t in self.request_times if t > minute_ago]

        except Exception as e:
            logger.error("record_request_failed", extra={"error": str(e)})

    def get_wait_time(self) -> int:
        """Calculate wait time before next request."""
        now = datetime.now(timezone.utc)
        with self.lock:
            minute_ago = now - timedelta(minutes=1)
            recent_requests = [t for t in self.request_times if t > minute_ago]
            if recent_requests:
                oldest_recent = min(recent_requests)
                wait_until = oldest_recent + timedelta(minutes=1)
                return max(0, int((wait_until - now).total_seconds()))
            return 0

    def exponential_backoff(self, attempt: int) -> int:
        """Calculate exponential backoff with jitter."""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        jitter = random.uniform(0.8, 1.2)
        return int(delay * jitter)


# Global shared rate limit handler singleton
global_rate_handler = RateLimitHandler()


def is_rate_limit_error(error: Exception) -> bool:
    """Classify whether exception is a 429 or quota error."""
    error_str = str(error).lower()
    error_name = error.__class__.__name__.lower()

    if 'resourceexhausted' in error_name or 'toomanyrequests' in error_name:
        return True
    if '429' in error_str or 'quota' in error_str or 'resource_exhausted' in error_str:
        return True
    return False


def rate_limited(func: Callable = None, *, raise_on_limit: bool = False) -> Callable:
    """
    Decorator to apply rate limiting using global_rate_handler singleton.
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(global_rate_handler.max_retries + 1):
                try:
                    if not global_rate_handler.can_make_request():
                        wait_time = global_rate_handler.get_wait_time() or 60
                        if raise_on_limit:
                            raise RateLimitExceededException("Rate limit reached", wait_seconds=wait_time)
                        logger.info("rate_limit_reached_waiting", extra={"wait_seconds": wait_time})
                        time.sleep(min(wait_time, 60))

                    global_rate_handler.record_request()
                    return fn(*args, **kwargs)

                except Exception as e:
                    if is_rate_limit_error(e):
                        if attempt < global_rate_handler.max_retries:
                            wait_time = global_rate_handler.exponential_backoff(attempt)
                            logger.warning("rate_limit_error_retry", extra={"attempt": attempt + 1, "wait_seconds": wait_time})
                            time.sleep(wait_time)
                            continue
                        logger.error("max_retries_reached_for_rate_limit")
                        raise
                    raise

            return None
        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


class GeminiRateLimiter:
    """Rate limiter wrapper using shared global rate limit handler."""

    def __init__(self, handler: Optional[RateLimitHandler] = None):
        self.rate_handler = handler or global_rate_handler

    def make_gemini_request(self, request_func: Callable, *args, **kwargs) -> Any:
        @rate_limited
        def _exec():
            return request_func(*args, **kwargs)
        return _exec()

    def get_status(self) -> Dict[str, Any]:
        """Get current rate limiting status using shared rate handler."""
        now = datetime.now(timezone.utc)
        with self.rate_handler.lock:
            minute_ago = now - timedelta(minutes=1)
            recent_count = len([t for t in self.rate_handler.request_times if t > minute_ago])
            daily_count = self.rate_handler.daily_requests

        return {
            'requests_last_minute': recent_count,
            'requests_today': daily_count,
            'can_make_request': self.rate_handler.can_make_request(),
            'wait_time_seconds': self.rate_handler.get_wait_time(),
            'daily_limit': self.rate_handler.requests_per_day,
            'minute_limit': self.rate_handler.requests_per_minute
        }


# Global instance
gemini_rate_limiter = GeminiRateLimiter()