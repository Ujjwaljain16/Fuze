"""
background/embed_worker.py
==========================
RQ job functions for asynchronous embedding generation.

Jobs:
  embed_bookmark_job(bookmark_id)   — generate and store embedding for one bookmark
  embed_project_job(project_id)     — generate and store embedding for one project

Design principles:
  - Idempotent: checks embedding IS NULL before generating (safe to retry)
  - Isolated: each job opens its own UnitOfWork (no shared session state)
  - Gated: respects the ASYNC_EMBEDDINGS / 'async_embeddings' feature flag
  - No side effects on failure: raises so RQ retry logic fires correctly

Retry policy (configured in task_queue.enqueue_embedding_job):
  max=3, interval=[60, 300, 900] — 1min, 5min, 15min backoff
"""

import time
import logging
from typing import Optional

from core.logging_config import get_logger

logger = get_logger(__name__)

EXPECTED_EMBEDDING_DIM = 384


def embed_bookmark_job(bookmark_id: int) -> dict:
    """
    RQ job: generate embedding for a single bookmark and persist it.

    Idempotent — if embedding already exists, returns early without re-generating.
    Raises on unrecoverable failure so RQ retry fires.
    """
    from uow.unit_of_work import UnitOfWork
    from services.bookmark_processing_service import (
        generate_comprehensive_embedding,
        validate_embedding,
    )

    logger.info("embed_bookmark_job_started", extra={"bookmark_id": bookmark_id})
    start = time.time()

    try:
        # Fetch bookmark — verify existence and check if embedding needed
        with UnitOfWork() as uow:
            bookmark = uow.bookmarks.get_by_id(bookmark_id)
            if not bookmark:
                logger.warning("embed_bookmark_job_not_found", extra={"bookmark_id": bookmark_id})
                return {"status": "not_found", "bookmark_id": bookmark_id}

            # Idempotency guard: skip if already embedded
            existing_embedding = getattr(bookmark, "embedding", None)
            if existing_embedding is not None:
                logger.info(
                    "embed_bookmark_job_already_embedded",
                    extra={"bookmark_id": bookmark_id},
                )
                return {"status": "already_embedded", "bookmark_id": bookmark_id}

            # Snapshot fields we need outside the UoW
            title = getattr(bookmark, "title", "") or ""
            notes = getattr(bookmark, "notes", "") or ""
            meta_description = getattr(bookmark, "meta_description", "") or ""
            headings_raw = getattr(bookmark, "headings", None)
            extracted_text = getattr(bookmark, "extracted_text", "") or ""

        headings = headings_raw if isinstance(headings_raw, list) else []

        # Generate embedding outside any transaction (heavy ML inference)
        from core.metrics import embedding_generation_duration
        
        embed_start = time.time()
        embedding = generate_comprehensive_embedding(
            title=title,
            description=notes,
            meta_description=meta_description,
            headings=headings,
            extracted_text=extracted_text,
        )
        
        try:
            embedding_generation_duration.observe(time.time() - embed_start)
        except Exception:
            pass

        if not validate_embedding(embedding, EXPECTED_EMBEDDING_DIM):
            logger.error(
                "embed_bookmark_job_invalid_embedding",
                extra={"bookmark_id": bookmark_id, "embedding_type": type(embedding).__name__},
            )
            raise ValueError(f"Invalid embedding generated for bookmark {bookmark_id}")

        # Persist embedding
        with UnitOfWork() as uow:
            bookmark = uow.bookmarks.get_by_id(bookmark_id)
            if not bookmark:
                logger.warning(
                    "embed_bookmark_job_deleted_during_generation",
                    extra={"bookmark_id": bookmark_id},
                )
                return {"status": "deleted_during_generation", "bookmark_id": bookmark_id}

            bookmark.embedding = embedding

        # Invalidate caches that may have stale representation
        try:
            from services.cache_invalidation_service import cache_invalidator
            user_id = getattr(bookmark, "user_id", None)
            if user_id:
                cache_invalidator.after_content_update(bookmark_id, user_id)
        except Exception as cache_err:
            logger.warning(
                "embed_bookmark_job_cache_invalidation_warning",
                extra={"bookmark_id": bookmark_id, "error": str(cache_err)},
            )

        elapsed_ms = (time.time() - start) * 1000
        logger.info(
            "embed_bookmark_job_completed",
            extra={"bookmark_id": bookmark_id, "elapsed_ms": round(elapsed_ms, 1)},
        )
        return {"status": "ok", "bookmark_id": bookmark_id, "elapsed_ms": round(elapsed_ms, 1)}

    except Exception:
        logger.exception("embed_bookmark_job_failed", extra={"bookmark_id": bookmark_id})
        raise  # Let RQ retry


def embed_project_job(project_id: int) -> dict:
    """
    RQ job: generate embedding for a single project and persist it.
    Idempotent — skips if embedding already exists.
    """
    from uow.unit_of_work import UnitOfWork
    from utils.embedding_utils import get_embedding

    logger.info("embed_project_job_started", extra={"project_id": project_id})
    start = time.time()

    try:
        with UnitOfWork() as uow:
            project = uow.projects.get_by_id(project_id)
            if not project:
                logger.warning("embed_project_job_not_found", extra={"project_id": project_id})
                return {"status": "not_found", "project_id": project_id}

            if getattr(project, "embedding", None) is not None:
                return {"status": "already_embedded", "project_id": project_id}

            title = getattr(project, "title", "") or ""
            description = getattr(project, "description", "") or ""
            technologies = getattr(project, "technologies", "") or ""

        text_to_embed = f"{title} | {description} | {technologies}".strip()
        embedding = get_embedding(text_to_embed)

        if embedding is None or len(embedding) != EXPECTED_EMBEDDING_DIM:
            raise ValueError(f"Invalid embedding for project {project_id}")

        with UnitOfWork() as uow:
            project = uow.projects.get_by_id(project_id)
            if project:
                project.embedding = embedding

        elapsed_ms = (time.time() - start) * 1000
        logger.info(
            "embed_project_job_completed",
            extra={"project_id": project_id, "elapsed_ms": round(elapsed_ms, 1)},
        )
        return {"status": "ok", "project_id": project_id, "elapsed_ms": round(elapsed_ms, 1)}

    except Exception:
        logger.exception("embed_project_job_failed", extra={"project_id": project_id})
        raise
