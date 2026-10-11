from core.events import BookmarkCreated
from core.logging_config import get_logger

logger = get_logger(__name__)

def handle_bookmark_created(event: BookmarkCreated):
    """
    Handler for BookmarkCreated domain event.
    Dispatches asynchronous bookmark content processing (RQ queue or daemon thread fallback).
    """
    logger.info(
        "bookmark_created_event_received",
        bookmark_id=event.bookmark_id,
        user_id=event.user_id,
        url=event.url
    )

    if event.content_captured:
        # The save carried the page content and stored it already; fetching would only redo it
        # (and for login-walled pages, worse).
        return

    try:
        from blueprints.bookmarks import process_bookmark_content_async
        process_bookmark_content_async(event.bookmark_id, event.url, event.user_id)
    except Exception as e:
        logger.exception(
            "bookmark_async_dispatch_failed",
            bookmark_id=event.bookmark_id,
            error=str(e)
        )

HANDLERS = {
    BookmarkCreated: [handle_bookmark_created]
}
