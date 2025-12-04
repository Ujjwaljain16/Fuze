#!/usr/bin/env python3
"""
API Key Revocation Manager
Implements Active Revocation List (ARL) in Redis for immediate key invalidation
"""

import logging
import hashlib
from typing import Optional, Set
from datetime import timedelta

class APIKeyRevocationManager:
    """
    Manages revoked API keys using Redis Set for instant invalidation.
    
    This prevents stale authorization where deleted keys are still accepted
    due to caching.
    
    Architecture:
    - When user deletes key → add to revoked_keys set
    - Every request checks revoked_keys first (0.2ms Redis lookup)
    - If revoked → block instantly (no DB hit)
    - If not revoked → use cached validation
    """
    
    def __init__(self, redis_cache=None):
        """
        Initialize the revocation manager
        
        Args:
            redis_cache: RedisCache instance (optional, will create if not provided)
        """
        self.logger = logging.getLogger("APIKeyRevocationManager")
        
        # Use provided Redis cache or create new one
        if redis_cache:
            self.redis_cache = redis_cache
        else:
            try:
                from utils.redis_utils import RedisCache
                self.redis_cache = RedisCache()
            except Exception as e:
                self.logger.error(f"Failed to initialize Redis cache: {e}")
                self.redis_cache = None
        
        # Redis key for revoked API keys set
        self.REVOKED_KEYS_SET = "fuze:api_keys:revoked"
        
        # TTL for revoked keys (keep for 7 days to handle edge cases)
        self.REVOCATION_TTL = 7 * 24 * 60 * 60  # 7 days in seconds
    
    def _hash_api_key(self, api_key: str) -> str:
        """
        Hash API key for secure storage in revocation list.
        We never store actual keys, only their hashes.
        """
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def revoke_api_key(self, api_key: str, user_id: int = None) -> bool:
        """
        Add API key to revocation list (immediate invalidation).
        
        Args:
            api_key: The API key to revoke
            user_id: Optional user ID for logging purposes
            
        Returns:
            True if successfully revoked, False otherwise
        """
        if not self.redis_cache or not self.redis_cache.connected:
            self.logger.warning("Redis not available, cannot revoke key (falling back to DB only)")
            return False
        
        try:
            # Hash the API key
            key_hash = self._hash_api_key(api_key)
            
            # Add to Redis set
            self.redis_cache.redis_client.sadd(self.REVOKED_KEYS_SET, key_hash)
            
            # Set expiration on the entire set (refreshed on each addition)
            self.redis_cache.redis_client.expire(self.REVOKED_KEYS_SET, self.REVOCATION_TTL)
            
            user_info = f" for user {user_id}" if user_id else ""
            self.logger.info(f"API key revoked{user_info} (hash: {key_hash[:8]}...)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error revoking API key: {e}")
            return False
    
    def is_api_key_revoked(self, api_key: str) -> bool:
        """
        Check if API key is in revocation list.
        
        This is a FAST operation (~0.2ms) and should be called BEFORE
        any cached validation.
        
        Args:
            api_key: The API key to check
            
        Returns:
            True if revoked, False if valid or Redis unavailable
        """
        if not self.redis_cache or not self.redis_cache.connected:
            # If Redis is down, fail open (allow request)
            # This is safer than blocking all requests
            return False
        
        try:
            # Hash the API key
            key_hash = self._hash_api_key(api_key)
            
            # Check if in revoked set (O(1) operation)
            is_revoked = self.redis_cache.redis_client.sismember(self.REVOKED_KEYS_SET, key_hash)
            
            if is_revoked:
                self.logger.warning(f"Blocked revoked API key (hash: {key_hash[:8]}...)")
            
            return bool(is_revoked)
            
        except Exception as e:
            self.logger.error(f"Error checking revocation status: {e}")
            # Fail open if error
            return False
    
    def remove_from_revocation_list(self, api_key: str) -> bool:
        """
        Remove API key from revocation list (e.g., if re-added by user).
        
        Args:
            api_key: The API key to unrevoke
            
        Returns:
            True if successfully removed, False otherwise
        """
        if not self.redis_cache or not self.redis_cache.connected:
            return False
        
        try:
            # Hash the API key
            key_hash = self._hash_api_key(api_key)
            
            # Remove from set
            removed = self.redis_cache.redis_client.srem(self.REVOKED_KEYS_SET, key_hash)
            
            if removed:
                self.logger.info(f"API key removed from revocation list (hash: {key_hash[:8]}...)")
            
            return bool(removed)
            
        except Exception as e:
            self.logger.error(f"Error removing from revocation list: {e}")
            return False
    
    def get_revoked_count(self) -> int:
        """Get total number of revoked keys"""
        if not self.redis_cache or not self.redis_cache.connected:
            return 0
        
        try:
            return self.redis_cache.redis_client.scard(self.REVOKED_KEYS_SET)
        except Exception as e:
            self.logger.error(f"Error getting revoked count: {e}")
            return 0
    
    def clear_all_revocations(self) -> bool:
        """
        Clear all revoked keys (admin function, use with caution).
        
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_cache or not self.redis_cache.connected:
            return False
        
        try:
            self.redis_cache.redis_client.delete(self.REVOKED_KEYS_SET)
            self.logger.warning("All API key revocations cleared (admin action)")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing revocations: {e}")
            return False


# Global instance (initialized when needed)
_revocation_manager = None

def get_revocation_manager():
    """Get or create global revocation manager instance"""
    global _revocation_manager
    if _revocation_manager is None:
        _revocation_manager = APIKeyRevocationManager()
    return _revocation_manager
