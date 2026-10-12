"""
Bookmark Processing Service
Handles asynchronous worker task execution for bookmark content acquisition, embedding, and analysis
using the decoupled 5-stage ContentAcquisitionEngine and PipelineOrchestrator.
"""

import time
from datetime import datetime

import numpy as np
from typing import Optional, Union, Dict, Any
from uow.unit_of_work import UnitOfWork
from services.bookmark_service import BookmarkService
from scrapers.acquisition_engine import ContentAcquisitionEngine
from scrapers.models import ContentDocument, compute_content_hash
from core.events import ScrapingCompleted, ScrapingSkipped
from services.pipeline_orchestrator import PipelineOrchestrator
from services.captured_content import fetch_beats_capture, has_captured_content
from utils.redis_utils import redis_cache
from utils.embedding_utils import active_embedding_model_name, get_embedding
from core.logging_config import get_logger

logger = get_logger(__name__)

EXPECTED_EMBEDDING_DIM = 384
DEFAULT_QUALITY_SCORE = 10


class TransientFetchError(RuntimeError):
    """The page couldn't be fetched for a reason that may pass (timeout, 5xx, 429): let RQ retry."""


def _record_failed_fetch(bookmark_id: int, user_id: int, doc: ContentDocument, pipeline_run_id: str) -> bool:
    """Keep what the user saved, mark the fetch as failed and still make the bookmark searchable.

    Failure documents used to be stored as SUCCESS: empty text, its hash (which then blocked any
    later re-fetch from storing real content) and titles like "Failed to Acquire Content".

    Returns False when nothing was recorded (bookmark gone, or it holds content the extension
    captured), in which case there is nothing to retry either.
    """
    from utils.event_bus import publish_pipeline_event
    status = {'blocked': 'BLOCKED', 'disallowed': 'DISALLOWED'}.get(doc.outcome, 'FAILED_FETCH')
    with UnitOfWork() as uow:
        bookmark = BookmarkService(uow).get_bookmark(bookmark_id)
        if not bookmark:
            return False
        if has_captured_content(bookmark):
            # The extension stored what the user saw; the server failing to read it changes nothing.
            logger.info("bg_acquisition_kept_captured_content", extra={"bookmark_id": bookmark_id, "outcome": doc.outcome})
            return False
        bookmark.scrape_status = status
        bookmark.strategy_used = doc.fetch_metadata.strategy
        bookmark.scraped_at = datetime.utcnow()
        needs_embedding = bookmark.embedding_status != 'SUCCESS'

    logger.warning("bg_acquisition_fetch_failed", extra={
        "bookmark_id": bookmark_id, "status": status, "http_status": doc.fetch_metadata.http_status,
        "retryable": doc.retryable})
    publish_pipeline_event(
        event_type="bookmark.pipeline.scraping.failed",
        bookmark_id=bookmark_id,
        user_id=user_id,
        pipeline_run_id=pipeline_run_id,
        sequence=2,
        error={"error_code": status, "http_status": doc.fetch_metadata.http_status, "retryable": doc.retryable},
    )
    # Title, notes and URL still describe the bookmark; embed them so search can find it.
    if needs_embedding:
        PipelineOrchestrator().request_embedding(bookmark_id, user_id)
    return True


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


def scrape_url_summary(url: str) -> Dict[str, Any]:
    """Run the acquisition engine and return the flat dict shape used by previews and scripts."""
    doc = extract_article_content(url)
    content = doc.markdown_content or ""
    headings = [line.lstrip("#").strip() for line in content.splitlines() if line.startswith("#")]
    return {
        "title": doc.metadata.title or "",
        "content": content,
        "headings": headings[:20],
        "meta_description": doc.metadata.description or "",
        # quality_metrics.score is 0-100; callers of this shape expect 1-10
        "quality_score": max(1, min(10, round(doc.quality_metrics.score / 10))),
    }


