"""POST /api/auth/fork-session: the browser extension gets a refresh-token family of its own."""


def _login(client, test_user):
    resp = client.post('/api/auth/login', json={'email': test_user['email'], 'password': test_user['password']})
    assert resp.status_code == 200
    return resp.json


def _fork(client, refresh_token):
    return client.post('/api/auth/fork-session', headers={'Authorization': f'Bearer {refresh_token}'})


def _refresh(client, refresh_token):
    return client.post('/api/auth/refresh', headers={'Authorization': f'Bearer {refresh_token}'})


def _family_id(app, token):
    from flask_jwt_extended import decode_token
    with app.app_context():
        return decode_token(token)['family_id']


def test_fork_returns_a_new_family_and_leaves_the_web_session_alone(app, test_user):
    client = app.test_client(use_cookies=False)
    web = _login(client, test_user)

    resp = _fork(client, web['refresh_token'])
    assert resp.status_code == 200, resp.get_json()
    ext = resp.json
    assert ext['access_token'] and ext['refresh_token']
    assert ext['user']['id'] == test_user['id']
    assert _family_id(app, ext['refresh_token']) != _family_id(app, web['refresh_token'])
    # The web app's own cookies must not be replaced.
    assert 'Set-Cookie' not in resp.headers

    # Both sessions now rotate independently; neither trips reuse detection for the other.
    ext_next = _refresh(client, ext['refresh_token'])
    assert ext_next.status_code == 200
    web_next = _refresh(client, web['refresh_token'])
    assert web_next.status_code == 200
    assert _refresh(client, ext_next.json['refresh_token']).status_code == 200


def test_fork_refuses_an_access_token(app, test_user):
    client = app.test_client(use_cookies=False)
    web = _login(client, test_user)
    resp = _fork(client, web['access_token'])
    assert resp.status_code == 401
    assert resp.json['error'] == 'invalid_refresh_token'


def test_fork_refuses_a_rotated_token_without_revoking_the_web_session(app, test_user):
    client = app.test_client(use_cookies=False)
    first = _login(client, test_user)['refresh_token']
    second = _refresh(client, first).json['refresh_token']

    assert _fork(client, first).status_code == 401
    # Unlike /refresh, a stale token here does not end the web app's session.
    assert _refresh(client, second).status_code == 200


def test_fork_refuses_a_revoked_family(app, test_user):
    client = app.test_client(use_cookies=False)
    web = _login(client, test_user)
    assert client.post('/api/auth/logout', headers={'Authorization': f"Bearer {web['access_token']}"}).status_code == 200
    assert _fork(client, web['refresh_token']).status_code == 401


def test_forked_session_keeps_the_original_sign_in_time(app, test_user):
    from datetime import datetime, timedelta
    from models import db, TokenFamily

    client = app.test_client(use_cookies=False)
    web = _login(client, test_user)
    long_ago = datetime(2020, 1, 1)
    with app.app_context():
        family = TokenFamily.query.filter_by(family_id=_family_id(app, web['refresh_token'])).one()
        family.created_at = long_ago
        db.session.commit()

    ext = _fork(client, web['refresh_token']).json
    with app.app_context():
        forked = TokenFamily.query.filter_by(family_id=_family_id(app, ext['refresh_token'])).one()
        created = forked.created_at.replace(tzinfo=None)
        assert abs(created - long_ago) < timedelta(seconds=1)


def test_fork_without_a_token_is_rejected(app):
    client = app.test_client(use_cookies=False)
    assert client.post('/api/auth/fork-session').status_code == 401
