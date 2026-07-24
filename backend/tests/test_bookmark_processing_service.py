import pytest
from unittest.mock import MagicMock, patch
from services.bookmark_processing_service import (
    process_bookmark_content_task,
    validate_embedding,
    truncate_title
)


def test_validate_embedding():
    assert validate_embedding([0.1] * 384) is True
    assert validate_embedding([0.1] * 10) is False
    assert validate_embedding(None) is False


def test_truncate_title():
    short_title = "Short Title"
    assert truncate_title(short_title) == "Short Title"

    long_title = "This is a very long title that exceeds the length limit " * 5
    truncated = truncate_title(long_title, max_len=50)
    assert len(truncated) <= 50
    assert truncated.endswith("...")


def test_process_bookmark_content_task_flow(app):
    with patch('services.bookmark_processing_service.UnitOfWork') as mock_uow_cls, \
         patch('services.bookmark_processing_service.extract_article_content') as mock_extract, \
         patch('services.bookmark_processing_service.generate_comprehensive_embedding') as mock_emb, \
         patch('services.bookmark_processing_service.redis_cache') as mock_redis:

        mock_uow = MagicMock()
        mock_uow_cls.return_value.__enter__.return_value = mock_uow

        mock_bookmark = MagicMock()
        mock_bookmark.title = 'Untitled Bookmark'
        mock_bookmark.notes = 'Notes'
        mock_uow.bookmarks.get_by_id.return_value = mock_bookmark
        mock_uow.bookmarks.get_by_id.return_value = mock_bookmark

        mock_extract.return_value = {
            'content': 'Scraped content \x00 with null bytes',
            'title': 'Scraped Title',
            'quality_score': 8
        }
        mock_emb.return_value = [0.1] * 384

        with patch('services.background_analysis_service.analyze_content') as mock_analyze:
            process_bookmark_content_task(bookmark_id=1, url='https://example.com', user_id=10)

            assert mock_bookmark.title == 'Scraped Title'
            assert '\x00' not in mock_bookmark.extracted_text
            assert mock_bookmark.quality_score == 8
            assert mock_bookmark.embedding == [0.1] * 384
