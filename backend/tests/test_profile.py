"""
Unit tests for profile blueprint
"""

import pytest

@pytest.mark.unit
@pytest.mark.requires_db
class TestProfile:
    """Test user profile endpoints"""

    def test_get_profile_success(self, client, auth_headers, test_user):
        """Test fetching profile data"""
        response = client.get('/api/profile', headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert data['id'] == test_user['id']
        assert data['username'] == test_user['username']

    def test_update_profile_dry(self, client, auth_headers, test_user):
        """Test updating profile via PUT /api/profile"""
        response = client.put('/api/profile', json={
            'username': 'new_valid_name',
            'technology_interests': 'Python, React, FastAPI'
        }, headers=auth_headers)

        assert response.status_code == 200
        data = response.json
        assert data['user']['username'] == 'new_valid_name'
        assert data['user']['technology_interests'] == 'Python, React, FastAPI'

    def test_update_user_compat_endpoint(self, client, auth_headers, test_user):
        """Test updating user via compatibility endpoint PUT /api/users/<id>"""
        user_id = test_user['id']
        response = client.put(f'/api/users/{user_id}', json={
            'username': 'compat_name',
            'technology_interests': 'Node.js'
        }, headers=auth_headers)

        assert response.status_code == 200
        assert response.json['user']['username'] == 'compat_name'

    def test_update_user_unauthorized_other(self, client, auth_headers):
        """Test attempting to update another user returns 403"""
        response = client.put('/api/users/99999', json={
            'username': 'hacked_name'
        }, headers=auth_headers)

        assert response.status_code == 403

    def test_change_password_weak(self, client, auth_headers, test_user):
        """Test changing password with password shorter than 8 characters returns 400"""
        user_id = test_user['id']
        response = client.put(f'/api/users/{user_id}/password', json={
            'current_password': 'testpassword123',
            'new_password': 'short'
        }, headers=auth_headers)

        assert response.status_code == 400
        assert 'at least 8 characters' in response.json['message']
