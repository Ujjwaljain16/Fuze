"""
Domain Rate Limiter Module
Per-domain token-bucket and sliding window rate limiting via Redis.
"""

import time
from urllib.parse import urlparse
from typing import Tuple
from utils.redis_utils import get_redis_client
from core.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_RATE_LIMIT = 5  # Requests per domain
DEFAULT_WINDOW_SECONDS = 10  # Window size in seconds


class DomainRateLimiter:
    """
    Enforces per-domain sliding window rate limiting using Redis.
    """
    def __init__(self, max_requests: int = DEFAULT_RATE_LIMIT, window_seconds: int = DEFAULT_WINDOW_SECONDS):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._redis = get_redis_client()

    def _get_domain(self, url: str) -> str:
        return urlparse(url).netloc.lower()

    def acquire(self, url: str) -> Tuple[bool, float]:
        """
        Check if request to domain can proceed under rate limits.
        Returns Tuple[allowed: bool, wait_time_seconds: float].
        """
        domain = self._get_domain(url)
        if not domain or not self._redis:
            return True, 0.0

        key = f"fuze:rate_limit:{domain}"
        now = time.time()
        cutoff = now - self.window_seconds

        try:
            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(key, 0, cutoff)
            pipe.zcard(key)
            pipe.zrange(key, 0, 0, withscores=True)
            pipe.expire(key, self.window_seconds * 2)
            results = pipe.execute()

            current_count = results[1]
            oldest_entry = results[2]

            if current_count < self.max_requests:
                self._redis.zadd(key, {f"{now}": now})
                return True, 0.0

            # Calculate wait time based on oldest request in window
            if oldest_entry:
                oldest_timestamp = oldest_entry[0][1]
                wait_time = max(0.1, (oldest_timestamp + self.window_seconds) - now)
            else:
                wait_time = 1.0

            logger.warning("domain_rate_limit_exceeded", extra={"domain": domain, "current_count": current_count, "wait_time": wait_time})
            return False, round(wait_time, 2)
        except Exception as e:
            logger.warning("rate_limit_check_failed", extra={"domain": domain, "error": str(e)})
            return True, 0.0
