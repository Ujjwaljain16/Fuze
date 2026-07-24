import pytest
from unittest.mock import MagicMock
from services.api_key_revocation_manager import APIKeyRevocationManager


def test_per_key_ttl_and_hmac_hashing():
    mock_redis = MagicMock()
    mock_redis.connected = True
    mock_redis.redis_client = MagicMock()

    manager = APIKeyRevocationManager(redis_cache=mock_redis)

    test_key = "AIzaSy_test_secret_api_key_12345"

    # 1. Revoke key
    assert manager.revoke_api_key(test_key, user_id=42) is True
    # Verify set(ex=...) was called on individual key
    mock_redis.redis_client.set.assert_called_once()
    redis_key_arg = mock_redis.redis_client.set.call_args[0][0]
    assert redis_key_arg.startswith("fuze:revoked:")
    assert mock_redis.redis_client.set.call_args[1].get('ex') == 7 * 24 * 60 * 60

    # 2. Check revoked status (EXISTS)
    mock_redis.redis_client.exists.return_value = 1
    assert manager.is_api_key_revoked(test_key) is True

    # 3. Unrevoke key (DELETE)
    mock_redis.redis_client.delete.return_value = 1
    assert manager.remove_from_revocation_list(test_key) is True

    # 4. Invalid input validation
    with pytest.raises(ValueError):
        manager._hash_api_key("")

    with pytest.raises(ValueError):
        manager._hash_api_key(None)

    # 5. Clear all without confirmation blocked
    assert manager.clear_all_revocations(confirm=False) is False
