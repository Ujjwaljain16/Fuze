import redis
import json
import pickle
import hashlib
import os
from typing import Optional, Dict, Any, List
from datetime import timedelta
import numpy as np

class RedisCache:
    """Redis cache utility for Fuze application"""
    
    def __init__(self):
        # Redis connection
        self.redis_host = os.environ.get('REDIS_HOST', 'localhost')
        self.redis_port = int(os.environ.get('REDIS_PORT', 6379))
        self.redis_db = int(os.environ.get('REDIS_DB', 0))
        self.redis_password = os.environ.get('REDIS_PASSWORD')
        
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_password,
                decode_responses=False,  # Keep binary for embeddings
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            self.connected = True
            print("✅ Redis connected successfully")
        except Exception as e:
            print(f"⚠️ Redis connection failed: {e}")
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
    
    # Cache Statistics
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.connected:
            return {"connected": False}
        
        try:
            info = self.redis_client.info()
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            return {"connected": True, "error": str(e)}
    
    # Generic Cache Methods
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
    
    def get_cache(self, key: str) -> Optional[Any]:
        """Generic method to get cached data"""
        if not self.connected:
            return None
        
        try:
            data_bytes = self.redis_client.get(key)
            if data_bytes:
                # Try to deserialize as JSON first, then as pickle
                try:
                    return json.loads(data_bytes.decode())
                except (json.JSONDecodeError, UnicodeDecodeError):
                    try:
                        return pickle.loads(data_bytes)
                    except:
                        return data_bytes.decode()
        except Exception as e:
            print(f"Error getting cache: {e}")
        return None
    
    def delete_cache(self, key: str) -> bool:
        """Delete cached data by key"""
        if not self.connected:
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            print(f"Error deleting cache: {e}")
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