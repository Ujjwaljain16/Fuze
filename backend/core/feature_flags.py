"""
core/feature_flags.py
=====================
Redis-backed feature flag service with runtime toggles, kill switches,
percentage-based rollouts, per-user targeting, and graceful env-var fallback.

Redis key schema:
    fuze:flags:{name}       → Hash: enabled (0/1), pct (0-100), description, updated_at
    fuze:flags:{name}:users → Set of explicitly targeted user IDs (optional)

Bucketing: deterministic hash(flag_name + str(user_id)) % 100 < pct
In-process cache: 5-second TTL to avoid Redis on every request.
Fallback: if Redis unavailable, returns env-var default — never raises.
"""

import os
import time
import hashlib
import threading
from typing import Optional, Dict, Any
from core.logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Env-var defaults — these are the fallback values when Redis is unavailable
# and the seed values when seed_feature_flags.py runs for the first time.
# Note: Several of these flags are classified as [RESERVED] as they are read
# primarily from UnifiedConfig rather than this dynamic Redis feature flag.
# ---------------------------------------------------------------------------
_ENV_DEFAULTS: Dict[str, bool] = {
    # [RESERVED] Controlled by UnifiedConfig at startup
    "gemini":                  os.getenv("ENABLE_GEMINI", "true").lower() == "true",
    "diversity":               os.getenv("ENABLE_DIVERSITY", "true").lower() == "true",
    "query_caching":           os.getenv("ENABLE_QUERY_CACHING", "true").lower() == "true",
    "embedding_caching":       os.getenv("ENABLE_EMBEDDING_CACHING", "true").lower() == "true",
    "parallel_processing":     os.getenv("ENABLE_PARALLEL_PROCESSING", "true").lower() == "true",
    "smart_engine":            os.getenv("USE_SMART_ENGINE", "true").lower() == "true",
    "prometheus_metrics":      os.getenv("METRICS_ENABLED", "true").lower() == "true",
    "embeddings":              os.getenv("DISABLE_EMBEDDINGS", "false").lower() != "true",

    # [ACTIVE] Dynamic runtime toggles evaluated via is_enabled()
    "async_embeddings":        os.getenv("ASYNC_EMBEDDINGS", "false").lower() == "true",
    "two_stage_retrieval":     os.getenv("RECOMMENDATIONS_TWO_STAGE", "false").lower() == "true",
    "search_rpc":              os.getenv("SEARCH_USE_RPC", "false").lower() == "true",
    "cache_warm_on_login":     os.getenv("CACHE_WARM_ON_LOGIN", "false").lower() == "true",
}

# In-process cache entry: (value: bool, expires_at: float)
_LOCAL_CACHE: Dict[str, tuple] = {}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL_SECONDS = int(os.getenv("FEATURE_FLAGS_CACHE_TTL", "5"))

_REDIS_KEY_PREFIX = "fuze:flags:"


def _get_redis():
    """Lazy import to avoid circular dependency at module load time."""
    try:
        from utils.redis_utils import redis_cache
        if redis_cache.connected and redis_cache.redis_client:
            return redis_cache.redis_client
    except Exception:
        pass
    return None


def _bucket(flag_name: str, user_id: Optional[int]) -> int:
    """
    Deterministic user bucket [0, 99].
    Stable across restarts — based only on flag_name + user_id.
    Renaming a flag resets bucketing (document this in ADR-006).
    """
    if user_id is None:
        return 0
    key = f"{flag_name}:{user_id}"
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return int(digest, 16) % 100


def _read_from_redis(flag_name: str) -> Optional[Dict[str, Any]]:
    """Read flag hash from Redis. Returns None if Redis unavailable or key missing."""
    try:
        r = _get_redis()
        if r is None:
            return None
        redis_key = f"{_REDIS_KEY_PREFIX}{flag_name}"
        data = r.hgetall(redis_key)
        if not data:
            return None
        # Redis returns bytes; decode
        decoded = {}
        for k, v in data.items():
            k = k.decode("utf-8") if isinstance(k, bytes) else k
            v = v.decode("utf-8") if isinstance(v, bytes) else v
            decoded[k] = v
        return decoded
    except Exception as exc:
        logger.warning("feature_flag_redis_read_error", extra={"flag": flag_name, "error": str(exc)})
        return None


