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
