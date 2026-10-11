"""A slow or dead Redis must not slow down or hang request handling."""
from unittest.mock import MagicMock, patch


def test_no_ping_before_each_cache_operation():
    from utils.redis_utils import RedisCache
    cache = RedisCache.__new__(RedisCache)
    cache.redis_client, cache.connected, cache._last_connect_attempt = MagicMock(), True, 0
    cache.redis_client.get.return_value = b'1'
    assert cache.get_cache('k') == 1
    cache.redis_client.ping.assert_not_called()


def test_reconnects_are_throttled_while_redis_is_down():
    import time
    from utils.redis_utils import RedisCache
    cache = RedisCache.__new__(RedisCache)
    cache.redis_client, cache.connected, cache._last_connect_attempt = None, False, time.monotonic()
    with patch.object(RedisCache, '_try_connect', return_value=False) as connect:
        for _ in range(50):
            assert cache.get_cache('k') is None
    connect.assert_not_called()  # within the reconnect interval: no connect attempt per request


def test_worker_connection_has_no_socket_timeout_but_web_connection_does():
    from services import task_queue
    with patch.object(task_queue, 'Redis') as redis_cls, patch.dict('os.environ', {'REDIS_URL': 'redis://h:6379/0'}):
        task_queue.get_queue_connection()
        task_queue._create_redis_connection()
    worker_kwargs = redis_cls.from_url.call_args_list[0].kwargs
    web_kwargs = redis_cls.from_url.call_args_list[1].kwargs
    assert worker_kwargs['socket_timeout'] is None
    assert web_kwargs['socket_timeout'] == 5 and web_kwargs['retry_on_timeout'] is False
