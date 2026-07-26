"""
Bookmark Processing Service
Handles asynchronous worker task execution for bookmark content acquisition, embedding, and analysis
using the decoupled 5-stage ContentAcquisitionEngine and PipelineOrchestrator.
"""

import time
from datetime import datetime
from typing import Optional, Union, Dict, Any
from uow.unit_of_work import UnitOfWork
from services.bookmark_service import BookmarkService
from scrapers.acquisition_engine import ContentAcquisitionEngine
from scrapers.models import ContentDocument, compute_content_hash
from core.events import ScrapingStarted, ScrapingCompleted, ScrapingSkipped, ScrapingFailed
from services.pipeline_orchestrator import PipelineOrchestrator
from utils.redis_utils import redis_cache
from utils.embedding_utils import get_embedding
from core.logging_config import get_logger

logger = get_logger(__name__)

EXPECTED_EMBEDDING_DIM = 384
DEFAULT_QUALITY_SCORE = 10


def truncate_title(title: str, max_len: int = 200) -> str:
    """Helper to cleanly truncate long titles on word boundaries."""
    if not title or len(title) <= max_len:
        return title or "Untitled Bookmark"

    truncated = title[:max_len - 3]
    last_space = truncated.rfind(' ')
    if last_space > 150:
        return truncated[:last_space] + "..."
    return truncated + "..."


def extract_article_content(url: str) -> Union[ContentDocument, Dict[str, Any]]:
    """
    Acquires and normalizes content from a URL using ContentAcquisitionEngine.
    """
    engine = ContentAcquisitionEngine()
    return engine.acquire_and_normalize(url)


def validate_embedding(embedding, expected_dim: int = EXPECTED_EMBEDDING_DIM) -> bool:
    """Validate embedding shape and dimension."""
    if embedding is None:
        return False
    if isinstance(embedding, (list, tuple)):
        return len(embedding) == expected_dim
    return False


def generate_comprehensive_embedding(
    title: str,
    description: str,
    meta_description: str,
    headings: list,
    extracted_text: str,
    url: Optional[str] = None
) -> Optional[list]:
    """
    Generate comprehensive embedding.
    Priority: title > meta_description > headings > notes > extracted_text
    """
    embedding_parts = []

    if title and title.strip():
        embedding_parts.append(title.strip())

    if meta_description and meta_description.strip():
        embedding_parts.append(meta_description.strip())

    if headings:
        embedding_parts.append(' '.join(headings[:10]))

    if description and description.strip():
        embedding_parts.append(description.strip())

    if extracted_text and extracted_text.strip():
        text_sample = extracted_text[:5000]
        if len(extracted_text) > 6000:
            text_sample += " " + extracted_text[-1000:]
        embedding_parts.append(text_sample.strip())

    full_text = " | ".join(embedding_parts) if embedding_parts else (title or "Untitled")
    return get_embedding(full_text)


