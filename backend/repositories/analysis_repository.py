from typing import Optional, List
from models import ContentAnalysis


class AnalysisRepository:
    """Repository pattern implementation for managing ContentAnalysis entities."""

    def __init__(self, session):
        self.session = session

    def add(self, analysis: ContentAnalysis) -> ContentAnalysis:
        """Add new content analysis to the session."""
        self.session.add(analysis)
        return analysis

    def get_by_content_id(self, content_id: int) -> Optional[ContentAnalysis]:
        """Fetch content analysis by associated content ID."""
        return self.session.query(ContentAnalysis).filter_by(content_id=content_id).first()

    def get_by_id(self, analysis_id: int) -> Optional[ContentAnalysis]:
        """Fetch content analysis by primary key ID."""
        return self.session.get(ContentAnalysis, analysis_id)

    def delete_by_content_id(self, content_id: int) -> int:
        """Delete content analysis records for content ID."""
        count = self.session.query(ContentAnalysis).filter_by(content_id=content_id).delete()
        return count
