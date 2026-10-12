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


def test_validate_embedding_accepts_numpy_and_rejects_fallback_vectors():
    import numpy as np
    assert validate_embedding(np.full(384, 0.1, dtype=np.float32)) is True
    assert validate_embedding(np.zeros(384, dtype=np.float32)) is False
    bad = np.full(384, 0.1, dtype=np.float32)
    bad[3] = np.nan
    assert validate_embedding(bad) is False
    assert validate_embedding(np.full((2, 384), 0.1)) is False


def test_generate_embedding_task_persists_numpy_embedding(app):
    import numpy as np
    from services.bookmark_processing_service import generate_embedding_task
    emb = np.full(384, 0.2, dtype=np.float32)
    with patch('services.bookmark_processing_service.UnitOfWork') as mock_uow_cls,          patch('services.bookmark_processing_service.generate_comprehensive_embedding', return_value=emb),          patch('services.bookmark_processing_service.redis_cache'),          patch('services.background_analysis_service.analyze_content'):
        mock_uow = MagicMock()
        mock_uow_cls.return_value.__enter__.return_value = mock_uow
        bookmark = MagicMock(title='T', notes='', extracted_text='text', url='https://example.com')
        mock_uow.bookmarks.get_by_id.return_value = bookmark
        generate_embedding_task(bookmark_id=1, user_id=10)
        assert bookmark.embedding is emb
        assert bookmark.embedding_status == 'SUCCESS'


def _run_embedding_task(embedding=None, side_effect=None, events=None):
    """Run generate_embedding_task with mocks; return the event types it published, in order."""
    from services.bookmark_processing_service import generate_embedding_task
    with patch('services.bookmark_processing_service.UnitOfWork') as mock_uow_cls, \
         patch('services.bookmark_processing_service.generate_comprehensive_embedding',
               return_value=embedding, side_effect=side_effect), \
         patch('services.bookmark_processing_service.redis_cache'), \
         patch('services.background_analysis_service.analyze_content'), \
         patch('utils.event_bus.publish_pipeline_event') as publish:
        mock_uow = MagicMock()
        mock_uow_cls.return_value.__enter__.return_value = mock_uow
        mock_uow.bookmarks.get_by_id.return_value = MagicMock(
            title='T', notes='', extracted_text='text', url='https://example.com')
        events = [] if events is None else events
        try:
            generate_embedding_task(bookmark_id=1, user_id=10)
        finally:
            events.extend((c.kwargs['event_type'], c.kwargs['sequence']) for c in publish.call_args_list)
    return events


def test_embedding_task_publishes_started_then_completed(app):
    import numpy as np
    events = _run_embedding_task(np.full(384, 0.2, dtype=np.float32))
    assert events == [('bookmark.pipeline.embedding.started', 3),
                      ('bookmark.pipeline.embedding.completed', 4)]


def test_embedding_task_publishes_failed_for_an_unusable_vector(app):
    import numpy as np
    events = _run_embedding_task(np.zeros(384, dtype=np.float32))
    assert events[-1] == ('bookmark.pipeline.embedding.failed', 4)


def test_embedding_task_publishes_failed_and_reraises_when_the_model_is_down(app):
    from utils.embedding_utils import EmbeddingUnavailable
    events = []
    with pytest.raises(EmbeddingUnavailable):
        _run_embedding_task(side_effect=EmbeddingUnavailable('model missing'), events=events)
    assert events == [('bookmark.pipeline.embedding.started', 3),
                      ('bookmark.pipeline.embedding.failed', 4)]


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
         patch('services.bookmark_processing_service.redis_cache'):

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

        with patch('services.background_analysis_service.analyze_content'), \
             patch('core.feature_flags.is_enabled', return_value=False):
            process_bookmark_content_task(bookmark_id=1, url='https://example.com', user_id=10)

            assert mock_bookmark.title == 'Scraped Title'
            assert '\x00' not in mock_bookmark.extracted_text
            assert mock_bookmark.quality_score == 8
            # embeddings are produced by generate_embedding_task, not inline
            mock_emb.assert_not_called()


def test_embedding_task_enqueues_analysis_instead_of_running_it_inline(app):
    """A slow or failing Gemini call used to hold the embedding worker for all of its retries."""
    import numpy as np
    from services.bookmark_processing_service import generate_embedding_task
    queue = MagicMock()
    with patch('services.bookmark_processing_service.UnitOfWork') as mock_uow_cls, \
         patch('services.bookmark_processing_service.generate_comprehensive_embedding',
               return_value=np.full(384, 0.2, dtype=np.float32)), \
         patch('services.bookmark_processing_service.redis_cache'), \
         patch('services.background_analysis_service.analyze_content') as inline, \
         patch('services.task_queue.get_queue', return_value=queue) as get_queue, \
         patch('services.task_queue.enqueue_unique') as enqueue:
        mock_uow = MagicMock()
        mock_uow_cls.return_value.__enter__.return_value = mock_uow
        mock_uow.bookmarks.get_by_id.return_value = MagicMock(
            title='T', notes='', extracted_text='text', url='https://example.com')
        generate_embedding_task(bookmark_id=7, user_id=3)
    inline.assert_not_called()
    get_queue.assert_called_with('default')
    args, kwargs = enqueue.call_args
    assert args[2] == 'analyze_bookmark_7' or args[2].endswith('7')
    assert kwargs['kwargs'] == {'bookmark_id': 7, 'user_id': 3}
