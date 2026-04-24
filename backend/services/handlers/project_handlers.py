from core.logging_config import get_logger

logger = get_logger(__name__)

def handle_project_created(event: ProjectCreated):
    """
    Handler for ProjectCreated: Generates embeddings and triggers intent analysis.
    IDEMPOTENCY: Overwrites existing analytics if re-run.
    """
    try:
        with UnitOfWork() as u:
            project = u.projects.get_by_id(event.project_id, event.user_id)
            if not project:
                logger.warning("project_handler_missing_project", project_id=event.project_id, user_id=event.user_id)
                return

            # 1. Generate/Refresh Embedding
            try:
                from utils.embedding_utils import get_project_embedding
                embedding = get_project_embedding(project)
                if embedding is not None:
                    project.embedding = embedding
                    logger.debug("project_embedding_success", project_id=event.project_id)
            except Exception as e:
                logger.error("project_embedding_failed", project_id=event.project_id, error=str(e))

            # 2. Trigger/Refresh Intent Analysis
            try:
                from ml.intent_analysis_engine import analyze_user_intent
                user_input = f"{project.title} {project.description} {project.technologies}"
                analyze_user_intent(user_input=user_input, project_id=project.id, force_analysis=True)
                logger.debug("project_intent_analysis_success", project_id=event.project_id)
            except Exception as e:
                logger.error("project_intent_analysis_failed", project_id=event.project_id, error=str(e))
            
            # 3. Cache Invalidation
            _safe_invalidate_cache(event.project_id, event.user_id)
            
    except Exception as e:
        logger.error("project_handler_exception", project_id=event.project_id, error=str(e))

def handle_project_updated(event: ProjectUpdated):
    """
    Handler for ProjectUpdated: Refreshes assets if relevant fields changed.
    """
    # For now, we refresh everything any time the update event is fired
    # In Phase 3 we can optimize by checking event.title_changed etc.
    handle_project_created(event) 

def handle_project_deleted(event: ProjectDeleted):
    """
    Handler for ProjectDeleted: Cleans up cache.
    """
    _safe_invalidate_cache(event.project_id, event.user_id)

def _safe_invalidate_cache(project_id: int, user_id: int):
    try:
        from services.cache_invalidation_service import cache_invalidator
        cache_invalidator.after_project_save(project_id, user_id)
        logger.debug("project_cache_invalidation_success", project_id=project_id, user_id=user_id)
    except Exception as e:
        logger.warning("project_cache_invalidation_failed", project_id=project_id, error=str(e))

# Explicit Handler Registry
HANDLERS = {
    ProjectCreated: [handle_project_created],
    ProjectUpdated: [handle_project_updated],
    ProjectDeleted: [handle_project_deleted],
}
