def _login(client, test_user):
    resp = client.post('/api/auth/login', json={'email': test_user['email'], 'password': test_user['password']})
    assert resp.status_code == 200
    assert resp.json.get('refresh_token'), "login must return the refresh token for cross-site clients"
    return resp.json


def test_refresh_with_refresh_token_in_header_rotates_tokens(app, test_user):
    """The SPA is cross-site, so its SameSite=Lax refresh cookie is never sent: it uses the header."""
    client = app.test_client(use_cookies=False)
    tokens = _login(client, test_user)
    resp = client.post('/api/auth/refresh', headers={'Authorization': f"Bearer {tokens['refresh_token']}"})
    assert resp.status_code == 200, resp.get_json()
    assert resp.json['access_token'] and resp.json['refresh_token'] != tokens['refresh_token']


def test_old_clients_sending_access_token_fall_back_to_cookie(client, test_user):
    """Previously the frontend sent the access token in Authorization; that must not shadow the cookie."""
    tokens = _login(client, test_user)
    resp = client.post('/api/auth/refresh', headers={'Authorization': f"Bearer {tokens['access_token']}"})
    assert resp.status_code == 200, resp.get_json()


def test_reusing_a_rotated_refresh_token_revokes_the_session(app, test_user):
    client = app.test_client(use_cookies=False)
    first = _login(client, test_user)['refresh_token']
    second = client.post('/api/auth/refresh', headers={'Authorization': f'Bearer {first}'}).json['refresh_token']

    replay = client.post('/api/auth/refresh', headers={'Authorization': f'Bearer {first}'})
    assert replay.status_code == 401
    # the whole family is revoked, so the legitimate latest token stops working too
    assert client.post('/api/auth/refresh', headers={'Authorization': f'Bearer {second}'}).status_code == 401


def test_refresh_without_any_token_is_rejected(app):
    client = app.test_client(use_cookies=False)
    resp = client.post('/api/auth/refresh')
    assert resp.status_code == 401 and resp.json['error'] == 'invalid_refresh_token'
