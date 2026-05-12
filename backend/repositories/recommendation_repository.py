from typing import List, Optional
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
