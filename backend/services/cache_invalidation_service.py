"""
Cache Invalidation Service for Fuze Architecture
Provides targeted cache invalidation hooks for recommendations, content, projects, and tasks.
Supports instance dependency injection and legacy class-level calls via metaclass delegation.
"""

from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from utils.redis_utils import redis_cache
from core.logging_config import get_logger

logger = get_logger(__name__)

# The after_*() hooks below are called from request handlers right before
# returning a response (e.g. blueprints/bookmarks.py after every save/update/
# delete) -- each one does several sequential, synchronous Redis round-trips
# (a SCAN-based pattern delete plus multiple individual key deletes). Measured
# directly against production Redis during an end-to-end test: ~1.7s for a
# single content invalidation, ~5.1s for a single user invalidation -- on an
# otherwise-empty database, for what callers treat as a fire-and-forget
# notification (none of them use the bool return value for control flow).
# That's several seconds added to the response time of routes like
# POST /api/bookmarks/quick-save, which explicitly documents itself as
# "Returns immediately so user can return to previous app." Dispatching this
# work to a small background pool instead keeps cache invalidation eventually
# consistent (a target cache read might see stale data for a few hundred ms)
# without blocking the HTTP response for multiple seconds.
_invalidation_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cache-invalidation")


def _dispatch_async(label: str, fn, *args, **kwargs) -> None:
    def _run():
        try:
            fn(*args, **kwargs)
        except Exception as e:
            logger.error("cache_invalidation_async_task_failed", extra={"label": label, "error": str(e)})

    _invalidation_executor.submit(_run)


class _CacheInvalidationMeta(type):
    """Metaclass allowing legacy class-level calls to delegate to global cache_invalidator instance."""

    def invalidate_content_cache(cls, content_id: int) -> bool:
        return cache_invalidator.invalidate_content_cache(content_id)

    def invalidate_user_cache(cls, user_id: int) -> bool:
        return cache_invalidator.invalidate_user_cache(user_id)

    def invalidate_project_cache(cls, project_id: int) -> bool:
        return cache_invalidator.invalidate_project_cache(project_id)

    def invalidate_task_cache(cls, task_id: int) -> bool:
        return cache_invalidator.invalidate_task_cache(task_id)

    def invalidate_recommendation_cache(cls, user_id: Optional[int] = None) -> bool:
        return cache_invalidator.invalidate_recommendation_cache(user_id)

    def invalidate_analysis_cache(cls, content_id: Optional[int] = None, user_id: Optional[int] = None) -> bool:
        return cache_invalidator.invalidate_analysis_cache(content_id=content_id, user_id=user_id)

    def invalidate_all_cache(cls, confirm: bool = False) -> bool:
        return cache_invalidator.invalidate_all_cache(confirm=confirm)

    def after_content_save(cls, content_id: int, user_id: int) -> bool:
        return cache_invalidator.after_content_save(content_id, user_id)

    def after_content_update(cls, content_id: int, user_id: int) -> bool:
        return cache_invalidator.after_content_update(content_id, user_id)

    def after_content_delete(cls, content_id: int, user_id: int) -> bool:
        return cache_invalidator.after_content_delete(content_id, user_id)

    def after_project_save(cls, project_id: int, user_id: int) -> bool:
        return cache_invalidator.after_project_save(project_id, user_id)

    def after_project_update(cls, project_id: int, user_id: int) -> bool:
        return cache_invalidator.after_project_update(project_id, user_id)

    def after_task_save(cls, task_id: int, user_id: int) -> bool:
        return cache_invalidator.after_task_save(task_id, user_id)

    def after_user_profile_update(cls, user_id: int) -> bool:
        return cache_invalidator.after_user_profile_update(user_id)

    def after_analysis_complete(cls, content_id: int, user_id: int) -> bool:
        return cache_invalidator.after_analysis_complete(content_id, user_id)


