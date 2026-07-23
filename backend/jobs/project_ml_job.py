import logging
from uow.unit_of_work import UnitOfWork
from utils.embedding_utils import get_project_embedding
from ml.intent_analysis_engine import analyze_user_intent
import numpy as np

logger = logging.getLogger(__name__)

def process_project_ml(project_id: int, user_id: int, title: str, description: str, technologies: str):
    """
    Background job to generate embeddings and analyze user intent for a project.
    """
    logger.info(f"Starting background ML processing for project: {title} (ID: {project_id})")

    # 1. Generate/Refresh Embedding
    try:
        with UnitOfWork() as uow:
            project = uow.projects.get_by_id(project_id, user_id)
            if not project:
                logger.warning(f"process_project_ml: Project {project_id} not found.")
                return

            embedding = get_project_embedding(project)
            
            if embedding is not None:
                project.embedding = embedding
                uow.projects.update(project)
                
                # Check if it's not a zero vector (fallback case)
                try:
                    is_zero_vector = isinstance(project.embedding, np.ndarray) and np.all(project.embedding == 0)
                except:
                    is_zero_vector = isinstance(project.embedding, (list, tuple)) and all(x == 0.0 for x in project.embedding)

                if not is_zero_vector:
                    logger.info(f"Generated and saved embedding for project: {title}")
                else:
                    logger.warning(f"Generated zero vector embedding for project: {title}")
    except Exception as embedding_error:
        logger.warning(f"Embedding generation failed for project: {str(embedding_error)}")
        logger.warning(f"Error details: {repr(embedding_error)}")

    # 2. Trigger/Refresh Intent Analysis
    try:
        # Build user input from project data
        user_input = f"{title} {description} {technologies}"

        # Generate intent analysis
        # force_analysis=True bypasses the local engine cache to always regenerate
        intent = analyze_user_intent(
            user_input=user_input,
            project_id=project_id,
            force_analysis=True
        )

        logger.info(f"Intent analysis generated for project: {intent.primary_goal} - {intent.project_type}")
    except Exception as intent_error:
        logger.warning(f"Intent analysis failed for project: {str(intent_error)}")
