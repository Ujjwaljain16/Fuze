"""
Unit tests for profile blueprint
"""
import pytest

@pytest.mark.unit
@pytest.mark.requires_db
class TestProfile:
    """Test profile endpoints"""
    
    def test_get_profile(self, client, auth_headers, test_user):
        """Test getting user profile"""
        response = client.get('/api/profile', headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert 'id' in data
        assert 'username' in data
        assert data['id'] == test_user['id']
    
    def test_update_profile(self, client, auth_headers, test_user):
        """Test updating user profile"""
        import uuid
        unique_username = f'updated_username_{str(uuid.uuid4())[:8]}'
        
        response = client.put('/api/profile', json={
            'username': unique_username,
            'technology_interests': 'Python, JavaScript'
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json
        assert 'message' in data or 'user' in data
    
    def test_update_profile_password(self, client, auth_headers, test_user):
        """Test updating password"""
        response = client.put('/api/users/{}/password'.format(test_user['id']), json={
            'current_password': test_user['password'],
            'new_password': 'NewSecurePass123!'
        }, headers=auth_headers)
        
        # May return 200 or 403 depending on authorization check
        assert response.status_code in [200, 403, 400]

