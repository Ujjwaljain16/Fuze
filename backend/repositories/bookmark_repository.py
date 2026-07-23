from sqlalchemy import func
from sqlalchemy.orm import joinedload
from models import SavedContent

class BookmarkRepository:
    """Core repository for Bookmark/SavedContent aggregate"""
    
    def __init__(self, session):
        self._session = session

    # --- CRUD ---

    def get_by_id(self, content_id: int) -> SavedContent:
        """Fetch bookmark by ID"""
        return self._session.query(SavedContent).get(content_id)

    def add(self, content: SavedContent):
        """Persist a new bookmark"""
        self._session.add(content)

    def delete(self, content: SavedContent):
        """Delete a bookmark"""
        self._session.delete(content)

    def delete_all_for_user(self, user_id: int) -> int:
        """Delete all bookmarks for a specific user. Returns number of deleted rows."""
        return self._session.query(SavedContent).filter_by(user_id=user_id).delete()

    # --- Lookup ---

    def get_by_url(self, user_id: int, url: str) -> SavedContent:
        """Find exact URL match for user"""
        return self._session.query(SavedContent).filter_by(user_id=user_id, url=url).first()

    def get_by_normalized_url(self, user_id: int, normalized_url: str) -> SavedContent:
        """Find normalized URL match for user"""
        return self._session.query(SavedContent).filter_by(user_id=user_id, url=normalized_url).first()

    def get_similar_by_domain_path(self, user_id: int, safe_domain_path: str) -> list[SavedContent]:
        """Find bookmarks sharing the same domain and path (used to detect duplicates with different query params)"""
        return self._session.query(SavedContent).filter(
            SavedContent.user_id == user_id,
            SavedContent.url.like(f"{safe_domain_path}%", escape='\\')
        ).all()
        
    def search_bookmarks(self, user_id: int, safe_query: str, limit: int = 10) -> list[SavedContent]:
        """Simple text search across title, notes, and tags"""
        from models import db
        from utils.query_sanitizer import sanitize_like_query
        clean_query = sanitize_like_query(safe_query) if safe_query else ''
        if not clean_query:
            return []
        return self._session.query(SavedContent).filter_by(user_id=user_id).filter(
            db.or_(
                SavedContent.title.ilike(f'%{clean_query}%', escape='\\'),
                SavedContent.notes.ilike(f'%{clean_query}%', escape='\\'),
                SavedContent.tags.ilike(f'%{clean_query}%', escape='\\')
            )
        ).limit(limit).all()

    def list_bookmarks(self, user_id: int, search: str = None, category: str = None, page: int = 1, per_page: int = 10):
        """List bookmarks with pagination and filtering"""
        from models import db
        query = self._session.query(SavedContent).options(joinedload(SavedContent.analyses)).filter_by(user_id=user_id)
        
        if search:
            from utils.query_sanitizer import sanitize_like_query
            safe_search = sanitize_like_query(search)
            if safe_search:
                query = query.filter(
                    db.or_(
                        SavedContent.title.ilike(f'%{safe_search}%', escape='\\'),
                        SavedContent.notes.ilike(f'%{safe_search}%', escape='\\'),
                        SavedContent.url.ilike(f'%{safe_search}%', escape='\\')
                    )
                )

        if category and category != 'all':
            if category.lower() in ('none', 'other', ''):
                query = query.filter(
                    db.or_(
                        SavedContent.category == category,
                        SavedContent.category.is_(None),
                        SavedContent.category == ''
                    )
                )
            else:
                query = query.filter(SavedContent.category == category)
                
        return query.order_by(SavedContent.saved_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    def get_all_by_user(self, user_id: int) -> list[SavedContent]:
        """Fetch all bookmarks for a user"""
        return self._session.query(SavedContent).filter_by(user_id=user_id).all()

    # --- Bookmark Stats ---

    def get_count(self, user_id: int) -> int:
        """Total bookmarks count for user"""
        return self._session.query(SavedContent).filter_by(user_id=user_id).count()

    def get_count_since(self, user_id: int, since_date) -> int:
        """Count bookmarks created since a specific date"""
        return self._session.query(SavedContent).filter(
            SavedContent.user_id == user_id,
            SavedContent.saved_at >= since_date
        ).count()
        
    def get_count_before(self, user_id: int, before_date) -> int:
        """Count bookmarks created before a specific date"""
        return self._session.query(SavedContent).filter(
            SavedContent.user_id == user_id,
            SavedContent.saved_at <= before_date
        ).count()

    def get_top_categories(self, user_id: int, limit: int = 5):
        """Get the top categories with counts for a user"""
        return self._session.query(
            SavedContent.category, 
            func.count(SavedContent.id)
        ).filter(
            SavedContent.user_id == user_id,
            SavedContent.category != None,
            SavedContent.category != ''
        ).group_by(
            SavedContent.category
        ).order_by(
            func.count(SavedContent.id).desc()
        ).limit(limit).all()
