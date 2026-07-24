import pytest
from unittest.mock import MagicMock, patch
from utils.redis_utils import RedisCache


@pytest.mark.unit
def test_redis_cache_sha256_hashing():
    with patch.object(RedisCache, '_try_connect', return_value=True):
        cache = RedisCache()
        content = "test content string"
        hashed = cache._hash_content(content)
        # Verify SHA-256 hex digest length (64 chars)
        assert len(hashed) == 64


@pytest.mark.unit
def test_redis_lock_acquire_extend_release():
    mock_redis = MagicMock()
    mock_redis.set.return_value = True
    mock_redis.eval.return_value = 1

    with patch.object(RedisCache, '_try_connect', return_value=True):
        cache = RedisCache()
        cache.redis_client = mock_redis
        cache.connected = True

        owner_id = cache.acquire_lock("resource_1", ttl_ms=60000)
        assert owner_id is not None

        extended = cache.extend_lock("resource_1", owner_id, ttl_ms=120000)
        assert extended is True

        released = cache.release_lock("resource_1", owner_id)
        assert released is True


@pytest.mark.unit
def test_redis_auto_reconnect_on_failure():
    with patch.object(RedisCache, '_try_connect', return_value=False):
        cache = RedisCache()
        assert cache.connected is False

        # When method is called, _ensure_connected attempts reconnection
        with patch.object(cache, '_try_connect', return_value=True) as mock_reconnect:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            cache.redis_client = mock_client

            assert cache._ensure_connected() is True
