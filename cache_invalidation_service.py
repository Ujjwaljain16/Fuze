#!/usr/bin/env python3
"""
Cache Invalidation Service
Provides comprehensive cache invalidation hooks for the Fuze recommendation system
"""

import logging
from typing import Optional, List
from redis_utils import redis_cache

logger = logging.getLogger(__name__)

class CacheInvalidationService:
    """Service for managing cache invalidation across the application"""
    
    @staticmethod
    def invalidate_content_cache(content_id: int) -> bool:
        """Invalidate all cache related to a specific content item"""
        try:
            logger.info(f"Invalidating cache for content {content_id}")
            
            # Invalidate content-specific cache
            redis_cache.invalidate_content_cache(content_id)
            
            # Invalidate analysis cache
            redis_cache.invalidate_analysis_cache(content_id=content_id)
            
            # Invalidate embedding cache for this content
            redis_cache.delete_keys_pattern(f"*embedding:*content_{content_id}*")
            
            logger.info(f"Successfully invalidated cache for content {content_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating content cache for {content_id}: {e}")
            return False
    
    @staticmethod
    def invalidate_user_cache(user_id: int) -> bool:
        """Invalidate all cache related to a specific user"""
        try:
            logger.info(f"Invalidating cache for user {user_id}")
            
            # Invalidate user bookmarks
            redis_cache.invalidate_user_bookmarks(user_id)
            
            # Invalidate user recommendations
            redis_cache.invalidate_user_recommendations(user_id)
            
            # Invalidate user analysis cache
            redis_cache.invalidate_analysis_cache(user_id=user_id)
            
            # Invalidate user profile cache
            redis_cache.delete_keys_pattern(f"*user_profile:{user_id}*")
            redis_cache.delete_keys_pattern(f"*user_context:{user_id}*")
            
            logger.info(f"Successfully invalidated cache for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating user cache for {user_id}: {e}")
            return False
    
    @staticmethod
    def invalidate_project_cache(project_id: int) -> bool:
        """Invalidate all cache related to a specific project"""
        try:
            logger.info(f"Invalidating cache for project {project_id}")
            
            # Invalidate project-specific cache
            redis_cache.invalidate_project_cache(project_id)
            
            # Invalidate project analysis cache
            redis_cache.delete_keys_pattern(f"*project_analysis:{project_id}*")
            
            # Invalidate project embedding cache
            redis_cache.delete_keys_pattern(f"*project_embedding:{project_id}*")
            
            logger.info(f"Successfully invalidated cache for project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating project cache for {project_id}: {e}")
            return False
    
    @staticmethod
    def invalidate_task_cache(task_id: int) -> bool:
        """Invalidate all cache related to a specific task"""
        try:
            logger.info(f"Invalidating cache for task {task_id}")
            
            # Invalidate task-specific cache
            redis_cache.delete_keys_pattern(f"*task_analysis:{task_id}*")
            redis_cache.delete_keys_pattern(f"*task_recommendations:*{task_id}*")
            redis_cache.delete_keys_pattern(f"*task_embedding:{task_id}*")
            
            logger.info(f"Successfully invalidated cache for task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating task cache for {task_id}: {e}")
            return False
    
    @staticmethod
    def invalidate_recommendation_cache(user_id: Optional[int] = None) -> bool:
        """Invalidate recommendation cache for a user or all users"""
        try:
            if user_id:
                logger.info(f"Invalidating recommendation cache for user {user_id}")
                redis_cache.invalidate_user_recommendations(user_id)
                # Also invalidate unified recommendation cache
                redis_cache.delete_keys_pattern(f"*unified_recommendations:*{user_id}*")
                redis_cache.delete_keys_pattern(f"*unified_project_recommendations:*{user_id}*")
                redis_cache.delete_keys_pattern(f"*context_extraction:*")
            else:
                logger.info("Invalidating all recommendation cache")
                redis_cache.invalidate_all_recommendations()
                # Also invalidate all unified recommendation cache
                redis_cache.delete_keys_pattern("*unified_recommendations:*")
                redis_cache.delete_keys_pattern("*unified_project_recommendations:*")
                redis_cache.delete_keys_pattern("*context_extraction:*")
            
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating recommendation cache: {e}")
            return False
    
    @staticmethod
    def invalidate_analysis_cache(content_id: Optional[int] = None, user_id: Optional[int] = None) -> bool:
        """Invalidate analysis cache for content or user"""
        try:
            logger.info(f"Invalidating analysis cache - content_id: {content_id}, user_id: {user_id}")
            redis_cache.invalidate_analysis_cache(content_id=content_id, user_id=user_id)
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating analysis cache: {e}")
            return False
    
    @staticmethod
    def invalidate_embedding_cache(content_id: Optional[int] = None) -> bool:
        """Invalidate embedding cache for content or all content"""
        try:
            if content_id:
                logger.info(f"Invalidating embedding cache for content {content_id}")
                redis_cache.delete_keys_pattern(f"*embedding:*content_{content_id}*")
            else:
                logger.info("Invalidating all embedding cache")
                redis_cache.delete_keys_pattern("*embedding:*")
            
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating embedding cache: {e}")
            return False
    
    @staticmethod
    def invalidate_all_cache() -> bool:
        """Invalidate all application cache"""
        try:
            logger.info("Invalidating all application cache")
            
            # Invalidate all recommendation cache
            redis_cache.invalidate_all_recommendations()
            
            # Invalidate all analysis cache
            redis_cache.invalidate_analysis_cache()
            
            # Invalidate all embedding cache
            redis_cache.delete_keys_pattern("*embedding:*")
            
            # Invalidate all content cache
            redis_cache.delete_keys_pattern("*content_analysis:*")
            redis_cache.delete_keys_pattern("*content_embedding:*")
            
            # Invalidate all project cache
            redis_cache.delete_keys_pattern("*project_analysis:*")
            redis_cache.delete_keys_pattern("*project_embedding:*")
            
            # Invalidate all task cache
            redis_cache.delete_keys_pattern("*task_analysis:*")
            redis_cache.delete_keys_pattern("*task_embedding:*")
            
            # Invalidate all user cache
            redis_cache.delete_keys_pattern("*user_profile:*")
            redis_cache.delete_keys_pattern("*user_context:*")
            redis_cache.delete_keys_pattern("*user_bookmarks:*")
            
            # Invalidate all unified recommendation cache
            redis_cache.delete_keys_pattern("*unified_recommendations:*")
            redis_cache.delete_keys_pattern("*unified_project_recommendations:*")
            redis_cache.delete_keys_pattern("*context_extraction:*")
            
            logger.info("Successfully invalidated all application cache")
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating all cache: {e}")
            return False
    
    @staticmethod
    def after_content_save(content_id: int, user_id: int) -> bool:
        """Hook to be called after content is saved"""
        try:
            logger.info(f"Cache invalidation hook: content saved - content_id: {content_id}, user_id: {user_id}")
            
            # Invalidate content-specific cache
            CacheInvalidationService.invalidate_content_cache(content_id)
            
            # Invalidate user recommendations (new content affects recommendations)
            CacheInvalidationService.invalidate_user_cache(user_id)
            
            # Invalidate embedding cache for this content
            CacheInvalidationService.invalidate_embedding_cache(content_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in after_content_save hook: {e}")
            return False
    
    @staticmethod
    def after_content_update(content_id: int, user_id: int) -> bool:
        """Hook to be called after content is updated"""
        try:
            logger.info(f"Cache invalidation hook: content updated - content_id: {content_id}, user_id: {user_id}")
            
            # Invalidate content-specific cache
            CacheInvalidationService.invalidate_content_cache(content_id)
            
            # Invalidate user recommendations (updated content affects recommendations)
            CacheInvalidationService.invalidate_user_cache(user_id)
            
            # Invalidate analysis cache for this content
            CacheInvalidationService.invalidate_analysis_cache(content_id=content_id)
            
            # Invalidate embedding cache for this content
            CacheInvalidationService.invalidate_embedding_cache(content_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in after_content_update hook: {e}")
            return False
    
    @staticmethod
    def after_content_delete(content_id: int, user_id: int) -> bool:
        """Hook to be called after content is deleted"""
        try:
            logger.info(f"Cache invalidation hook: content deleted - content_id: {content_id}, user_id: {user_id}")
            
            # Invalidate content-specific cache
            CacheInvalidationService.invalidate_content_cache(content_id)
            
            # Invalidate user recommendations (deleted content affects recommendations)
            CacheInvalidationService.invalidate_user_cache(user_id)
            
            # Invalidate embedding cache for this content
            CacheInvalidationService.invalidate_embedding_cache(content_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in after_content_delete hook: {e}")
            return False
    
    @staticmethod
    def after_project_save(project_id: int, user_id: int) -> bool:
        """Hook to be called after project is saved"""
        try:
            logger.info(f"Cache invalidation hook: project saved - project_id: {project_id}, user_id: {user_id}")
            
            # Invalidate project-specific cache
            CacheInvalidationService.invalidate_project_cache(project_id)
            
            # Invalidate user recommendations (new project affects recommendations)
            CacheInvalidationService.invalidate_user_cache(user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in after_project_save hook: {e}")
            return False
    
    @staticmethod
    def after_project_update(project_id: int, user_id: int) -> bool:
        """Hook to be called after project is updated"""
        try:
            logger.info(f"Cache invalidation hook: project updated - project_id: {project_id}, user_id: {user_id}")
            
            # Invalidate project-specific cache
            CacheInvalidationService.invalidate_project_cache(project_id)
            
            # Invalidate user recommendations (updated project affects recommendations)
            CacheInvalidationService.invalidate_user_cache(user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in after_project_update hook: {e}")
            return False
    
    @staticmethod
    def after_task_save(task_id: int, user_id: int) -> bool:
        """Hook to be called after task is saved"""
        try:
            logger.info(f"Cache invalidation hook: task saved - task_id: {task_id}, user_id: {user_id}")
            
            # Invalidate task-specific cache
            CacheInvalidationService.invalidate_task_cache(task_id)
            
            # Invalidate user recommendations (new task affects recommendations)
            CacheInvalidationService.invalidate_user_cache(user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in after_task_save hook: {e}")
            return False
    
    @staticmethod
    def after_user_profile_update(user_id: int) -> bool:
        """Hook to be called after user profile is updated"""
        try:
            logger.info(f"Cache invalidation hook: user profile updated - user_id: {user_id}")
            
            # Invalidate user cache (profile changes affect recommendations)
            CacheInvalidationService.invalidate_user_cache(user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in after_user_profile_update hook: {e}")
            return False
    
    @staticmethod
    def after_analysis_complete(content_id: int, user_id: int) -> bool:
        """Hook to be called after content analysis is completed"""
        try:
            logger.info(f"Cache invalidation hook: analysis completed - content_id: {content_id}, user_id: {user_id}")
            
            # Invalidate content-specific cache (new analysis data)
            CacheInvalidationService.invalidate_content_cache(content_id)
            
            # Invalidate user recommendations (new analysis affects recommendations)
            CacheInvalidationService.invalidate_user_cache(user_id)
            
            # Invalidate analysis cache for this content
            CacheInvalidationService.invalidate_analysis_cache(content_id=content_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in after_analysis_complete hook: {e}")
            return False

# Global instance for easy access
cache_invalidator = CacheInvalidationService() 