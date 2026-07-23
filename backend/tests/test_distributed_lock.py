import pytest
from unittest.mock import patch, MagicMock
from core.distributed_lock import DistributedLock, synchronized


def test_distributed_lock_acquisition_and_release():
    mock_client = MagicMock()
    mock_client.set.return_value = True
    mock_script = MagicMock()
    mock_script.return_value = 1
    mock_client.register_script.return_value = mock_script

    with patch('core.distributed_lock.redis_cache') as mock_cache:
        mock_cache.redis_client = mock_client
        lock = DistributedLock("resource_1", ttl_ms=10000)

        assert lock.acquire() is True
        assert lock.locked is True
        mock_client.set.assert_called_once_with(
            "lock:resource_1", lock.owner_id, nx=True, px=10000
        )

        assert lock.release() is True
        assert lock.locked is False
        mock_script.assert_called_once_with(
            keys=["lock:resource_1"], args=[lock.owner_id]
        )


def test_distributed_lock_context_manager():
    mock_client = MagicMock()
    mock_client.set.return_value = True
    mock_script = MagicMock()
    mock_script.return_value = 1
    mock_client.register_script.return_value = mock_script

    with patch('core.distributed_lock.redis_cache') as mock_cache:
        mock_cache.redis_client = mock_client
        with DistributedLock("resource_ctx", ttl_ms=5000) as lock:
            assert lock is not None
            assert lock.locked is True
        assert lock.locked is False


def test_synchronized_decorator():
    mock_client = MagicMock()
    mock_client.set.return_value = True
    mock_script = MagicMock()
    mock_script.return_value = 1
    mock_client.register_script.return_value = mock_script

    with patch('core.distributed_lock.redis_cache') as mock_cache:
        mock_cache.redis_client = mock_client

        @synchronized("sync_resource", ttl_ms=5000)
        def dummy_function(x, y):
            return x + y

        result = dummy_function(2, 3)
        assert result == 5
