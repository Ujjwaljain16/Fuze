"""Per-user content version used in result cache keys.

Bumping the version on any change to a user's content or context makes every cached
result for that user unreachable at once, without having to know or delete the keys.
"""

from core.logging_config import get_logger

logger = get_logger(__name__)


def _key(user_id) -> str:
    return f"content_version:{user_id}"


def get_content_version(user_id) -> int:
    try:
        from utils.redis_utils import redis_cache
        client = getattr(redis_cache, "redis_client", None)
        value = client.get(_key(user_id)) if client is not None else None
        return int(value) if value else 0
    except Exception as e:
        logger.warning("content_version_read_failed", extra={"user_id": user_id, "error": str(e)})
        return -1  # unknown version: callers' cache keys won't match anything stored


def bump_content_version(user_id) -> None:
    try:
        from utils.redis_utils import redis_cache
        client = getattr(redis_cache, "redis_client", None)
        if client is not None:
            client.incr(_key(user_id))
    except Exception as e:
        logger.warning("content_version_bump_failed", extra={"user_id": user_id, "error": str(e)})
