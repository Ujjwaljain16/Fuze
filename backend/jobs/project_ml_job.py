import numpy as np
from typing import Optional, Union, List, Tuple
from uow.unit_of_work import UnitOfWork
from utils.embedding_utils import get_project_embedding
from ml.intent_analysis_engine import analyze_user_intent
from core.logging_config import get_logger

logger = get_logger(__name__)

EXPECTED_EMBEDDING_DIM = 384


def is_zero_vector(embedding: Union[np.ndarray, List[float], Tuple[float, ...]]) -> bool:
    """Safely check if an embedding vector is all zeros without broad exceptions."""
    if embedding is None:
        return True
    try:
        if isinstance(embedding, np.ndarray):
            return not np.any(embedding)
        if isinstance(embedding, (list, tuple)):
            return not any(x != 0.0 for x in embedding)
    except (TypeError, ValueError, AttributeError):
        return False
    return False


def validate_embedding(embedding, expected_dim: int = EXPECTED_EMBEDDING_DIM) -> bool:
    """Validate embedding shape and dimensions."""
    if embedding is None:
        return False
    if isinstance(embedding, (list, tuple, np.ndarray)):
        return len(embedding) == expected_dim
    return False


def process_project_ml(project_id: int, user_id: int, title: Optional[str] = None, description: Optional[str] = None, technologies: Optional[str] = None):
    """
    Background job to generate embeddings and analyze user intent for a project.
    Always uses the database as the single source of truth to avoid payload race conditions.
    """
    logger.info("project_ml_job_started", extra={"project_id": project_id, "user_id": user_id})

    with UnitOfWork() as uow:
        project = uow.projects.get_by_id(project_id, user_id)
        if not project:
            logger.warning("project_ml_job_project_not_found", extra={"project_id": project_id, "user_id": user_id})
            return

        # 1. Generate & Validate Project Embedding
        try:
            embedding = get_project_embedding(project)
            if embedding is not None and validate_embedding(embedding):
                project.embedding = embedding
                uow.projects.update(project)

                if not is_zero_vector(embedding):
                    logger.info("project_embedding_saved", extra={"project_id": project_id})
                else:
                    logger.warning("project_embedding_zero_vector", extra={"project_id": project_id})
            else:
                logger.warning("project_embedding_invalid_or_none", extra={"project_id": project_id})
        except Exception:
            logger.exception("project_embedding_generation_failed", extra={"project_id": project_id, "user_id": user_id})

        # 2. Perform Intent Analysis using Fresh DB Fields (Single Source of Truth)
        try:
            user_input = " ".join(filter(None, [project.title, project.description, project.technologies]))

            if user_input.strip():
                # force_analysis=True bypasses the local engine cache to always regenerate
                intent = analyze_user_intent(
                    user_input=user_input,
                    project_id=project_id,
                    force_analysis=True
                )

                if intent:
                    primary_goal = getattr(intent, 'primary_goal', 'unknown')
                    project_type = getattr(intent, 'project_type', 'unknown')
                    logger.info("project_intent_analysis_completed", extra={"project_id": project_id, "primary_goal": primary_goal, "project_type": project_type})
                else:
                    logger.warning("project_intent_analysis_returned_none", extra={"project_id": project_id})
        except Exception:
            logger.exception("project_intent_analysis_failed", extra={"project_id": project_id, "user_id": user_id})
