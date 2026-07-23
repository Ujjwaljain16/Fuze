from core.events import RecommendationFeedbackRecorded
from core.logging_config import get_logger

logger = get_logger(__name__)


def handle_feedback_recorded(event: RecommendationFeedbackRecorded):
    """
    React to user feedback on a recommendation.

    Current behavior:
        - Log the feedback event for observability.
        - Invalidate the user's recommendation cache so fresh results
          are fetched on the next request.

    Explicitly NOT doing:
        - Calling ML model weight updates (GeminiAnalysisTriggered path is BLOCKED).
        - Calling BackgroundAnalysisService (scans all users — dangerous, blocked).
        - Any Gemini / embedding calls.

    Future phases will add a dedicated recommendation ML job enqueue here,
    once the job architecture for recommendations is designed and reviewed.

    FAILURE ISOLATION: This handler is called post-commit. A failure here
    logs an error but does NOT rollback the already-committed feedback record.
    """
    logger.info(
        "rec_feedback_received",
        user_id=event.user_id,
        content_id=event.content_id,
        feedback_type=event.feedback_type,
        recommendation_id=event.recommendation_id,
    )

    try:
        from services.cache_invalidation_service import cache_invalidator
        cache_invalidator.invalidate_recommendation_cache(event.user_id)
        logger.debug(
            "rec_feedback_cache_invalidated",
            user_id=event.user_id
        )
    except Exception as e:
        logger.exception(
            "rec_feedback_cache_invalidation_failed",
            user_id=event.user_id,
            error=str(e)
        )


# GeminiAnalysisTriggered is intentionally NOT handled here.
# The architecture-shift handler calls BackgroundAnalysisService().start_background_analysis()
# which scans all users — not scoped to event.content_id — and is classified DANGEROUS.
# This will be revisited in a dedicated recommendation job architecture phase.

HANDLERS = {
    RecommendationFeedbackRecorded: [handle_feedback_recorded],
}
