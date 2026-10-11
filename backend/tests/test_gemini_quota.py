"""Per-user Gemini quotas reset with each window, however active the user is."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from freezegun import freeze_time


class _CountingRedis:
    """Enough of a Redis client for the quota counters, recording every TTL that is set."""
    def __init__(self):
        self.data, self.ttls = {}, {}

    def incr(self, key):
        self.data[key] = int(self.data.get(key, 0)) + 1
        return self.data[key]

    def expire(self, key, ttl):
        self.ttls.setdefault(key, []).append(ttl)

    def get(self, key):
        return None if key not in self.data else str(self.data[key]).encode()


@pytest.fixture
def manager(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'x' * 48)
    from services.multi_user_api_manager import MultiUserAPIManager
    client = _CountingRedis()

    def get_cache(key):
        raw = client.get(key)
        return None if raw is None else int(raw)
    redis_cache = SimpleNamespace(connected=True, redis_client=client, get_cache=get_cache)
    return MultiUserAPIManager(redis_client=redis_cache), client


def test_minute_limit_resets_in_the_next_minute_even_for_a_busy_user(manager):
    mgr, _ = manager
    with freeze_time('2026-10-12 10:00:05'):
        for _ in range(mgr.REQUESTS_PER_MINUTE):
            mgr.record_user_request(7)
        assert not mgr.check_user_rate_limit(7)['can_make_request']
    with freeze_time('2026-10-12 10:01:01'):
        assert mgr.check_user_rate_limit(7)['can_make_request']


def test_window_ttl_is_set_once_not_rearmed(manager):
    mgr, client = manager
    with freeze_time('2026-10-12 10:00:05'):
        for _ in range(5):
            mgr.record_user_request(7)
    assert all(len(ttls) == 1 for ttls in client.ttls.values())


def test_client_errors_do_not_trip_the_shared_gemini_breaker():
    """One user's bad key or 429 must not block Gemini for everybody."""
    from google.genai import errors as genai_errors
    from utils.gemini_utils import GeminiAnalyzer
    with patch('utils.gemini_utils.genai.Client') as client_cls, \
         patch('utils.gemini_utils.gemini_circuit_breaker') as breaker:
        breaker.allow_request.return_value = True
        client_cls.return_value.models.generate_content.side_effect = genai_errors.ClientError(
            401, {'error': {'code': 401, 'message': 'API key not valid', 'status': 'UNAUTHENTICATED'}})
        assert GeminiAnalyzer(api_key='bad')._make_gemini_request('hi') is None
    breaker.record_failure.assert_not_called()
