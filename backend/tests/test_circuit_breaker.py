import time
from unittest.mock import patch, MagicMock
from core.circuit_breaker import RedisCircuitBreaker, CircuitState


def test_circuit_breaker_closed_by_default():
    with patch('core.circuit_breaker.redis_cache') as mock_redis:
        mock_redis.connected = True
        mock_redis.redis_client.get.return_value = None

        cb = RedisCircuitBreaker(name="test_default")
        assert cb.get_state() == CircuitState.CLOSED
        assert cb.allow_request() is True


def test_circuit_breaker_trips_to_open_on_failures():
    with patch('core.circuit_breaker.redis_cache') as mock_redis:
        mock_redis.connected = True
        mock_redis.redis_client.incr.return_value = 5
        mock_redis.redis_client.get.return_value = b"CLOSED"

        cb = RedisCircuitBreaker(name="test_trip", failure_threshold=5)
        cb.record_failure()

        mock_redis.redis_client.pipeline().execute.assert_called()


def test_circuit_breaker_blocks_when_open():
    with patch('core.circuit_breaker.redis_cache') as mock_redis:
        mock_redis.connected = True
        mapping = {
            "fuze:circuit:test_block:state": b"OPEN",
            "fuze:circuit:test_block:opened_at": str(time.time()).encode('utf-8')
        }
        mock_redis.redis_client.get.side_effect = lambda key: mapping.get(key)

        cb = RedisCircuitBreaker(name="test_block", recovery_timeout=120)
        assert cb.get_state() == CircuitState.OPEN
        assert cb.allow_request() is False


def test_circuit_breaker_transitions_to_half_open_after_timeout():
    with patch('core.circuit_breaker.redis_cache') as mock_redis:
        mock_redis.connected = True
        past_time = time.time() - 150  # 150s ago (> 120s timeout)
        mapping = {
            "fuze:circuit:test_half_open:state": b"OPEN",
            "fuze:circuit:test_half_open:opened_at": str(past_time).encode('utf-8')
        }
        mock_redis.redis_client.get.side_effect = lambda key: mapping.get(key)

        cb = RedisCircuitBreaker(name="test_half_open", recovery_timeout=120)
        assert cb.get_state() == CircuitState.HALF_OPEN
        assert cb.allow_request() is True
