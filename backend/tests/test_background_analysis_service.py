import pytest
from unittest.mock import MagicMock, patch
from services.background_analysis_service import BackgroundAnalysisService


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
        mock_analyzer.generate_json.return_value = {
            'summary': 'Instant primary summary', 'use_when': 'When learning Python',
            'key_concepts': ['python'], 'technologies': ['python'],
            'audience_level': 'beginner', 'content_type': 'tutorial', 'teaches_or_solves': [],
        }
        mock_db.session.query.return_value.filter_by.return_value.first.return_value = None
        mock_db.session.get_bind.return_value.dialect.name = 'sqlite'

        service._analyze_single_content(mock_content)

        # Exactly one model call (the structured profile)
        mock_analyzer.generate_json.assert_called_once()
        # Verify _make_gemini_request (second LLM call) was NEVER called!
        assert not hasattr(mock_analyzer, '_make_gemini_request') or mock_analyzer._make_gemini_request.call_count == 0


def _content():
    content = MagicMock()
    content.id = 77
    content.user_id = 1
    content.title = "Post"
    content.notes = ""
    content.extracted_text = "Body"
    content.url = "https://example.com/post"
    return content


@pytest.mark.unit
@pytest.mark.parametrize('outcome,expected', [
    # The live dashboard counts analyses in flight from these events: every started one must end.
    ('success', ['bookmark.pipeline.analysis.started', 'bookmark.pipeline.analysis.completed']),
    ('empty', ['bookmark.pipeline.analysis.started', 'bookmark.pipeline.analysis.failed']),
    ('crash', ['bookmark.pipeline.analysis.started', 'bookmark.pipeline.analysis.failed']),
    # Deferred until the user's key allowance resets: nothing ran, so nothing is announced.
    ('deferred', []),
])
def test_analysis_live_events_pair_started_with_an_outcome(outcome, expected):
    service = BackgroundAnalysisService()
    service.redis_cache = MagicMock()
    profile_kwargs = {'side_effect': RuntimeError('boom')} if outcome == 'crash' else {
        'return_value': None if outcome == 'empty' else {'summary': 'x'}}

    with patch('utils.event_bus.publish_pipeline_event') as publish, \
         patch('services.background_analysis_service.GeminiAnalyzer'), \
         patch('services.background_analysis_service.db'), \
         patch('services.multi_user_api_manager.check_user_rate_limit', return_value={'can_make_request': True}), \
         patch('services.multi_user_api_manager.get_user_api_key', return_value='' if outcome == 'deferred' else 'key'), \
         patch('services.multi_user_api_manager.record_user_request'), \
         patch('services.content_profile.generate_profile', **profile_kwargs), \
         patch('services.content_profile.store_profile'), \
         patch('services.content_profile.index_profile_chunk'), \
         patch('services.content_profile.analysis_payload', return_value={'summary': 'x'}), \
         patch('services.cache_invalidation_service.cache_invalidator'):
        service._analyze_single_content(_content())

    assert [c.kwargs['event_type'] for c in publish.call_args_list] == expected
