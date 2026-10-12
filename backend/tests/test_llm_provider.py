"""An OpenAI-compatible provider (LLM_PROVIDER=openai_compat) serves every LLM call in a deployment."""
from unittest.mock import MagicMock, patch

import pytest
import requests

from utils import llm_provider
from utils.gemini_utils import GeminiAnalyzer

SECRET = 'closerouter_test_secret_value'


@pytest.fixture
def provider_on(monkeypatch):
    for name, value in {'LLM_PROVIDER': 'openai_compat', 'LLM_BASE_URL': 'https://api.example.test/v1',
                        'LLM_API_KEY': SECRET, 'LLM_MODEL': 'vendor/model-a',
                        'LLM_FALLBACK_MODEL': 'vendor/model-b'}.items():
        monkeypatch.setenv(name, value)
    from utils.unified_config import reload_config
    reload_config()
    yield
    monkeypatch.undo()
    reload_config()


def _response(status=200, body=None, headers=None):
    r = MagicMock()
    r.status_code = status
    r.headers = headers or {}
    r.json.return_value = body if body is not None else {}
    return r


def _ok(text='hello'):
    return _response(200, {'choices': [{'message': {'content': text}}]})


def test_off_by_default():
    assert llm_provider.is_active() is False
    assert llm_provider.active_key() is None


def test_incomplete_or_unsafe_settings_are_reported():
    from utils.unified_config import AIConfig
    ai = AIConfig()
    ai.llm_provider = 'openai_compat'
    ai.llm_base_url = ai.llm_api_key = ai.llm_model = None
    assert len(llm_provider.config_problems(ai)) == 3
    ai.llm_base_url, ai.llm_api_key, ai.llm_model = 'http://evil.example/v1', 'k', 'm'
    assert any('https' in p for p in llm_provider.config_problems(ai))
    ai.llm_base_url = 'http://localhost:8080/v1'
    assert llm_provider.config_problems(ai) == []
    ai.llm_base_url = 'https://user:pw@api.example.test/v1'
    assert any('credentials' in p for p in llm_provider.config_problems(ai))
    ai.llm_provider = 'something-else'
    assert any('LLM_PROVIDER' in p for p in llm_provider.config_problems(ai))


def test_a_partly_configured_provider_is_not_active(monkeypatch):
    from utils.unified_config import reload_config
    monkeypatch.setenv('LLM_PROVIDER', 'openai_compat')
    monkeypatch.setenv('LLM_API_KEY', 'k')  # no base URL, no model
    reload_config()
    try:
        assert llm_provider.is_active() is False  # falls back to Gemini instead of failing every call
    finally:
        monkeypatch.undo()
        reload_config()


def test_chat_sends_a_bearer_request_and_reads_the_reply():
    client = llm_provider.OpenAICompatClient('https://api.example.test/v1/', SECRET, timeout=5)
    with patch('utils.llm_provider.requests.post', return_value=_ok('  answer  ')) as post:
        assert client.chat('vendor/model-a', 'question', max_tokens=100, temperature=0.2) == 'answer'
    args, kwargs = post.call_args
    assert args[0] == 'https://api.example.test/v1/chat/completions'
    assert kwargs['headers']['Authorization'] == f'Bearer {SECRET}'
    assert kwargs['json']['messages'] == [{'role': 'user', 'content': 'question'}]
    assert kwargs['json']['max_tokens'] == 100 and 'response_format' not in kwargs['json']
    assert kwargs['timeout'] == 5


def test_json_mode_is_only_sent_when_enabled():
    with patch('utils.llm_provider.requests.post', return_value=_ok('{}')) as post:
        llm_provider.OpenAICompatClient('https://x.test/v1', 'k', 5, json_mode=True).chat('m', 'p', max_tokens=5, temperature=0, json_mode=True)
        assert post.call_args.kwargs['json']['response_format'] == {'type': 'json_object'}
        llm_provider.OpenAICompatClient('https://x.test/v1', 'k', 5, json_mode=False).chat('m', 'p', max_tokens=5, temperature=0, json_mode=True)
        assert 'response_format' not in post.call_args.kwargs['json']


@pytest.mark.parametrize('status, headers, exception, code', [
    (429, {'Retry-After': '3600'}, llm_provider.ProviderClientError, 429),
    (402, {}, llm_provider.ProviderClientError, 402),
    (401, {}, llm_provider.ProviderClientError, 401),
    (503, {}, llm_provider.ProviderServerError, None),
])
def test_errors_are_split_into_retryable_and_not(status, headers, exception, code):
    body = {'error': {'code': 'x', 'message': 'nope'}}
    with patch('utils.llm_provider.requests.post', return_value=_response(status, body, headers)):
        with pytest.raises(exception) as caught:
            llm_provider.OpenAICompatClient('https://x.test/v1', 'k', 5).chat('m', 'p', max_tokens=5, temperature=0)
    if code:
        assert caught.value.code == code


def test_a_rate_limit_carries_the_wait_in_the_form_the_cooldown_parser_reads():
    from core import gemini_quota
    with patch('utils.llm_provider.requests.post', return_value=_response(429, {}, {'Retry-After': '3600'})):
        with pytest.raises(llm_provider.ProviderClientError) as caught:
            llm_provider.OpenAICompatClient('https://x.test/v1', 'k', 5).chat('m', 'p', max_tokens=5, temperature=0)
    assert gemini_quota.parse_retry_seconds(str(caught.value)) == 3600


