import time
from typing import Optional
from utils.redis_utils import redis_cache
from core.logging_config import get_logger

logger = get_logger(__name__)


class CircuitState:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class RedisCircuitBreaker:
    """
    Distributed Redis-backed Circuit Breaker.
    Shares trip status across all Gunicorn worker processes and background RQ workers.
    """

    def __init__(
        self,
        name: str = "gemini",
        failure_threshold: int = 5,
        recovery_timeout: int = 120,
        window_seconds: int = 60
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.window_seconds = window_seconds

        self.state_key = f"fuze:circuit:{name}:state"
        self.failures_key = f"fuze:circuit:{name}:failures"
        self.opened_at_key = f"fuze:circuit:{name}:opened_at"

    def get_state(self) -> str:
        """Get current state of circuit breaker."""
        if not redis_cache or not redis_cache.connected:
            return CircuitState.CLOSED

        try:
            state_bytes = redis_cache.redis_client.get(self.state_key)
            if not state_bytes:
                return CircuitState.CLOSED

            state = state_bytes.decode('utf-8') if isinstance(state_bytes, bytes) else str(state_bytes)

            if state == CircuitState.OPEN:
                opened_at_bytes = redis_cache.redis_client.get(self.opened_at_key)
                if opened_at_bytes:
                    opened_at = float(opened_at_bytes.decode('utf-8') if isinstance(opened_at_bytes, bytes) else opened_at_bytes)
                    if time.time() - opened_at >= self.recovery_timeout:
                        redis_cache.redis_client.set(self.state_key, CircuitState.HALF_OPEN)
                        logger.info("circuit_breaker_transition_half_open", extra={"name": self.name})
                        return CircuitState.HALF_OPEN
            return state
        except Exception as e:
            logger.error("circuit_breaker_get_state_failed", extra={"name": self.name, "error": str(e)})
            return CircuitState.CLOSED

    def record_success(self):
        """Record successful call, resetting state to CLOSED."""
        if not redis_cache or not redis_cache.connected:
            return

        try:
            state = self.get_state()
            if state != CircuitState.CLOSED:
                pipe = redis_cache.redis_client.pipeline()
                pipe.set(self.state_key, CircuitState.CLOSED)
                pipe.delete(self.failures_key)
                pipe.delete(self.opened_at_key)
                pipe.execute()
                logger.info("circuit_breaker_reset_closed", extra={"name": self.name})
            else:
                redis_cache.redis_client.delete(self.failures_key)
        except Exception as e:
            logger.error("circuit_breaker_record_success_failed", extra={"name": self.name, "error": str(e)})

    def record_failure(self):
        """Record failed API call, tripping state to OPEN if threshold reached."""
        if not redis_cache or not redis_cache.connected:
            return

        try:
            failures = redis_cache.redis_client.incr(self.failures_key)
            if failures == 1:
                redis_cache.redis_client.expire(self.failures_key, self.window_seconds)

            state = self.get_state()
            if state == CircuitState.HALF_OPEN or failures >= self.failure_threshold:
                now = time.time()
                pipe = redis_cache.redis_client.pipeline()
                pipe.set(self.state_key, CircuitState.OPEN)
                pipe.set(self.opened_at_key, str(now))
                pipe.execute()
                logger.warning("circuit_breaker_tripped_open", extra={
                    "name": self.name,
                    "failures": failures,
                    "recovery_timeout": self.recovery_timeout
                })
        except Exception as e:
            logger.error("circuit_breaker_record_failure_failed", extra={"name": self.name, "error": str(e)})

    def allow_request(self) -> bool:
        """Check whether outbound API request is permitted."""
        state = self.get_state()
        if state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
            return True
        logger.warning("circuit_breaker_request_blocked", extra={"name": self.name, "state": state})
        return False


gemini_circuit_breaker = RedisCircuitBreaker(name="gemini")
