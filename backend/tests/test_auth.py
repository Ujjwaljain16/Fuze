"""
Unit tests for authentication blueprint
"""
import pytest

@pytest.mark.unit
class TestAuth:
    """Test authentication endpoints"""
    
    def test_register_success(self, client):
        """Test successful user registration"""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        response = client.post('/api/auth/register', json={
            'username': f'newuser_{unique_id}',
            'email': f'newuser_{unique_id}@example.com',
            'password': 'SecurePass123!',
            'name': 'New User'
        })
        assert response.status_code == 201
        data = response.json
        # Registration endpoint returns success message, not token
        assert 'message' in data
        assert 'success' in data['message'].lower() or 'registered' in data['message'].lower()
    
    def test_register_duplicate_username(self, client, test_user):
        """Test registration with duplicate username"""
        response = client.post('/api/auth/register', json={
            'username': test_user['username'],
            'email': 'different@example.com',
            'password': 'SecurePass123!',
            'name': 'Different User'
        })
        # 409 Conflict is the correct status for duplicate resources
        assert response.status_code in [400, 409]
        assert 'username' in response.json.get('message', '').lower() or 'already' in response.json.get('message', '').lower()
    
    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email"""
        response = client.post('/api/auth/register', json={
            'username': 'differentuser',
            'email': test_user['email'],
            'password': 'SecurePass123!',
            'name': 'Different User'
        })
        # 409 Conflict is the correct status for duplicate resources
        assert response.status_code in [400, 409]
        assert 'credentials' in response.json.get('message', '').lower() or 'already' in response.json.get('message', '').lower()
    
    def test_register_weak_password(self, client):
        """Test registration with weak password"""
        response = client.post('/api/auth/register', json={
            'username': 'weakuser',
            'email': 'weak@example.com',
            'password': '123',
            'name': 'Weak User'
        })
        assert response.status_code == 400
    
    def test_login_success(self, client, test_user):
        """Test successful login"""
        response = client.post('/api/auth/login', json={
            'email': test_user['email'],
            'password': test_user['password']
        })
        assert response.status_code == 200
        data = response.json
        assert 'access_token' in data
        assert 'user' in data
        assert data['user']['email'] == test_user['email']
    
    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password"""
        response = client.post('/api/auth/login', json={
            'email': test_user['email'],
            'password': 'wrongpassword'
        })
        assert response.status_code == 401
    
    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user"""
        response = client.post('/api/auth/login', json={
            'email': 'nonexistent@example.com',
            'password': 'anypassword'
        })
        assert response.status_code == 401
    
    def test_refresh_token(self, client, test_user):
        """Test token refresh"""
        # First login to get refresh token cookie
        login_response = client.post('/api/auth/login', json={
            'email': test_user['email'],
            'password': test_user['password']
        })
        assert login_response.status_code == 200
        
        # Verify cookie was set
        cookies = login_response.headers.getlist('Set-Cookie')
        assert any('refresh_token' in cookie for cookie in cookies), "Refresh token cookie not set"
        
        # Refresh endpoint requires refresh token from cookie, not access token from header
        # The refresh token is set as a cookie during login
        # Flask test client automatically preserves cookies between requests
        response = client.post('/api/auth/refresh')
        assert response.status_code == 200, f"Refresh failed: {response.json if hasattr(response, 'json') else response.data}"
        assert 'access_token' in response.json
    
    def test_logout(self, client, auth_headers):
        """Test logout"""
        response = client.post('/api/auth/logout', headers=auth_headers)
        assert response.status_code == 200


@pytest.mark.unit
class TestSupabaseOAuthProviderErrors:
    """A Supabase outage must not be reported to the user as a bad token."""

    @pytest.fixture(autouse=True)
    def supabase_env(self, monkeypatch):
        monkeypatch.setenv('SUPABASE_URL', 'https://project.supabase.example')
        monkeypatch.setenv('SUPABASE_ANON_KEY', 'anon')

    @staticmethod
    def _response(status_code):
        from unittest.mock import MagicMock
        resp = MagicMock()
        resp.status_code = status_code
        return resp

    def test_supabase_5xx_is_503(self, client, monkeypatch):
        monkeypatch.setattr('blueprints.auth.requests.get', lambda *a, **k: self._response(503))
        response = client.post('/api/auth/supabase-oauth', json={'access_token': 'tok'})
        assert response.status_code == 503
        assert response.json['error'] == 'auth_provider_unavailable'

    def test_supabase_timeout_is_503(self, client, monkeypatch):
        import requests

        def timeout(*a, **k):
            raise requests.Timeout('read timed out')
        monkeypatch.setattr('blueprints.auth.requests.get', timeout)
        response = client.post('/api/auth/supabase-oauth', json={'access_token': 'tok'})
        assert response.status_code == 503
        assert response.json == {'message': 'Sign-in service is unavailable, please try again',
                                 'error': 'auth_provider_unavailable'}

    def test_supabase_connection_error_is_503(self, client, monkeypatch):
        import requests

        def refused(*a, **k):
            raise requests.ConnectionError('connection refused')
        monkeypatch.setattr('blueprints.auth.requests.get', refused)
        response = client.post('/api/auth/supabase-oauth', json={'access_token': 'tok'})
        assert response.status_code == 503

    @pytest.mark.parametrize('status_code', [401, 403])
    def test_rejected_token_is_still_401(self, client, monkeypatch, status_code):
        monkeypatch.setattr('blueprints.auth.requests.get', lambda *a, **k: self._response(status_code))
        response = client.post('/api/auth/supabase-oauth', json={'access_token': 'tok'})
        assert response.status_code == 401
        assert response.json['message'] == 'Invalid Supabase token'

