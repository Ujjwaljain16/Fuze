from typing import List, Optional, Dict, Any
from sqlalchemy import func
from models import SavedContent, ContentAnalysis, UserFeedback

class RecommendationRepository:
    """Repository for managing saved bookmarks and their ML analyses"""
    
    def __init__(self, session):
        self.session = session

    def get_bookmark_by_id(self, content_id: int) -> Optional[SavedContent]:
        return self.session.get(SavedContent, content_id)

    def get_analysis_by_content_id(self, content_id: int) -> Optional[ContentAnalysis]:
        return self.session.query(ContentAnalysis).filter_by(content_id=content_id).first()

    def add_bookmark(self, bookmark: SavedContent):
        self.session.add(bookmark)
        return bookmark

    def delete_bookmark(self, bookmark: SavedContent):
        self.session.delete(bookmark)

    def add_feedback(self, feedback: UserFeedback):
        self.session.add(feedback)
        return feedback

    def get_user_bookmarks(self, user_id: int, limit: int = 50) -> List[SavedContent]:
        return self.session.query(SavedContent).filter_by(user_id=user_id).order_by(SavedContent.saved_at.desc()).limit(limit).all()

    def get_unanalyzed_bookmarks(self, user_id: int, limit: int = 10) -> List[SavedContent]:
        """Find bookmarks that don't have a content analysis yet"""
        return self.session.query(SavedContent).outerjoin(
            ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
        ).filter(
            SavedContent.user_id == user_id,
            ContentAnalysis.id.is_(None)
        ).limit(limit).all()

    def get_analysis_stats(self, user_id: int) -> Dict[str, Any]:
        """Get total, analyzed, and pending content counts for user analysis stats"""
        total_content = self.session.query(SavedContent).filter_by(user_id=user_id).count()
        analyzed_count = self.session.query(SavedContent).join(
            ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
        ).filter(SavedContent.user_id == user_id).count()
        pending_count = max(0, total_content - analyzed_count)
        return {
            'total_content': total_content,
            'analyzed_count': analyzed_count,
            'pending_count': pending_count
        }

    def get_user_preferences_data(self, user_id: int) -> Dict[str, Any]:
        """Aggregate user preference data including bookmark count, avg quality score, feedback stats, and top tags"""
        total_bookmarks = self.session.query(SavedContent).filter_by(user_id=user_id).count()
        avg_score_res = self.session.query(func.avg(SavedContent.quality_score)).filter_by(user_id=user_id).scalar()
        avg_quality_score = float(avg_score_res) if avg_score_res is not None else 0.0

        feedback_stats = self.session.query(
            UserFeedback.feedback_type,
            func.count(UserFeedback.id).label('count')
        ).filter_by(user_id=user_id).group_by(UserFeedback.feedback_type).all()

        # Compute top tags/technologies from bookmarks
        bookmarks = self.session.query(SavedContent.tags).filter_by(user_id=user_id).filter(SavedContent.tags.isnot(None)).all()
        tag_counts = {}
        for (tags_str,) in bookmarks:
            if tags_str:
                for tag in tags_str.split(','):
                    t = tag.strip().lower()
                    if t:
                        tag_counts[t] = tag_counts.get(t, 0) + 1
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            'total_bookmarks': total_bookmarks,
            'avg_quality_score': avg_quality_score,
            'feedback_stats': feedback_stats,
            'top_technologies': sorted_tags
        }

    def get_recent_bookmarks_for_learning(self, user_id: int, limit: int = 20) -> List[SavedContent]:
        """Retrieve recent bookmarks for user learning insights"""
        return self.session.query(SavedContent).filter_by(user_id=user_id).order_by(SavedContent.saved_at.desc()).limit(limit).all()

