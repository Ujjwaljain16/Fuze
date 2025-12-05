import redis
import json
import pickle
import hashlib
import os
from typing import Optional, Dict, Any, List
from datetime import timedelta
import numpy as np

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Global connection pool (shared across instances)
_redis_connection_pool = None
_pool_lock = __import__('threading').Lock()

class RedisCache:
    """Redis cache utility for Fuze application with connection pooling"""
    
    def __init__(self):
        global _redis_connection_pool
        
        # Check if REDIS_URL is provided (supports both redis:// and rediss:// for TLS)
        redis_url = os.environ.get('REDIS_URL')
        
        if redis_url:
            # Upstash requires TLS but provides redis:// URLs
            # Convert redis:// to rediss:// (keep port 6379 - Upstash handles TLS on standard port)
            if 'upstash.io' in redis_url and redis_url.startswith('redis://'):
                redis_url = redis_url.replace('redis://', 'rediss://', 1)
                print("Converted Upstash URL to use TLS (rediss://)")
            
            # Use REDIS_URL (supports TLS with rediss://)
            try:
                # Create or reuse connection pool (thread-safe)
                with _pool_lock:
                    if _redis_connection_pool is None:
                        # Parse URL to add SSL parameters for TLS connections
                        pool_kwargs = {
                            'decode_responses': False,  # Keep binary for embeddings
                            'socket_connect_timeout': 10,
                            'socket_timeout': 10,
                            'max_connections': 20,  # Connection pool size
                            'socket_keepalive': True,
                            'socket_keepalive_options': {
                                1: 1,  # TCP_KEEPIDLE
                                2: 1,  # TCP_KEEPINTVL  
                                3: 3   # TCP_KEEPCNT
                            }
                        }
                        
                        # Add SSL parameters for rediss:// URLs
                        if redis_url.startswith('rediss://'):
                            pool_kwargs['ssl_cert_reqs'] = None  # Don't verify SSL certificates for Upstash
                        
                        _redis_connection_pool = redis.ConnectionPool.from_url(
                            redis_url,
                            **pool_kwargs
                        )
                        ssl_status = "with TLS" if redis_url.startswith('rediss://') else "without TLS"
                        print(f"Redis connection pool created ({ssl_status})")
                
                # Use connection from pool
                self.redis_client = redis.Redis(connection_pool=_redis_connection_pool)
                # Test connection
                self.redis_client.ping()
                self.connected = True
            except Exception as e:
                print(f"Redis connection via REDIS_URL failed: {e}")
                self.connected = False
                self.redis_client = None
        else:
            # Use individual connection parameters
            self.redis_host = os.environ.get('REDIS_HOST', 'localhost')
            self.redis_port = int(os.environ.get('REDIS_PORT', 6379))
            self.redis_db = int(os.environ.get('REDIS_DB', 0))
            self.redis_password = os.environ.get('REDIS_PASSWORD')
            
            # Check if TLS is required (for Upstash and other cloud providers)
            use_ssl = os.environ.get('REDIS_SSL', 'false').lower() == 'true'
            # Auto-detect TLS for common cloud providers
            if not use_ssl and any(provider in self.redis_host for provider in ['upstash.io', 'redislabs.com', 'redis.cache']):
                use_ssl = True
                print("Auto-detected TLS requirement for cloud Redis provider")
            
            try:
                connection_params = {
                    'host': self.redis_host,
                    'port': self.redis_port,
                    'db': self.redis_db,
                    'password': self.redis_password,
                    'decode_responses': False,  # Keep binary for embeddings
                    'socket_connect_timeout': 10,
                    'socket_timeout': 10
                }
                
                # Add SSL parameters if TLS is required
                if use_ssl:
                    connection_params['ssl'] = True
                    connection_params['ssl_cert_reqs'] = None  # Don't verify cert (for cloud providers)
                
                self.redis_client = redis.Redis(**connection_params)
                
                # Test connection
                self.redis_client.ping()
                self.connected = True
                ssl_status = "with TLS" if use_ssl else "without TLS"
                print(f"Redis connected successfully {ssl_status}")
            except Exception as e:
                print(f"Redis connection failed: {e}")
                self.connected = False
                self.redis_client = None
    
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
            # Serialize numpy array
            embedding_bytes = pickle.dumps(embedding)
            return self.redis_client.setex(key, ttl, embedding_bytes)
        except Exception as e:
            print(f"Error caching embedding: {e}")
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
                return pickle.loads(embedding_bytes)
        except Exception as e:
            print(f"Error getting cached embedding: {e}")
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
            print(f"Error caching scraped content: {e}")
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
            print(f"Error getting cached scraped content: {e}")
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
            print(f"Error caching user bookmarks: {e}")
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
            print(f"Error getting cached user bookmarks: {e}")
        return None
    
    def invalidate_user_bookmarks(self, user_id: int) -> bool:
        """Invalidate user bookmarks cache when new bookmarks are added"""
        if not self.connected:
            return False
        
        try:
            key = self._get_key("user_bookmarks", str(user_id))
            return bool(self.redis_client.delete(key))
        except Exception as e:
            print(f"Error invalidating user bookmarks: {e}")
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
            print(f"Error checking rate limit: {e}")
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
            print(f"Error caching session: {e}")
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
            print(f"Error getting cached session: {e}")
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
            print(f"Error caching query result: {e}")
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
            print(f"Error getting cached query result: {e}")
        return None
    
    def invalidate_query_cache(self, pattern: str = None) -> int:
        """Invalidate query cache by pattern"""
        if not self.connected:
            return 0
        
        try:
            if pattern:
                keys = self.redis_client.keys(self._get_key("query", f"*{pattern}*"))
            else:
                keys = self.redis_client.keys(self._get_key("query", "*"))
            
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Error invalidating query cache: {e}")
            return 0
    
    # API Response Cache
    def cache_api_response(self, endpoint: str, params: Dict, response: Any, ttl: int = 60) -> bool:
        """Cache API response"""
        if not self.connected:
            return False
        
        try:
            # Create cache key from endpoint and params
            import hashlib
            params_str = json.dumps(params, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()
            cache_key = f"{endpoint}:{params_hash}"
            
            key = self._get_key("api", cache_key)
            response_json = json.dumps(response, default=str)
            return self.redis_client.setex(key, ttl, response_json.encode())
        except Exception as e:
            print(f"Error caching API response: {e}")
            return False
    
    def get_cached_api_response(self, endpoint: str, params: Dict) -> Optional[Any]:
        """Get cached API response"""
        if not self.connected:
            return None
        
        try:
            import hashlib
            params_str = json.dumps(params, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()
            cache_key = f"{endpoint}:{params_hash}"
            
            key = self._get_key("api", cache_key)
            response_json = self.redis_client.get(key)
            if response_json:
                return json.loads(response_json.decode())
        except Exception as e:
            print(f"Error getting cached API response: {e}")
        return None
    
    # Cache Statistics
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.connected:
            return {"connected": False}
        
        try:
            info = self.redis_client.info()
            # Count keys by prefix
            query_keys = len(self.redis_client.keys(self._get_key("query", "*")))
            api_keys = len(self.redis_client.keys(self._get_key("api", "*")))
            embedding_keys = len(self.redis_client.keys(self._get_key("embedding", "*")))
            
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "cache_keys": {
                    "queries": query_keys,
                    "api_responses": api_keys,
                    "embeddings": embedding_keys,
                },
                "keyspace_misses": info.get("keyspace_misses", 0)
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
            
            # Try to deserialize data
            try:
                # Try pickle first (for numpy arrays)
                return pickle.loads(data_bytes)
            except:
                # Try JSON if pickle fails
                return json.loads(data_bytes.decode())
                
        except Exception as e:
            print(f"Error getting cache: {e}")
            return None
    
    def get(self, key: str) -> Optional[Any]:
        """Alias for get_cache method"""
        return self.get_cache(key)
    
    def setex(self, key: str, ttl: int, value: Any) -> bool:
        """Set cache with expiration time"""
        if not self.connected:
            return False
        
        try:
            # Serialize data
            if isinstance(value, np.ndarray):
                data_bytes = pickle.dumps(value)
            elif isinstance(value, str):
                data_bytes = value.encode()
            else:
                data_bytes = json.dumps(value, default=str).encode()
            
            return self.redis_client.setex(key, ttl, data_bytes)
        except Exception as e:
            print(f"Error setting cache with TTL: {e}")
            return False
    
    def set_cache(self, key: str, data: Any, ttl: int = 3600) -> bool:
        """Generic method to cache any data"""
        if not self.connected:
            return False
        
        try:
            # Serialize data
            if isinstance(data, np.ndarray):
                data_bytes = pickle.dumps(data)
            else:
                data_bytes = json.dumps(data, default=str).encode()
            
            return self.redis_client.setex(key, ttl, data_bytes)
        except Exception as e:
            print(f"Error setting cache: {e}")
            return False
    
    def delete_cache(self, key: str) -> bool:
        """Delete cached data by key"""
        if not self.connected:
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            print(f"Error deleting cache: {e}")
            return False
    
    def delete_keys_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern"""
        if not self.connected:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Error deleting keys with pattern {pattern}: {e}")
            return 0
    
    def invalidate_content_cache(self, content_id: int) -> bool:
        """Invalidate all cache related to a specific content item"""
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
                deleted_count += self.delete_keys_pattern(pattern)
            
            print(f"Invalidated {deleted_count} cache entries for content {content_id}")
            return deleted_count > 0
        except Exception as e:
            print(f"Error invalidating content cache for {content_id}: {e}")
            return False
    
    def invalidate_user_recommendations(self, user_id: int) -> bool:
        """Invalidate all recommendation cache for a user"""
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
                deleted_count += self.delete_keys_pattern(pattern)
            
            print(f"Invalidated {deleted_count} recommendation cache entries for user {user_id}")
            return deleted_count > 0
        except Exception as e:
            print(f"Error invalidating user recommendations for {user_id}: {e}")
            return False
    
    def invalidate_project_cache(self, project_id: int) -> bool:
        """Invalidate all cache related to a specific project"""
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
                deleted_count += self.delete_keys_pattern(pattern)
            
            print(f"Invalidated {deleted_count} cache entries for project {project_id}")
            return deleted_count > 0
        except Exception as e:
            print(f"Error invalidating project cache for {project_id}: {e}")
            return False
    
    def invalidate_analysis_cache(self, content_id: int = None, user_id: int = None) -> bool:
        """Invalidate analysis cache for content or user"""
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
                deleted_count += self.delete_keys_pattern(pattern)
            
            print(f"Invalidated {deleted_count} analysis cache entries")
            return deleted_count > 0
        except Exception as e:
            print(f"Error invalidating analysis cache: {e}")
            return False
    
    def invalidate_all_recommendations(self) -> bool:
        """Invalidate all recommendation cache"""
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
                deleted_count += self.delete_keys_pattern(pattern)
            
            print(f"Invalidated {deleted_count} recommendation cache entries")
            return deleted_count > 0
        except Exception as e:
            print(f"Error invalidating all recommendations: {e}")
            return False
    
    # Cache Cleanup
    def cleanup_expired_keys(self, pattern: str = "fuze:*") -> int:
        """Clean up expired keys (this is usually automatic in Redis)"""
        if not self.connected:
            return 0
        
        try:
            # This is just for monitoring, Redis handles expiration automatically
            keys = self.redis_client.keys(pattern)
            return len(keys)
        except Exception as e:
            print(f"Error cleaning up keys: {e}")
            return 0

# Global Redis instance
redis_cache = RedisCache() 