def test_network_failures_and_odd_replies_are_retryable_and_never_leak_the_prompt_or_key():
    client = llm_provider.OpenAICompatClient('https://x.test/v1', SECRET, 5)
    with patch('utils.llm_provider.requests.post', side_effect=requests.ConnectionError(f'secret prompt {SECRET}')):
        with pytest.raises(llm_provider.ProviderServerError) as caught:
            client.chat('m', 'secret prompt', max_tokens=5, temperature=0)
    assert SECRET not in str(caught.value) and 'secret prompt' not in str(caught.value)
    with patch('utils.llm_provider.requests.post', return_value=_response(200, {'unexpected': True})):
        with pytest.raises(llm_provider.ProviderServerError):
            client.chat('m', 'p', max_tokens=5, temperature=0)


def test_the_analyzer_uses_the_provider_and_never_touches_google(provider_on):
    with patch('utils.gemini_utils.genai.Client') as google, \
         patch('utils.llm_provider.requests.post', return_value=_ok('from provider')) as post, \
         patch('utils.gemini_utils.gemini_circuit_breaker') as breaker:
        breaker.allow_request.return_value = True
        analyzer = GeminiAnalyzer(api_key='AIza-a-users-own-gemini-key')  # ignored: the provider is in charge
        assert analyzer._make_gemini_request('hi') == 'from provider'
    google.assert_not_called()
    assert post.call_args.kwargs['json']['model'] == 'vendor/model-a'
    assert 'AIza' not in str(post.call_args)


def test_generate_json_parses_a_fenced_provider_reply(provider_on):
    fenced = '```json\n{"topics": ["rust"]}\n```'
    with patch('utils.llm_provider.requests.post', return_value=_ok(fenced)), \
         patch('utils.gemini_utils.gemini_circuit_breaker') as breaker:
        breaker.allow_request.return_value = True
        assert GeminiAnalyzer().generate_json('p') == {'topics': ['rust']}


def test_an_unknown_model_falls_back_to_the_second_model(provider_on):
    calls = []

    def post(url, json, **kwargs):
        calls.append(json['model'])
        return _response(404, {'error': {'code': 'model_not_found', 'message': 'no'}}) if len(calls) == 1 else _ok('fallback')
    with patch('utils.llm_provider.requests.post', side_effect=post), \
         patch('utils.gemini_utils.gemini_circuit_breaker') as breaker:
        breaker.allow_request.return_value = True
        assert GeminiAnalyzer()._make_gemini_request('hi') == 'fallback'
    assert calls == ['vendor/model-a', 'vendor/model-b']


@pytest.mark.parametrize('status, headers', [(429, {'Retry-After': '7200'}), (402, {})])
def test_rate_limit_or_empty_balance_stops_calls_to_the_provider(provider_on, status, headers):
    from core import gemini_quota
    with patch('utils.llm_provider.requests.post', return_value=_response(status, {}, headers)) as post, \
         patch('utils.gemini_utils.gemini_circuit_breaker') as breaker:
        breaker.allow_request.return_value = True
        analyzer = GeminiAnalyzer()
        assert analyzer._make_gemini_request('first') is None
        assert post.call_count == 1
        assert gemini_quota.cooldown_seconds(SECRET) > 0  # keyed by the provider key
        for _ in range(4):
            assert analyzer._make_gemini_request('again') is None
        assert post.call_count == 1  # no more requests while it is cooling down


def test_a_forced_gemini_analyzer_ignores_the_provider(provider_on):
    """A user's own key is validated against Google even when the deployment uses a provider."""
    with patch('utils.gemini_utils.genai.Client') as google, \
         patch('utils.llm_provider.requests.post') as post:
        analyzer = GeminiAnalyzer(api_key='AIza-users-key', provider='gemini')
    google.assert_called_once()
    assert google.call_args.kwargs['api_key'] == 'AIza-users-key'
    post.assert_not_called()
    assert analyzer._compat is None


def test_validate_key_checks_the_provider(provider_on):
    with patch('utils.llm_provider.requests.post', return_value=_ok('OK')):
        assert GeminiAnalyzer().validate_key() is True
    with patch('utils.llm_provider.requests.post', return_value=_response(401, {'error': {'code': 'invalid_api_key', 'message': 'bad'}})):
        assert GeminiAnalyzer().validate_key() is False


def test_nobody_needs_a_gemini_key_when_a_provider_is_configured(provider_on, app, test_user):
    from services.multi_user_api_manager import api_manager, get_user_api_key
    assert get_user_api_key(test_user['id']) == SECRET
    assert get_user_api_key(test_user['id'], for_use=False) == SECRET
    with app.app_context():
        stats = api_manager.get_user_api_stats(test_user['id'])
    assert stats['has_api_key'] is True and stats['api_key_status'] == 'active'
    assert api_manager.has_gemini_allowance(test_user['id']) is True


def test_the_key_is_never_part_of_the_status_response(provider_on, client, auth_headers):
    response = client.get('/api/user/api-key/status', headers=auth_headers)
    assert response.status_code == 200 and SECRET not in response.get_data(as_text=True)
