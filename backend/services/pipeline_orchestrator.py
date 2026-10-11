"""
Pipeline Orchestrator Service
Listens to scraping lifecycle events (scraping.completed, scraping.skipped)
and orchestrates downstream execution for Embedding, AI Analysis, and Recommendation engines
with automatic backpressure control.

Nothing here drops work. When the queue is backed up or unreachable the bookmark keeps
embedding_status PENDING and the reconciler (services/pipeline_reconciler.py) enqueues it later.
"""

from core.events import ScrapingCompleted, ScrapingSkipped, Event
from core.logging_config import get_logger
from services.task_queue import get_queue, enqueue_unique
from utils.event_bus import publish_pipeline_event

logger = get_logger(__name__)

MAX_QUEUE_BACKLOG = 500  # Backpressure threshold in jobs count
EMBEDDING_TASK = "services.bookmark_processing_service.generate_embedding_task"


def embedding_job_id(bookmark_id: int) -> str:
    return f"embed_bookmark_{bookmark_id}"


class PipelineOrchestrator:
    """
    Decoupled Orchestrator for downstream pipeline processing with backpressure control.
    """
    def __init__(self, queue_name: str = 'default', max_backlog: int = MAX_QUEUE_BACKLOG):
        self.queue_name = queue_name
        self.max_backlog = max_backlog

    def _get_queue(self):
        return get_queue(self.queue_name)

    def handle_event(self, event: Event) -> bool:
        """
        Evaluate event and dispatch downstream processing jobs.
        """
        if isinstance(event, ScrapingCompleted):
            return self._on_scraping_completed(event)
        elif isinstance(event, ScrapingSkipped):
            return self._on_scraping_skipped(event)
        return False

    def request_embedding(self, bookmark_id: int, user_id: int) -> bool:
        """Enqueue (at most one) embedding job; False means deferred to the reconciler."""
        queue = self._get_queue()
        if not queue:
            logger.warning("orchestrator_queue_unavailable_deferred", extra={"bookmark_id": bookmark_id})
            return False

        try:
            queue_length = len(queue)
        except Exception as len_err:
            logger.debug("queue_length_check_failed", extra={"error": str(len_err)})
            queue_length = 0
        if queue_length >= self.max_backlog:
            logger.warning(
                "orchestrator_backpressure_deferred",
                extra={"queue": self.queue_name, "queue_length": queue_length, "max_backlog": self.max_backlog,
                       "bookmark_id": bookmark_id}
            )
            publish_pipeline_event(
                event_type="bookmark.pipeline.backpressure_applied",
                bookmark_id=bookmark_id,
                user_id=user_id,
                pipeline_run_id='run_backpressure',
                sequence=2,
                data={"queue_length": queue_length, "threshold": self.max_backlog}
            )
            return False

        job = enqueue_unique(queue, EMBEDDING_TASK, embedding_job_id(bookmark_id),
                             kwargs={'bookmark_id': bookmark_id, 'user_id': user_id}, job_timeout=300)
        if job is not None:
            logger.info("orchestrator_enqueued_embedding_task", extra={"bookmark_id": bookmark_id})
        return job is not None

    def _on_scraping_completed(self, event: ScrapingCompleted) -> bool:
        logger.info(
            "orchestrator_handling_scraping_completed",
            extra={
                "bookmark_id": event.bookmark_id,
                "user_id": event.user_id,
                "content_hash": event.content_hash,
                "quality_score": event.quality_score
            }
        )
        return self.request_embedding(event.bookmark_id, event.user_id)

    def _on_scraping_skipped(self, event: ScrapingSkipped) -> bool:
        logger.info(
            "orchestrator_handling_scraping_skipped",
            extra={"bookmark_id": event.bookmark_id, "user_id": event.user_id, "reason": event.reason}
        )
        return True
