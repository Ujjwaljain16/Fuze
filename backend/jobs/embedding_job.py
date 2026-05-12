import sys
import os

from rq import get_current_job
from core.logging_config import get_logger
from uow.unit_of_work import UnitOfWork
from utils.embedding_utils import get_embedding, get_embedding_artifact
from dataclasses import asdict
from models import db

logger = get_logger(__name__)

def embed_content_job(content_id: str, text_content: str, user_id: str):
    """
    RQ job: compute and store embedding for a saved content item.
    
    Called immediately after bookmark save via RQ queue.
    Non-blocking for the HTTP request — user gets 201 immediately,
    embedding appears in DB within seconds.
    
    Idempotent: if embedding already exists, skips computation.
    Safe to retry: embedding same text always produces same vector.
    """
    job = get_current_job()
    logger.info(
        "embed_job_started",
        content_id=content_id,
        user_id=user_id,
        job_id=job.id if job else None,
    )
    
    try:
        # Import app and push context inside the job
        try:
            from run_production import app
        except ImportError:
            from run import app
            
        with app.app_context():
            with UnitOfWork(db.session) as uow:
                content = uow.bookmarks.get_by_id(content_id)
                
                if content is None:
                    logger.warning("embed_job_content_not_found", content_id=content_id)
                    return
                
                # Idempotency check — skip if already embedded
                if content.embedding is not None:
                    logger.info("embed_job_skipped_already_exists", content_id=content_id)
                    return
                
                # Compute embedding — this is the only slow part (~50-200ms)
                # The user passed text_content from the route if it's there
                # But we can also build it from content itself using the logic in bookmarks.py
                text_to_embed = _build_embed_text(content)
                if not text_to_embed:
                    text_to_embed = text_content or "unknown content"
                
                try:
                    # using the existing get_embedding helper instead of embed_async
                    artifact = get_embedding_artifact(text_to_embed)
                except Exception as e:
                    logger.error(
                        "embed_job_model_failed",
                        content_id=content_id,
                        error=str(e),
                    )
                    raise  # RQ will retry based on job config
                
                if artifact is not None:
                    # Store embedding — atomic with the UoW
                    content.embedding = artifact.vector
                    content.embedding_metadata = asdict(artifact)
                    uow.bookmarks.add(content)
                    logger.info("embed_job_complete", content_id=content_id)
                else:
                    logger.warning("embed_job_produced_none", content_id=content_id)

    except Exception as e:
        logger.error("embed_job_failed_fatal", content_id=content_id, error=str(e))
        raise

def _build_embed_text(content) -> str:
    """
    Build the text to embed from a SavedContent record.
    Combines title + notes + extracted_text for rich semantic representation.
    """
    parts = []
    if content.title:
        parts.append(content.title)
    if content.notes:
        parts.append(content.notes)
    if content.extracted_text:
        # Truncate extracted text
        parts.append(content.extracted_text[:300])
    
    combined = ' '.join(parts)
    return combined[:2048]

def backfill_missing_embeddings(user_id: str = None, batch_size: int = 50):
    """
    Backfill job: embed all content that has no embedding yet.
    Run once after deploy to catch existing bookmarks.
    """
    try:
        from run_production import app
    except ImportError:
        from run import app
        
    with app.app_context():
        with UnitOfWork(db.session) as uow:
            items = uow.bookmarks.get_unembedded(
                user_id=user_id,
                limit=batch_size,
            )
            for item in items:
                text = _build_embed_text(item)
                artifact = get_embedding_artifact(text)
                if artifact is not None:
                    item.embedding = artifact.vector
                    item.embedding_metadata = asdict(artifact)
                    uow.bookmarks.add(item)
        
        logger.info(
            "backfill_complete",
            count=len(items),
            user_id=user_id or "all",
        )