def process_bookmark_content_task(bookmark_id: int, url: str, user_id: int):
    """
    RQ Task function executing the 5-Stage Content Acquisition Engine.
    Acquires, quality-evaluates, normalizes, fingerprint-checks, and persists content,
    then notifies PipelineOrchestrator for downstream processing.
    """
    from utils.event_bus import publish_pipeline_event, generate_pipeline_run_id
    pipeline_run_id = generate_pipeline_run_id()

    logger.info("bg_acquisition_task_started", extra={"bookmark_id": bookmark_id, "user_id": user_id, "url": url, "run_id": pipeline_run_id})

    # Step 1: Initial existence check
    with UnitOfWork() as uow:
        service = BookmarkService(uow)
        bookmark = service.get_bookmark(bookmark_id)
        if not bookmark:
            logger.error("bg_bookmark_not_found", extra={"bookmark_id": bookmark_id})
            return
        bookmark_title = bookmark.title
        bookmark_notes = bookmark.notes or ''

    publish_pipeline_event(
        event_type="bookmark.pipeline.scraping.started",
        bookmark_id=bookmark_id,
        user_id=user_id,
        pipeline_run_id=pipeline_run_id,
        sequence=1,
        data={"url": url}
    )

    try:
        # Step 2: Execute extraction via extract_article_content
        scraped = extract_article_content(url)

        if isinstance(scraped, ContentDocument):
            extracted_text_raw = scraped.markdown_content
            scraped_title = scraped.metadata.title
            quality_score = scraped.quality_metrics.score
            author = scraped.metadata.author
            reading_time = scraped.metadata.reading_time_minutes
            language = scraped.metadata.language
            content_hash = scraped.content_hash
            strategy_used = scraped.fetch_metadata.strategy
            scrapling_version = scraped.fetch_metadata.scrapling_version
            extractor_version = scraped.extractor_version
            provider_raw_payload = scraped.provider_raw_payload
        elif isinstance(scraped, dict):
            extracted_text_raw = scraped.get('content', '')
            scraped_title = scraped.get('title', '')
            quality_score = scraped.get('quality_score', DEFAULT_QUALITY_SCORE)
            author = None
            reading_time = 0
            language = None
            content_hash = compute_content_hash(str(extracted_text_raw))
            strategy_used = "HTTP"
            scrapling_version = "0.2.0"
            extractor_version = "2.0.0"
            provider_raw_payload = {}
        else:
            extracted_text_raw = str(scraped)
            scraped_title = ''
            quality_score = DEFAULT_QUALITY_SCORE
            author = None
            reading_time = 0
            language = None
            content_hash = compute_content_hash(extracted_text_raw)
            strategy_used = "HTTP"
            scrapling_version = "0.2.0"
            extractor_version = "2.0.0"
            provider_raw_payload = {}

        final_title = bookmark_title
        if scraped_title and (not bookmark_title or bookmark_title == 'Untitled Bookmark'):
            final_title = truncate_title(scraped_title.strip())

        extracted_text = None
        if extracted_text_raw is not None:
            extracted_text = str(extracted_text_raw).replace('\x00', '')

        # Step 3: Check Idempotency & Save to Database
        is_skipped = False
        with UnitOfWork() as uow:
            service = BookmarkService(uow)
            bookmark = service.get_bookmark(bookmark_id)
            if not bookmark or getattr(bookmark, 'scrape_status', None) == 'CANCELLED':
                logger.info("bg_bookmark_cancelled_during_acquisition", extra={"bookmark_id": bookmark_id})
                return

            # Idempotency check: Content hash unchanged?
            if getattr(bookmark, 'content_hash', None) == content_hash and content_hash:
                logger.info("bg_acquisition_idempotency_skip", extra={"bookmark_id": bookmark_id, "hash": content_hash})
                bookmark.scrape_status = 'SUCCESS'
                bookmark.scraped_at = datetime.utcnow()
                is_skipped = True
            else:
                if not bookmark.title or bookmark.title == 'Untitled Bookmark':
                    bookmark.title = final_title

                bookmark.extracted_text = extracted_text
                bookmark.quality_score = quality_score
                bookmark.author = author
                bookmark.reading_time = reading_time
                bookmark.language = language
                bookmark.content_hash = content_hash
                bookmark.strategy_used = strategy_used
                bookmark.scrapling_version = scrapling_version
                bookmark.extractor_version = extractor_version
                bookmark.scrape_status = 'SUCCESS'
                bookmark.scraped_at = datetime.utcnow()

                # Persist raw provider JSON payload into bookmark_metadata table if payload exists
                if provider_raw_payload:
                    try:
                        from models import BookmarkMetadata
                        existing_meta = uow.session.query(BookmarkMetadata).filter_by(bookmark_id=bookmark_id).first()
                        if existing_meta:
                            existing_meta.jsonb_payload = provider_raw_payload
                            existing_meta.updated_at = datetime.utcnow()
                        else:
                            new_meta = BookmarkMetadata(bookmark_id=bookmark_id, jsonb_payload=provider_raw_payload)
                            uow.session.add(new_meta)
                    except Exception as meta_err:
                        logger.warning("bg_bookmark_metadata_persistence_warning", extra={"bookmark_id": bookmark_id, "error": str(meta_err)})

            # Async embeddings / direct embedding generation fallback for legacy tests
            from core.feature_flags import is_enabled
            if not is_enabled("async_embeddings", user_id=user_id):
                embedding = generate_comprehensive_embedding(
                    title=final_title,
                    description=bookmark_notes,
                    meta_description="",
                    headings=[],
                    extracted_text=extracted_text_raw,
                    url=url
                )
                if validate_embedding(embedding):
                    bookmark.embedding = embedding
                    bookmark.embedding_status = 'SUCCESS'
                    bookmark.embedded_at = datetime.utcnow()

        # Step 4: Publish Scraping Events & Trigger Pipeline Orchestrator
        orchestrator = PipelineOrchestrator()

        if is_skipped:
            skipped_event = ScrapingSkipped(bookmark_id=bookmark_id, user_id=user_id, url=url, content_hash=content_hash)
            orchestrator.handle_event(skipped_event)
        else:
            completed_event = ScrapingCompleted(
                bookmark_id=bookmark_id,
                user_id=user_id,
                url=url,
                content_hash=content_hash,
                quality_score=quality_score,
                strategy_used=strategy_used
            )
            orchestrator.handle_event(completed_event)

        publish_pipeline_event(
            event_type="bookmark.pipeline.scraping.completed",
            bookmark_id=bookmark_id,
            user_id=user_id,
            pipeline_run_id=pipeline_run_id,
            sequence=2,
            data={
                "title": final_title,
                "content_length": len(extracted_text) if extracted_text else 0,
                "quality_score": quality_score,
                "strategy": strategy_used
            }
        )

    except Exception as e:
        logger.exception("bg_acquisition_task_failed", extra={"bookmark_id": bookmark_id, "user_id": user_id})
        with UnitOfWork() as uow:
            service = BookmarkService(uow)
            bookmark = service.get_bookmark(bookmark_id)
            if bookmark:
                bookmark.scrape_status = 'FAILED'
        raise


