#!/usr/bin/env python3
"""
API Key Revocation Manager
Implements Active Revocation List (ARL) in Redis for immediate key invalidation
using independent per-key TTLs and HMAC-SHA256 hashing.
"""

import os
import hmac
import hashlib
from typing import Optional
from core.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_REVOCATION_SECRET = b"fuze_key_revocation_default_secret_salt_2026"


class APIKeyRevocationManager:
    """
    Manages revoked API keys using per-key Redis keys with explicit TTLs.

    Architecture:
    - Per-key TTL using 'fuze:revoked:<hmac_hash>' key structure
    - Independent 7-day expiration per key (automatic memory cleanup)
    - O(1) EXISTS checks (~0.2ms lookup)
    - HMAC-SHA256 salted hashing to prevent rainbow-table brute-force attacks
    """

    def __init__(self, redis_cache=None):
        """
        Initialize the revocation manager

        Args:
            redis_cache: RedisCache instance (optional, will create if not provided)
        """
        if redis_cache:
            self.redis_cache = redis_cache
        else:
            try:
                from utils.redis_utils import RedisCache
                self.redis_cache = RedisCache()
            except Exception as e:
                logger.error("revocation_redis_init_failed", extra={"error": str(e)})
                self.redis_cache = None

        self.REVOCATION_KEY_PREFIX = "fuze:revoked:"
        self.REVOCATION_TTL = 7 * 24 * 60 * 60  # 7 days in seconds
        self.fail_open = os.environ.get('REVOCATION_FAIL_OPEN', 'true').lower() == 'true'

        secret_env = os.environ.get('REVOCATION_SECRET')
        self._secret = secret_env.encode() if secret_env else DEFAULT_REVOCATION_SECRET

    def _hash_api_key(self, api_key: str) -> str:
        """
        Hash API key using HMAC-SHA256 for secure storage.
        We never store actual keys, only HMAC hashes.
        """
        if not api_key or not isinstance(api_key, str):
            raise ValueError("api_key must be a non-empty string")
        return hmac.new(self._secret, api_key.encode('utf-8'), hashlib.sha256).hexdigest()

    def _get_redis_key(self, key_hash: str) -> str:
        return f"{self.REVOCATION_KEY_PREFIX}{key_hash}"

    def revoke_api_key(self, api_key: str, user_id: Optional[int] = None) -> bool:
        """
        Add API key to revocation list with an independent 7-day TTL.

        Args:
            api_key: The API key to revoke
            user_id: Optional user ID for logging purposes

        Returns:
            True if successfully revoked, False otherwise
        """
        if not self.redis_cache or not self.redis_cache.connected:
            logger.warning("revocation_redis_not_available", extra={"user_id": user_id})
            return False

        try:
            key_hash = self._hash_api_key(api_key)
            redis_key = self._get_redis_key(key_hash)

            # SETEX in Redis: per-key independent TTL
            self.redis_cache.redis_client.set(redis_key, "1", ex=self.REVOCATION_TTL)
            logger.info("api_key_revoked", extra={"user_id": user_id, "key_hash_preview": key_hash[:8]})
            return True

        except Exception:
            logger.exception("api_key_revocation_failed", extra={"user_id": user_id})
            return False

    def is_api_key_revoked(self, api_key: str) -> bool:
        """
        Check if API key is in revocation list using O(1) Redis EXISTS.

        Args:
            api_key: The API key to check

        Returns:
            True if revoked, False if valid or Redis unavailable (if fail_open)
        """
        if not self.redis_cache or not self.redis_cache.connected:
            return not self.fail_open

        try:
            key_hash = self._hash_api_key(api_key)
            redis_key = self._get_redis_key(key_hash)

            is_revoked = bool(self.redis_cache.redis_client.exists(redis_key))

            if is_revoked:
                logger.warning("revoked_api_key_blocked", extra={"key_hash_preview": key_hash[:8]})

            return is_revoked

        except Exception:
            logger.exception("api_key_revocation_check_failed")
            return not self.fail_open

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
            key_hash = self._hash_api_key(api_key)
            redis_key = self._get_redis_key(key_hash)

            deleted = self.redis_cache.redis_client.delete(redis_key)
            if deleted:
                logger.info("api_key_unrevoked", extra={"key_hash_preview": key_hash[:8]})

            return bool(deleted)

        except Exception:
            logger.exception("api_key_unrevocation_failed")
            return False

    def clear_all_revocations(self, confirm: bool = False) -> bool:
        """
        Clear all revoked keys (admin function, requires explicit confirm=True).

        Returns:
            True if successful, False otherwise
        """
        if not confirm:
            logger.error("clear_all_revocations_blocked_missing_confirmation")
            return False

        if not self.redis_cache or not self.redis_cache.connected:
            return False

        try:
            keys = self.redis_cache.redis_client.keys(f"{self.REVOCATION_KEY_PREFIX}*")
            if keys:
                self.redis_cache.redis_client.delete(*keys)
            logger.warning("all_revocations_cleared", extra={"cleared_count": len(keys)})
            return True
        except Exception:
            logger.exception("clear_revocations_failed")
            return False


# Global instance (initialized when needed)
_revocation_manager: Optional[APIKeyRevocationManager] = None


def get_revocation_manager() -> APIKeyRevocationManager:
    """Get or create global revocation manager instance"""
    global _revocation_manager
    if _revocation_manager is None:
        _revocation_manager = APIKeyRevocationManager()
    return _revocation_manager
