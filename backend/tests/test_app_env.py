"""The process environment is resolved in one place, and deployed environments fail closed on weak secrets."""
import subprocess
import sys
from pathlib import Path

import pytest

from core import app_env

BACKEND = Path(__file__).resolve().parents[1]
STRONG = 'x' * 48


@pytest.mark.parametrize('env,expected', [
    ({}, 'production'),
    ({'APP_ENV': 'dev'}, 'development'),
    ({'ENVIRONMENT': 'development'}, 'development'),
    ({'FLASK_ENV': 'testing'}, 'testing'),
    ({'APP_ENV': 'production', 'FLASK_ENV': 'development'}, 'production'),
    ({'APP_ENV': 'preview'}, 'production'),
])
def test_resolution(monkeypatch, env, expected):
    for name in ('APP_ENV', 'ENVIRONMENT', 'FLASK_ENV'):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    assert app_env.app_env() == expected


@pytest.mark.parametrize('secret,jwt_secret', [
    ('', STRONG),
    ('dev-secret-key-change-in-production', STRONG),
    (STRONG, 'dev-jwt-secret-change-in-production'),
    (STRONG, 'short'),
])
def test_production_rejects_weak_secrets(monkeypatch, secret, jwt_secret):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('SECRET_KEY', secret)
    monkeypatch.setenv('JWT_SECRET_KEY', jwt_secret)
    with pytest.raises(RuntimeError, match='unsafe secrets'):
        app_env.require_secrets()


def test_api_key_encryption_key_is_optional_but_checked_when_set(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('SECRET_KEY', STRONG)
    monkeypatch.setenv('JWT_SECRET_KEY', 'y' * 48)
    monkeypatch.delenv('API_KEY_ENCRYPTION_KEY', raising=False)
    app_env.require_secrets()  # not required

    monkeypatch.setenv('API_KEY_ENCRYPTION_KEY', 'z' * 16)
    app_env.require_secrets()  # 16+ characters is accepted

    for weak in ('short', 'change-me'):
        monkeypatch.setenv('API_KEY_ENCRYPTION_KEY', weak)
        with pytest.raises(RuntimeError, match='API_KEY_ENCRYPTION_KEY'):
            app_env.require_secrets()


def test_development_allows_defaults(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.delenv('SECRET_KEY', raising=False)
    app_env.require_secrets()


def test_derived_secrets_are_purpose_specific(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', STRONG)
    assert app_env.derived_secret('a') != app_env.derived_secret('b')


def test_app_refuses_to_boot_on_default_secrets():
    """End to end: a production process with the shipped defaults must exit, not serve."""
    env = {
        'APP_ENV': 'production', 'SECRET_KEY': 'dev-secret-key-change-in-production',
        'JWT_SECRET_KEY': 'dev-jwt-secret-change-in-production', 'DATABASE_URL': 'sqlite:///:memory:',
        'SKIP_STARTUP_VALIDATION': '1', 'PATH': '', 'SYSTEMROOT': __import__('os').environ.get('SYSTEMROOT', ''),
    }
    result = subprocess.run([sys.executable, '-c', 'import config'], cwd=BACKEND, env=env,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode != 0
    assert 'SECRET_KEY' in result.stderr
