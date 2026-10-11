import pytest

from utils.cors_utils import is_allowed_origin


@pytest.mark.parametrize("origin", [
    "https://itsfuze.vercel.app",
    "https://itsfuze-abc123-ujjwaljain16s-projects.vercel.app",
    "https://itsfuze-git-feature-x-ujjwaljain16s-projects.vercel.app",
    "http://localhost:5173",
])
def test_own_origins_allowed(origin):
    assert is_allowed_origin(origin)


@pytest.mark.parametrize("origin", [
    "https://evil.vercel.app",
    "https://itsfuze.vercel.app.evil.com",
    "https://notitsfuze-abc.vercel.app",
    "https://itsfuze-attacker.vercel.app",  # a project name anyone can claim
    "https://itsfuze-x-ujjwaljain16s-projects.vercel.app.evil.com",
    "http://itsfuze-abc.vercel.app",
    "https://evil.com",
    None,
])
def test_other_origins_rejected(origin):
    assert not is_allowed_origin(origin)


@pytest.fixture
def fresh_origins(monkeypatch):
    import utils.cors_utils as cors
    monkeypatch.setattr(cors, '_cached_origins', None)
    yield cors
    monkeypatch.setattr(cors, '_cached_origins', None)


def test_production_rejects_localhost_and_wildcards(fresh_origins, monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('CORS_ORIGINS', 'chrome-extension://*,https://admin.example.com')
    assert not fresh_origins.is_allowed_origin('http://localhost:5173')
    assert not fresh_origins.is_allowed_origin('chrome-extension://abcdefghijklmnop')
    assert fresh_origins.is_allowed_origin('https://admin.example.com')
    assert fresh_origins.is_allowed_origin('https://itsfuze.vercel.app')


def test_specific_extension_origin(fresh_origins, monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('EXTENSION_ID', 'abcdefghijklmnop')
    assert fresh_origins.is_allowed_origin('chrome-extension://abcdefghijklmnop')
    assert not fresh_origins.is_allowed_origin('chrome-extension://someoneelse')


def test_api_responses_carry_security_headers(client):
    headers = client.get('/health/liveness').headers
    assert headers['Content-Security-Policy'].startswith("default-src 'none'")
    assert 'max-age' in headers['Strict-Transport-Security']
    assert headers['X-Content-Type-Options'] == 'nosniff'
