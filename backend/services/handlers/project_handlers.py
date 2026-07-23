from core.events import ProjectCreated, ProjectUpdated, ProjectDeleted
from core.logging_config import get_logger

logger = get_logger(__name__)

def handle_project_created(event: ProjectCreated):
    """
    Handler for ProjectCreated.
    Invalidates project and user caches.
    """
    logger.info(
        "project_created_event_received",
        project_id=event.project_id,
        user_id=event.user_id
    )
    
    try:
        from services.cache_invalidation_service import cache_invalidator
        cache_invalidator.after_project_save(event.project_id, event.user_id)
        
        from services.task_queue import enqueue_project_ml_job
        enqueue_project_ml_job(
            project_id=event.project_id,
            user_id=event.user_id,
            title=event.title,
            description=event.description,
            technologies=event.technologies
        )
    except Exception as e:
        logger.exception(
            "project_cache_invalidation_failed",
            project_id=event.project_id,
            error=str(e)
        )

def handle_project_updated(event: ProjectUpdated):
    """
    Handler for ProjectUpdated.
    Invalidates project and user caches.
    """
    logger.info(
        "project_updated_event_received",
        project_id=event.project_id,
        user_id=event.user_id
    )
    
    try:
        from services.cache_invalidation_service import cache_invalidator
        cache_invalidator.after_project_update(event.project_id, event.user_id)
        
        from services.task_queue import enqueue_project_ml_job
        enqueue_project_ml_job(
            project_id=event.project_id,
            user_id=event.user_id,
            title=event.title,
            description=event.description,
            technologies=event.technologies
        )
    except Exception as e:
        logger.exception(
            "project_cache_invalidation_failed",
            project_id=event.project_id,
            error=str(e)
        )

def handle_project_deleted(event: ProjectDeleted):
    """
    Handler for ProjectDeleted.
    Invalidates project and user caches.
    """
    logger.info(
        "project_deleted_event_received",
        project_id=event.project_id,
        user_id=event.user_id
    )
    
    try:
        from services.cache_invalidation_service import cache_invalidator
        cache_invalidator.invalidate_project_cache(event.project_id)
        cache_invalidator.invalidate_user_cache(event.user_id)
    except Exception as e:
        logger.exception(
            "project_cache_invalidation_failed",
            project_id=event.project_id,
            error=str(e)
        )


# Explicit domain handler registry — consumed by services/handlers/__init__.py
HANDLERS = {
    ProjectCreated: [handle_project_created],
    ProjectUpdated: [handle_project_updated],
    ProjectDeleted: [handle_project_deleted],
}
