"""
Bookmark Processing Service
Handles asynchronous worker task execution for bookmark content extraction, embedding, and analysis
"""

import logging
from uow.unit_of_work import UnitOfWork
from services.bookmark_service import BookmarkService
from utils.redis_utils import redis_cache
from core.logging_config import get_logger

logger = get_logger(__name__)

def process_bookmark_content_task(bookmark_id: int, url: str, user_id: int):
    """
    RQ Task function to process bookmark content extraction, embedding, and analysis.
    Executed asynchronously by background RQ workers.
    """
    task_logger = logging.getLogger(__name__)

    try:
        # Import app context creator for worker compatibility
        from run_production import create_app
        app = create_app()

        task_logger.info(f"Starting background processing for bookmark {bookmark_id}")

        with app.app_context():
            from blueprints.bookmarks import extract_article_content, generate_comprehensive_embedding

            # First UoW: Fetch bookmark info to check existence and get initial context
            with UnitOfWork() as uow:
                service = BookmarkService(uow)
                bookmark = service.get_bookmark(bookmark_id)
                if not bookmark:
                    task_logger.error(f"Bookmark {bookmark_id} not found for background processing")
                    return

                bookmark_title = bookmark.title
                bookmark_notes = bookmark.notes or ''

            task_logger.info(f"Background processing started for bookmark {bookmark_id}: {url}")

            # --- OUTSIDE UoW: Heavy side effects (scraping, ML embeddings) ---
            scraped = extract_article_content(url)
            extracted_text = scraped.get('content', '')
            scraped_title = scraped.get('title', '')
            headings = scraped.get('headings', [])
            meta_description = scraped.get('meta_description', '')
            quality_score = scraped.get('quality_score', 10)

            final_title = bookmark_title
            if scraped_title and (not bookmark_title or bookmark_title == 'Untitled Bookmark'):
                final_title = scraped_title.strip()
                if len(final_title) > 200:
                    truncated = final_title[:197]
                    last_space = truncated.rfind(' ')
                    final_title = (truncated[:last_space] + "...") if last_space > 150 else (truncated + "...")

            embedding = generate_comprehensive_embedding(
                title=final_title,
                description=bookmark_notes,
                meta_description=meta_description,
                headings=headings,
                extracted_text=extracted_text,
                url=url
            )

            if extracted_text:
                extracted_text = extracted_text.replace('\x00', '')
                if not isinstance(extracted_text, str):
                    extracted_text = str(extracted_text)

            # --- SECOND UoW: Save extraction results ---
            with UnitOfWork() as uow:
                service = BookmarkService(uow)
                bookmark = service.get_bookmark(bookmark_id)
                if not bookmark:
                    task_logger.error(f"Bookmark {bookmark_id} was deleted during background processing")
                    return

                bookmark.title = final_title
                bookmark.extracted_text = extracted_text

                if embedding is not None:
                    bookmark.embedding = embedding

                bookmark.quality_score = quality_score

            # Invalidate caches
            from services.cache_invalidation_service import cache_invalidator
            cache_invalidator.after_content_update(bookmark_id, user_id)
            redis_cache.invalidate_query_cache(f"bookmarks:{user_id}:*")

            task_logger.info(f"Background processing completed for bookmark {bookmark_id}")

            # Trigger background AI analysis
            try:
                from services.background_analysis_service import analyze_content
                analyze_content(bookmark_id, user_id)
                task_logger.info(f"Background analysis triggered for bookmark {bookmark_id}")
            except Exception as e:
                task_logger.error(f"Error triggering background analysis for bookmark {bookmark_id}: {e}")

    except Exception as e:
        task_logger.error(f"Error in background processing for bookmark {bookmark_id}: {e}", exc_info=True)
        raise