def generate_embedding_task(bookmark_id: int, user_id: int):
    """
    Decoupled RQ Task function for vector embedding generation.
    Enqueued by PipelineOrchestrator on scraping completion.
    """
    from utils.event_bus import publish_pipeline_event, generate_pipeline_run_id
    pipeline_run_id = generate_pipeline_run_id()

    logger.info("bg_embedding_task_started", extra={"bookmark_id": bookmark_id, "user_id": user_id})

    with UnitOfWork() as uow:
        service = BookmarkService(uow)
        bookmark = service.get_bookmark(bookmark_id)
        if not bookmark:
            return

        title = bookmark.title
        notes = bookmark.notes or ''
        text = bookmark.extracted_text or ''
        url = bookmark.url

    start_embed = time.time()
    embedding = generate_comprehensive_embedding(
        title=title,
        description=notes,
        meta_description="",
        headings=[],
        extracted_text=text,
        url=url
    )
    embed_duration_ms = round((time.time() - start_embed) * 1000)

    is_embedded = False
    with UnitOfWork() as uow:
        service = BookmarkService(uow)
        bookmark = service.get_bookmark(bookmark_id)
        if bookmark:
            if validate_embedding(embedding):
                bookmark.embedding = embedding
                bookmark.embedding_status = 'SUCCESS'
                bookmark.embedded_at = datetime.utcnow()
                is_embedded = True
            else:
                bookmark.embedding_status = 'FAILED'

    # Selective cache invalidation
    try:
        from services.cache_invalidation_service import cache_invalidator
        cache_invalidator.after_content_update(bookmark_id, user_id)
        redis_cache.invalidate_query_cache(f"bookmarks:{user_id}:*")
    except Exception as cache_err:
        logger.warning("bg_embedding_cache_invalidation_warning", extra={"bookmark_id": bookmark_id, "error": str(cache_err)})

    # Trigger AI analysis downstream
    try:
        from services.background_analysis_service import analyze_content
        analyze_content(bookmark_id, user_id, pipeline_run_id=pipeline_run_id)
    except Exception as e:
        logger.error("bg_embedding_analysis_trigger_failed", extra={"bookmark_id": bookmark_id, "error": str(e)})
