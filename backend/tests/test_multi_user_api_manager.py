import pytest
from unittest.mock import MagicMock, patch
from services.multi_user_api_manager import MultiUserAPIManager, UserAPIKey, APIKeyStatus


@pytest.mark.unit
def test_user_api_key_dataclass():
    key = UserAPIKey(
        user_id=1,
        api_key_hash="hash123",
        api_key_name="Test Key",
        status=APIKeyStatus.ACTIVE,
        encrypted_key="enc123"
    )
    assert key.encrypted_key == "enc123"
    assert key.status == APIKeyStatus.ACTIVE


@pytest.mark.unit
def test_api_manager_encryption_decryption():
    manager = MultiUserAPIManager()
    raw_key = "AIzaSyTestApiKey1234567890"

    encrypted = manager.encrypt_api_key(raw_key)
    assert encrypted != raw_key

    decrypted = manager.decrypt_api_key(encrypted)
    assert decrypted == raw_key


@pytest.mark.unit
def test_get_user_api_key_revoked_returns_none():
    manager = MultiUserAPIManager()
    user_id = 99
    raw_key = "AIzaSyTestApiKey1234567890"
    encrypted = manager.encrypt_api_key(raw_key)

    user_api_key = UserAPIKey(
        user_id=user_id,
        api_key_hash=manager.hash_api_key(raw_key),
        api_key_name="Test Key",
        status=APIKeyStatus.ACTIVE,
        encrypted_key=encrypted
    )
    manager.user_api_keys[user_id] = user_api_key

    with patch('services.api_key_revocation_manager.get_revocation_manager') as mock_get_rev:
        mock_rev = MagicMock()
        mock_get_rev.return_value = mock_rev
        mock_rev.is_api_key_revoked.return_value = True

        res = manager.get_user_api_key(user_id)
        # Should return None for revoked user key, NOT system key!
        assert res is None


@pytest.mark.unit
def test_rate_limiting_redis():
    mock_redis = MagicMock()
    mock_redis.connected = True
    mock_redis.get_cache.return_value = "5"

    manager = MultiUserAPIManager(redis_client=mock_redis)
    status = manager.check_user_rate_limit(user_id=1)

    assert status['can_make_request'] is True
    assert status['requests_last_minute'] == 5


OLD_SECRET = 'old-secret-key-' + 'a' * 32
NEW_SECRET = 'new-secret-key-' + 'b' * 32
ENCRYPTION_KEY = 'api-key-encryption-' + 'c' * 32
RAW_KEY = 'AIzaSyTestApiKey1234567890abcdef'


def _manager(monkeypatch, secret, encryption_key=None):
    monkeypatch.setenv('SECRET_KEY', secret)
    monkeypatch.delenv('ENCRYPTION_SECRET', raising=False)
    if encryption_key:
        monkeypatch.setenv('API_KEY_ENCRYPTION_KEY', encryption_key)
    else:
        monkeypatch.delenv('API_KEY_ENCRYPTION_KEY', raising=False)
    return MultiUserAPIManager(redis_client=MagicMock())


def _read_stored_key(manager, user_id):
    with patch('services.api_key_revocation_manager.get_revocation_manager') as get_rev:
        get_rev.return_value.is_api_key_revoked.return_value = False
        return manager.get_user_api_key(user_id)


def _stored_ciphertext(user_id):
    from models import db, User
    db.session.expire_all()
    return db.session.get(User, user_id).user_metadata['api_key']['encrypted']


@pytest.mark.unit
def test_new_values_use_api_key_encryption_key_when_set(monkeypatch):
    with_key = _manager(monkeypatch, OLD_SECRET, ENCRYPTION_KEY)
    encrypted = with_key.encrypt_api_key(RAW_KEY)
    # Readable with the encryption key alone: SECRET_KEY plays no part.
    assert _manager(monkeypatch, NEW_SECRET, ENCRYPTION_KEY).decrypt_api_key(encrypted) == RAW_KEY
    assert _manager(monkeypatch, OLD_SECRET).decrypt_api_key(encrypted) is None


