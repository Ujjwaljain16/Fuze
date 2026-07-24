import pytest
from unittest.mock import patch, MagicMock
from core.distributed_lock import DistributedLock, synchronized, LockAcquisitionError


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


def test_distributed_lock_invalid_ttl():
    with pytest.raises(ValueError):
        DistributedLock("resource_bad_ttl", ttl_ms=0)

    with pytest.raises(ValueError):
        DistributedLock("resource_bad_ttl", ttl_ms=-500)


def test_distributed_lock_extend():
    mock_client = MagicMock()
    mock_client.set.return_value = True
    mock_extend_script = MagicMock()
    mock_extend_script.return_value = 1
    mock_client.register_script.return_value = mock_extend_script

    with patch('core.distributed_lock.redis_cache') as mock_cache:
        mock_cache.redis_client = mock_client
        lock = DistributedLock("resource_extend", ttl_ms=5000)

        assert lock.acquire() is True
        assert lock.extend(10000) is True
        mock_extend_script.assert_called_once_with(
            keys=["lock:resource_extend"], args=[lock.owner_id, 10000]
        )


def test_distributed_lock_is_owner():
    mock_client = MagicMock()
    mock_client.set.return_value = True

    with patch('core.distributed_lock.redis_cache') as mock_cache:
        mock_cache.redis_client = mock_client
        lock = DistributedLock("resource_owner", ttl_ms=5000)

        assert lock.acquire() is True
        mock_client.get.return_value = lock.owner_id.encode('utf-8')
        assert lock.is_owner() is True

        mock_client.get.return_value = b"other_owner"
        assert lock.is_owner() is False


def test_synchronized_decorator_dynamic_key():
    mock_client = MagicMock()
    mock_client.set.return_value = True
    mock_script = MagicMock()
    mock_script.return_value = 1
    mock_client.register_script.return_value = mock_script

    with patch('core.distributed_lock.redis_cache') as mock_cache:
        mock_cache.redis_client = mock_client

        @synchronized(lambda *a, **kw: f"project:{kw['project_id']}")
        def update_project(project_id, title):
            return f"Updated {project_id} to {title}"

        res = update_project(project_id=42, title="Fuze")
        assert res == "Updated 42 to Fuze"
        mock_client.set.assert_called_with("lock:project:42", mock_client.set.call_args[0][1], nx=True, px=30000)
