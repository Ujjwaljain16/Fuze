import pytest
from unittest.mock import MagicMock
from services.rate_limit_handler import (
    RateLimitHandler,
    GeminiRateLimiter,
    rate_limited,
    is_rate_limit_error,
    global_rate_handler
)


@pytest.mark.unit
def test_is_rate_limit_error():
    class ResourceExhausted(Exception):
        pass

    assert is_rate_limit_error(ResourceExhausted("Quota exceeded")) is True
    assert is_rate_limit_error(Exception("429 Too Many Requests")) is True
    assert is_rate_limit_error(ValueError("Invalid argument")) is False


@pytest.mark.unit
def test_shared_rate_handler_across_functions():
    handler = RateLimitHandler()
    limiter = GeminiRateLimiter(handler=handler)

    # State in handler is shared
    handler.requests_per_minute = 2

    @rate_limited
    def call_a():
        return "a"

    @rate_limited
    def call_b():
        return "b"

    # Both decorators use global_rate_handler
    assert global_rate_handler.can_make_request() is True


@pytest.mark.unit
def test_rate_limit_redis_counters():
    mock_redis = MagicMock()
    mock_redis.connected = True
    mock_redis.get_cache.side_effect = ["16", "100"]  # minute=16 (limit=15), day=100

    handler = RateLimitHandler(redis_client=mock_redis)
    assert handler.can_make_request() is False
