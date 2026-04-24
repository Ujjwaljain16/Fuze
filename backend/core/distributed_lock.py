import uuid
from core.logging_config import get_logger
from utils.redis_utils import redis_cache

logger = get_logger(__name__)

class DistributedLock:
    """
    Production-grade distributed lock using Redis.
    Uses SET key value NX PX ttl to ensure atomicity.
    Uses a Lua script for safe release (only owner can release).
    """

    RELEASE_LUA_SCRIPT = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """

    def __init__(self, key: str, ttl_ms: int = 30000):
        self.key = f"lock:{key}"
        self.ttl_ms = ttl_ms
        self.owner_id = str(uuid.uuid4())
        self.locked = False
        self.client = redis_cache.redis_client

    def acquire(self) -> bool:
        """
        Attempt to acquire the lock. 
        Returns True if successful, False otherwise.
        """
        try:
            # nx=True: set if not exists
            # px=ttl_ms: set expiry in milliseconds
            result = self.client.set(self.key, self.owner_id, nx=True, px=self.ttl_ms)
            if result:
                self.locked = True
                logger.debug("lock_acquired", lock_key=self.key, owner_id=self.owner_id)
                return True
            return False
        except Exception as e:
            logger.error("lock_acquisition_failed", lock_key=self.key, error=str(e))
            return False

    def release(self) -> bool:
        """
        Release the lock using Lua script to ensure only the owner can release.
        """
        if not self.locked:
            return False
            
        try:
            result = self.client.register_script(self.RELEASE_LUA_SCRIPT)(
                keys=[self.key], 
                args=[self.owner_id]
            )
            self.locked = False
            logger.debug("lock_released", lock_key=self.key)
            return bool(result)
        except Exception as e:
            logger.error("lock_release_failed", lock_key=self.key, error=str(e))
            return False

    def __enter__(self):
        if self.acquire():
            return self
        return None

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.locked:
            self.release()

def synchronized(lock_key: str, ttl_ms: int = 30000):
    """Decorator for distributed synchronization"""
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def wrapper(*args, **kwargs):
            lock = DistributedLock(lock_key, ttl_ms)
            if lock.acquire():
                try:
                    return f(*args, **kwargs)
                finally:
                    lock.release()
            else:
                logger.warning("lock_decorator_acquisition_failed", lock_key=lock_key, function=f.__name__)
                return None
        return wrapper
    return decorator
