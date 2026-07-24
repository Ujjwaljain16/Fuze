import pytest
from unittest.mock import MagicMock
from models import SavedContent
from services.bookmark_service import BookmarkService


@pytest.mark.unit
def test_bookmark_service_invariants_and_events():
    mock_uow = MagicMock()
    service = BookmarkService(mock_uow)

    # 1. Validation error on missing URL
    with pytest.raises(ValueError) as exc_info:
        service.create_bookmark(user_id=1, url="")
    assert "URL is required" in str(exc_info.value)

    # 2. Duplicate URL protection
    existing_bookmark = SavedContent(id=10, user_id=1, url="https://example.com/duplicate")
    mock_uow.bookmarks.get_by_url.return_value = existing_bookmark

    res = service.create_bookmark(user_id=1, url="https://example.com/duplicate")
    assert res.id == 10
    # Ensure add and emit were NOT called for duplicate!
    assert mock_uow.bookmarks.add.call_count == 0
    assert mock_uow.emit.call_count == 0

    # 3. Create Bookmark emits BookmarkCreated
    mock_uow.bookmarks.get_by_url.return_value = None
    created = service.create_bookmark(user_id=1, url="https://example.com/new", title="New Title")
    assert mock_uow.bookmarks.add.call_count == 1
    assert mock_uow.emit.call_count == 1
    event = mock_uow.emit.call_args[0][0]
    assert event.__class__.__name__ == 'BookmarkCreated'

    # 4. Delete Bookmark emits BookmarkDeleted
    mock_uow.emit.reset_mock()
    service.delete_bookmark(created)
    assert mock_uow.bookmarks.delete.call_count == 1
    assert mock_uow.emit.call_count == 1
    del_event = mock_uow.emit.call_args[0][0]
    assert del_event.__class__.__name__ == 'BookmarkDeleted'


@pytest.mark.unit
def test_bookmark_service_stats_trend_math():
    mock_uow = MagicMock()
    service = BookmarkService(mock_uow)

    mock_uow.bookmarks.get_count.return_value = 50
    mock_uow.bookmarks.get_count_since.side_effect = [30, 10, 15]  # month, this_week, two_weeks_total
    mock_uow.bookmarks.get_top_categories.return_value = [('tech', 20)]

    stats = service.get_bookmark_stats(user_id=1)
    assert stats['total'] == 50
    assert stats['month'] == 30
    assert stats['weekly'] == 10
    # last_week_count = max(0, 15 - 10) = 5
    # trend = ((10 - 5) / 5) * 100 = 100.0
    assert stats['trend'] == 100.0