class CacheInvalidationService(metaclass=_CacheInvalidationMeta):
    """Service for managing targeted cache invalidation across the application"""

    def __init__(self, redis_cache=None):
        self._redis = redis_cache

    @property
    def client(self):
        return self._redis if self._redis is not None else redis_cache

    def invalidate_content_cache(self, content_id: int) -> bool:
        """Invalidate cache related to a specific content item."""
        try:
            logger.info("cache_invalidate_content_start", extra={"content_id": content_id})
            client = self.client
            if hasattr(client, 'invalidate_content_cache'):
                client.invalidate_content_cache(content_id)
            elif hasattr(client, 'delete_cache'):
                client.delete_cache(f"content_cache:{content_id}")
            if hasattr(client, 'delete_cache'):
                client.delete_cache(f"content_analysis:{content_id}")
            logger.info("cache_invalidate_content_success", extra={"content_id": content_id})
            return True
        except Exception as e:
            logger.error("cache_invalidate_content_failed", extra={"content_id": content_id, "error": str(e)})
            return False

    def invalidate_user_cache(self, user_id: int) -> bool:
        """Invalidate user-specific bookmarks and recommendations cache without global wildcard scans."""
        try:
            logger.info("cache_invalidate_user_start", extra={"user_id": user_id})
            client = self.client
            if hasattr(client, 'invalidate_user_bookmarks'):
                client.invalidate_user_bookmarks(user_id)
            elif hasattr(client, 'invalidate_query_cache'):
                client.invalidate_query_cache(f"bookmarks:{user_id}:*")
            if hasattr(client, 'invalidate_recommendation_cache'):
                client.invalidate_recommendation_cache(user_id)
            if hasattr(client, 'delete_cache'):
                client.delete_cache(f"user_context:{user_id}")
                client.delete_cache(f"unified_recommendations:{user_id}")
                client.delete_cache(f"user_profile:{user_id}")
                client.delete_cache(f"dashboard_summary:{user_id}")
            logger.info("cache_invalidate_user_success", extra={"user_id": user_id})
            return True
        except Exception as e:
            logger.error("cache_invalidate_user_failed", extra={"user_id": user_id, "error": str(e)})
            return False

    def invalidate_project_cache(self, project_id: int) -> bool:
        """Invalidate project-specific cache."""
        try:
            logger.info("cache_invalidate_project_start", extra={"project_id": project_id})
            client = self.client
            if hasattr(client, 'invalidate_project_cache'):
                client.invalidate_project_cache(project_id)
            if hasattr(client, 'delete_cache'):
                client.delete_cache(f"project_embedding:{project_id}")
            logger.info("cache_invalidate_project_success", extra={"project_id": project_id})
            return True
        except Exception as e:
            logger.error("cache_invalidate_project_failed", extra={"project_id": project_id, "error": str(e)})
            return False

    def invalidate_task_cache(self, task_id: int) -> bool:
        """Invalidate task-specific cache."""
        try:
            logger.info("cache_invalidate_task_start", extra={"task_id": task_id})
            client = self.client
            if hasattr(client, 'delete_cache'):
                client.delete_cache(f"task_analysis:{task_id}")
                client.delete_cache(f"task_embedding:{task_id}")
            logger.info("cache_invalidate_task_success", extra={"task_id": task_id})
            return True
        except Exception as e:
            logger.error("cache_invalidate_task_failed", extra={"task_id": task_id, "error": str(e)})
            return False

    def invalidate_recommendation_cache(self, user_id: Optional[int] = None) -> bool:
        """Invalidate recommendation cache for user or all users."""
        try:
            client = self.client
            if user_id:
                logger.info("cache_invalidate_rec_user_start", extra={"user_id": user_id})
                if hasattr(client, 'invalidate_recommendation_cache'):
                    client.invalidate_recommendation_cache(user_id)
                if hasattr(client, 'delete_cache'):
                    client.delete_cache(f"unified_recommendations:{user_id}")
            else:
                logger.info("cache_invalidate_rec_all_start")
                if hasattr(client, 'invalidate_all_recommendations'):
                    client.invalidate_all_recommendations()
            return True
        except Exception as e:
            logger.error("cache_invalidate_rec_failed", extra={"user_id": user_id, "error": str(e)})
            return False

    def invalidate_analysis_cache(self, content_id: Optional[int] = None, user_id: Optional[int] = None) -> bool:
        """Invalidate analysis cache for content or user."""
        try:
            client = self.client
            logger.info("cache_invalidate_analysis_start", extra={"content_id": content_id, "user_id": user_id})
            if hasattr(client, 'invalidate_analysis_cache'):
                client.invalidate_analysis_cache(content_id=content_id, user_id=user_id)
            return True
        except Exception as e:
            logger.error("cache_invalidate_analysis_failed", extra={"content_id": content_id, "user_id": user_id, "error": str(e)})
            return False

    def invalidate_all_cache(self, confirm: bool = False) -> bool:
        """Safety-guarded function to invalidate all application cache requiring explicit confirm=True."""
        if not confirm:
            logger.error("cache_invalidate_all_blocked_missing_confirmation")
            return False

        try:
            client = self.client
            logger.info("cache_invalidate_all_start")
            if hasattr(client, 'invalidate_all_recommendations'):
                client.invalidate_all_recommendations()
            if hasattr(client, 'invalidate_query_cache'):
                client.invalidate_query_cache("bookmarks:*")
            if hasattr(client, 'invalidate_analysis_cache'):
                client.invalidate_analysis_cache()
            logger.info("cache_invalidate_all_success")
            return True
        except Exception as e:
            logger.error("cache_invalidate_all_failed", extra={"error": str(e)})
            return False

    def after_content_save(self, content_id: int, user_id: int) -> bool:
        """Hook called after content is saved. Runs in the background -- see
        _dispatch_async's docstring-equivalent comment above for why."""
        logger.info("cache_invalidation_hook_content_saved", extra={"content_id": content_id, "user_id": user_id})
        _dispatch_async("after_content_save", self._invalidate_content_and_user, content_id, user_id)
        return True

    def after_content_update(self, content_id: int, user_id: int) -> bool:
        """Hook called after content is updated (async, see after_content_save)."""
        logger.info("cache_invalidation_hook_content_updated", extra={"content_id": content_id, "user_id": user_id})
        _dispatch_async("after_content_update", self._invalidate_content_and_user, content_id, user_id)
        return True

    def after_content_delete(self, content_id: int, user_id: int) -> bool:
        """Hook called after content is deleted (async, see after_content_save)."""
        logger.info("cache_invalidation_hook_content_deleted", extra={"content_id": content_id, "user_id": user_id})
        _dispatch_async("after_content_delete", self._invalidate_content_and_user, content_id, user_id)
        return True

    def _invalidate_content_and_user(self, content_id: int, user_id: int) -> None:
        self.invalidate_content_cache(content_id)
        self.invalidate_user_cache(user_id)

    def after_project_save(self, project_id: int, user_id: int) -> bool:
        """Hook called after project is saved (async, see after_content_save)."""
        logger.info("cache_invalidation_hook_project_saved", extra={"project_id": project_id, "user_id": user_id})
        _dispatch_async("after_project_save", self._invalidate_project_and_user, project_id, user_id)
        return True

    def after_project_update(self, project_id: int, user_id: int) -> bool:
        """Hook called after project is updated (async, see after_content_save)."""
        logger.info("cache_invalidation_hook_project_updated", extra={"project_id": project_id, "user_id": user_id})
        _dispatch_async("after_project_update", self._invalidate_project_and_user, project_id, user_id)
        return True

    def _invalidate_project_and_user(self, project_id: int, user_id: int) -> None:
        self.invalidate_project_cache(project_id)
        self.invalidate_user_cache(user_id)

    def after_task_save(self, task_id: int, user_id: int) -> bool:
        """Hook called after task is saved (async, see after_content_save)."""
        logger.info("cache_invalidation_hook_task_saved", extra={"task_id": task_id, "user_id": user_id})

        def _run():
            self.invalidate_task_cache(task_id)
            self.invalidate_user_cache(user_id)

        _dispatch_async("after_task_save", _run)
        return True

    def after_user_profile_update(self, user_id: int) -> bool:
        """Hook called after user profile is updated (async, see after_content_save)."""
        logger.info("cache_invalidation_hook_profile_updated", extra={"user_id": user_id})
        _dispatch_async("after_user_profile_update", self.invalidate_user_cache, user_id)
        return True

    def after_analysis_complete(self, content_id: int, user_id: int) -> bool:
        """Hook called after content analysis is completed (async, see after_content_save)."""
        logger.info("cache_invalidation_hook_analysis_complete", extra={"content_id": content_id, "user_id": user_id})
        _dispatch_async("after_analysis_complete", self._invalidate_content_and_user, content_id, user_id)
        return True


# Global singleton instance for easy access
cache_invalidator = CacheInvalidationService()