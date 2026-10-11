"""Password changes end other sessions; failed passwords can't lock the real owner out."""
from unittest.mock import patch

import pytest


def _login(client, user):
    response = client.post('/api/auth/login', json={'email': user['email'], 'password': user['password']})
    assert response.status_code == 200, response.json
    return response.json


def test_password_change_ends_other_sessions(client, test_user):
    mine = _login(client, test_user)
    other = _login(client, test_user)

    with patch('core.sessions.mark_family_revoked') as mark:
        response = client.put(f"/api/users/{test_user['id']}/password",
                              json={'current_password': test_user['password'], 'new_password': 'NewPassw0rd!'},
                              headers={'Authorization': f"Bearer {mine['access_token']}"})
    assert response.status_code == 200
    assert mark.call_count == 1  # the other session's access tokens are blocked at once

    refreshed_other = client.post('/api/auth/refresh', headers={'Authorization': f"Bearer {other['refresh_token']}"})
    assert refreshed_other.status_code == 401
    refreshed_mine = client.post('/api/auth/refresh', headers={'Authorization': f"Bearer {mine['refresh_token']}"})
    assert refreshed_mine.status_code == 200


def test_access_tokens_of_a_revoked_family_are_rejected(client, test_user, patch_redis_for_tests):
    session = _login(client, test_user)
    headers = {'Authorization': f"Bearer {session['access_token']}"}
    assert client.get('/api/auth/verify', headers=headers).status_code == 200

    revoked_keys = set()
    patch_redis_for_tests.redis_client.setex.side_effect = lambda key, ttl, value: revoked_keys.add(key)
    patch_redis_for_tests.redis_client.exists.side_effect = lambda key: int(key in revoked_keys)
    assert client.post('/api/auth/logout', headers=headers).status_code == 200
    assert client.get('/api/auth/verify', headers=headers).status_code == 401


class _DictRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def incr(self, key):
        self.data[key] = int(self.data.get(key, 0)) + 1
        return self.data[key]

    def expire(self, key, seconds):
        return True

    def delete(self, key):
        self.data.pop(key, None)


@pytest.fixture
def throttle_store():
    store = _DictRedis()
    with patch('core.login_throttle._client', return_value=store):
        yield store


def _attempt(client, user, password, ip):
    return client.post('/api/auth/login', json={'email': user['email'], 'password': password},
                       environ_base={'REMOTE_ADDR': ip})


def test_guessing_from_one_client_does_not_lock_out_the_owner(client, test_user, throttle_store):
    for _ in range(6):
        assert _attempt(client, test_user, 'wrong-password', '203.0.113.9').status_code == 401
    # The guessing client is blocked even with the right password...
    assert _attempt(client, test_user, test_user['password'], '203.0.113.9').status_code == 401
    # ...but the owner on another network still gets in.
    assert _attempt(client, test_user, test_user['password'], '198.51.100.7').status_code == 200


def test_without_the_client_throttle_the_account_locks_after_five(client, test_user):
    with patch('core.login_throttle._client', return_value=None):
        for _ in range(5):
            _attempt(client, test_user, 'wrong-password', '203.0.113.9')
        assert _attempt(client, test_user, test_user['password'], '198.51.100.7').status_code == 401
