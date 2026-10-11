from typing import Optional
from uow.unit_of_work import UnitOfWork
from core.logging_config import get_logger

logger = get_logger(__name__)


def process_project_ml(project_id: int, user_id: int, title: Optional[str] = None, description: Optional[str] = None, technologies: Optional[str] = None):
    """
    Background job run when a project is created or edited: precompute its intent statement.
    Reads the project from the database (not the job payload) to avoid stale-payload races.
    """
    logger.info("project_ml_job_started", extra={"project_id": project_id, "user_id": user_id})

    with UnitOfWork() as uow:
        project = uow.projects.get_by_id(project_id, user_id)
        if not project:
            logger.warning("project_ml_job_project_not_found", extra={"project_id": project_id, "user_id": user_id})
            return

        # Precompute the project's intent statement so recommendations have it on first open.
        try:
            from ml.intent_engine.intent import compute_intent_job, load_context, resolve_intent
            intent = resolve_intent(load_context(uow.session, user_id, project_id=project_id), schedule=False)
            if intent.text and not intent.statement:
                ok = compute_intent_job(intent.hash, intent.text, user_id)
                logger.info("project_intent_precomputed", extra={"project_id": project_id, "ok": ok})
        except Exception:
            logger.exception("project_intent_analysis_failed", extra={"project_id": project_id, "user_id": user_id})
