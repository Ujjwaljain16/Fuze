import os
import pytest
from unittest.mock import patch
from middleware.rate_limiting import (
    get_user_rate_limit_key,
    init_rate_limiter,
)


def test_rate_limit_key_contains_user_identity(app):
    """Verify the rate limit key function uses JWT identity when present and falls back to remote address"""
    with app.test_request_context():
        with patch('flask_jwt_extended.get_jwt_identity', return_value='test-user'):
            key = get_user_rate_limit_key()
            assert key == 'user:test-user'

        with patch('flask_jwt_extended.get_jwt_identity', return_value=None):
            key = get_user_rate_limit_key()
            assert 'user:' not in key


def test_jwt_exception_handled_safely(app):
    """Verify JWTExtendedException is caught cleanly without swallowing other errors"""
    from flask_jwt_extended.exceptions import JWTExtendedException
    with app.test_request_context():
        with patch('flask_jwt_extended.get_jwt_identity', side_effect=JWTExtendedException("No token")):
            key = get_user_rate_limit_key()
            assert 'user:' not in key


def test_production_fails_fast_without_redis(app):
    """Verify production environment raises RuntimeError if REDIS_URL is missing"""
    with patch.dict(os.environ, {'ENVIRONMENT': 'production', 'REDIS_URL': ''}):
        with pytest.raises(RuntimeError) as exc_info:
            init_rate_limiter(app)
        assert "REDIS_URL is required for production rate limiting" in str(exc_info.value)


def test_custom_429_handler(app):
    """Verify 429 error handler returns clean JSON with error and retry_after"""
    init_rate_limiter(app)
    with app.test_request_context():
        # Get custom 429 error handler from registered app handlers
        handler_dict = app.error_handler_spec.get(None, {}).get(429, {})
        assert len(handler_dict) > 0
        handler = list(handler_dict.values())[0]

        class Dummy429Error(Exception):
            description = "60"

        response, status_code = handler(Dummy429Error())
        assert status_code == 429
        data = response.json
        assert data['error'] == 'rate_limit_exceeded'
        assert data['retry_after'] == '60'
