from datetime import datetime
from typing import Dict, Any, Optional, List
from models import UserFeedback
from core.events import RecommendationFeedbackRecorded
from core.logging_config import get_logger

logger = get_logger(__name__)

class RecommendationService:
    """
    Service for managing recommendation persistence and feedback loops.
    Focuses strictly on pure persistence tasks without ML engine coupling.
    """
    
    def __init__(self, uow):
        self.uow = uow

    def record_feedback(self, user_id: int, content_id: int, feedback_type: str, recommendation_id: Optional[int] = None, feedback_data: Dict[str, Any] = None) -> UserFeedback:
        """
        Capture user feedback and persist to the database.
        Emits RecommendationFeedbackRecorded post-commit to trigger cache invalidation.
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
        
        # Emit post-commit event. Handler invalidates recommendation cache.
        # No ML is triggered — GeminiAnalysisTriggered path is intentionally blocked.
        self.uow.emit(
            RecommendationFeedbackRecorded(
                user_id=user_id,
                content_id=content_id,
                recommendation_id=recommendation_id,
                feedback_type=feedback_type,
            )
        )
        
        return feedback


    def get_analysis_stats(self, user_id: int) -> Dict[str, Any]:
        """Get aggregate statistics about content analysis for a user formatted for the frontend."""
        stats = self.uow.recommendations.get_analysis_stats(user_id)
        total_user_content = stats['total_content']
        analyzed_user_content = stats['analyzed_count']
        pending_analysis = stats['pending_count']
        
        if pending_analysis > 0 and total_user_content > 0:
            coverage_percentage = round((analyzed_user_content / total_user_content) * 100, 1)
            return {
                'total_content': total_user_content,
                'analyzed_content': analyzed_user_content,
                'pending_analysis': pending_analysis,
                'coverage_percentage': coverage_percentage,
                'analysis_percentage': coverage_percentage,
                'batch_processing_active': True,
                'batch_message': f"Processing {pending_analysis} items ({coverage_percentage}% complete)"
            }
        else:
            return {
                'total_content': total_user_content,
                'analyzed_content': analyzed_user_content,
                'pending_analysis': 0,
                'coverage_percentage': 100.0 if total_user_content > 0 else 0.0,
                'analysis_percentage': 100.0 if total_user_content > 0 else 0.0,
                'batch_processing_active': False,
                'batch_message': None
            }

    def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Aggregate user preferences based on recent feedback and bookmarks."""
        data = self.uow.recommendations.get_user_preferences_data(user_id)
        
        content_stats = {
            'total_bookmarks': data['total_bookmarks'],
            'avg_quality_score': data['avg_quality_score']
        }
        
        return {
            'user_id': user_id,
            'feedback_patterns': {stat.feedback_type: stat.count for stat in data['feedback_stats']},
            'content_statistics': content_stats,
            'top_technologies': [{'technology': tag, 'count': count} for tag, count in data['top_technologies'] if tag],
            'learning_style': 'adaptive'  # Could be enhanced with ML later
        }

    def get_learning_insights(self, user_id: int) -> Dict[str, Any]:
        """Aggregate basic learning insights for the user."""
        recent_bookmarks = self.uow.recommendations.get_recent_bookmarks_for_learning(user_id=user_id, limit=20)
        
        # Analyze recent patterns
        from collections import defaultdict
        
        technologies = []
        for bookmark in recent_bookmarks:
            if bookmark.tags:
                # tags might be stored as string or list, fallback logic handles string splitting
                tags_list = bookmark.tags.split(',') if isinstance(bookmark.tags, str) else bookmark.tags
                if isinstance(tags_list, list):
                    technologies.extend(tags_list)
                
        tech_frequency = defaultdict(int)
        for tech in technologies:
            tech_frequency[tech.strip().lower()] += 1
            
        return {
            'user_id': user_id,
            'learning_trends': {
                'recent_technologies': dict(list(tech_frequency.items())[:10]),
                'learning_velocity': len(recent_bookmarks),
                'engagement_score': 7.5  # Basic score
            },
            'recommendations': [
                'Continue exploring your current technology stack',
                'Consider diversifying into related technologies',
                'Regular review sessions would be beneficial'
            ],
            'engine_used': 'basic_insights'
        }
