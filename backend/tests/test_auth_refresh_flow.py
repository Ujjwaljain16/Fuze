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


class _DictRedis:
    """Just enough of a Redis client for the grace window: setex and get."""
    def __init__(self):
        self.data = {}

    def setex(self, key, ttl, value):
        self.data[key] = value if isinstance(value, bytes) else str(value).encode()

    def get(self, key):
        return self.data.get(key)

    def exists(self, key):
        return int(key in self.data)


def _with_grace_redis(monkeypatch):
    from utils.redis_utils import redis_cache
    fake = _DictRedis()
    monkeypatch.setattr(redis_cache, 'redis_client', fake)
    monkeypatch.setattr(redis_cache, 'connected', True)
    return fake


def test_a_lost_refresh_response_can_be_fetched_again_within_the_grace_window(app, test_user, monkeypatch):
    """Chrome may stop the extension's service worker after the server rotated but before it saved."""
    fake = _with_grace_redis(monkeypatch)
    client = app.test_client(use_cookies=False)
    first = _login(client, test_user)['refresh_token']
    lost = client.post('/api/auth/refresh', headers={'Authorization': f'Bearer {first}'}).json

    again = client.post('/api/auth/refresh', headers={'Authorization': f'Bearer {first}'})
    assert again.status_code == 200, again.get_json()
    assert again.json == lost  # the same pair, not a new rotation
    # The session is intact: the pair keeps rotating normally.
    assert client.post('/api/auth/refresh', headers={'Authorization': f"Bearer {lost['refresh_token']}"}).status_code == 200
    # Stored encrypted: Redis never holds a usable token in plain text.
    assert all(lost['refresh_token'].encode() not in v for v in fake.data.values())


def test_a_replay_after_the_pair_rotated_on_is_still_reuse(app, test_user, monkeypatch):
    _with_grace_redis(monkeypatch)
    client = app.test_client(use_cookies=False)
    first = _login(client, test_user)['refresh_token']
    second = client.post('/api/auth/refresh', headers={'Authorization': f'Bearer {first}'}).json['refresh_token']
    third = client.post('/api/auth/refresh', headers={'Authorization': f'Bearer {second}'}).json['refresh_token']

    # `first` was rotated into `second`, which is no longer current: no grace, the family is revoked.
    replay = client.post('/api/auth/refresh', headers={'Authorization': f'Bearer {first}'})
    assert replay.status_code == 401 and replay.json['error'] == 'session_compromised'
    assert client.post('/api/auth/refresh', headers={'Authorization': f'Bearer {third}'}).status_code == 401


def test_grace_can_be_turned_off(app, test_user, monkeypatch):
    import blueprints.auth as auth
    _with_grace_redis(monkeypatch)
    monkeypatch.setattr(auth, 'REFRESH_GRACE_SECONDS', 0)
    client = app.test_client(use_cookies=False)
    first = _login(client, test_user)['refresh_token']
    client.post('/api/auth/refresh', headers={'Authorization': f'Bearer {first}'})
    assert client.post('/api/auth/refresh', headers={'Authorization': f'Bearer {first}'}).status_code == 401
