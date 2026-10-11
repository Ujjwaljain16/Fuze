"""
Password-guessing limits that a stranger can't turn into a lockout of the real owner.

Failures are counted per (account, client IP): five wrong passwords from one client block that
client for that account for 15 minutes, while the owner signing in from elsewhere is unaffected.
A much higher account-wide threshold (AuthService.record_failed_login) still stops a guessing
attack spread across many addresses. Without Redis the per-client count isn't available, so
callers fall back to the strict account-wide threshold.
"""

from typing import Optional

from core.logging_config import get_logger

logger = get_logger(__name__)

PER_CLIENT_LIMIT = 5
WINDOW_SECONDS = 15 * 60
ACCOUNT_LIMIT_WITH_CLIENT_THROTTLE = 50
ACCOUNT_LIMIT_WITHOUT_CLIENT_THROTTLE = 5


def _key(user_id: int, client: str) -> str:
    return f"login_fail:{user_id}:{client}"


def _client():
    from utils.redis_utils import redis_cache
    if not getattr(redis_cache, 'connected', False):
        return None
    return redis_cache.client


def client_blocked(user_id: int, client: str) -> Optional[bool]:
    """True/False, or None when the throttle is unavailable."""
    redis_client = _client()
    if redis_client is None:
        return None
    try:
        return int(redis_client.get(_key(user_id, client)) or 0) >= PER_CLIENT_LIMIT
    except Exception as e:
        logger.warning("login_throttle_read_failed", extra={"error": str(e)})
        return None


def record_client_failure(user_id: int, client: str) -> bool:
    """Count a failure; returns False when the throttle is unavailable."""
    redis_client = _client()
    if redis_client is None:
        return False
    try:
        key = _key(user_id, client)
        if redis_client.incr(key) == 1:
            redis_client.expire(key, WINDOW_SECONDS)
        return True
    except Exception as e:
        logger.warning("login_throttle_write_failed", extra={"error": str(e)})
        return False


def clear_client_failures(user_id: int, client: str) -> None:
    redis_client = _client()
    if redis_client is None:
        return
    try:
        redis_client.delete(_key(user_id, client))
    except Exception:
        pass