def is_enabled(flag_name: str, user_id: Optional[int] = None) -> bool:
    """
    Evaluate a feature flag for an optional user_id.

    Resolution order:
    1. In-process cache (5s TTL)
    2. Redis hash
    3. Env-var default

    Never raises — always returns a boolean.
    """
    # 1. In-process cache
    cache_key = f"{flag_name}:{user_id}"
    now = time.monotonic()
    
    result = None
    with _CACHE_LOCK:
        entry = _LOCAL_CACHE.get(cache_key)
        if entry is not None and entry[1] > now:
            result = entry[0]

    # Emit metric via closure to avoid import cycles / overhead blocking the return
    def _emit_metric(res: bool):
        try:
            from core.metrics import feature_flag_evaluation_total
            feature_flag_evaluation_total.labels(flag=flag_name, result=str(res).lower()).inc()
        except Exception:
            pass

    if result is not None:
        _emit_metric(result)
        return result

    # 2. Redis
    try:
        data = _read_from_redis(flag_name)
        if data is not None:
            enabled_raw = data.get("enabled", "1")
            enabled = str(enabled_raw).strip() in ("1", "true", "True")

            if not enabled:
                result = False
            else:
                pct = int(data.get("pct", "100"))
                if pct >= 100:
                    result = True
                elif pct <= 0:
                    result = False
                else:
                    # Check explicit user targeting first
                    if user_id is not None:
                        try:
                            r = _get_redis()
                            user_key = f"{_REDIS_KEY_PREFIX}{flag_name}:users"
                            if r and r.sismember(user_key, str(user_id)):
                                result = True
                            else:
                                result = _bucket(flag_name, user_id) < pct
                        except Exception:
                            result = _bucket(flag_name, user_id) < pct
                    else:
                        result = False  # Percentage flags require a user_id

            with _CACHE_LOCK:
                _LOCAL_CACHE[cache_key] = (result, now + _CACHE_TTL_SECONDS)
            _emit_metric(result)
            return result
    except Exception as exc:
        logger.warning("feature_flag_eval_error", extra={"flag": flag_name, "error": str(exc)})

    # 3. Env-var fallback
    result = _ENV_DEFAULTS.get(flag_name, False)
    with _CACHE_LOCK:
        _LOCAL_CACHE[cache_key] = (result, now + _CACHE_TTL_SECONDS)
    _emit_metric(result)
    return result


def set_flag(
    flag_name: str,
    enabled: bool,
    percentage: int = 100,
    description: str = "",
) -> bool:
    """
    Write or update a feature flag in Redis.
    percentage: 0–100 — percentage of users to receive the flag when enabled=True.
    Returns True on success, False if Redis unavailable.
    """
    try:
        r = _get_redis()
        if r is None:
            logger.error("feature_flag_set_redis_unavailable", extra={"flag": flag_name})
            return False

        redis_key = f"{_REDIS_KEY_PREFIX}{flag_name}"
        pct = max(0, min(100, percentage))
        r.hset(redis_key, mapping={
            "enabled": "1" if enabled else "0",
            "pct": str(pct),
            "description": description,
            "updated_at": str(time.time()),
        })

        # Invalidate local cache for this flag (all user_id variants)
        _invalidate_local_cache(flag_name)

        logger.info(
            "feature_flag_updated",
            extra={"flag": flag_name, "enabled": enabled, "pct": pct},
        )
        return True
    except Exception as exc:
        logger.error("feature_flag_set_error", extra={"flag": flag_name, "error": str(exc)})
        return False


def kill_switch(flag_name: str) -> bool:
    """
    Immediately disable a feature flag for all users.
    Takes effect within FEATURE_FLAGS_CACHE_TTL seconds (default 5s).
    """
    logger.warning("feature_flag_kill_switch_activated", extra={"flag": flag_name})
    return set_flag(flag_name, enabled=False, percentage=0, description="KILL SWITCH ACTIVATED")


def get_flag_info(flag_name: str) -> Dict[str, Any]:
    """Return current flag state from Redis, or env-var default if Redis unavailable."""
    data = _read_from_redis(flag_name)
    if data:
        return {
            "flag": flag_name,
            "source": "redis",
            "enabled": data.get("enabled", "0") in ("1", "true"),
            "pct": int(data.get("pct", "100")),
            "description": data.get("description", ""),
            "updated_at": data.get("updated_at", ""),
        }
    return {
        "flag": flag_name,
        "source": "env_default",
        "enabled": _ENV_DEFAULTS.get(flag_name, False),
        "pct": 100,
        "description": "env-var fallback",
        "updated_at": "",
    }


def get_all_flags() -> Dict[str, Dict[str, Any]]:
    """Return info for all known flags."""
    return {name: get_flag_info(name) for name in _ENV_DEFAULTS}


def add_user_to_flag(flag_name: str, user_id: int) -> bool:
    """Explicitly target a user_id for a flag regardless of percentage."""
    try:
        r = _get_redis()
        if r is None:
            return False
        user_key = f"{_REDIS_KEY_PREFIX}{flag_name}:users"
        r.sadd(user_key, str(user_id))
        _invalidate_local_cache(flag_name)
        return True
    except Exception as exc:
        logger.error("feature_flag_add_user_error", extra={"flag": flag_name, "error": str(exc)})
        return False


def remove_user_from_flag(flag_name: str, user_id: int) -> bool:
    """Remove explicit user targeting for a flag."""
    try:
        r = _get_redis()
        if r is None:
            return False
        user_key = f"{_REDIS_KEY_PREFIX}{flag_name}:users"
        r.srem(user_key, str(user_id))
        _invalidate_local_cache(flag_name)
        return True
    except Exception as exc:
        logger.error("feature_flag_remove_user_error", extra={"flag": flag_name, "error": str(exc)})
        return False


def _invalidate_local_cache(flag_name: str) -> None:
    """Remove all local cache entries for a given flag_name."""
    with _CACHE_LOCK:
        keys_to_delete = [k for k in _LOCAL_CACHE if k.startswith(f"{flag_name}:")]
        for k in keys_to_delete:
            del _LOCAL_CACHE[k]
