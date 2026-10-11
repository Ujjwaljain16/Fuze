"""Endpoints that used to fail every time, or fail after already succeeding."""
import time
from unittest.mock import patch

from flask_jwt_extended import create_access_token


def test_quick_save_succeeds_when_the_queue_is_down(client, auth_headers):
    """The bookmark is committed before the enqueue; a queue outage used to turn that into a 500."""
    with patch('services.task_queue.is_rq_available', return_value=False):
        response = client.post('/api/bookmarks/quick-save', json={'url': 'https://example.com/q', 'title': 'Q'},
                               headers=auth_headers)
    assert response.status_code == 201


def test_removed_analysis_endpoints_are_gone(client, auth_headers):
    for path in ('/api/recommendations/analysis/start-background', '/api/recommendations/analysis/batch-analyze'):
        assert client.post(path, json={}, headers=auth_headers).status_code in (404, 405)


def _oauth_user(app, password_set=False):
    from models import db, User
    from blueprints.auth import hash_password
    with app.app_context():
        meta = {'supabase_user_id': 'google-1'}
        if password_set:
            meta['password_set'] = True
        user = User(username=f'g_{time.time_ns()}', email=f'g{time.time_ns()}@example.com',
                    password_hash=hash_password('random-unknown-pw-1'), provider_name='google',
                    provider_user_id='google-1', user_metadata=meta)
        db.session.add(user)
        db.session.commit()
        return user.id


def test_google_account_can_set_its_first_password_after_a_recent_sign_in(client, app):
    user_id = _oauth_user(app)
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    response = client.post('/api/auth/set-password', json={'new_password': 'NewPassw0rd!'},
                           headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200, response.json

    from models import db, User
    with app.app_context():
        assert db.session.get(User, user_id).user_metadata.get('password_set') is True
    # from now on the current password is required, like any account
    response = client.post('/api/auth/set-password', json={'new_password': 'Another1Pass!'},
                           headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 400


def test_first_password_needs_a_recent_sign_in(client, app):
    user_id = _oauth_user(app)
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    with patch('blueprints.auth.time.time', return_value=time.time() + 3600):
        response = client.post('/api/auth/set-password', json={'new_password': 'NewPassw0rd!'},
                               headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 401
    assert response.json['error'] == 'recent_sign_in_required'
