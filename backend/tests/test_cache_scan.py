import pytest
from unittest.mock import patch, MagicMock
from utils.redis_utils import RedisCache

@pytest.fixture
def mocked_cache():
    """Create a RedisCache with a mocked redis_client"""
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        cache = RedisCache()
        cache.redis_client = mock_instance
        yield cache

def test_safe_delete_pattern_uses_scan(mocked_cache):
    """Verify that safe_delete_pattern uses SCAN instead of KEYS"""
    cache = mocked_cache
    
    # Mock scan to return a cursor and some keys
    # First call: (cursor=10, [key1, key2])
    # Second call: (cursor=0, [key3])
    cache.redis_client.scan.side_effect = [
        (10, [b"key1", b"key2"]),
        (0, [b"key3"])
    ]
    
    # Mock delete to avoid real calls
    cache.redis_client.delete.return_value = 1
    
    count = cache.safe_delete_pattern("test:*")
    
    # Check that scan was called twice
    assert cache.redis_client.scan.call_count == 2
    
    # Check that delete was called for every batch found
    # Iteration 1 had keys, Iteration 2 had keys.
    assert cache.redis_client.delete.call_count == 2
    # Total "deleted" count (sum of return values from delete - mocked to return 1 per call)
    assert count == 2

def test_deletion_batching(mocked_cache):
    """Verify deletion logic is called once per found batch"""
    cache = mocked_cache
    cache.redis_client.scan.return_value = (0, [b"k1", b"k2"])
    
    cache.safe_delete_pattern("any:*")
    # One batch deletion call for the found keys
    assert cache.redis_client.delete.call_count == 1
