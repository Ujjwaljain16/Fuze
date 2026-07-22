"""
Cache Invalidation Service for Fuze Architecture
Provides comprehensive cache invalidation hooks for the Fuze recommendation system.
Ensures recommendations reflect the latest content, project, and task data.
"""

import sys
import os
from typing import Optional

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from utils.redis_utils import redis_cache
from core.logging_config import get_logger

logger = get_logger(__name__)


class CacheInvalidationService:
    """Service for managing cache invalidation across the application"""

    @staticmethod
    def invalidate_content_cache(content_id: int) -> bool:
        """Invalidate all cache related to a specific content item"""
        try:
            logger.info("cache_invalidate_content_start", content_id=content_id)

            # Invalidate content-specific cache
            redis_cache.invalidate_content_cache(content_id)

            # Invalidate analysis cache for this content
            redis_cache.invalidate_analysis_cache(content_id=content_id)

            # Invalidate embedding cache for this content
            redis_cache.delete_keys_pattern(f"*embedding:*content_{content_id}*")

            logger.info("cache_invalidate_content_success", content_id=content_id)
            return True

        except Exception as e:
            logger.error("cache_invalidate_content_failed", content_id=content_id, error=str(e))
            return False

    @staticmethod
    def invalidate_user_cache(user_id: int) -> bool:
        """Invalidate all cache related to a specific user"""
        try:
            logger.info("cache_invalidate_user_start", user_id=user_id)

            # Invalidate user bookmarks
            redis_cache.invalidate_user_bookmarks(user_id)

            # Invalidate user recommendations
            redis_cache.invalidate_recommendation_cache(user_id)

            # Invalidate user context cache
            redis_cache.delete_keys_pattern(f"*user_context:{user_id}*")
            redis_cache.delete_keys_pattern(f"*unified_recommendations:{user_id}*")
            redis_cache.delete_keys_pattern(f"*unified_project_recommendations:{user_id}*")

            # Invalidate user profile cache
            redis_cache.delete_keys_pattern(f"*user_profile:{user_id}*")

            logger.info("cache_invalidate_user_success", user_id=user_id)
            return True

        except Exception as e:
            logger.error("cache_invalidate_user_failed", user_id=user_id, error=str(e))
            return False

    @staticmethod
    def invalidate_project_cache(project_id: int) -> bool:
        """Invalidate all cache related to a specific project"""
        try:
            logger.info("cache_invalidate_project_start", project_id=project_id)

            # Invalidate project-specific cache
            redis_cache.invalidate_project_cache(project_id)

            # Invalidate project recommendations
            redis_cache.delete_keys_pattern(f"*unified_project_recommendations:*:project_{project_id}*")

            # Invalidate project embedding cache
            redis_cache.delete_keys_pattern(f"*project_embedding:{project_id}*")

            logger.info("cache_invalidate_project_success", project_id=project_id)
            return True

        except Exception as e:
            logger.error("cache_invalidate_project_failed", project_id=project_id, error=str(e))
            return False

    @staticmethod
    def invalidate_task_cache(task_id: int) -> bool:
        """Invalidate all cache related to a specific task"""
        try:
            logger.info("cache_invalidate_task_start", task_id=task_id)

            # Invalidate task-specific cache
            redis_cache.delete_keys_pattern(f"*task_analysis:{task_id}*")
            redis_cache.delete_keys_pattern(f"*task_embedding:{task_id}*")

            logger.info("cache_invalidate_task_success", task_id=task_id)
            return True

        except Exception as e:
            logger.error("cache_invalidate_task_failed", task_id=task_id, error=str(e))
            return False

    @staticmethod
    def invalidate_recommendation_cache(user_id: Optional[int] = None) -> bool:
        """Invalidate recommendation cache for user or all users"""
        try:
            if user_id:
                logger.info("cache_invalidate_rec_user_start", user_id=user_id)
                redis_cache.invalidate_recommendation_cache(user_id)
                redis_cache.delete_keys_pattern(f"*unified_recommendations:{user_id}*")
                redis_cache.delete_keys_pattern(f"*unified_project_recommendations:{user_id}*")
                redis_cache.delete_keys_pattern(f"*context_extraction:{user_id}*")

                try:
                    from models import db, UserFeedback
                    db.session.query(UserFeedback).filter_by(user_id=user_id).delete()
                    db.session.commit()
                    logger.info("cache_clear_db_feedback_success", user_id=user_id)
                except Exception as e:
                    logger.warning("cache_clear_db_feedback_failed", user_id=user_id, error=str(e))

                try:
                    from models import db, SavedContent
                    db.session.query(SavedContent).filter_by(user_id=user_id).update({'intent_analysis': None})
                    db.session.commit()
                    logger.info("cache_clear_db_intent_analysis_success", user_id=user_id)
                except Exception as e:
                    logger.warning("cache_clear_db_intent_analysis_failed", user_id=user_id, error=str(e))
            else:
                logger.info("cache_invalidate_rec_all_start")
                redis_cache.invalidate_all_recommendations()
                redis_cache.delete_keys_pattern("*unified_recommendations:*")
                redis_cache.delete_keys_pattern("*unified_project_recommendations:*")
                redis_cache.delete_keys_pattern("*context_extraction:*")
                redis_cache.delete_keys_pattern("*content_embedding:*")
                redis_cache.delete_keys_pattern("*project_embedding:*")
                redis_cache.delete_keys_pattern("*task_embedding:*")

                try:
                    from models import db, Project
                    db.session.query(Project).update({'intent_analysis': None, 'embedding_metadata': None})
                    db.session.commit()
                    logger.info("cache_clear_db_project_analysis_success")
                except Exception as e:
                    logger.warning("cache_clear_db_project_analysis_failed", error=str(e))

            return True

        except Exception as e:
            logger.error("cache_invalidate_rec_failed", user_id=user_id, error=str(e))
            return False

    @staticmethod
    def invalidate_analysis_cache(content_id: Optional[int] = None, user_id: Optional[int] = None) -> bool:
        """Invalidate analysis cache for content or user"""
        try:
            logger.info("cache_invalidate_analysis_start", content_id=content_id, user_id=user_id)
            redis_cache.invalidate_analysis_cache(content_id=content_id, user_id=user_id)
            return True

        except Exception as e:
            logger.error("cache_invalidate_analysis_failed", content_id=content_id, user_id=user_id, error=str(e))
            return False

    @staticmethod
    def invalidate_embedding_cache(content_id: Optional[int] = None) -> bool:
        """Invalidate embedding cache for content or all content"""
        try:
            if content_id:
                logger.info("cache_invalidate_embedding_content_start", content_id=content_id)
                redis_cache.delete_keys_pattern(f"*embedding:*content_{content_id}*")
            else:
                logger.info("cache_invalidate_embedding_all_start")
                redis_cache.delete_keys_pattern("*embedding:*")

            return True

        except Exception as e:
            logger.error("cache_invalidate_embedding_failed", content_id=content_id, error=str(e))
            return False

    @staticmethod
    def invalidate_all_cache() -> bool:
        """Invalidate all application cache"""
        try:
            logger.info("cache_invalidate_all_start")

            redis_cache.invalidate_all_recommendations()
            redis_cache.invalidate_user_bookmarks(None)

            redis_cache.delete_keys_pattern("*content_cache:*")
            redis_cache.delete_keys_pattern("*user_bookmarks:*")

            redis_cache.invalidate_analysis_cache()
            redis_cache.delete_keys_pattern("*embedding:*")

            redis_cache.delete_keys_pattern("*content_analysis:*")
            redis_cache.delete_keys_pattern("*content_embedding:*")

            redis_cache.delete_keys_pattern("*project_analysis:*")
            redis_cache.delete_keys_pattern("*project_embedding:*")

            redis_cache.delete_keys_pattern("*task_analysis:*")
            redis_cache.delete_keys_pattern("*task_embedding:*")

            redis_cache.delete_keys_pattern("*user_profile:*")
            redis_cache.delete_keys_pattern("*user_context:*")

            redis_cache.delete_keys_pattern("*unified_recommendations:*")
            redis_cache.delete_keys_pattern("*unified_project_recommendations:*")
            redis_cache.delete_keys_pattern("*context_extraction:*")

            logger.info("cache_invalidate_all_success")
            return True

        except Exception as e:
            logger.error("cache_invalidate_all_failed", error=str(e))
            return False

    @staticmethod
    def after_content_save(content_id: int, user_id: int) -> bool:
        """Hook to be called after content is saved"""
        try:
            logger.info("cache_invalidation_hook_content_saved", content_id=content_id, user_id=user_id)

            CacheInvalidationService.invalidate_content_cache(content_id)
            CacheInvalidationService.invalidate_user_cache(user_id)
            CacheInvalidationService.invalidate_embedding_cache(content_id)

            return True

        except Exception as e:
            logger.error("cache_invalidation_hook_content_saved_failed", content_id=content_id, user_id=user_id, error=str(e))
            return False

    @staticmethod
    def after_content_update(content_id: int, user_id: int) -> bool:
        """Hook to be called after content is updated"""
        try:
            logger.info("cache_invalidation_hook_content_updated", content_id=content_id, user_id=user_id)

            CacheInvalidationService.invalidate_content_cache(content_id)
            CacheInvalidationService.invalidate_user_cache(user_id)
            CacheInvalidationService.invalidate_analysis_cache(content_id=content_id)
            CacheInvalidationService.invalidate_embedding_cache(content_id)

            return True

        except Exception as e:
            logger.error("cache_invalidation_hook_content_updated_failed", content_id=content_id, user_id=user_id, error=str(e))
            return False

    @staticmethod
    def after_content_delete(content_id: int, user_id: int) -> bool:
        """Hook to be called after content is deleted"""
        try:
            logger.info("cache_invalidation_hook_content_deleted", content_id=content_id, user_id=user_id)

            CacheInvalidationService.invalidate_content_cache(content_id)
            CacheInvalidationService.invalidate_user_cache(user_id)
            CacheInvalidationService.invalidate_embedding_cache(content_id)

            return True

        except Exception as e:
            logger.error("cache_invalidation_hook_content_deleted_failed", content_id=content_id, user_id=user_id, error=str(e))
            return False

    @staticmethod
    def after_project_save(project_id: int, user_id: int) -> bool:
        """Hook to be called after project is saved"""
        try:
            logger.info("cache_invalidation_hook_project_saved", project_id=project_id, user_id=user_id)

            CacheInvalidationService.invalidate_project_cache(project_id)
            CacheInvalidationService.invalidate_user_cache(user_id)

            return True

        except Exception as e:
            logger.error("cache_invalidation_hook_project_saved_failed", project_id=project_id, user_id=user_id, error=str(e))
            return False

    @staticmethod
    def after_project_update(project_id: int, user_id: int) -> bool:
        """Hook to be called after project is updated"""
        try:
            logger.info("cache_invalidation_hook_project_updated", project_id=project_id, user_id=user_id)

            CacheInvalidationService.invalidate_project_cache(project_id)
            CacheInvalidationService.invalidate_user_cache(user_id)

            return True

        except Exception as e:
            logger.error("cache_invalidation_hook_project_updated_failed", project_id=project_id, user_id=user_id, error=str(e))
            return False

    @staticmethod
    def after_task_save(task_id: int, user_id: int) -> bool:
        """Hook to be called after task is saved"""
        try:
            logger.info("cache_invalidation_hook_task_saved", task_id=task_id, user_id=user_id)

            CacheInvalidationService.invalidate_task_cache(task_id)
            CacheInvalidationService.invalidate_user_cache(user_id)

            return True

        except Exception as e:
            logger.error("cache_invalidation_hook_task_saved_failed", task_id=task_id, user_id=user_id, error=str(e))
            return False

    @staticmethod
    def after_user_profile_update(user_id: int) -> bool:
        """Hook to be called after user profile is updated"""
        try:
            logger.info("cache_invalidation_hook_profile_updated", user_id=user_id)

            CacheInvalidationService.invalidate_user_cache(user_id)

            return True

        except Exception as e:
            logger.error("cache_invalidation_hook_profile_updated_failed", user_id=user_id, error=str(e))
            return False

    @staticmethod
    def after_analysis_complete(content_id: int, user_id: int) -> bool:
        """Hook to be called after content analysis is completed"""
        try:
            logger.info("cache_invalidation_hook_analysis_complete", content_id=content_id, user_id=user_id)

            CacheInvalidationService.invalidate_content_cache(content_id)
            CacheInvalidationService.invalidate_user_cache(user_id)
            CacheInvalidationService.invalidate_analysis_cache(content_id=content_id)

            return True

        except Exception as e:
            logger.error("cache_invalidation_hook_analysis_complete_failed", content_id=content_id, user_id=user_id, error=str(e))
            return False


# Global instance for easy access
cache_invalidator = CacheInvalidationService()