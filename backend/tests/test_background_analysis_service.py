import pytest
from unittest.mock import MagicMock, patch
from services.background_analysis_service import BackgroundAnalysisService


@pytest.mark.unit
def test_bg_analysis_failed_tracking_redis():
    mock_redis = MagicMock()
    mock_redis.connected = True
    service = BackgroundAnalysisService()
    service.redis_cache = mock_redis

    # Mark content 100 failed
    service._mark_failed(100)
    mock_redis.set_cache.assert_called_once_with("fuze:bg_analysis:failed:100", "1", ttl=86400)

    # Check content 100 failed
    mock_redis.get_cache.return_value = "1"
    assert service._is_failed(100) is True


@pytest.mark.unit
def test_bg_analysis_thread_restartability():
    service = BackgroundAnalysisService()
    mock_thread = MagicMock()
    mock_thread.is_alive.return_value = False  # Thread died!

    service.running = True
    service.analysis_thread = mock_thread

    with patch('threading.Thread') as mock_thread_cls:
        new_thread = MagicMock()
        mock_thread_cls.return_value = new_thread

        service.start_background_analysis()

        mock_thread_cls.assert_called_once()
        new_thread.start.assert_called_once()


@pytest.mark.unit
def test_bg_analysis_single_pass_summary_no_second_llm_call():
    mock_redis = MagicMock()
    mock_redis.connected = True

    service = BackgroundAnalysisService()
    service.redis_cache = mock_redis

    mock_content = MagicMock()
    mock_content.id = 50
    mock_content.user_id = 1
    mock_content.title = "Test Post"
    mock_content.notes = "Notes"
    mock_content.extracted_text = "Content"
    mock_content.url = "https://example.com"

    with patch('services.background_analysis_service.GeminiAnalyzer') as mock_analyzer_cls, \
         patch('services.background_analysis_service.db') as mock_db:

        mock_analyzer = MagicMock()
        mock_analyzer_cls.return_value = mock_analyzer
        mock_analyzer.analyze_bookmark_content.return_value = {
            'technologies': ['python'],
            'summary': 'Instant primary summary'
        }
        mock_db.session.query.return_value.filter_by.return_value.first.return_value = None

        service._analyze_single_content(mock_content)

        # Ensure single analyze_bookmark_content call was made
        mock_analyzer.analyze_bookmark_content.assert_called_once()
        # Verify _make_gemini_request (second LLM call) was NEVER called!
        assert not hasattr(mock_analyzer, '_make_gemini_request') or mock_analyzer._make_gemini_request.call_count == 0
