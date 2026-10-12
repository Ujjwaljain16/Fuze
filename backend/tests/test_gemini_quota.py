"""A key that is out of quota is not called again until Google says it is back."""
import pytest
from unittest.mock import MagicMock, patch

from core import gemini_quota

GOOGLE_429 = ("429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota. "
              "* Quota exceeded for metric: generate_content_free_tier_requests, limit: 20, model: gemini-2.5-flash\n"
              "Please retry in 6h52m17.104265304s.', 'status': 'RESOURCE_EXHAUSTED'}}")


@pytest.mark.parametrize('message, expected', [
    (GOOGLE_429, 6 * 3600 + 52 * 60 + 17.1),
    ('Please retry in 45s', 45),
    ('Please retry in 2m5.5s.', 125.5),
    ("details: {'retryDelay': '24734s'}", 24734),
    ('quota exceeded', None),
    ('', None),
])
def test_google_retry_delay_is_read_from_the_error(message, expected):
    got = gemini_quota.parse_retry_seconds(message)
    assert (got is None) if expected is None else abs(got - expected) < 0.5


def test_cooldown_is_bounded_and_per_key():
    assert 6 * 3600 < gemini_quota.mark_exhausted('key-a', GOOGLE_429) < 7 * 3600
    assert gemini_quota.cooldown_seconds('key-a') > 6 * 3600
    assert gemini_quota.cooldown_seconds('key-b') == 0  # another user's key is unaffected
    assert gemini_quota.mark_exhausted('key-c', 'Please retry in 1s') == gemini_quota.MIN_COOLDOWN_SECONDS
    assert gemini_quota.mark_exhausted('key-d', 'Please retry in 999h') == gemini_quota.MAX_COOLDOWN_SECONDS
    assert gemini_quota.mark_exhausted('key-e', 'no hint') == gemini_quota.DEFAULT_COOLDOWN_SECONDS
    gemini_quota.clear('key-a')
    assert gemini_quota.cooldown_seconds('key-a') == 0


def test_the_key_itself_is_never_stored():
    client = MagicMock()
    with patch.object(gemini_quota, '_redis', return_value=client):
        gemini_quota.mark_exhausted('super-secret-key', 'Please retry in 60s')
    stored_key = client.setex.call_args.args[0]
    assert 'super-secret-key' not in stored_key and stored_key.startswith('gemini_cooldown:')


def _analyzer(key='key-x'):
    from utils.gemini_utils import GeminiAnalyzer
    with patch('utils.gemini_utils.genai.Client') as client_cls:
        analyzer = GeminiAnalyzer(api_key=key)
    return analyzer, client_cls.return_value.models.generate_content


def test_a_429_starts_a_cooldown_and_later_calls_make_no_request():
    from google.genai import errors as genai_errors
    analyzer, generate = _analyzer()
    generate.side_effect = genai_errors.ClientError(429, {'error': {'code': 429, 'message': GOOGLE_429, 'status': 'RESOURCE_EXHAUSTED'}})
    with patch('utils.gemini_utils.gemini_circuit_breaker') as breaker:
        breaker.allow_request.return_value = True
        assert analyzer._make_gemini_request('first') is None
        assert generate.call_count == 1
        assert gemini_quota.cooldown_seconds('key-x') > 6 * 3600
        for _ in range(5):
            assert analyzer._make_gemini_request('again') is None
        assert generate.call_count == 1  # five more bookmarks, zero more calls to Google
        breaker.record_failure.assert_not_called()  # a quota stop is not a Gemini outage


def test_the_reconciler_skips_a_user_whose_key_is_in_cooldown():
    from services.multi_user_api_manager import MultiUserAPIManager
    manager = MultiUserAPIManager()
    with patch.object(manager, 'check_user_rate_limit', return_value={'can_make_request': True}), \
         patch.object(manager, 'get_user_api_key', return_value='users-own-key'):
        assert manager.has_gemini_allowance(1) is True
        gemini_quota.mark_exhausted('users-own-key', 'Please retry in 2h')
        assert manager.has_gemini_allowance(1) is False


def test_analysis_during_a_cooldown_stays_pending_and_is_not_a_failure(app, test_user):
    from models import db, SavedContent
    from services.background_analysis_service import BackgroundAnalysisService
    gemini_quota.mark_exhausted('users-own-key', 'Please retry in 2h')
    with app.app_context():
        bookmark = SavedContent(user_id=test_user['id'], url='https://example.com/quota', title='T',
                                extracted_text='some text to analyze', embedding_status='SUCCESS')
        db.session.add(bookmark)
        db.session.commit()
        service = BackgroundAnalysisService.__new__(BackgroundAnalysisService)
        service.redis_cache = MagicMock()
        service._local_failed_analyses = set()
        with patch('services.multi_user_api_manager.get_user_api_key', return_value='users-own-key'), \
             patch('services.multi_user_api_manager.check_user_rate_limit', return_value={'can_make_request': True}), \
             patch('services.background_analysis_service.GeminiAnalyzer') as analyzer_cls, \
             patch('utils.event_bus.publish_pipeline_event') as publish:
            service._analyze_single_content(bookmark, user_id=test_user['id'], pipeline_run_id='run_x')
        analyzer_cls.assert_not_called()  # no client, no request
        publish.assert_not_called()       # nothing announced, so nothing left half-counted
        assert db.session.get(SavedContent, bookmark.id).analysis_status in (None, 'PENDING')
