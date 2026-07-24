from datetime import datetime, timezone
from typing import Dict, Any, Optional
from collections import Counter
from models import UserFeedback
from core.events import RecommendationFeedbackRecorded
from core.logging_config import get_logger

logger = get_logger(__name__)

VALID_FEEDBACK_TYPES = {"helpful", "not_relevant", "clicked", "saved", "like", "dislike", "completed"}
DEFAULT_LEARNING_STYLE = "adaptive"


class RecommendationService:
    """
    Service for managing recommendation persistence and feedback loops.
    Focuses strictly on pure persistence tasks without ML engine coupling.
    """

    def __init__(self, uow):
        self.uow = uow

    def record_feedback(
        self,
        user_id: int,
        content_id: int,
        feedback_type: str,
        recommendation_id: Optional[int] = None,
        feedback_data: Optional[Dict[str, Any]] = None
    ) -> UserFeedback:
        """
        Validate, verify ownership, and record user feedback to database.
        Emits RecommendationFeedbackRecorded event.
        """
        if not user_id or user_id <= 0:
            raise ValueError("Valid user_id is required")

        if not feedback_type or feedback_type.lower() not in VALID_FEEDBACK_TYPES:
            raise ValueError(f"Invalid feedback_type '{feedback_type}'. Must be one of {sorted(VALID_FEEDBACK_TYPES)}")

        clean_feedback_type = feedback_type.lower()

        # Ownership and existence verification
        content = self.uow.bookmarks.get_by_id(content_id)
        if not content:
            raise ValueError(f"Content {content_id} not found")

        if content.user_id != user_id:
            raise PermissionError(f"Content {content_id} does not belong to user {user_id}")

        feedback = UserFeedback(
            user_id=user_id,
            content_id=content_id,
            recommendation_id=recommendation_id,
            feedback_type=clean_feedback_type,
            context_data=feedback_data or {},
            timestamp=datetime.now(timezone.utc)
        )

        self.uow.recommendations.add_feedback(feedback)
        self.uow.flush()

        self.uow.emit(
            RecommendationFeedbackRecorded(
                user_id=user_id,
                content_id=content_id,
                recommendation_id=recommendation_id,
                feedback_type=clean_feedback_type,
            )
        )

        return feedback

    def get_analysis_stats(self, user_id: int) -> Dict[str, Any]:
        """Get aggregate statistics about content analysis for a user."""
        if not user_id:
            return {}

        stats = self.uow.recommendations.get_analysis_stats(user_id)
        total_user_content = stats.get('total_content', 0)
        analyzed_user_content = stats.get('analyzed_count', 0)
        pending_analysis = stats.get('pending_count', 0)

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
        if not user_id:
            return {}

        data = self.uow.recommendations.get_user_preferences_data(user_id)

        content_stats = {
            'total_bookmarks': data.get('total_bookmarks', 0),
            'avg_quality_score': data.get('avg_quality_score', 0.0)
        }

        raw_feedback = data.get('feedback_stats', [])
        if isinstance(raw_feedback, dict):
            feedback_patterns = raw_feedback
        elif isinstance(raw_feedback, list):
            feedback_patterns = {
                (stat.feedback_type if hasattr(stat, 'feedback_type') else stat[0]): (stat.count if hasattr(stat, 'count') else stat[1])
                for stat in raw_feedback
            }
        else:
            feedback_patterns = {}

        return {
            'user_id': user_id,
            'feedback_patterns': feedback_patterns,
            'content_statistics': content_stats,
            'top_technologies': [{'technology': tag, 'count': count} for tag, count in data.get('top_technologies', []) if tag],
            'learning_style': DEFAULT_LEARNING_STYLE
        }

    def get_learning_insights(self, user_id: int) -> Dict[str, Any]:
        """Aggregate basic learning insights for the user without fake metrics."""
        if not user_id:
            return {}

        recent_bookmarks = self.uow.recommendations.get_recent_bookmarks_for_learning(user_id=user_id, limit=20)

        technologies = []
        for bookmark in recent_bookmarks:
            if getattr(bookmark, 'tags', None):
                tags_list = bookmark.tags.split(',') if isinstance(bookmark.tags, str) else bookmark.tags
                if isinstance(tags_list, list):
                    for tag in tags_list:
                        if tag and tag.strip():
                            technologies.append(tag.strip().lower())

        tech_counter = Counter(technologies)

        return {
            'user_id': user_id,
            'learning_trends': {
                'recent_technologies': dict(tech_counter.most_common(10)),
                'learning_velocity': len(recent_bookmarks)
            },
            'recommendations': [
                'Continue exploring your current technology stack',
                'Consider diversifying into related technologies',
                'Regular review sessions would be beneficial'
            ],
            'engine_used': 'basic_insights'
        }
