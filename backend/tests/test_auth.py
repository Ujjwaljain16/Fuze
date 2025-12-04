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
        assert 'email' in response.json.get('message', '').lower()
    
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

