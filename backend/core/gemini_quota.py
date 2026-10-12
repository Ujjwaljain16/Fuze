"""Remember when a Gemini key is out of quota, so nothing keeps calling it until it resets.

A free key can have a very small daily limit (20 requests a day for gemini-2.5-flash) that Fuze
cannot know in advance: the rate limits it counts itself assume far more. Google says what to do
in the 429 itself ("Please retry in 6h52m17s"), so that is what is recorded here, per key
(by fingerprint, never the key), in Redis so every worker sees it, with an in-process copy for
when Redis is down.
"""

import hashlib
import re
import time
from typing import Dict, Optional

from core.logging_config import get_logger

logger = get_logger(__name__)

MIN_COOLDOWN_SECONDS = 30
MAX_COOLDOWN_SECONDS = 24 * 3600
# When a quota error does not say how long: a daily quota is the likely kind, a short wait is cheap.
DEFAULT_COOLDOWN_SECONDS = 15 * 60

_RETRY_IN = re.compile(r'retry in\s+(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:([\d.]+)s)?', re.IGNORECASE)
_RETRY_DELAY = re.compile(r"retryDelay['\"]?\s*[:=]\s*['\"]?([\d.]+)s", re.IGNORECASE)

_local: Dict[str, float] = {}


def fingerprint(api_key: str) -> str:
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()[:16]


def _redis_key(api_key: str) -> str:
    return f"gemini_cooldown:{fingerprint(api_key)}"


def parse_retry_seconds(message: str) -> Optional[float]:
    """Seconds Google asks us to wait, from "Please retry in 6h52m17.1s" or a retryDelay field."""
    text = str(message or '')
    match = _RETRY_IN.search(text)
    if match and any(match.groups()):
        hours, minutes, seconds = (float(g) if g else 0.0 for g in match.groups())
        return hours * 3600 + minutes * 60 + seconds
    match = _RETRY_DELAY.search(text)
    return float(match.group(1)) if match else None


def _redis():
    try:
        from utils.redis_utils import redis_cache
        if getattr(redis_cache, 'connected', False):
            return redis_cache.redis_client
    except Exception:
        pass
    return None


def mark_exhausted(api_key: str, error_message: str = '') -> int:
    """Record that this key is out of quota; returns the cooldown in seconds."""
    if not api_key:
        return 0
    wait = parse_retry_seconds(error_message)
    seconds = int(min(max(wait if wait is not None else DEFAULT_COOLDOWN_SECONDS, MIN_COOLDOWN_SECONDS),
                      MAX_COOLDOWN_SECONDS))
    _local[fingerprint(api_key)] = time.time() + seconds
    client = _redis()
    if client is not None:
        try:
            client.setex(_redis_key(api_key), seconds, str(int(time.time()) + seconds))
        except Exception as e:
            logger.warning("gemini_cooldown_store_failed", extra={"error": str(e)})
    logger.warning("gemini_quota_exhausted", extra={"cooldown_seconds": seconds})
    return seconds


def cooldown_seconds(api_key: Optional[str]) -> int:
    """Seconds left before this key may be called again (0 when it may be called now)."""
    if not api_key:
        return 0
    now = time.time()
    remaining = _local.get(fingerprint(api_key), 0) - now
    client = _redis()
    if client is not None:
        try:
            ttl = client.ttl(_redis_key(api_key))
            if isinstance(ttl, int) and ttl > 0:
                remaining = max(remaining, ttl)
        except Exception:
            pass
    return int(remaining) if remaining > 0 else 0


def clear(api_key: str) -> None:
    """Forget a cooldown (a new key was saved, or the quota was raised)."""
    if not api_key:
        return
    _local.pop(fingerprint(api_key), None)
    client = _redis()
    if client is not None:
        try:
            client.delete(_redis_key(api_key))
        except Exception:
            pass
