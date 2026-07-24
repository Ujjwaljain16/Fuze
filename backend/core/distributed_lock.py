import uuid
import time
import random
from typing import Optional, Union, Callable, Any
from core.logging_config import get_logger
from utils.redis_utils import redis_cache

logger = get_logger(__name__)


class LockAcquisitionError(Exception):
    """Raised when a distributed lock cannot be acquired."""
    pass


class DistributedLock:
    """
    Production-grade distributed lock using Redis.
    Uses SET key value NX PX ttl to ensure atomicity.
    Uses Lua scripts for safe release and lock extension (only owner can release/extend).
    Supports retry with randomized backpressure jitter and heartbeat extensions.
    """

    RELEASE_LUA_SCRIPT = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """

    EXTEND_LUA_SCRIPT = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("pexpire", KEYS[1], ARGV[2])
    else
        return 0
    end
    """

    def __init__(self, key: str, ttl_ms: int = 30000, acquire_timeout_s: float = 0.0, retry_interval_s: float = 0.1):
        if ttl_ms <= 0:
            raise ValueError("ttl_ms must be a positive integer")

        self.key = f"lock:{key}" if not key.startswith("lock:") else key
        self.ttl_ms = ttl_ms
        self.acquire_timeout_s = acquire_timeout_s
        self.retry_interval_s = retry_interval_s
        self.owner_id = str(uuid.uuid4())
        self.locked = False
        self.client = redis_cache.redis_client
        self._release_script = None
        self._extend_script = None

    def acquire(self, blocking: Optional[bool] = None, acquire_timeout_s: Optional[float] = None) -> bool:
        """
        Attempt to acquire the lock.
        If blocking is True (or acquire_timeout_s > 0), retries until timeout is reached with jittered backoff.
        Returns True if successful, False otherwise.
        """
        if not self.client:
            logger.warning("lock_acquire_skipped_no_redis", extra={"lock_key": self.key})
            return False

        timeout = acquire_timeout_s if acquire_timeout_s is not None else self.acquire_timeout_s
        should_block = blocking if blocking is not None else (timeout > 0)
        start_time = time.monotonic()

        while True:
            try:
                result = self.client.set(self.key, self.owner_id, nx=True, px=self.ttl_ms)
                if result:
                    self.locked = True
                    logger.debug("lock_acquired", extra={"lock_key": self.key, "owner_id": self.owner_id})
                    return True
            except Exception:
                logger.exception("lock_acquisition_exception", extra={"lock_key": self.key})
                return False

            if not should_block:
                return False

            elapsed = time.monotonic() - start_time
            if elapsed >= timeout:
                logger.warning("lock_acquisition_timed_out", extra={"lock_key": self.key, "elapsed_s": elapsed})
                return False

            # Randomized backpressure jitter (50%-150% of retry interval)
            jitter = random.uniform(self.retry_interval_s * 0.5, self.retry_interval_s * 1.5)
            time.sleep(min(jitter, max(0.01, timeout - elapsed)))

    def release(self) -> bool:
        """
        Release the lock using Lua script to ensure only the owner can release.
        Only marks self.locked = False if release actually succeeded.
        """
        if not self.locked or not self.client:
            return False

        try:
            if self._release_script is None:
                self._release_script = self.client.register_script(self.RELEASE_LUA_SCRIPT)

            result = self._release_script(
                keys=[self.key],
                args=[self.owner_id]
            )

            released = bool(result)
            if released:
                self.locked = False
                logger.debug("lock_released", extra={"lock_key": self.key, "owner_id": self.owner_id})
            else:
                logger.warning("lock_release_failed_ownership_lost_or_expired", extra={"lock_key": self.key, "owner_id": self.owner_id})

            return released
        except Exception:
            logger.exception("lock_release_exception", extra={"lock_key": self.key})
            return False

    def extend(self, additional_ttl_ms: Optional[int] = None) -> bool:
        """
        Extend the TTL of the lock if currently held by this owner (lock heartbeat/renewal).
        Returns True if successfully extended, False otherwise.
        """
        if not self.locked or not self.client:
            return False

        new_ttl = additional_ttl_ms or self.ttl_ms
        try:
            if self._extend_script is None:
                self._extend_script = self.client.register_script(self.EXTEND_LUA_SCRIPT)

            result = self._extend_script(
                keys=[self.key],
                args=[self.owner_id, new_ttl]
            )
            extended = bool(result)
            if extended:
                logger.debug("lock_extended", extra={"lock_key": self.key, "new_ttl_ms": new_ttl})
            else:
                self.locked = False
                logger.warning("lock_extend_failed_ownership_lost", extra={"lock_key": self.key})
            return extended
        except Exception:
            logger.exception("lock_extend_exception", extra={"lock_key": self.key})
            return False

    def is_owner(self) -> bool:
        """Check if this instance is still the owner of the lock in Redis."""
        if not self.client:
            return False
        try:
            val = self.client.get(self.key)
            if val is None:
                return False
            val_str = val.decode('utf-8') if isinstance(val, bytes) else str(val)
            return val_str == self.owner_id
        except Exception:
            logger.exception("lock_owner_check_exception", extra={"lock_key": self.key})
            return False

    def __enter__(self):
        if self.acquire():
            return self
        raise LockAcquisitionError(f"Could not acquire distributed lock for key: {self.key}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.locked:
            self.release()


def synchronized(lock_key: Union[str, Callable[..., str]], ttl_ms: int = 30000, raise_on_failure: bool = False):
    """
    Decorator for distributed synchronization.
    Supports static keys or dynamic key callables (e.g., lambda *args, **kwargs: f"project:{kwargs['id']}").
    """
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def wrapper(*args, **kwargs):
            key_name = lock_key(*args, **kwargs) if callable(lock_key) else str(lock_key)
            lock = DistributedLock(key_name, ttl_ms)
            if lock.acquire():
                try:
                    return f(*args, **kwargs)
                finally:
                    lock.release()
            else:
                logger.warning("lock_decorator_acquisition_failed", extra={"lock_key": key_name, "function": f.__name__})
                if raise_on_failure:
                    raise LockAcquisitionError(f"Could not acquire distributed lock for function '{f.__name__}' on key '{key_name}'")
                return None
        return wrapper
    return decorator
