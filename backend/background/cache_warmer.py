"""
background/cache_warmer.py
===========================
RQ job: pre-warm the Redis cache for a user immediately after login.

warm_user_cache(user_id) is enqueued by blueprints/auth.py on successful login
using the 'high' priority queue. It runs concurrently with the user's first
request so that its first recommendations are already computed.

Distributed lock (fuze:warm_lock:{user_id}, TTL=30s) prevents thundering herd
when the same user logs in from multiple devices simultaneously.

Only recommendations are warmed: the bookmark and project endpoints read the database
directly, so caching their responses here only spent Redis commands on keys nobody read.

CACHE_WARM_TTL_RECOMMENDATIONS=300 (5 minutes) sets how long a warm marker suppresses re-warming.
"""

import os
import time
import logging

from core.logging_config import get_logger

logger = get_logger(__name__)

WARM_TTL_RECOMMENDATIONS = int(os.getenv("CACHE_WARM_TTL_RECOMMENDATIONS", "300"))
LOCK_TTL_MS = 30_000  # 30 seconds


def warm_user_cache(user_id: int) -> dict:
    """
    RQ job entry point: warm all cache layers for user_id.

    Uses a distributed lock to prevent duplicate warm jobs for the same user.
    Returns a summary dict with per-layer results.
    """
    logger.info("cache_warm_started", extra={"user_id": user_id})
    start = time.time()

    # Distributed lock — prevents thundering herd on multi-device login
    lock_key = f"fuze:warm_lock:{user_id}"
    lock_owner = None

    try:
        from utils.redis_utils import redis_cache
        if redis_cache.connected:
            lock_owner = redis_cache.acquire_lock(lock_key, ttl_ms=LOCK_TTL_MS)
            if not lock_owner:
                logger.info(
                    "cache_warm_skipped_lock_held",
                    extra={"user_id": user_id},
                )
                return {"status": "skipped", "reason": "lock_held", "user_id": user_id}
    except Exception as lock_err:
        logger.warning(
            "cache_warm_lock_error",
            extra={"user_id": user_id, "error": str(lock_err)},
        )
        # Continue without lock — better to warm than to skip

    results = {}
    try:
        results["recommendations"] = _warm_recommendations(user_id)
    finally:
        # Release lock
        if lock_owner:
            try:
                from utils.redis_utils import redis_cache
                redis_cache.release_lock(lock_key, lock_owner)
            except Exception:
                pass

    elapsed_ms = round((time.time() - start) * 1000, 1)
    logger.info(
        "cache_warm_completed",
        extra={"user_id": user_id, "elapsed_ms": elapsed_ms, "results": results},
    )
    return {"status": "ok", "user_id": user_id, "elapsed_ms": elapsed_ms, "layers": results}


# ---------------------------------------------------------------------------
# Layer warmers
# ---------------------------------------------------------------------------

def _warm_recommendations(user_id: int) -> str:
    """
    Pre-compute and cache recommendations for the user.
    Skips if cache already warm (NX semantics via warm_set).
    """
    try:
        from utils.redis_utils import redis_cache
        cache_key = f"fuze:recommendations:{user_id}:warm"

        # NX: only set if key does not exist — avoids overwriting fresh cache
        if redis_cache.redis_client and redis_cache.redis_client.exists(cache_key):
            return "already_warm"

        # Warm the live engine for the user's most recent project: intent statement first (so the
        # first request already gets the Gemini-refined intent), then the result cache.
        from uow.unit_of_work import UnitOfWork
        from ml.intent_engine.engine import recommend
        from ml.intent_engine.intent import compute_intent_job, load_context, resolve_intent

        with UnitOfWork() as uow:
            pagination = uow.projects.list_by_user(user_id=user_id, page=1, per_page=1)
            projects = pagination.items if hasattr(pagination, "items") else pagination
            if not projects:
                return "no_project"
            project_id = projects[0].id
            intent = resolve_intent(load_context(uow.session, user_id, project_id=project_id), schedule=False)

        # Gemini with no session open, then a fresh session for the (database-only) ranking.
        if intent.text and not intent.statement:
            compute_intent_job(intent.hash, intent.text, user_id)
        with UnitOfWork() as uow:
            recommend(uow.session, user_id, project_id=project_id)

        # Mark as warm so subsequent calls skip re-computation
        if redis_cache.redis_client:
            redis_cache.redis_client.setex(cache_key, WARM_TTL_RECOMMENDATIONS, "1")

        return "warmed"
    except Exception as exc:
        logger.warning(
            "cache_warm_recommendations_error",
            extra={"user_id": user_id, "error": str(exc)},
        )
        return f"error: {exc}"
