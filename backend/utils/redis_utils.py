import redis
import json
import hashlib
import os
import ssl
import uuid
from typing import Optional, Dict, Any, List
import numpy as np
from core.logging_config import get_logger

logger = get_logger(__name__)

# Global connection pool (shared across instances)
_redis_connection_pool = None
_pool_lock = __import__('threading').Lock()

# Atomic Release Script: Only delete if owner matches
LUA_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

class RedisCache:
    """Redis cache utility for Fuze application with connection pooling"""
    
    def __init__(self):
        global _redis_connection_pool
        
        # Check if REDIS_URL is provided (supports both redis:// and rediss:// for TLS)
        redis_url = os.environ.get('REDIS_URL')
        
        if redis_url:
            # Upstash requires TLS but provides redis:// URLs
            if 'upstash.io' in redis_url and redis_url.startswith('redis://'):
                redis_url = redis_url.replace('redis://', 'rediss://', 1)
                logger.info("redis_upstash_tls_conversion", original="redis://upstash.io", updated="rediss://upstash.io")
            
            try:
                with _pool_lock:
                    if _redis_connection_pool is None:
                        pool_kwargs = {
                            'decode_responses': False,
                            'socket_connect_timeout': 10,
                            'socket_timeout': 10,
                            'max_connections': 20,
                            'socket_keepalive': True
                        }
                        
                        if redis_url.startswith('rediss://'):
                            pool_kwargs['ssl_cert_reqs'] = ssl.CERT_NONE
                            pool_kwargs['ssl_check_hostname'] = False
                        
                        _redis_connection_pool = redis.ConnectionPool.from_url(
                            redis_url,
                            **pool_kwargs
                        )
                        logger.info("redis_pool_created", tls=redis_url.startswith('rediss://'))
                
                self.redis_client = redis.Redis(connection_pool=_redis_connection_pool)
                self.redis_client.ping()
                self.connected = True
            except Exception as e:
                logger.error("redis_conn_url_failed", error=str(e))
                self.connected = False
                self.redis_client = None
        else:
            self.redis_host = os.environ.get('REDIS_HOST', 'localhost')
            self.redis_port = int(os.environ.get('REDIS_PORT', 6379))
            self.redis_db = int(os.environ.get('REDIS_DB', 0))
            self.redis_password = os.environ.get('REDIS_PASSWORD')
            
            use_ssl = os.environ.get('REDIS_SSL', 'false').lower() == 'true'
            if not use_ssl and any(provider in self.redis_host for provider in ['upstash.io', 'redislabs.com', 'redis.cache']):
                use_ssl = True
            
            try:
                connection_params = {
                    'host': self.redis_host,
                    'port': self.redis_port,
                    'db': self.redis_db,
                    'password': self.redis_password,
                    'decode_responses': False,
                    'socket_connect_timeout': 10,
                    'socket_timeout': 10
                }
                
                if use_ssl:
                    connection_params['ssl'] = True
                    connection_params['ssl_cert_reqs'] = None
                
                self.redis_client = redis.Redis(**connection_params)
                self.redis_client.ping()
                self.connected = True
                logger.info("redis_conn_established", tls=use_ssl)
            except Exception as e:
                logger.error("redis_conn_failed", error=str(e))
                self.connected = False
                self.redis_client = None

    # DISTRIBUTED LOCKING (SETNX + LUA)
    def acquire_lock(self, resource: str, ttl_ms: int = 300000) -> Optional[str]:
        """
        Acquire a distributed lock for a resource.
        - Uses SET NX PX (Atomic Set-if-not-exists with expiration)
        - Returns unique owner_id on success, None on failure.
        - Default TTL: 5 minutes (Conservative Production Guard)
        """
        if not self.connected:
            return None
        
        owner_id = str(uuid.uuid4())
        key = f"lock:{resource}"
        try:
            if self.redis_client.set(key, owner_id, nx=True, px=ttl_ms):
                logger.debug("redis_lock_acquired", resource=resource, owner_id=owner_id)
                return owner_id
        except Exception as e:
            logger.error("redis_lock_acquisition_error", resource=resource, error=str(e))
        
        return None

    def release_lock(self, resource: str, owner_id: str) -> bool:
        """
        Release a distributed lock safely using Lua.
        - Ensures only the owner who acquired the lock can release it.
        - Prevents accidental release of expired locks held by new owners.
        """
        if not self.connected or not owner_id:
            return False
        
        key = f"lock:{resource}"
        try:
            result = self.redis_client.eval(LUA_RELEASE_SCRIPT, 1, key, owner_id)
            if result:
                logger.debug("redis_lock_released", resource=resource, owner_id=owner_id)
                return True
            else:
                logger.warning("redis_lock_release_failed_expired", resource=resource, owner_id=owner_id)
        except Exception as e:
            logger.error("redis_lock_release_error", resource=resource, error=str(e))
        
        return False

    # MEMORY-SAFE CLEANUP (SCAN)
    def safe_delete_pattern(self, pattern: str, batch_size: int = 100) -> int:
        """
        Memory-safe deletion using SCAN instead of KEYS.
        - Iterates via cursor to prevent blocking Redis at scale.
        - Returns total number of deleted keys.
        """
        if not self.connected:
            return 0
        
        deleted_count = 0
        cursor = 0
        try:
            while True:
                cursor, keys = self.redis_client.scan(cursor=cursor, match=pattern, count=batch_size)
                if keys:
                    count = self.redis_client.delete(*keys)
                    deleted_count += count
                    logger.info("redis_scan_deleted", count=count, pattern=pattern)
                if cursor == 0:
                    break
        except Exception as e:
            logger.error("redis_scan_error", pattern=pattern, error=str(e))
            
        return deleted_count

    def _get_key(self, prefix: str, identifier: str) -> str:
        """Generate Redis key with prefix"""
        return f"fuze:{prefix}:{identifier}"
    
    def _hash_content(self, content: str) -> str:
        """Generate hash for content"""
        return hashlib.md5(content.encode()).hexdigest()
    
    # Embedding Cache
    def cache_embedding(self, content: str, embedding: np.ndarray, ttl: int = 86400) -> bool:
        """Cache embedding for content (24 hours default)"""
        if not self.connected:
            return False
        
        try:
            content_hash = self._hash_content(content)
            key = self._get_key("embedding", content_hash)
            # Store raw float32 bytes for maximum performance (no base64 overhead)
            embedding_bytes = embedding.astype(np.float32).tobytes()
            return self.redis_client.setex(key, ttl, embedding_bytes)
        except Exception as e:
            logger.error("redis_cache_embedding_error", error=str(e))
            return False
    
    def get_cached_embedding(self, content: str) -> Optional[np.ndarray]:
        """Get cached embedding for content"""
        if not self.connected:
            return None
        
        try:
            content_hash = self._hash_content(content)
            key = self._get_key("embedding", content_hash)
            embedding_bytes = self.redis_client.get(key)
            if embedding_bytes:
                # 384 dimensions * 4 bytes per float32 = 1536 bytes
                if len(embedding_bytes) == 1536:
                    # Validate size and use .copy() to prevent immutable buffer issues
                    return np.frombuffer(embedding_bytes, dtype=np.float32).copy()
                else:
                    logger.warning("Legacy pickle cache detected in embeddings", key=key, bytes_len=len(embedding_bytes))
                    self.redis_client.delete(key)
                    return None
        except Exception as e:
            logger.error("redis_get_cached_embedding_error", error=str(e))
        return None
    
    # Scraping Cache
    def cache_scraped_content(self, url: str, content: Dict[str, Any], ttl: int = 3600) -> bool:
        """Cache scraped content for URL (1 hour default)"""
        if not self.connected:
            return False
        
        try:
            url_hash = self._hash_content(url)
            key = self._get_key("scraped", url_hash)
            content_json = json.dumps(content, default=str)
            return self.redis_client.setex(key, ttl, content_json.encode())
        except Exception as e:
            logger.error("redis_cache_scraped_content_error", url=url, error=str(e))
            return False
    
    def get_cached_scraped_content(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached scraped content for URL"""
        if not self.connected:
            return None
        
        try:
            url_hash = self._hash_content(url)
            key = self._get_key("scraped", url_hash)
            content_json = self.redis_client.get(key)
            if content_json:
                return json.loads(content_json.decode())
        except Exception as e:
            logger.error("redis_get_cached_scraped_content_error", url=url, error=str(e))
        return None
    
    # User Bookmarks Cache
    def cache_user_bookmarks(self, user_id: int, bookmarks: List[Dict], ttl: int = 300) -> bool:
        """Cache user's bookmarks for fast duplicate checking (5 minutes default)"""
        if not self.connected:
            return False
        
        try:
            key = self._get_key("user_bookmarks", str(user_id))
            bookmarks_json = json.dumps(bookmarks, default=str)
            return self.redis_client.setex(key, ttl, bookmarks_json.encode())
        except Exception as e:
            logger.error("redis_cache_user_bookmarks_error", user_id=user_id, error=str(e))
            return False
    
    def get_cached_user_bookmarks(self, user_id: int) -> Optional[List[Dict]]:
        """Get cached user bookmarks"""
        if not self.connected:
            return None
        
        try:
            key = self._get_key("user_bookmarks", str(user_id))
            bookmarks_json = self.redis_client.get(key)
            if bookmarks_json:
                return json.loads(bookmarks_json.decode())
        except Exception as e:
            logger.error("redis_get_cached_user_bookmarks_error", user_id=user_id, error=str(e))
        return None
    
    def invalidate_user_bookmarks(self, user_id: int) -> bool:
        """Invalidate user bookmarks cache when new bookmarks are added"""
        if not self.connected:
            return False
        
        try:
            key = self._get_key("user_bookmarks", str(user_id))
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error("redis_invalidate_user_bookmarks_error", user_id=user_id, error=str(e))
            return False
    
    # Rate Limiting
    def check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """Check if rate limit is exceeded"""
        if not self.connected:
            return True  # Allow if Redis is down
        
        try:
            current = self.redis_client.incr(key)
            if current == 1:
                self.redis_client.expire(key, window)
            return current <= limit
        except Exception as e:
            logger.error("redis_check_rate_limit_error", key=key, error=str(e))
            return True  # Allow if Redis is down
    
    # Session Cache
    def cache_session(self, session_id: str, data: Dict, ttl: int = 3600) -> bool:
        """Cache session data"""
        if not self.connected:
            return False
        
        try:
            key = self._get_key("session", session_id)
            data_json = json.dumps(data)
            return self.redis_client.setex(key, ttl, data_json.encode())
        except Exception as e:
            logger.error("redis_cache_session_error", session_id=session_id, error=str(e))
            return False
    
    def get_cached_session(self, session_id: str) -> Optional[Dict]:
        """Get cached session data"""
        if not self.connected:
            return None
        
        try:
            key = self._get_key("session", session_id)
            data_json = self.redis_client.get(key)
            if data_json:
                return json.loads(data_json.decode())
        except Exception as e:
            logger.error("redis_get_cached_session_error", session_id=session_id, error=str(e))
        return None
    
    # Query Result Cache (Enhanced)
    def cache_query_result(self, cache_key: str, result: Any, ttl: int = 300) -> bool:
        """Cache database query result"""
        if not self.connected:
            return False
        
        try:
            key = self._get_key("query", cache_key)
            result_json = json.dumps(result, default=str)
            return self.redis_client.setex(key, ttl, result_json.encode())
        except Exception as e:
            logger.error("redis_cache_query_result_error", cache_key=cache_key, error=str(e))
            return False
    
    def get_cached_query_result(self, cache_key: str) -> Optional[Any]:
        """Get cached query result"""
        if not self.connected:
            return None
        
        try:
            key = self._get_key("query", cache_key)
            result_json = self.redis_client.get(key)
            if result_json:
                return json.loads(result_json.decode())
        except Exception as e:
            logger.error("redis_get_cached_query_result_error", cache_key=cache_key, error=str(e))
        return None
    
    def invalidate_query_cache(self, pattern: str = None) -> int:
        """Invalidate query cache by pattern using SCAN"""
        if not self.connected:
            return 0
        
        try:
            if pattern:
                scan_pattern = self._get_key("query", f"*{pattern}*")
            else:
                scan_pattern = self._get_key("query", "*")
            
            return self.safe_delete_pattern(scan_pattern)
        except Exception as e:
            logger.error("redis_invalidate_query_cache_error", pattern=pattern, error=str(e))
            return 0
    
    # API Response Cache
    def cache_api_response(self, endpoint: str, params: Dict, response: Any, ttl: int = 60) -> bool:
        """Cache API response"""
        if not self.connected:
            return False
        
        try:
            params_str = json.dumps(params, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()
            cache_key = f"{endpoint}:{params_hash}"
            
            key = self._get_key("api", cache_key)
            response_json = json.dumps(response, default=str)
            return self.redis_client.setex(key, ttl, response_json.encode())
        except Exception as e:
            logger.error("redis_cache_api_response_error", endpoint=endpoint, error=str(e))
            return False
    
    def get_cached_api_response(self, endpoint: str, params: Dict) -> Optional[Any]:
        """Get cached API response"""
        if not self.connected:
            return None
        
        try:
            params_str = json.dumps(params, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()
            cache_key = f"{endpoint}:{params_hash}"
            
            key = self._get_key("api", cache_key)
            response_json = self.redis_client.get(key)
            if response_json:
                return json.loads(response_json.decode())
        except Exception as e:
            logger.error("redis_get_cached_api_response_error", endpoint=endpoint, error=str(e))
        return None
    
    # Cache Statistics
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.connected:
            return {"connected": False}
        
        try:
            info = self.redis_client.info()
            
            # Use SCAN for counting keys in production
            def count_pattern(pattern):
                count = 0
                cursor = 0
                while True:
                    cursor, keys = self.redis_client.scan(cursor=cursor, match=pattern, count=1000)
                    count += len(keys)
                    if cursor == 0: break
                return count

            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "cache_keys": {
                    "queries": count_pattern(self._get_key("query", "*")),
                    "api_responses": count_pattern(self._get_key("api", "*")),
                    "embeddings": count_pattern(self._get_key("embedding", "*")),
                }
            }
        except Exception as e:
            return {"connected": True, "error": str(e)}
    
    # Generic Cache Methods
    def get_cache(self, key: str) -> Optional[Any]:
        """Generic method to get cached data"""
        if not self.connected:
            return None
        
        try:
            data_bytes = self.redis_client.get(key)
            if data_bytes is None:
                return None
            
            try:
                data_str = data_bytes.decode('utf-8')
                data = json.loads(data_str)
                # Handle generic numpy arrays wrapped in JSON
                if isinstance(data, dict) and data.get("__numpy__"):
                    import base64
                    buffer = base64.b64decode(data["data"])
                    return np.frombuffer(buffer, dtype=np.dtype(data["dtype"])).reshape(data["shape"]).copy()
                return data
            except (UnicodeDecodeError, json.JSONDecodeError):
                # We refuse to use pickle.loads() for security reasons.
                # If we encounter un-decodable bytes (likely legacy pickle data),
                # we log a warning and return None.
                logger.warning("Legacy non-JSON (possibly pickle) cache detected and ignored.", key=key)
                return None
                
        except Exception as e:
            logger.error("redis_get_cache_error", key=key, error=str(e))
            return None
    
    def get(self, key: str) -> Optional[Any]:
        """Alias for get_cache method"""
        return self.get_cache(key)
    
    def setex(self, key: str, ttl: int, value: Any) -> bool:
        """Set cache with expiration time"""
        if not self.connected:
            return False
        
        try:
            if isinstance(value, np.ndarray):
                import base64
                data_dict = {
                    "__numpy__": True,
                    "dtype": str(value.dtype),
                    "shape": value.shape,
                    "data": base64.b64encode(value.tobytes()).decode('ascii')
                }
                data_bytes = json.dumps(data_dict).encode('utf-8')
            elif isinstance(value, str):
                data_bytes = value.encode()
            else:
                data_bytes = json.dumps(value, default=str).encode()
            
            return self.redis_client.setex(key, ttl, data_bytes)
        except Exception as e:
            logger.error("redis_set_cache_error", key=key, error=str(e))
            return False
    
    def set_cache(self, key: str, data: Any, ttl: int = 3600) -> bool:
        """Generic method to cache any data"""
        return self.setex(key, ttl, data)
    
    def delete_cache(self, key: str) -> bool:
        """Delete cached data by key"""
        if not self.connected:
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error("redis_delete_cache_error", key=key, error=str(e))
            return False
    
    def delete_keys_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern using SCAN"""
        return self.safe_delete_pattern(pattern)
    
    def invalidate_content_cache(self, content_id: int) -> bool:
        """Invalidate all cache related to a specific content item using SCAN"""
        if not self.connected:
            return False
        
        try:
            patterns = [
                f"*content_analysis:{content_id}*",
                f"*content_embedding:{content_id}*",
                f"*content_analysis_data:{content_id}*"
            ]
            
            deleted_count = 0
            for pattern in patterns:
                deleted_count += self.safe_delete_pattern(pattern)
            
            logger.info("redis_invalidate_content_success", count=deleted_count, content_id=content_id)
            return deleted_count > 0
        except Exception as e:
            logger.error("redis_invalidate_content_error", content_id=content_id, error=str(e))
            return False
    
    def invalidate_user_recommendations(self, user_id: int) -> bool:
        """Invalidate all recommendation cache for a user using SCAN"""
        if not self.connected:
            return False
        
        try:
            patterns = [
                f"*recommendations:{user_id}*",
                f"*smart_recommendations:{user_id}*",
                f"*enhanced_recommendations:{user_id}*",
                f"*unified_recommendations:{user_id}*",
                f"*gemini_enhanced_recommendations:{user_id}*",
                f"*project_recommendations:{user_id}*",
                f"*task_recommendations:{user_id}*",
                f"*learning_path_recommendations:{user_id}*"
            ]
            
            deleted_count = 0
            for pattern in patterns:
                deleted_count += self.safe_delete_pattern(pattern)
            
            logger.info("redis_invalidate_user_rec_success", count=deleted_count, user_id=user_id)
            return deleted_count > 0
        except Exception as e:
            logger.error("redis_invalidate_user_rec_error", user_id=user_id, error=str(e))
            return False
    
    def invalidate_project_cache(self, project_id: int) -> bool:
        """Invalidate all cache related to a specific project using SCAN"""
        if not self.connected:
            return False
        
        try:
            patterns = [
                f"*project_analysis:{project_id}*",
                f"*project_recommendations:*{project_id}*",
                f"*project_embedding:{project_id}*"
            ]
            
            deleted_count = 0
            for pattern in patterns:
                deleted_count += self.safe_delete_pattern(pattern)
            
            logger.info("redis_invalidate_project_success", count=deleted_count, project_id=project_id)
            return deleted_count > 0
        except Exception as e:
            logger.error("redis_invalidate_project_error", project_id=project_id, error=str(e))
            return False
    
    def invalidate_analysis_cache(self, content_id: int = None, user_id: int = None) -> bool:
        """Invalidate analysis cache for content or user using SCAN"""
        if not self.connected:
            return False
        
        try:
            patterns = []
            if content_id:
                patterns.extend([
                    f"*content_analysis:{content_id}*",
                    f"*analysis_data:{content_id}*"
                ])
            if user_id:
                patterns.extend([
                    f"*user_analysis:{user_id}*",
                    f"*user_context:{user_id}*"
                ])
            
            if not patterns:
                patterns = ["*content_analysis:*", "*analysis_data:*"]
            
            deleted_count = 0
            for pattern in patterns:
                deleted_count += self.safe_delete_pattern(pattern)
            
            logger.info("redis_invalidate_analysis_success", count=deleted_count, content_id=content_id, user_id=user_id)
            return deleted_count > 0
        except Exception as e:
            logger.error("redis_invalidate_analysis_error", content_id=content_id, user_id=user_id, error=str(e))
            return False
    
    def invalidate_all_recommendations(self) -> bool:
        """Invalidate all recommendation cache using SCAN"""
        if not self.connected:
            return False
        
        try:
            patterns = [
                "*recommendations:*",
                "*smart_recommendations:*",
                "*enhanced_recommendations:*",
                "*unified_recommendations:*",
                "*gemini_enhanced_recommendations:*",
                "*project_recommendations:*",
                "*task_recommendations:*",
                "*learning_path_recommendations:*"
            ]
            
            deleted_count = 0
            for pattern in patterns:
                deleted_count += self.safe_delete_pattern(pattern)
            
            logger.info("redis_invalidate_all_rec_success", count=deleted_count)
            return deleted_count > 0
        except Exception as e:
            logger.error("redis_invalidate_all_rec_error", error=str(e))
            return False
    
    # Cache Cleanup
    def cleanup_expired_keys(self, pattern: str = "fuze:*") -> int:
        """Clean up expired keys (monitored via SCAN)"""
        if not self.connected:
            return 0
        
        try:
            count = 0
            cursor = 0
            while True:
                cursor, keys = self.redis_client.scan(cursor=cursor, match=pattern, count=1000)
                count += len(keys)
                if cursor == 0: break
            return count
        except Exception as e:
            logger.error("redis_cleanup_expired_keys_error", error=str(e))
            return 0

# Global Redis instance
redis_cache = RedisCache() 
