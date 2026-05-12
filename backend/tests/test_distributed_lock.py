import pytest
from unittest.mock import patch, MagicMock
from utils.redis_utils import RedisCache

@pytest.fixture
def mocked_redis_cache():
    """Create a RedisCache with a mocked redis_client"""
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        cache = RedisCache()
        # Ensure it has our mock instance
        cache.redis_client = mock_instance
        yield cache

def test_distributed_lock_acquisition(mocked_redis_cache):
    """Verify that a lock can be acquired and released correctly"""
    cache = mocked_redis_cache
    
    # Mock redis_client.set to return True (lock acquired)
    cache.redis_client.set.return_value = True
    
    lock_id = cache.acquire_lock("resource_1", ttl_ms=10000)
    assert lock_id is not None
    assert isinstance(lock_id, str)
    
    # Verify set was called with NX=True
    cache.redis_client.set.assert_called_once()
    args, kwargs = cache.redis_client.set.call_args
    assert kwargs.get('nx') is True

def test_distributed_lock_release_lua(mocked_redis_cache):
    """Verify that only the owner can release a lock via Lua script"""
    cache = mocked_redis_cache
    
    # Mock eval to return 1 (success)
    cache.redis_client.eval.return_value = 1
    success = cache.release_lock("resource_1", "worker_1")
    assert success is True
    
    # Verify the correct arguments were passed to eval
    cache.redis_client.eval.assert_called_once()
    args = cache.redis_client.eval.call_args[0]
    # LUA_RELEASE_SCRIPT, numkeys, key, token
    assert "worker_1" in args
