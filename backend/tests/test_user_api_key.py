"""
Unit tests for user API key blueprint
"""
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.unit
@pytest.mark.requires_db
class TestUserAPIKey:
    """Test user API key endpoints"""
    
    def test_add_api_key(self, client, auth_headers, test_user):
        """Test adding an API key"""
        with patch('blueprints.user_api_key.get_multi_user_api_manager') as mock_manager:
            mock_add_key = MagicMock(return_value=True)
            mock_manager.return_value = (mock_add_key, None, None, None, MagicMock())
            
            response = client.post('/api/user/api-key', json={
                'api_key': 'AIzaSyTest123456789012345678901234567890',
                'api_key_name': 'Test Key'
            }, headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json
            assert 'message' in data
    
    def test_add_api_key_invalid_format(self, client, auth_headers):
        """Test adding an API key with invalid format"""
        response = client.post('/api/user/api-key', json={
            'api_key': 'invalid-key',
            'api_key_name': 'Test Key'
        }, headers=auth_headers)
        
        assert response.status_code == 400
    
    def test_get_api_key_info(self, client, auth_headers, test_user, app):
        """Test getting API key info"""
        from models import db, User
        
        with app.app_context():
            user = User.query.get(test_user['id'])
            user.user_metadata = {
                'api_key': {
                    'name': 'Test Key',
                    'status': 'active',
                    'created_at': '2024-01-01T00:00:00'
                }
            }
            db.session.commit()
        
        response = client.get('/api/user/api-key', headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert 'has_api_key' in data
    
    def test_delete_api_key(self, client, auth_headers):
        """Test deleting an API key"""
        with patch('blueprints.user_api_key.get_multi_user_api_manager') as mock_manager:
            mock_manager.return_value = (None, None, None, None, MagicMock())
            
            response = client.delete('/api/user/api-key', headers=auth_headers)
            # May return 200 or 404 depending on whether key exists
            assert response.status_code in [200, 404]
    
    def test_get_api_key_status(self, client, auth_headers):
        """Test getting API key status"""
        response = client.get('/api/user/api-key/status', headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert 'has_api_key' in data



def test_a_saved_key_is_reported_after_a_restart_or_on_another_worker(app, client, auth_headers, test_user):
    """has_api_key read only a per-process in-memory map, so after a restart (or on the other
    gunicorn worker) users with a saved key were told to add one."""
    from sqlalchemy.orm.attributes import flag_modified
    from models import db, User
    from services.multi_user_api_manager import api_manager
    with app.app_context():
        user = db.session.get(User, test_user['id'])
        meta = dict(user.user_metadata or {})
        meta['api_key'] = {'encrypted': 'gAAAA-not-decrypted-here', 'status': 'active'}
        user.user_metadata = meta
        flag_modified(user, 'user_metadata')
        db.session.commit()
    with api_manager.lock:
        api_manager.user_api_keys.pop(test_user['id'], None)  # a fresh process knows nothing

    status = client.get('/api/user/api-key/status', headers=auth_headers)
    assert status.status_code == 200 and status.json['has_api_key'] is True
    summary = client.get('/api/dashboard/summary', headers=auth_headers)
    assert summary.status_code == 200 and summary.json['apiKeyStatus']['has_api_key'] is True


def test_no_saved_key_is_still_reported_as_none(app, client, auth_headers, test_user):
    from services.multi_user_api_manager import api_manager
    with api_manager.lock:
        api_manager.user_api_keys.pop(test_user['id'], None)
    status = client.get('/api/user/api-key/status', headers=auth_headers)
    assert status.status_code == 200 and status.json['has_api_key'] is False
