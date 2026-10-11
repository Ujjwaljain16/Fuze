"""Ceilings on request size, import size, page size and shared Gemini usage."""
from types import SimpleNamespace
from unittest.mock import patch


def test_oversized_body_is_refused(client, auth_headers, app):
    with patch.dict(app.config, {'MAX_CONTENT_LENGTH': 1024}):
        response = client.post('/api/bookmarks', data='x' * 4096, content_type='application/json',
                               headers=auth_headers)
    assert response.status_code == 413


def test_import_is_capped(client, auth_headers):
    from blueprints.bookmarks import MAX_IMPORT_ITEMS
    items = [{'url': f'https://e.com/{i}', 'title': str(i)} for i in range(MAX_IMPORT_ITEMS + 1)]
    with patch('blueprints.bookmarks.MAX_IMPORT_ITEMS', 10):
        response = client.post('/api/bookmarks/import', json=items[:11], headers=auth_headers)
    assert response.status_code == 413


def test_per_page_is_capped(client, auth_headers):
    response = client.get('/api/bookmarks?per_page=100000', headers=auth_headers)
    assert response.status_code == 200
    assert response.json['per_page'] <= 100


class _Counter:
    def __init__(self):
        self.data = {}

    def incr(self, key):
        self.data[key] = self.data.get(key, 0) + 1
        return self.data[key]

    def expire(self, key, ttl):
        pass


def test_shared_gemini_key_has_a_daily_allowance_per_user(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'x' * 48)
    monkeypatch.setenv('GEMINI_API_KEY', 'system-key')
    from services import multi_user_api_manager as mm
    mgr = mm.MultiUserAPIManager(redis_client=SimpleNamespace(connected=True, redis_client=_Counter()))
    with patch.object(mm, 'SYSTEM_KEY_DAILY_LIMIT', 3):
        keys = [mgr._system_key_for(9, for_use=True) for _ in range(4)]
        assert keys == ['system-key'] * 3 + ['']
        assert mgr._system_key_for(9, for_use=False) == 'system-key'  # status checks aren't counted
        assert mgr._system_key_for(10, for_use=True) == 'system-key'  # other users unaffected


def test_empty_key_disables_gemini_instead_of_falling_back_to_the_system_key():
    from utils.gemini_utils import GeminiAnalyzer
    assert GeminiAnalyzer(api_key='').client is None
