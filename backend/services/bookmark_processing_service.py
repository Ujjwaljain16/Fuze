"""
Bookmark Processing Service
Handles asynchronous worker task execution for bookmark content extraction, embedding, and analysis
"""

from typing import Optional
from uow.unit_of_work import UnitOfWork
from services.bookmark_service import BookmarkService
from utils.redis_utils import redis_cache
from utils.embedding_utils import get_embedding
from scrapers.scrapling_enhanced_scraper import scrape_url_enhanced
from core.logging_config import get_logger

logger = get_logger(__name__)

EXPECTED_EMBEDDING_DIM = 384
DEFAULT_QUALITY_SCORE = 10


def extract_article_content(url: str) -> dict:
    """Extract main content, title, headings, and metadata from a URL."""
    return scrape_url_enhanced(url)


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


def truncate_title(title: str, max_len: int = 200) -> str:
    """Helper to cleanly truncate long titles on word boundaries."""
    if not title or len(title) <= max_len:
        return title or "Untitled Bookmark"

    truncated = title[:max_len - 3]
    last_space = truncated.rfind(' ')
    if last_space > 150:
        return truncated[:last_space] + "..."
    return truncated + "..."


def validate_embedding(embedding, expected_dim: int = EXPECTED_EMBEDDING_DIM) -> bool:
    """Validate embedding shape and dimension."""
    if embedding is None:
        return False
    if isinstance(embedding, (list, tuple)):
        return len(embedding) == expected_dim
    return False


def process_bookmark_content_task(bookmark_id: int, url: str, user_id: int):
    """
    RQ Task function to process bookmark content extraction, embedding, and analysis.
    Executed asynchronously by background RQ workers using clean service dependencies.
    """
    logger.info("bg_bookmark_processing_started", extra={"bookmark_id": bookmark_id, "user_id": user_id, "url": url})

    try:
        # First UoW: Fetch bookmark info to check existence and get initial context
        with UnitOfWork() as uow:
            service = BookmarkService(uow)
            bookmark = service.get_bookmark(bookmark_id)
            if not bookmark:
                logger.error("bg_bookmark_not_found", extra={"bookmark_id": bookmark_id})
                return

            bookmark_title = bookmark.title
            bookmark_notes = bookmark.notes or ''

        # Heavy side effects outside transaction (scraping, ML embeddings)
        scraped = extract_article_content(url)
        extracted_text_raw = scraped.get('content', '')
        scraped_title = scraped.get('title', '')
        headings = scraped.get('headings', [])
        meta_description = scraped.get('meta_description', '')
        quality_score = scraped.get('quality_score', DEFAULT_QUALITY_SCORE)

        # Title formatting
        final_title = bookmark_title
        if scraped_title and (not bookmark_title or bookmark_title == 'Untitled Bookmark'):
            final_title = truncate_title(scraped_title.strip())

        embedding = generate_comprehensive_embedding(
            title=final_title,
            description=bookmark_notes,
            meta_description=meta_description,
            headings=headings,
            extracted_text=extracted_text_raw,
            url=url
        )

        # Null byte & type conversion
        extracted_text = None
        if extracted_text_raw is not None:
            extracted_text = str(extracted_text_raw).replace('\x00', '')

        # Second UoW: Save extraction results safely
        with UnitOfWork() as uow:
            service = BookmarkService(uow)
            bookmark = service.get_bookmark(bookmark_id)
            if not bookmark:
                logger.error("bg_bookmark_deleted_during_processing", extra={"bookmark_id": bookmark_id})
                return

            # Preserve user title edits if user updated title during scraping
            if not bookmark.title or bookmark.title == 'Untitled Bookmark':
                bookmark.title = final_title

            bookmark.extracted_text = extracted_text

            if validate_embedding(embedding):
                bookmark.embedding = embedding

            bookmark.quality_score = quality_score

        # Safe cache invalidation
        try:
            from services.cache_invalidation_service import cache_invalidator
            cache_invalidator.after_content_update(bookmark_id, user_id)
            redis_cache.invalidate_query_cache(f"bookmarks:{user_id}:*")
        except Exception as cache_err:
            logger.warning("bg_bookmark_cache_invalidation_warning", extra={"bookmark_id": bookmark_id, "error": str(cache_err)})

        logger.info("bg_bookmark_processing_completed", extra={"bookmark_id": bookmark_id, "user_id": user_id})

        # Trigger background AI analysis
        try:
            from services.background_analysis_service import analyze_content
            analyze_content(bookmark_id, user_id)
            logger.info("bg_bookmark_analysis_triggered", extra={"bookmark_id": bookmark_id})
        except Exception as e:
            logger.error("bg_bookmark_analysis_trigger_failed", extra={"bookmark_id": bookmark_id, "error": str(e)})

    except Exception as e:
        logger.exception("bg_bookmark_processing_failed", extra={"bookmark_id": bookmark_id, "user_id": user_id})
        raise
