from datetime import datetime
from typing import Optional, List
from models import ContentAnalysis
from core.events import GeminiAnalysisTriggered
from backend.core.logging_config import get_logger

logger = get_logger(__name__)

class ContentService:
    """
    Service for content intelligence and enrichment.
    Orchestrates Gemini analysis and background processing.
    """
    
    def __init__(self, uow):
        self.uow = uow

    def trigger_analysis(self, user_id: int, content_id: int):
        """
        Record the intent to analyze content.
        Actual heavy-lifting happens in a background handler or service.
        """
        logger.info("gemini_analysis_trigger_requested", content_id=content_id, user_id=user_id)
        # Ensure content exists and belongs to user
        content = self.uow.recommendations.get_bookmark_by_id(content_id)
        if not content or content.user_id != user_id:
            logger.error("gemini_analysis_trigger_failed", reason="not_found_or_unauthorized", content_id=content_id)
            return
            
        # Emit event so the system can react (e.g. by starting a background thread or queue job)
        self.uow.emit(GeminiAnalysisTriggered(user_id=user_id, content_id=content_id))

    def get_analysis(self, content_id: int) -> Optional[ContentAnalysis]:
        """Retrieve existing analysis results"""
        return self.uow.recommendations.get_analysis_by_content_id(content_id)

    def batch_trigger_analysis(self, user_id: int, content_ids: List[int]):
        """Trigger analysis for multiple items"""
        for cid in content_ids:
            self.trigger_analysis(user_id, cid)

    def start_full_background_analysis(self, user_id: int):
        """Find unanalyzed content and trigger analysis for them"""
        unanalyzed = self.uow.recommendations.get_unanalyzed_bookmarks(user_id, limit=50)
        logger.info("background_analysis_started", user_id=user_id, found_count=len(unanalyzed))
        for item in unanalyzed:
            self.trigger_analysis(user_id, item.id)

    def generate_interactive_context(self, user_id: int, recommendation_id: int, context_data: dict) -> dict:
        """
        On-demand interactive analysis using user's own API key.
        Refactored from recommendations blueprint.
        """
        from services.multi_user_api_manager import get_user_api_key
        from utils.gemini_utils import GeminiAnalyzer
        
        user_api_key = get_user_api_key(user_id)
        if not user_api_key:
            raise ValueError("User API key not found. Please add your Gemini API key in settings.")
            
        analyzer = GeminiAnalyzer(api_key=user_api_key)
        
        # Prepare content for analysis
        prompt = f"Explain why this recommendation is relevant to my context: {context_data.get('title', '')}"
        # (This is a simplified version of the blueprint logic for brevity)
        
        analysis_result = analyzer.analyze_text(prompt)
        return {
            'recommendation_id': recommendation_id,
            'analysis': analysis_result,
            'generated_at': datetime.utcnow().isoformat()
        }
