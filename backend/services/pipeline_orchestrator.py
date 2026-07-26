"""
Pipeline Orchestrator Service
Listens to scraping lifecycle events (scraping.completed, scraping.skipped)
and orchestrates downstream execution for Embedding, AI Analysis, and Recommendation engines
with automatic backpressure control.
"""

from typing import Dict, Any, Optional
from core.events import ScrapingCompleted, ScrapingSkipped, Event
from core.logging_config import get_logger
from services.task_queue import get_queue
from utils.event_bus import publish_pipeline_event

logger = get_logger(__name__)

MAX_QUEUE_BACKLOG = 500  # Backpressure threshold in jobs count


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

        queue = self._get_queue()
        if queue:
            # Backpressure Check: Check current queue length
            try:
                queue_length = len(queue)
                if queue_length >= self.max_backlog:
                    logger.warning(
                        "orchestrator_backpressure_applied",
                        extra={"queue": self.queue_name, "queue_length": queue_length, "max_backlog": self.max_backlog}
                    )
                    publish_pipeline_event(
                        event_type="bookmark.pipeline.backpressure_applied",
                        bookmark_id=event.bookmark_id,
                        user_id=event.user_id,
                        pipeline_run_id=getattr(event, 'pipeline_run_id', 'run_backpressure'),
                        sequence=2,
                        data={"queue_length": queue_length, "threshold": self.max_backlog}
                    )
                    return False
            except Exception as len_err:
                logger.debug("queue_length_check_failed", extra={"error": str(len_err)})

            try:
                queue.enqueue(
                    "services.bookmark_processing_service.generate_embedding_task",
                    bookmark_id=event.bookmark_id,
                    user_id=event.user_id,
                    job_timeout=120
                )
                logger.info("orchestrator_enqueued_embedding_task", extra={"bookmark_id": event.bookmark_id})
            except Exception as e:
                logger.error("orchestrator_enqueue_embedding_failed", extra={"bookmark_id": event.bookmark_id, "error": str(e)})

        return True

    def _on_scraping_skipped(self, event: ScrapingSkipped) -> bool:
        logger.info(
            "orchestrator_handling_scraping_skipped",
            extra={"bookmark_id": event.bookmark_id, "user_id": event.user_id, "reason": event.reason}
        )
        return True
