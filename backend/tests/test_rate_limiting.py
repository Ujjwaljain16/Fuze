from unittest.mock import patch
from middleware.rate_limiting import get_user_rate_limit_key

def test_rate_limit_key_contains_user_identity(app):
    """Verify the rate limit key function uses JWT identity when present and falls back to remote address"""
    with app.test_request_context():
        with patch('flask_jwt_extended.get_jwt_identity', return_value='test-user'):
            key = get_user_rate_limit_key()
            assert key == 'user:test-user'
        
        with patch('flask_jwt_extended.get_jwt_identity', return_value=None):
            key = get_user_rate_limit_key()
            assert 'user:' not in key
