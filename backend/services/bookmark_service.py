from typing import Dict, Any, Optional
from models import SavedContent
from uow.unit_of_work import UnitOfWork
from core.events import BookmarkCreated

class BookmarkService:
    """
    Orchestrates the persistence of Bookmark/SavedContent aggregates.
    Note: Currently handles ONLY persistence. Side effects (ML/Cache) 
    are kept procedural in the routes pending event handler migration.
    """
    
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    # --- Reads ---
    
    def get_bookmark(self, content_id: int) -> Optional[SavedContent]:
        """Fetch bookmark by ID"""
        return self.uow.bookmarks.get_by_id(content_id)

    def get_bookmark_by_url(self, user_id: int, url: str) -> Optional[SavedContent]:
        """Find exact URL match for user"""
        return self.uow.bookmarks.get_by_url(user_id, url)

    def get_bookmark_by_normalized_url(self, user_id: int, normalized_url: str) -> Optional[SavedContent]:
        """Find normalized URL match for user"""
        return self.uow.bookmarks.get_by_normalized_url(user_id, normalized_url)

    def search_bookmarks(self, user_id: int, query: str, limit: int = 10) -> list[SavedContent]:
        """Search bookmarks"""
        return self.uow.bookmarks.search_bookmarks(user_id, query, limit)

    def list_bookmarks(self, user_id: int, search: str = None, category: str = None, page: int = 1, per_page: int = 10):
        """List bookmarks with pagination and filtering"""
        return self.uow.bookmarks.list_bookmarks(user_id, search, category, page, per_page)

    def get_bookmark_stats(self, user_id: int, month_ago, week_ago, two_weeks_ago) -> Dict[str, Any]:
        """Get analytics and statistics for user's bookmarks"""
        total = self.uow.bookmarks.get_count(user_id)
        month_count = self.uow.bookmarks.get_count_since(user_id, month_ago)
        weekly = self.uow.bookmarks.get_count_since(user_id, week_ago)
        last_weekly = self.uow.bookmarks.get_count_before(user_id, week_ago) - self.uow.bookmarks.get_count_before(user_id, two_weeks_ago)
        
        # Adjust calculation logic safely here
        if last_weekly < 0:
            last_weekly = 0
            
        top_categories = self.uow.bookmarks.get_top_categories(user_id, limit=5)
        
        # Calculate trend
        if last_weekly > 0:
            trend = ((weekly - last_weekly) / last_weekly) * 100
        else:
            trend = 100 if weekly > 0 else 0
            
        return {
            'total': total,
            'month': month_count,
            'weekly': weekly,
            'trend': trend,
            'top_categories': [{'name': c[0], 'count': c[1]} for c in top_categories]
        }

    # --- Writes ---
    
    def create_bookmark(self, user_id: int, url: str, title: str = None, 
                        notes: str = None, tags: str = None, category: str = None,
                        extracted_text: str = None) -> SavedContent:
        """Create a new bookmark in the repository"""
        bookmark = SavedContent(
            user_id=user_id,
            url=url,
            title=title or '',
            notes=notes or '',
            tags=tags or '',
            category=category or 'other',
            extracted_text=extracted_text,
            quality_score=0
        )
        self.uow.bookmarks.add(bookmark)
        self.uow.flush()

        self.uow.emit(BookmarkCreated(
            bookmark_id=bookmark.id,
            user_id=user_id,
            url=url
        ))

        return bookmark

    def delete_bookmark(self, bookmark: SavedContent):
        """Delete a single bookmark"""
        self.uow.bookmarks.delete(bookmark)

    def delete_all_for_user(self, user_id: int) -> int:
        """Delete all bookmarks for a user"""
        return self.uow.bookmarks.delete_all_for_user(user_id)
