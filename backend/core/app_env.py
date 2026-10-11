"""
Single source of truth for "which environment is this process running in?".

APP_ENV wins; ENVIRONMENT and FLASK_ENV are read as fallbacks for older deployments.
When none is set the process is treated as production: a forgotten variable must
make the app stricter, never looser.
"""

import hashlib
import hmac
import os

DEVELOPMENT = 'development'
TESTING = 'testing'
PRODUCTION = 'production'

_ALIASES = {
    'dev': DEVELOPMENT, 'develop': DEVELOPMENT, 'local': DEVELOPMENT, DEVELOPMENT: DEVELOPMENT,
    'test': TESTING, 'tests': TESTING, TESTING: TESTING,
    'prod': PRODUCTION, 'staging': PRODUCTION, PRODUCTION: PRODUCTION,
}

# Values that shipped as code defaults at some point. Any of these in a deployed
# environment means anyone can forge session tokens.
KNOWN_DEFAULT_SECRETS = {
    'dev-secret-key-change-in-production',
    'dev-jwt-secret-change-in-production',
    'development-fallback-secret-key-do-not-use-in-prod',
    'your-secret-key-here',
    'your-jwt-secret-key-here',
    'change-me',
    'secret',
}

REQUIRED_SECRETS = ('SECRET_KEY', 'JWT_SECRET_KEY')
# Checked like the required ones when set, but may be left unset.
OPTIONAL_SECRETS = ('API_KEY_ENCRYPTION_KEY',)
_MIN_SECRET_LENGTH = 16


def app_env() -> str:
    raw = os.environ.get('APP_ENV') or os.environ.get('ENVIRONMENT') or os.environ.get('FLASK_ENV') or PRODUCTION
    # Unknown names (e.g. "preview") are deployed environments: treat them as production.
    return _ALIASES.get(raw.strip().lower(), PRODUCTION)


def is_production() -> bool:
    return app_env() == PRODUCTION


def is_testing() -> bool:
    return app_env() == TESTING


def is_development() -> bool:
    return app_env() == DEVELOPMENT


def secret_problems() -> list:
    """Reasons the configured secrets are unsafe for a deployed environment (empty when fine)."""
    problems = []
    for name in REQUIRED_SECRETS + OPTIONAL_SECRETS:
        value = os.environ.get(name, '')
        if not value:
            if name in REQUIRED_SECRETS:
                problems.append(f'{name} is not set')
        elif value in KNOWN_DEFAULT_SECRETS:
            problems.append(f'{name} is a published default value')
        elif len(value) < _MIN_SECRET_LENGTH:
            problems.append(f'{name} is shorter than {_MIN_SECRET_LENGTH} characters')
    return problems


def require_secrets() -> None:
    """Refuse to start a deployed environment with missing or default secrets."""
    if app_env() in (DEVELOPMENT, TESTING):
        return
    problems = secret_problems()
    if problems:
        raise RuntimeError(
            f"Refusing to start in {app_env()} with unsafe secrets: {'; '.join(problems)}. "
            "Set them as secrets on the host, or set APP_ENV=development for local work."
        )


def derived_secret(purpose: str) -> bytes:
    """A key for one purpose, derived from SECRET_KEY so each use is independent of the others."""
    base = os.environ.get('SECRET_KEY', '')
    if not base:
        if app_env() not in (DEVELOPMENT, TESTING):
            raise RuntimeError('SECRET_KEY is required')
        base = 'local-development-only'
    return hmac.new(base.encode(), purpose.encode(), hashlib.sha256).digest()
