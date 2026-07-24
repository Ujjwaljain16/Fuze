from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from models import SavedContent
from uow.unit_of_work import UnitOfWork
from core.events import BookmarkCreated, BookmarkDeleted


class BookmarkService:
    """
    Orchestrates the persistence of Bookmark/SavedContent aggregates.
    Enforces domain invariants, input validation, duplicate protection,
    and event emissions.
    """

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    # --- Reads ---

    def get_bookmark(self, content_id: int) -> Optional[SavedContent]:
        """Fetch bookmark by ID"""
        return self.uow.bookmarks.get_by_id(content_id)

    def get_bookmark_by_url(self, user_id: int, url: str) -> Optional[SavedContent]:
        """Find exact URL match for user"""
        if not user_id or not url:
            return None
        return self.uow.bookmarks.get_by_url(user_id, url.strip())

    def get_bookmark_by_normalized_url(self, user_id: int, normalized_url: str) -> Optional[SavedContent]:
        """Find normalized URL match for user"""
        if not user_id or not normalized_url:
            return None
        return self.uow.bookmarks.get_by_normalized_url(user_id, normalized_url.strip())

    def search_bookmarks(self, user_id: int, query: str, limit: int = 10) -> List[SavedContent]:
        """Search bookmarks"""
        if not user_id or not query:
            return []
        return self.uow.bookmarks.search_bookmarks(user_id, query, limit)

    def list_bookmarks(self, user_id: int, search: Optional[str] = None, category: Optional[str] = None, page: int = 1, per_page: int = 10):
        """List bookmarks with pagination and filtering"""
        return self.uow.bookmarks.list_bookmarks(user_id, search, category, page, per_page)

    def get_bookmark_stats(
        self,
        user_id: int,
        month_ago: Optional[datetime] = None,
        week_ago: Optional[datetime] = None,
        two_weeks_ago: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get analytics and statistics for user's bookmarks with accurate trend calculations.
        If date parameters are omitted, internally computes UTC date boundaries.
        """
        now = datetime.now(timezone.utc)
        if not week_ago:
            week_ago = now - timedelta(days=7)
        if not month_ago:
            month_ago = now - timedelta(days=30)
        if not two_weeks_ago:
            two_weeks_ago = now - timedelta(days=14)

        total = self.uow.bookmarks.get_count(user_id)
        month_count = self.uow.bookmarks.get_count_since(user_id, month_ago)
        this_week_count = self.uow.bookmarks.get_count_since(user_id, week_ago)

        # Accurate previous week window: count between two_weeks_ago and week_ago
        two_weeks_total = self.uow.bookmarks.get_count_since(user_id, two_weeks_ago)
        last_week_count = max(0, two_weeks_total - this_week_count)

        top_categories = self.uow.bookmarks.get_top_categories(user_id, limit=5)

        # Calculate percentage trend
        if last_week_count > 0:
            trend = round(((this_week_count - last_week_count) / last_week_count) * 100, 1)
        else:
            trend = 100.0 if this_week_count > 0 else 0.0

        return {
            'total': total,
            'month': month_count,
            'weekly': this_week_count,
            'trend': trend,
            'top_categories': [{'name': c[0], 'count': c[1]} for c in top_categories]
        }

    # --- Writes ---

    def create_bookmark(
        self,
        user_id: int,
        url: str,
        title: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[str] = None,
        category: Optional[str] = None,
        extracted_text: Optional[str] = None
    ) -> SavedContent:
        """
        Create a new bookmark with input validation and duplicate URL protection.
        """
        if not user_id or user_id <= 0:
            raise ValueError("Valid user_id is required")

        if not url or not isinstance(url, str) or not url.strip():
            raise ValueError("Valid URL is required")

        clean_url = url.strip()

        # Duplicate protection at service boundary
        existing = self.uow.bookmarks.get_by_url(user_id, clean_url)
        if existing:
            return existing

        bookmark = SavedContent(
            user_id=user_id,
            url=clean_url,
            title=(title or '').strip(),
            notes=(notes or '').strip(),
            tags=(tags or '').strip(),
            category=(category or 'other').strip(),
            extracted_text=extracted_text,
            quality_score=0
        )
        self.uow.bookmarks.add(bookmark)
        self.uow.flush()

        self.uow.emit(BookmarkCreated(
            bookmark_id=bookmark.id,
            user_id=user_id,
            url=clean_url
        ))

        return bookmark

    def delete_bookmark(self, bookmark: SavedContent):
        """Delete a single bookmark and emit BookmarkDeleted event."""
        if not bookmark:
            return
        bookmark_id = bookmark.id
        user_id = bookmark.user_id

        self.uow.bookmarks.delete(bookmark)
        self.uow.flush()

        self.uow.emit(BookmarkDeleted(
            bookmark_id=bookmark_id,
            user_id=user_id
        ))

    def delete_all_for_user(self, user_id: int) -> int:
        """Delete all bookmarks for a user."""
        if not user_id:
            return 0
        return self.uow.bookmarks.delete_all_for_user(user_id)