def validate_embedding(embedding, expected_dim: int = EXPECTED_EMBEDDING_DIM) -> bool:
    """Validate shape and values. Accepts lists/tuples and numpy arrays (what the model returns).

    Rejects all-zero vectors: get_embedding() returns zeros when the model fails, and a zero
    vector makes cosine distance undefined in pgvector.
    """
    if embedding is None:
        return False
    try:
        arr = np.asarray(embedding, dtype=np.float32)
    except (TypeError, ValueError):
        return False
    if arr.ndim != 1 or arr.shape[0] != expected_dim:
        return False
    return bool(np.all(np.isfinite(arr)) and np.any(arr))


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

        if isinstance(scraped, ContentDocument) and scraped.outcome != "ok":
            recorded = _record_failed_fetch(bookmark_id, user_id, scraped, pipeline_run_id)
            if recorded and scraped.retryable:
                raise TransientFetchError(f"fetch failed with HTTP {scraped.fetch_metadata.http_status}")
            return

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
            needs_embedding = bookmark.embedding_status != 'SUCCESS'
            if getattr(bookmark, 'content_hash', None) == content_hash and content_hash:
                logger.info("bg_acquisition_idempotency_skip", extra={"bookmark_id": bookmark_id, "hash": content_hash})
                bookmark.scrape_status = 'SUCCESS'
                bookmark.scraped_at = datetime.utcnow()
                is_skipped = True
            elif has_captured_content(bookmark) and not (
                    isinstance(scraped, ContentDocument) and fetch_beats_capture(bookmark.extracted_text, scraped)):
                # What the extension captured is what the user saw (signed in, rendered); a server
                # fetch only replaces it when clearly better, never with a thinner or challenge page.
                logger.info("bg_acquisition_kept_captured_content", extra={"bookmark_id": bookmark_id})
                content_hash = bookmark.content_hash
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


        # Step 4: Publish Scraping Events & Trigger Pipeline Orchestrator
        orchestrator = PipelineOrchestrator()

        if is_skipped:
            skipped_event = ScrapingSkipped(bookmark_id=bookmark_id, user_id=user_id, url=url, content_hash=content_hash)
            orchestrator.handle_event(skipped_event)
            # Same content as last time, but an earlier embedding may have failed or been deferred.
            if needs_embedding:
                orchestrator.request_embedding(bookmark_id, user_id)
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

    except TransientFetchError:
        raise
    except Exception:
        logger.exception("bg_acquisition_task_failed", extra={"bookmark_id": bookmark_id, "user_id": user_id})
        with UnitOfWork() as uow:
            service = BookmarkService(uow)
            bookmark = service.get_bookmark(bookmark_id)
            if bookmark and not has_captured_content(bookmark):
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
        has_content = bool(text.strip())

    publish_pipeline_event(
        event_type="bookmark.pipeline.embedding.started",
        bookmark_id=bookmark_id,
        user_id=user_id,
        pipeline_run_id=pipeline_run_id,
        sequence=3,
    )

    def _failed(code, message):
        publish_pipeline_event(
            event_type="bookmark.pipeline.embedding.failed",
            bookmark_id=bookmark_id,
            user_id=user_id,
            pipeline_run_id=pipeline_run_id,
            sequence=4,
            error={"code": code, "message": message},
        )

    start_embed = time.time()
    try:
        embedding = generate_comprehensive_embedding(
            title=title,
            description=notes,
            meta_description="",
            headings=[],
            extracted_text=text,
            url=url
        )
    except Exception as e:
        # RQ retries the job; the dashboard still learns this attempt failed.
        _failed("embedding_unavailable", str(e)[:200])
        raise
    embed_duration_ms = round((time.time() - start_embed) * 1000)

    is_embedded = False
    with UnitOfWork() as uow:
        service = BookmarkService(uow)
        bookmark = service.get_bookmark(bookmark_id)
        if bookmark:
            if validate_embedding(embedding):
                bookmark.embedding = embedding
                bookmark.embedding_metadata = {"model": active_embedding_model_name()}
                bookmark.embedding_status = 'SUCCESS'
                bookmark.embedded_at = datetime.utcnow()
                is_embedded = True
            else:
                bookmark.embedding_status = 'FAILED'

    if is_embedded:
        publish_pipeline_event(
            event_type="bookmark.pipeline.embedding.completed",
            bookmark_id=bookmark_id,
            user_id=user_id,
            pipeline_run_id=pipeline_run_id,
            sequence=4,
            data={"model": active_embedding_model_name(), "duration_ms": embed_duration_ms},
        )
    elif not validate_embedding(embedding):
        _failed("invalid_embedding", "The model returned an unusable vector")

    # Passage chunks (full-text coverage beyond the model's input limit). Separate transaction so a
    # chunking failure never loses the document embedding above.
    if is_embedded:
        try:
            with UnitOfWork() as uow:
                if uow.session.get_bind().dialect.name == 'postgresql':
                    from services.hybrid_search import index_content_chunks
                    n_chunks = index_content_chunks(uow.session, bookmark_id)
                    logger.info("bg_chunks_indexed", extra={"bookmark_id": bookmark_id, "chunks": n_chunks})
        except Exception as chunk_err:
            logger.warning("bg_chunk_indexing_failed", extra={"bookmark_id": bookmark_id, "error": str(chunk_err)})

    # Selective cache invalidation
    try:
        from services.cache_invalidation_service import cache_invalidator
        cache_invalidator.after_content_update(bookmark_id, user_id)
        from core import cache_keys
        redis_cache.invalidate_query_cache(cache_keys.bookmarks_pattern(user_id))
    except Exception as cache_err:
        logger.warning("bg_embedding_cache_invalidation_warning", extra={"bookmark_id": bookmark_id, "error": str(cache_err)})

    # AI analysis is its own job on the default queue. Run inline it held this worker for the whole
    # Gemini call (30 s or more, or all of its retries) while the next bookmarks waited to be
    # embedded, and a slow or failing Gemini slowed search for everything imported after it.
    # If the enqueue fails the bookmark stays PENDING and the reconciler enqueues it.
    if has_content and is_embedded:
        try:
            from services.pipeline_reconciler import ANALYSIS_TASK, analysis_job_id
            from services.task_queue import enqueue_unique, get_queue
            queue = get_queue('default')
            if queue is not None:
                enqueue_unique(queue, ANALYSIS_TASK, analysis_job_id(bookmark_id),
                               kwargs={'bookmark_id': bookmark_id, 'user_id': user_id}, job_timeout=300)
        except Exception as e:
            logger.error("bg_embedding_analysis_trigger_failed", extra={"bookmark_id": bookmark_id, "error": str(e)})


def analyze_bookmark_task(bookmark_id: int, user_id: int):
    """
    RQ task: run the AI analysis for one bookmark. The pipeline reconciler enqueues it for
    bookmarks whose analysis failed, was rate limited, or was deferred for lack of Gemini allowance.
    """
    from services.background_analysis_service import analyze_content
    logger.info("bg_analysis_retry_task_started", extra={"bookmark_id": bookmark_id, "user_id": user_id})
    analyze_content(bookmark_id, user_id)
