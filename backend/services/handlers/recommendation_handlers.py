from backend.core.logging_config import get_logger

logger = get_logger(__name__)

def handle_feedback_recorded(event: RecommendationFeedbackRecorded):
    """
    React to user feedback on a recommendation.
    Side effects: Invalidate user recommendation cache, update ML model weights (async).
    """
    logger.info("rec_feedback_processing_start", user_id=event.user_id, feedback_type=event.feedback_type)
    try:
        from services.cache_invalidation_service import cache_invalidator
        # Invalidate recommendation cache so the user sees updated results
        cache_invalidator.invalidate_recommendation_cache(event.user_id)
    except Exception as e:
        logger.error("rec_feedback_cache_invalidation_failed", user_id=event.user_id, error=str(e))

def handle_analysis_triggered(event: GeminiAnalysisTriggered):
    """
    Trigger the actual Gemini analysis.
    In production, this should dispatch to a queue. For now, it delegates to 
    the legacy BackgroundAnalysisService.
    """
    logger.info("rec_gemini_analysis_triggered_start", content_id=event.content_id)
    try:
        from services.background_analysis_service import BackgroundAnalysisService
        # This is a legacy call that might be slow/blocking; it should eventually be async
        service = BackgroundAnalysisService()
        # Non-blocking if it starts its own thread, but we should be careful
        service.start_background_analysis() 
    except Exception as e:
        logger.error("rec_gemini_analysis_trigger_failed", content_id=event.content_id, error=str(e))

HANDLERS = {
    RecommendationFeedbackRecorded: [handle_feedback_recorded],
    GeminiAnalysisTriggered: [handle_analysis_triggered]
}
