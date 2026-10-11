"""API-key revocation list: revoked keys are detected, nothing else is, and keys are stored hashed."""
from types import SimpleNamespace

import pytest

from services.api_key_revocation_manager import APIKeyRevocationManager


class _MemoryRedis:
    def __init__(self):
        self.data = {}

    def set(self, key, value, ex=None):
        self.data[key] = value

    def exists(self, key):
        return int(key in self.data)

    def delete(self, *keys):
        return sum(1 for k in keys if self.data.pop(k, None) is not None)

    def keys(self, pattern):
        prefix = pattern.rstrip('*')
        return [k for k in self.data if k.startswith(prefix)]


@pytest.fixture
def manager(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'x' * 48)
    monkeypatch.delenv('REVOCATION_SECRET', raising=False)
    store = _MemoryRedis()
    return APIKeyRevocationManager(SimpleNamespace(connected=True, redis_client=store)), store


KEY = 'AIzaSyDummyKeyForTesting123456789012345'


def test_revoked_key_is_detected_and_others_are_not(manager):
    mgr, _ = manager
    assert mgr.revoke_api_key(KEY, user_id=1)
    assert mgr.is_api_key_revoked(KEY)
    assert not mgr.is_api_key_revoked('AIzaSyDifferentKeyForTesting123456789012')
    assert mgr.get_revoked_count() == 1


def test_unrevoke(manager):
    mgr, _ = manager
    mgr.revoke_api_key(KEY)
    assert mgr.remove_from_revocation_list(KEY)
    assert not mgr.is_api_key_revoked(KEY)


def test_keys_are_stored_as_keyed_hashes_only(manager):
    mgr, store = manager
    mgr.revoke_api_key(KEY)
    [stored] = store.data
    assert KEY not in stored
    other_secret = APIKeyRevocationManager(SimpleNamespace(connected=True, redis_client=_MemoryRedis()))
    other_secret._secret = b'another-deployment'
    assert other_secret._hash_api_key(KEY) != mgr._hash_api_key(KEY)


def test_clear_requires_confirmation(manager):
    mgr, _ = manager
    mgr.revoke_api_key(KEY)
    assert not mgr.clear_all_revocations()
    assert mgr.clear_all_revocations(confirm=True)
    assert mgr.get_revoked_count() == 0


def test_redis_down_fails_open_by_default(monkeypatch):
    monkeypatch.delenv('REVOCATION_FAIL_OPEN', raising=False)
    mgr = APIKeyRevocationManager(SimpleNamespace(connected=False, redis_client=None))
    assert not mgr.revoke_api_key(KEY)
    assert not mgr.is_api_key_revoked(KEY)
