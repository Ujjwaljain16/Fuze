from models import SavedContent

class BookmarkRepository:
    """Core repository for Bookmark/SavedContent aggregate"""
    
    def __init__(self, session):
        self._session = session

    def get_by_id(self, content_id: str) -> SavedContent:
        """Fetch bookmark by ID"""
        return self._session.query(SavedContent).get(content_id)

    def add(self, content: SavedContent):
        """Persist a new bookmark"""
        self._session.add(content)

    def get_unembedded(
        self,
        user_id: str = None,
        limit: int = 50,
    ) -> list[SavedContent]:
        """
        Fetch content items that have no embedding stored.
        Used by backfill job and background analysis service.
        """
        query = (
            self._session.query(SavedContent)
            .filter(SavedContent.embedding.is_(None))
        )
        if user_id:
            query = query.filter(SavedContent.user_id == user_id)
        return query.order_by(SavedContent.saved_at.asc()).limit(limit).all()
