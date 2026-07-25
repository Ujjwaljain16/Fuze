"""
background/cache_warmer.py
===========================
RQ job: pre-warm the Redis cache for a user immediately after login.

warm_user_cache(user_id) is enqueued by blueprints/auth.py on successful login
using the 'high' priority queue. It runs concurrently with the user's first
request so that recommendations and bookmarks are served from cache.

Distributed lock (fuze:warm_lock:{user_id}, TTL=30s) prevents thundering herd
when the same user logs in from multiple devices simultaneously.

Cache warming order (highest ROI first):
  1. Recommendations — most latency-sensitive
  2. Bookmarks list  — most frequently accessed
  3. Project context — supplementary

TTLs are configured via env vars:
  CACHE_WARM_TTL_RECOMMENDATIONS=300  (5 minutes)
  CACHE_WARM_TTL_BOOKMARKS=60         (1 minute)
  CACHE_WARM_TTL_PROJECTS=120         (2 minutes)
"""

import os
import time
import logging

from core.logging_config import get_logger

logger = get_logger(__name__)

WARM_TTL_RECOMMENDATIONS = int(os.getenv("CACHE_WARM_TTL_RECOMMENDATIONS", "300"))
WARM_TTL_BOOKMARKS = int(os.getenv("CACHE_WARM_TTL_BOOKMARKS", "60"))
WARM_TTL_PROJECTS = int(os.getenv("CACHE_WARM_TTL_PROJECTS", "120"))
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
        results["bookmarks"] = _warm_bookmarks(user_id)
        results["projects"] = _warm_projects(user_id)
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

        # Trigger recommendation pipeline to populate the real cache
        from uow.unit_of_work import UnitOfWork
        from ml.recommendation.pipeline import RecommendationPipeline
        from ml.recommendation.domain import RecommendationRequest

        with UnitOfWork() as uow:
            # Fetch user's most recent project for context
            projects = uow.projects.get_user_projects(user_id=user_id, limit=1)
            if projects:
                proj = projects[0]
                req = RecommendationRequest(
                    user_id=user_id,
                    title=getattr(proj, "title", "") or "",
                    description=getattr(proj, "description", "") or "",
                    technologies=getattr(proj, "technologies", "") or "",
                    max_recommendations=10,
                )
            else:
                req = RecommendationRequest(
                    user_id=user_id,
                    title="",
                    max_recommendations=10,
                )

            pipeline = RecommendationPipeline(
                data_layer=None,  # pipeline will construct its own with uow
                redis_cache=redis_cache,
            )
            from ml.recommendation.data_layer import RecommendationDataLayer
            pipeline.data_layer = RecommendationDataLayer(uow=uow)
            pipeline.run(req)

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


def _warm_bookmarks(user_id: int) -> str:
    """
    Pre-populate the bookmarks list cache.
    Calls the same cache path that GET /api/bookmarks uses.
    """
    try:
        from utils.redis_utils import redis_cache
        from uow.unit_of_work import UnitOfWork
        from services.bookmark_service import BookmarkService

        cache_key = f"fuze:bookmarks:{user_id}:page1"
        if redis_cache.redis_client and redis_cache.redis_client.exists(cache_key):
            return "already_warm"

        with UnitOfWork() as uow:
            service = BookmarkService(uow)
            bookmarks = service.get_user_bookmarks(user_id=user_id, limit=20, offset=0)

        if redis_cache.redis_client and bookmarks:
            import json
            serialized = json.dumps(
                [b.to_dict() if hasattr(b, "to_dict") else {"id": getattr(b, "id", None)}
                 for b in (bookmarks if isinstance(bookmarks, list) else [])],
                default=str,
            )
            redis_cache.redis_client.setex(cache_key, WARM_TTL_BOOKMARKS, serialized)

        return "warmed"
    except Exception as exc:
        logger.warning(
            "cache_warm_bookmarks_error",
            extra={"user_id": user_id, "error": str(exc)},
        )
        return f"error: {exc}"


def _warm_projects(user_id: int) -> str:
    """Pre-populate the project list in cache."""
    try:
        from utils.redis_utils import redis_cache
        from uow.unit_of_work import UnitOfWork

        cache_key = f"fuze:projects:{user_id}:list"
        if redis_cache.redis_client and redis_cache.redis_client.exists(cache_key):
            return "already_warm"

        with UnitOfWork() as uow:
            projects = uow.projects.get_user_projects(user_id=user_id, limit=20)

        if redis_cache.redis_client and projects:
            import json
            serialized = json.dumps(
                [{"id": getattr(p, "id", None), "title": getattr(p, "title", "")}
                 for p in projects],
                default=str,
            )
            redis_cache.redis_client.setex(cache_key, WARM_TTL_PROJECTS, serialized)

        return "warmed"
    except Exception as exc:
        logger.warning(
            "cache_warm_projects_error",
            extra={"user_id": user_id, "error": str(exc)},
        )
        return f"error: {exc}"
