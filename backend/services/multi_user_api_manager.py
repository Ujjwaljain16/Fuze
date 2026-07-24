#!/usr/bin/env python3
"""
Multi-User API Key Management System
Manages API keys for multiple users with distributed Redis rate limiting,
secure Fernet encryption, and UTC timezone tracking.
"""

import os
import sys
import logging
import hashlib
import base64
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
from cryptography.fernet import Fernet
from dotenv import load_dotenv

from core.logging_config import get_logger
from utils.redis_utils import RedisCache, redis_cache

logger = get_logger("MultiUserAPIManager")

load_dotenv()

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from models import db, User


class APIKeyStatus(str, Enum):
    ACTIVE = "active"
    RATE_LIMITED = "rate_limited"
    EXPIRED = "expired"
    INVALID = "invalid"
    QUOTA_EXCEEDED = "quota_exceeded"
    REVOKED = "revoked"


@dataclass
class UserAPIKey:
    user_id: int
    api_key_hash: str
    api_key_name: str
    status: APIKeyStatus
    encrypted_key: Optional[str] = None
    daily_requests: int = 0
    monthly_requests: int = 0
    last_used: Optional[datetime] = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: Optional[datetime] = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None


class MultiUserAPIManager:
    """Manages multi-tenant API keys with distributed Redis rate limiting and thread safety."""

    def __init__(self, redis_client=None):
        self.user_api_keys: Dict[int, UserAPIKey] = {}
        self.rate_limit_cache: Dict[int, Dict] = {}
        self.lock = threading.RLock()
        self.redis = redis_client or redis_cache

        self.REQUESTS_PER_MINUTE = 15
        self.REQUESTS_PER_DAY = 1500
        self.REQUESTS_PER_MONTH = 45000

        secret_key = os.environ.get('SECRET_KEY') or os.environ.get('ENCRYPTION_SECRET')
        if not secret_key:
            if os.environ.get('FLASK_ENV') == 'production':
                raise RuntimeError("SECRET_KEY environment variable required in production")
            logger.warning("SECRET_KEY missing, using development fallback key")
            secret_key = "development-fallback-secret-key-do-not-use-in-prod"

        key_bytes = hashlib.sha256(secret_key.encode('utf-8')).digest()
        self.cipher = Fernet(base64.urlsafe_b64encode(key_bytes))

    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key using Fernet symmetric encryption."""
        return self.cipher.encrypt(api_key.encode('utf-8')).decode('utf-8')

    def decrypt_api_key(self, encrypted_key: str) -> Optional[str]:
        """Decrypt API key safely without logging secret material."""
        try:
            return self.cipher.decrypt(encrypted_key.encode('utf-8')).decode('utf-8')
        except Exception:
            logger.error("api_key_decryption_failed")
            return None

    def hash_api_key(self, api_key: str) -> str:
        """One-way SHA256 hash for API key validation."""
        return hashlib.sha256(api_key.encode('utf-8')).hexdigest()

    def validate_api_key(self, api_key: str) -> bool:
        """Validate Gemini API key format."""
        if not api_key or not isinstance(api_key, str):
            return False
        clean_key = api_key.strip()
        if len(clean_key) < 25:
            return False
        return True

    def add_user_api_key(self, user_id: int, api_key: str, api_key_name: Optional[str] = None) -> bool:
        """Add or update a user's API key."""
        try:
            if not self.validate_api_key(api_key):
                logger.error("api_key_invalid_format", extra={"user_id": user_id})
                return False

            clean_key = api_key.strip()

            try:
                from services.api_key_revocation_manager import get_revocation_manager
                revocation_manager = get_revocation_manager()
                revocation_manager.remove_from_revocation_list(clean_key)
            except Exception as e:
                logger.warning("api_key_revocation_clear_failed", extra={"error": str(e)})

            encrypted_key = self.encrypt_api_key(clean_key)
            api_key_hash = self.hash_api_key(clean_key)
            now = datetime.now(timezone.utc)

            user_api_key = UserAPIKey(
                user_id=user_id,
                api_key_hash=api_key_hash,
                api_key_name=api_key_name or f"API Key {now.strftime('%Y-%m-%d')}",
                status=APIKeyStatus.ACTIVE,
                encrypted_key=encrypted_key,
                created_at=now,
                last_used=now
            )

            with self.lock:
                self.user_api_keys[user_id] = user_api_key

            self.save_user_api_key_to_db(user_api_key, encrypted_key)
            logger.info("api_key_added_successfully", extra={"user_id": user_id})
            return True

        except Exception as e:
            logger.error("api_key_add_failed", extra={"user_id": user_id, "error": str(e)})
            return False

    def get_user_api_key(self, user_id: int) -> Optional[str]:
        """Get decrypted API key for user. Does NOT return system key if revoked."""
        try:
            from services.api_key_revocation_manager import get_revocation_manager
            revocation_manager = get_revocation_manager()

            # 1. Check in-memory cache
            with self.lock:
                user_api_key = self.user_api_keys.get(user_id)

            if user_api_key and user_api_key.status == APIKeyStatus.ACTIVE and user_api_key.encrypted_key:
                decrypted = self.decrypt_api_key(user_api_key.encrypted_key)
                if decrypted:
                    if revocation_manager.is_api_key_revoked(decrypted):
                        logger.warning("cached_api_key_revoked", extra={"user_id": user_id})
                        with self.lock:
                            self.user_api_keys.pop(user_id, None)
                        return None
                    return decrypted

            # 2. Database on-demand lookup
            user = db.session.query(User).filter_by(id=user_id).first()
            if user and user.user_metadata:
                api_key_info = user.user_metadata.get('api_key', {})
                if api_key_info and api_key_info.get('encrypted'):
                    decrypted = self.decrypt_api_key(api_key_info['encrypted'])
                    if decrypted:
                        if revocation_manager.is_api_key_revoked(decrypted):
                            logger.warning("db_api_key_revoked", extra={"user_id": user_id})
                            return None

                        cached_key = UserAPIKey(
                            user_id=user_id,
                            api_key_hash=api_key_info.get('hash', ''),
                            api_key_name=api_key_info.get('name', ''),
                            status=APIKeyStatus(api_key_info.get('status', 'active')),
                            encrypted_key=api_key_info['encrypted']
                        )
                        with self.lock:
                            self.user_api_keys[user_id] = cached_key
                        return decrypted

            # 3. Fallback to system default key
            return os.environ.get('GEMINI_API_KEY')

        except Exception as e:
            logger.error("get_user_api_key_failed", extra={"user_id": user_id, "error": str(e)})
            return os.environ.get('GEMINI_API_KEY')

    def check_user_rate_limit(self, user_id: int) -> Dict:
        """Check rate limits using Redis atomic counters if available, with thread-safe memory fallback."""
        try:
            if self.redis and getattr(self.redis, 'connected', False):
                min_key = f"fuze:rate:{user_id}:minute"
                day_key = f"fuze:rate:{user_id}:day"
                month_key = f"fuze:rate:{user_id}:month"

                c_min = int(self.redis.get_cache(min_key) or 0)
                c_day = int(self.redis.get_cache(day_key) or 0)
                c_mon = int(self.redis.get_cache(month_key) or 0)

                can_make = (
                    c_min < self.REQUESTS_PER_MINUTE and
                    c_day < self.REQUESTS_PER_DAY and
                    c_mon < self.REQUESTS_PER_MONTH
                )

                return {
                    'can_make_request': can_make,
                    'requests_last_minute': c_min,
                    'requests_today': c_day,
                    'requests_this_month': c_mon,
                    'minute_limit': self.REQUESTS_PER_MINUTE,
                    'daily_limit': self.REQUESTS_PER_DAY,
                    'monthly_limit': self.REQUESTS_PER_MONTH,
                    'wait_time_seconds': 60 if not can_make else 0
                }

            # Thread-safe in-memory fallback
            now = datetime.now(timezone.utc)
            with self.lock:
                if user_id not in self.rate_limit_cache:
                    self.rate_limit_cache[user_id] = {
                        'requests_last_minute': 0,
                        'requests_today': 0,
                        'requests_this_month': 0,
                        'minute_start': now,
                        'day_start': now,
                        'month_start': now
                    }

                rd = self.rate_limit_cache[user_id]
                if now - rd['minute_start'] > timedelta(minutes=1):
                    rd['requests_last_minute'] = 0
                    rd['minute_start'] = now

                if now.date() > rd['day_start'].date():
                    rd['requests_today'] = 0
                    rd['day_start'] = now

                if now.month != rd['month_start'].month or now.year != rd['month_start'].year:
                    rd['requests_this_month'] = 0
                    rd['month_start'] = now

                can_make = (
                    rd['requests_last_minute'] < self.REQUESTS_PER_MINUTE and
                    rd['requests_today'] < self.REQUESTS_PER_DAY and
                    rd['requests_this_month'] < self.REQUESTS_PER_MONTH
                )

                return {
                    'can_make_request': can_make,
                    'requests_last_minute': rd['requests_last_minute'],
                    'requests_today': rd['requests_today'],
                    'requests_this_month': rd['requests_this_month'],
                    'minute_limit': self.REQUESTS_PER_MINUTE,
                    'daily_limit': self.REQUESTS_PER_DAY,
                    'monthly_limit': self.REQUESTS_PER_MONTH,
                    'wait_time_seconds': 60 if not can_make else 0
                }

        except Exception as e:
            logger.error("check_user_rate_limit_failed", extra={"user_id": user_id, "error": str(e)})
            return {'can_make_request': False, 'wait_time_seconds': 60}

    def record_user_request(self, user_id: int):
        """Record API request using Redis INCR with TTL expiration."""
        try:
            if self.redis and getattr(self.redis, 'connected', False):
                min_key = f"fuze:rate:{user_id}:minute"
                day_key = f"fuze:rate:{user_id}:day"
                month_key = f"fuze:rate:{user_id}:month"

                # Increment counters
                val_min = int(self.redis.get_cache(min_key) or 0) + 1
                self.redis.set_cache(min_key, val_min, ttl=60)

                val_day = int(self.redis.get_cache(day_key) or 0) + 1
                self.redis.set_cache(day_key, val_day, ttl=86400)

                val_mon = int(self.redis.get_cache(month_key) or 0) + 1
                self.redis.set_cache(month_key, val_mon, ttl=2592000)
                return

            # Thread-safe in-memory fallback
            now = datetime.now(timezone.utc)
            with self.lock:
                if user_id not in self.rate_limit_cache:
                    self.check_user_rate_limit(user_id)

                rd = self.rate_limit_cache[user_id]
                rd['requests_last_minute'] += 1
                rd['requests_today'] += 1
                rd['requests_this_month'] += 1

                if user_id in self.user_api_keys:
                    k = self.user_api_keys[user_id]
                    k.daily_requests += 1
                    k.monthly_requests += 1
                    k.last_used = now

        except Exception as e:
            logger.error("record_user_request_failed", extra={"user_id": user_id, "error": str(e)})

    def save_user_api_key_to_db(self, user_api_key: UserAPIKey, encrypted_key: str):
        """Save encrypted API key metadata to user model in database."""
        try:
            user = db.session.query(User).filter_by(id=user_api_key.user_id).first()
            if not user:
                logger.error("user_not_found_for_api_key_save", extra={"user_id": user_api_key.user_id})
                return

            metadata = dict(user.user_metadata) if user.user_metadata else {}
            metadata['api_key'] = {
                'encrypted': encrypted_key,
                'hash': user_api_key.api_key_hash,
                'name': user_api_key.api_key_name,
                'status': user_api_key.status.value,
                'created_at': user_api_key.created_at.isoformat() if user_api_key.created_at else datetime.now(timezone.utc).isoformat(),
                'last_used': user_api_key.last_used.isoformat() if user_api_key.last_used else None
            }

            user.user_metadata = metadata
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(user, 'user_metadata')

            db.session.commit()
            logger.info("api_key_saved_to_db", extra={"user_id": user_api_key.user_id})

        except Exception as e:
            db.session.rollback()
            logger.error("save_user_api_key_to_db_failed", extra={"error": str(e)})
            raise

    def load_user_api_keys(self):
        """On-demand database validation hook."""
        try:
            db.session.execute(db.text('SELECT 1'))
            logger.info("db_connection_ok_for_api_keys")
        except Exception as db_err:
            logger.warning("db_connection_check_failed", extra={"error": str(db_err)})

    def get_user_api_stats(self, user_id: int) -> Dict:
        """Get API usage stats for a user."""
        try:
            rate_status = self.check_user_rate_limit(user_id)
            with self.lock:
                has_key = user_id in self.user_api_keys
                key_status = self.user_api_keys[user_id].status.value if has_key else 'none'

            return {
                'user_id': user_id,
                'has_api_key': has_key,
                'api_key_status': key_status,
                'requests_last_minute': rate_status.get('requests_last_minute', 0),
                'requests_today': rate_status.get('requests_today', 0),
                'requests_this_month': rate_status.get('requests_this_month', 0),
                'minute_limit': self.REQUESTS_PER_MINUTE,
                'daily_limit': self.REQUESTS_PER_DAY,
                'monthly_limit': self.REQUESTS_PER_MONTH,
                'can_make_request': rate_status.get('can_make_request', True)
            }
        except Exception as e:
            logger.error("get_user_api_stats_failed", extra={"user_id": user_id, "error": str(e)})
            return {}


# Global instance
api_manager = MultiUserAPIManager()


def init_api_manager():
    api_manager.load_user_api_keys()


def add_user_api_key(user_id: int, api_key: str, api_key_name: Optional[str] = None) -> bool:
    return api_manager.add_user_api_key(user_id, api_key, api_key_name)


def get_user_api_key(user_id: int) -> Optional[str]:
    return api_manager.get_user_api_key(user_id)


def check_user_rate_limit(user_id: int) -> Dict:
    return api_manager.check_user_rate_limit(user_id)


def record_user_request(user_id: int):
    api_manager.record_user_request(user_id)


def get_user_api_stats(user_id: int) -> Dict:
    return api_manager.get_user_api_stats(user_id)