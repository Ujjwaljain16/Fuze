import os
import ssl
import json
import uuid
import hashlib
import threading
from typing import Optional, Dict, Any, List
import numpy as np
import redis
from core.logging_config import get_logger

logger = get_logger(__name__)

_redis_connection_pool = None
_pool_lock = threading.Lock()

LUA_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

LUA_EXTEND_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("pexpire", KEYS[1], ARGV[2])
else
    return 0
end
"""


class RedisCache:
    """Redis cache utility for Fuze application with auto-reconnection and distributed locking."""

    def __init__(self):
        self.redis_client = None
        self.connected = False
        self._try_connect()

    def _try_connect(self) -> bool:
        global _redis_connection_pool

        redis_url = os.environ.get('REDIS_URL')
        if redis_url:
            if 'upstash.io' in redis_url and redis_url.startswith('redis://'):
                redis_url = redis_url.replace('redis://', 'rediss://', 1)

            try:
                with _pool_lock:
                    if _redis_connection_pool is None:
                        pool_kwargs = {
                            'decode_responses': False,
                            'socket_connect_timeout': 5,
                            'socket_timeout': 5,
                            'max_connections': 20,
                            'socket_keepalive': True
                        }
                        if redis_url.startswith('rediss://'):
                            allow_unverified = os.environ.get('REDIS_ALLOW_UNVERIFIED_SSL', 'false').lower() == 'true'
                            if allow_unverified:
                                logger.warning("redis_ssl_unverified_warning_in_use")
                                pool_kwargs['ssl_cert_reqs'] = ssl.CERT_NONE
                                pool_kwargs['ssl_check_hostname'] = False
                            else:
                                pool_kwargs['ssl_cert_reqs'] = ssl.CERT_REQUIRED
                                pool_kwargs['ssl_check_hostname'] = True

                        _redis_connection_pool = redis.ConnectionPool.from_url(redis_url, **pool_kwargs)

                client = redis.Redis(connection_pool=_redis_connection_pool)
                client.ping()
                self.redis_client = client
                self.connected = True
                logger.info("redis_pool_connected_successfully")
                return True
            except Exception as e:
                logger.error("redis_conn_url_failed", extra={"error": str(e)})
                self.connected = False
                return False

        redis_host = os.environ.get('REDIS_HOST', 'localhost')
        redis_port = int(os.environ.get('REDIS_PORT', 6379))
        redis_db = int(os.environ.get('REDIS_DB', 0))
        redis_password = os.environ.get('REDIS_PASSWORD')
        use_ssl = os.environ.get('REDIS_SSL', 'false').lower() == 'true'

        if not use_ssl and any(provider in redis_host for provider in ['upstash.io', 'redislabs.com', 'redis.cache']):
            use_ssl = True

        try:
            params = {
                'host': redis_host,
                'port': redis_port,
                'db': redis_db,
                'password': redis_password,
                'decode_responses': False,
                'socket_connect_timeout': 5,
                'socket_timeout': 5
            }
            if use_ssl:
                params['ssl'] = True
                allow_unverified = os.environ.get('REDIS_ALLOW_UNVERIFIED_SSL', 'false').lower() == 'true'
                if allow_unverified:
                    params['ssl_cert_reqs'] = ssl.CERT_NONE
                    params['ssl_check_hostname'] = False
                else:
                    params['ssl_cert_reqs'] = ssl.CERT_REQUIRED
                    params['ssl_check_hostname'] = True

            client = redis.Redis(**params)
            client.ping()
            self.redis_client = client
            self.connected = True
            logger.info("redis_direct_connected_successfully")
            return True
        except Exception as e:
            logger.error("redis_conn_failed", extra={"error": str(e)})
            self.connected = False
            return False

    def _ensure_connected(self) -> bool:
        """Verify connection or attempt auto-recovery if Redis was disconnected."""
        if self.connected and self.redis_client:
            try:
                self.redis_client.ping()
                return True
            except Exception:
                self.connected = False

        return self._try_connect()

    def acquire_lock(self, resource: str, ttl_ms: int = 300000) -> Optional[str]:
        """Acquire distributed lock using SET NX PX."""
        if not self._ensure_connected():
            return None

        owner_id = str(uuid.uuid4())
        key = f"lock:{resource}"
        try:
            if self.redis_client.set(key, owner_id, nx=True, px=ttl_ms):
                logger.debug("redis_lock_acquired", extra={"resource": resource, "owner_id": owner_id})
                return owner_id
        except Exception as e:
            logger.error("redis_lock_acquisition_error", extra={"resource": resource, "error": str(e)})

        return None

    def extend_lock(self, resource: str, owner_id: str, ttl_ms: int = 300000) -> bool:
        """Renew an existing lock using Lua PEXPIRE."""
        if not self._ensure_connected() or not owner_id:
            return False

        key = f"lock:{resource}"
        try:
            res = self.redis_client.eval(LUA_EXTEND_SCRIPT, 1, key, owner_id, ttl_ms)
            return bool(res)
        except Exception as e:
            logger.error("redis_lock_extend_error", extra={"resource": resource, "error": str(e)})
            return False

    def release_lock(self, resource: str, owner_id: str) -> bool:
        """Release distributed lock using Lua script."""
        if not self._ensure_connected() or not owner_id:
            return False

        key = f"lock:{resource}"
        try:
            result = self.redis_client.eval(LUA_RELEASE_SCRIPT, 1, key, owner_id)
            return bool(result)
        except Exception as e:
            logger.error("redis_lock_release_error", extra={"resource": resource, "error": str(e)})
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        if not self._ensure_connected():
            return {"connected": False}
        try:
            info = self.redis_client.info()
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            return {"connected": True, "error": str(e)}

    def safe_delete_pattern(self, pattern: str, batch_size: int = 100) -> int:
        """Memory-safe deletion using SCAN instead of KEYS."""
        if not self._ensure_connected():
            return 0

        deleted_count = 0
        cursor = 0
        try:
            while True:
                cursor, keys = self.redis_client.scan(cursor=cursor, match=pattern, count=batch_size)
                if keys:
                    count = self.redis_client.delete(*keys)
                    deleted_count += count
                if cursor == 0:
                    break
        except Exception as e:
            logger.error("redis_scan_error", extra={"pattern": pattern, "error": str(e)})

        return deleted_count

    def _get_key(self, prefix: str, identifier: str) -> str:
        return f"fuze:{prefix}:{identifier}"

    def _hash_content(self, content: str) -> str:
        """Generate SHA-256 hash for content caching."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def cache_embedding(self, content: str, embedding: np.ndarray, ttl: int = 86400) -> bool:
        if not self._ensure_connected():
            return False
        try:
            content_hash = self._hash_content(content)
            key = self._get_key("embedding", content_hash)
            embedding_bytes = embedding.astype(np.float32).tobytes()
            return bool(self.redis_client.setex(key, ttl, embedding_bytes))
        except Exception as e:
            logger.error("redis_cache_embedding_error", extra={"error": str(e)})
            return False

    def get_cached_embedding(self, content: str) -> Optional[np.ndarray]:
        if not self._ensure_connected():
            return None
        try:
            content_hash = self._hash_content(content)
            key = self._get_key("embedding", content_hash)
            embedding_bytes = self.redis_client.get(key)
            if embedding_bytes and len(embedding_bytes) == 1536:
                return np.frombuffer(embedding_bytes, dtype=np.float32).copy()
        except Exception as e:
            logger.error("redis_get_cached_embedding_error", extra={"error": str(e)})
        return None

    def check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        if not self._ensure_connected():
            return True
        try:
            current = self.redis_client.incr(key)
            if current == 1:
                self.redis_client.expire(key, window)
            return current <= limit
        except Exception as e:
            logger.error("redis_check_rate_limit_error", extra={"key": key, "error": str(e)})
            return True

    def get_cache(self, key: str) -> Optional[Any]:
        if not self._ensure_connected():
            return None
        try:
            data_bytes = self.redis_client.get(key)
            if data_bytes is None:
                return None
            data_str = data_bytes.decode('utf-8')
            return json.loads(data_str)
        except Exception as e:
            logger.error("redis_get_cache_error", extra={"key": key, "error": str(e)})
            return None

    def get(self, key: str) -> Optional[Any]:
        return self.get_cache(key)

    def setex(self, key: str, ttl: int, value: Any) -> bool:
        if not self._ensure_connected():
            return False
        try:
            if isinstance(value, str):
                data_bytes = value.encode('utf-8')
            else:
                data_bytes = json.dumps(value, default=str).encode('utf-8')
            return bool(self.redis_client.setex(key, ttl, data_bytes))
        except Exception as e:
            logger.error("redis_set_cache_error", extra={"key": key, "error": str(e)})
            return False

    def set_cache(self, key: str, data: Any, ttl: int = 3600) -> bool:
        return self.setex(key, ttl, data)

    def delete_cache(self, key: str) -> bool:
        if not self._ensure_connected():
            return False
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error("redis_delete_cache_error", extra={"key": key, "error": str(e)})
            return False

    def delete_keys_pattern(self, pattern: str) -> int:
        return self.safe_delete_pattern(pattern)


# Global Redis instance
redis_cache = RedisCache()
