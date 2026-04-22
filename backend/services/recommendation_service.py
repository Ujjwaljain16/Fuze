from datetime import datetime
from typing import Dict, Any, Optional
from models import UserFeedback
from core.events import RecommendationFeedbackRecorded
from backend.core.logging_config import get_logger

logger = get_logger(__name__)

class RecommendationService:
    """
    Service for serving product recommendations and managing feedback loops.
    Focuses on latency and consumption-ready data.
    """
    
    def __init__(self, uow):
        self.uow = uow
        self._engine = None

    def _get_engine(self):
        """Lazy initialization of the recommendation orchestrator"""
        if not self._engine:
            try:
                from ml.orchestrator import get_orchestrator
                self._engine = get_orchestrator()
            except ImportError:
                logger.error("ml_orchestrator_not_found", detail="Library or engine module missing")
                return None
        return self._engine

    def get_recommendations(self, user_id: int, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Produce a list of recommendation candidates for the user using the modular orchestrator.
        """
        from ml.recommendation.schemas import UnifiedRecommendationRequest
        from dataclasses import asdict
        
        # 1. Prepare the request
        unified_request = UnifiedRecommendationRequest(
            user_id=user_id,
            title=request_data.get('title', ''),
            description=request_data.get('description', ''),
            technologies=request_data.get('technologies', ''),
            user_interests=request_data.get('user_interests', ''),
            project_id=request_data.get('project_id'),
            max_recommendations=request_data.get('max_recommendations', 10),
            engine_preference=request_data.get('engine_preference', 'context'),
            quality_threshold=request_data.get('quality_threshold', 3),
            include_global_content=request_data.get('include_global_content', True)
        )
        
        engine = self._get_engine()
        if not engine:
            logger.warning("recommendation_engine_unavailable_using_fallback", user_id=user_id)
            bookmarks = self.uow.recommendations.get_user_bookmarks(user_id, limit=unified_request.max_recommendations)
            return {
                'recommendations': [b.to_dict() for b in bookmarks],
                'total_recommendations': len(bookmarks),
                'engine_used': 'fallback_latest'
            }
            
        # 2. Execute
        recommendations = engine.get_recommendations(unified_request)
        result = [asdict(rec) for rec in recommendations]
        
        return {
            'recommendations': result,
            'total_recommendations': len(result),
            'engine_used': 'UnifiedOrchestrator_v2_Optimized',
            'performance_metrics': engine.get_performance_metrics() if hasattr(engine, 'get_performance_metrics') else {}
        }

    def record_feedback(self, user_id: int, content_id: int, feedback_type: str, recommendation_id: Optional[int] = None, feedback_data: Dict[str, Any] = None):
        """
        Capture user feedback and emit fact for learning updates.
        """
        # Map feedback types to canonical model types if necessary
        feedback = UserFeedback(
            user_id=user_id,
            content_id=content_id,
            recommendation_id=recommendation_id,
            feedback_type=feedback_type,
            context_data=feedback_data or {},
            timestamp=datetime.utcnow()
        )
        
        self.uow.recommendations.add_feedback(feedback)
        
        # Emit fact for post-commit learning/cache invalidation
        self.uow.emit(RecommendationFeedbackRecorded(
            user_id=user_id,
            content_id=content_id,
            recommendation_id=recommendation_id,
            feedback_type=feedback_type
        ))
        
        return feedback