@pytest.mark.unit
@pytest.mark.parametrize('derivation', ['hkdf', 'legacy_sha256'])
def test_secret_key_ciphertext_moves_to_encryption_key_and_survives_secret_rotation(
        monkeypatch, app, test_user, derivation):
    import base64
    import hashlib
    from cryptography.fernet import Fernet
    from models import db, User

    old = _manager(monkeypatch, OLD_SECRET)
    if derivation == 'hkdf':
        encrypted = old.encrypt_api_key(RAW_KEY)
    else:
        legacy = Fernet(base64.urlsafe_b64encode(hashlib.sha256(OLD_SECRET.encode()).digest()))
        encrypted = legacy.encrypt(RAW_KEY.encode()).decode()

    with app.app_context():
        user = db.session.get(User, test_user['id'])
        user.user_metadata = {'api_key': {'encrypted': encrypted, 'hash': old.hash_api_key(RAW_KEY),
                                          'name': 'k', 'status': 'active'}}
        db.session.commit()

        # Set the new key: the old value still decrypts, and is re-encrypted with the new key.
        assert _read_stored_key(_manager(monkeypatch, OLD_SECRET, ENCRYPTION_KEY), test_user['id']) == RAW_KEY
        migrated = _stored_ciphertext(test_user['id'])
        assert migrated != encrypted
        assert _manager(monkeypatch, 'unrelated-secret-' + 'd' * 32, ENCRYPTION_KEY).decrypt_api_key(migrated) == RAW_KEY

        # Rotate SECRET_KEY afterwards: the stored key still decrypts and nothing is rewritten.
        assert _read_stored_key(_manager(monkeypatch, NEW_SECRET, ENCRYPTION_KEY), test_user['id']) == RAW_KEY
        assert _stored_ciphertext(test_user['id']) == migrated


@pytest.mark.unit
def test_reencrypt_all_moves_unused_keys_before_secret_rotation(monkeypatch, app, test_user):
    from models import db, User

    old = _manager(monkeypatch, OLD_SECRET)
    with app.app_context():
        user = db.session.get(User, test_user['id'])
        user.user_metadata = {'api_key': {'encrypted': old.encrypt_api_key(RAW_KEY), 'name': 'k',
                                          'status': 'active'}, 'other': 'kept'}
        db.session.commit()

        counts = _manager(monkeypatch, OLD_SECRET, ENCRYPTION_KEY).reencrypt_all_stored_keys()
        assert counts['reencrypted'] >= 1
        db.session.expire_all()
        metadata = db.session.get(User, test_user['id']).user_metadata
        assert metadata['other'] == 'kept' and metadata['api_key']['name'] == 'k'

        rotated = _manager(monkeypatch, NEW_SECRET, ENCRYPTION_KEY)
        assert rotated._decrypt_with_source(metadata['api_key']['encrypted']) == (RAW_KEY, False)
        # A second run finds nothing left to move for this user.
        again = _manager(monkeypatch, OLD_SECRET, ENCRYPTION_KEY)
        before = metadata['api_key']['encrypted']
        again.reencrypt_all_stored_keys()
        assert _stored_ciphertext(test_user['id']) == before


@pytest.mark.unit
def test_without_encryption_key_legacy_values_still_move_to_secret_key_hkdf(monkeypatch, app, test_user):
    import base64
    import hashlib
    from cryptography.fernet import Fernet
    from models import db, User

    legacy = Fernet(base64.urlsafe_b64encode(hashlib.sha256(OLD_SECRET.encode()).digest()))
    with app.app_context():
        user = db.session.get(User, test_user['id'])
        user.user_metadata = {'api_key': {'encrypted': legacy.encrypt(RAW_KEY.encode()).decode(),
                                          'name': 'k', 'status': 'active'}}
        db.session.commit()

        manager = _manager(monkeypatch, OLD_SECRET)
        assert _read_stored_key(manager, test_user['id']) == RAW_KEY
        migrated = _stored_ciphertext(test_user['id'])
        assert manager._decrypt_with_source(migrated) == (RAW_KEY, False)
