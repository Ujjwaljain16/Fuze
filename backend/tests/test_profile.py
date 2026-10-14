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

    def test_saving_the_form_with_your_own_username_works(self, client, auth_headers, test_user):
        """The profile form always sends the username; keeping it and changing only the interests must save."""
        response = client.put('/api/profile', json={
            'username': test_user['username'],
            'technology_interests': 'Go, Postgres'
        }, headers=auth_headers)
        assert response.status_code == 200, response.json
        assert response.json['user']['technology_interests'] == 'Go, Postgres'
        assert client.get('/api/profile', headers=auth_headers).json['technology_interests'] == 'Go, Postgres'

    def test_update_returns_the_fields_the_page_shows(self, client, auth_headers, test_user):
        user = client.put('/api/profile', json={'username': test_user['username']}, headers=auth_headers).json['user']
        assert user['created_at'] and user['created_at'].endswith('Z')   # "Member Since"
        assert user['email'] == test_user['email']

    def test_username_is_unique_regardless_of_case_and_stored_lowercase(self, client, auth_headers, test_user, app):
        import uuid
        from models import db, User
        from blueprints.auth import hash_password
        tag = uuid.uuid4().hex[:8]
        with app.app_context():
            other = User(username=f'taken_{tag}', email=f'taken_{tag}@example.com', password_hash=hash_password('pw123456'))
            db.session.add(other)
            db.session.commit()
            other_id = other.id
        try:
            clash = client.put('/api/profile', json={'username': f'TAKEN_{tag}'}, headers=auth_headers)
            assert clash.status_code == 400 and clash.json['error'] == 'username_taken'

            mixed = client.put('/api/profile', json={'username': f'Fresh_{tag}'}, headers=auth_headers)
            assert mixed.status_code == 200
            assert mixed.json['user']['username'] == f'fresh_{tag}'
        finally:
            with app.app_context():
                db.session.delete(db.session.get(User, other_id))
                db.session.commit()

    def test_old_username_endpoint_accepts_your_own_name(self, client, auth_headers, test_user):
        """It used to answer 'an account already exists' for the caller's own current username."""
        response = client.post('/api/auth/update-username', json={'new_username': test_user['username']},
                               headers=auth_headers)
        assert response.status_code == 200, response.json

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
