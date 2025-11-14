#!/usr/bin/env python3
"""
Multi-User API Key Management System
Manages API keys for multiple users with individual rate limiting
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import json
import hashlib
import base64
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from models import db, User

class APIKeyStatus(Enum):
    ACTIVE = "active"
    RATE_LIMITED = "rate_limited"
    EXPIRED = "expired"
    INVALID = "invalid"
    QUOTA_EXCEEDED = "quota_exceeded"

@dataclass
class UserAPIKey:
    user_id: int
    api_key_hash: str  # Store hashed version for security
    api_key_name: str  # User-friendly name
    status: APIKeyStatus
    daily_requests: int = 0
    monthly_requests: int = 0
    last_used: datetime = None
    created_at: datetime = None
    expires_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_used is None:
            self.last_used = datetime.now()

class MultiUserAPIManager:
    """
    Manages API keys for multiple users with individual rate limiting
    """
    
    def __init__(self):
        self.user_api_keys: Dict[int, UserAPIKey] = {}
        self.rate_limit_cache: Dict[int, Dict] = {}  # user_id -> rate limit data
        self.logger = logging.getLogger("MultiUserAPIManager")
        
        # Rate limiting settings
        self.REQUESTS_PER_MINUTE = 15
        self.REQUESTS_PER_DAY = 1500
        self.REQUESTS_PER_MONTH = 45000
        
        # Encryption key for API keys (use SECRET_KEY from env)
        secret_key = os.environ.get('SECRET_KEY', 'default-secret-key-change-in-production')
        # Generate Fernet key from SECRET_KEY (32 bytes needed)
        key = hashlib.sha256(secret_key.encode()).digest()
        self.cipher = Fernet(base64.urlsafe_b64encode(key))
        
        # Note: load_user_api_keys() should be called after app context is available
    
    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key for secure storage (can be decrypted)"""
        return self.cipher.encrypt(api_key.encode()).decode()
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt API key from storage"""
        try:
            return self.cipher.decrypt(encrypted_key.encode()).decode()
        except Exception as e:
            self.logger.error(f"Error decrypting API key: {e}")
            return None
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash API key for verification (one-way, cannot decrypt)"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def validate_api_key(self, api_key: str) -> bool:
        """Basic validation of API key format"""
        if not api_key:
            return False
        
        # Basic Gemini API key validation (starts with AIza)
        if not api_key.startswith('AIza'):
            return False
        
        # Check length (Gemini API keys are typically 39 characters)
        if len(api_key) < 30:
            return False
        
        return True
    
    def add_user_api_key(self, user_id: int, api_key: str, api_key_name: str = None) -> bool:
        """Add or update a user's API key"""
        try:
            # Validate API key
            if not self.validate_api_key(api_key):
                self.logger.error(f"Invalid API key format for user {user_id}")
                return False
            
            # Encrypt the API key for storage
            encrypted_key = self.encrypt_api_key(api_key)
            # Also hash for verification
            api_key_hash = self.hash_api_key(api_key)
            
            # Create or update user API key
            user_api_key = UserAPIKey(
                user_id=user_id,
                api_key_hash=api_key_hash,
                api_key_name=api_key_name or f"API Key {datetime.now().strftime('%Y-%m-%d')}",
                status=APIKeyStatus.ACTIVE
            )
            
            # Store encrypted key separately (we'll store in DB)
            user_api_key.encrypted_key = encrypted_key
            
            # Store in memory
            self.user_api_keys[user_id] = user_api_key
            
            # Save to database
            self.save_user_api_key_to_db(user_api_key, encrypted_key)
            
            self.logger.info(f"Successfully added API key for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding API key for user {user_id}: {e}")
            return False
    
    def get_user_api_key(self, user_id: int) -> Optional[str]:
        """Get user's API key (decrypted, returns None if not found)"""
        try:
            # Check if user has API key in memory
            if user_id in self.user_api_keys:
                user_api_key = self.user_api_keys[user_id]
                if user_api_key.status == APIKeyStatus.ACTIVE:
                    # Decrypt and return the key
                    if hasattr(user_api_key, 'encrypted_key'):
                        decrypted = self.decrypt_api_key(user_api_key.encrypted_key)
                        if decrypted:
                            return decrypted
            
            # Try loading from database
            user = db.session.query(User).filter_by(id=user_id).first()
            if user and user.user_metadata:
                api_key_info = user.user_metadata.get('api_key', {})
                if api_key_info and api_key_info.get('encrypted'):
                    decrypted = self.decrypt_api_key(api_key_info['encrypted'])
                    if decrypted:
                        # Cache in memory
                        if user_id not in self.user_api_keys:
                            self.user_api_keys[user_id] = UserAPIKey(
                                user_id=user_id,
                                api_key_hash=api_key_info.get('hash', ''),
                                api_key_name=api_key_info.get('name', ''),
                                status=APIKeyStatus(api_key_info.get('status', 'active'))
                            )
                        self.user_api_keys[user_id].encrypted_key = api_key_info['encrypted']
                        return decrypted
            
            # Fallback to default API key (if no user key found)
            return os.environ.get('GEMINI_API_KEY')
            
        except Exception as e:
            self.logger.error(f"Error getting API key for user {user_id}: {e}")
            # Fallback to default
            return os.environ.get('GEMINI_API_KEY')
    
    def check_user_rate_limit(self, user_id: int) -> Dict:
        """Check if user can make API request"""
        try:
            current_time = datetime.now()
            
            # Initialize rate limit data for user
            if user_id not in self.rate_limit_cache:
                self.rate_limit_cache[user_id] = {
                    'requests_last_minute': 0,
                    'requests_today': 0,
                    'requests_this_month': 0,
                    'last_request_time': None,
                    'minute_start': current_time,
                    'day_start': current_time.replace(hour=0, minute=0, second=0, microsecond=0),
                    'month_start': current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                }
            
            rate_data = self.rate_limit_cache[user_id]
            
            # Reset counters if needed
            if current_time - rate_data['minute_start'] > timedelta(minutes=1):
                rate_data['requests_last_minute'] = 0
                rate_data['minute_start'] = current_time
            
            if current_time.date() > rate_data['day_start'].date():
                rate_data['requests_today'] = 0
                rate_data['day_start'] = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            if current_time.month != rate_data['month_start'].month or current_time.year != rate_data['month_start'].year:
                rate_data['requests_this_month'] = 0
                rate_data['month_start'] = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Check limits
            can_make_request = (
                rate_data['requests_last_minute'] < self.REQUESTS_PER_MINUTE and
                rate_data['requests_today'] < self.REQUESTS_PER_DAY and
                rate_data['requests_this_month'] < self.REQUESTS_PER_MONTH
            )
            
            return {
                'can_make_request': can_make_request,
                'requests_last_minute': rate_data['requests_last_minute'],
                'requests_today': rate_data['requests_today'],
                'requests_this_month': rate_data['requests_this_month'],
                'minute_limit': self.REQUESTS_PER_MINUTE,
                'daily_limit': self.REQUESTS_PER_DAY,
                'monthly_limit': self.REQUESTS_PER_MONTH,
                'wait_time_seconds': self.calculate_wait_time(rate_data) if not can_make_request else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error checking rate limit for user {user_id}: {e}")
            return {'can_make_request': False, 'wait_time_seconds': 60}
    
    def calculate_wait_time(self, rate_data: Dict) -> int:
        """Calculate how long to wait before next request"""
        current_time = datetime.now()
        
        # Check minute limit
        if rate_data['requests_last_minute'] >= self.REQUESTS_PER_MINUTE:
            minute_end = rate_data['minute_start'] + timedelta(minutes=1)
            return max(0, int((minute_end - current_time).total_seconds()))
        
        # Check daily limit
        if rate_data['requests_today'] >= self.REQUESTS_PER_DAY:
            day_end = rate_data['day_start'] + timedelta(days=1)
            return max(0, int((day_end - current_time).total_seconds()))
        
        # Check monthly limit
        if rate_data['requests_this_month'] >= self.REQUESTS_PER_MONTH:
            # Calculate next month start
            if current_time.month == 12:
                next_month = current_time.replace(year=current_time.year + 1, month=1, day=1)
            else:
                next_month = current_time.replace(month=current_time.month + 1, day=1)
            return max(0, int((next_month - current_time).total_seconds()))
        
        return 0
    
    def record_user_request(self, user_id: int):
        """Record that user made an API request"""
        try:
            current_time = datetime.now()
            
            if user_id not in self.rate_limit_cache:
                self.check_user_rate_limit(user_id)  # Initialize
            
            rate_data = self.rate_limit_cache[user_id]
            rate_data['requests_last_minute'] += 1
            rate_data['requests_today'] += 1
            rate_data['requests_this_month'] += 1
            rate_data['last_request_time'] = current_time
            
            # Update user API key usage
            if user_id in self.user_api_keys:
                user_api_key = self.user_api_keys[user_id]
                user_api_key.daily_requests += 1
                user_api_key.monthly_requests += 1
                user_api_key.last_used = current_time
            
            self.logger.debug(f"Recorded request for user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error recording request for user {user_id}: {e}")
    
    def save_user_api_key_to_db(self, user_api_key: UserAPIKey, encrypted_key: str):
        """Save user API key to database (encrypted)"""
        try:
            user = db.session.query(User).filter_by(id=user_api_key.user_id).first()
            if user:
                # Store API key info in user metadata (JSON field)
                metadata = user.user_metadata or {}
                metadata['api_key'] = {
                    'encrypted': encrypted_key,  # Store encrypted key
                    'hash': user_api_key.api_key_hash,  # Hash for verification
                    'name': user_api_key.api_key_name,
                    'status': user_api_key.status.value,
                    'created_at': user_api_key.created_at.isoformat(),
                    'last_used': user_api_key.last_used.isoformat() if user_api_key.last_used else None
                }
                user.user_metadata = metadata
                db.session.commit()
                
        except Exception as e:
            self.logger.error(f"Error saving API key to database: {e}")
            db.session.rollback()
    
    def load_user_api_keys(self):
        """Load user API keys from database"""
        try:
            users = db.session.query(User).all()
            for user in users:
                metadata = getattr(user, 'user_metadata', {}) or {}
                if 'api_key' in metadata:
                    api_key_data = metadata['api_key']
                    user_api_key = UserAPIKey(
                        user_id=user.id,
                        api_key_hash=api_key_data['hash'],
                        api_key_name=api_key_data['name'],
                        status=APIKeyStatus(api_key_data['status']),
                        created_at=datetime.fromisoformat(api_key_data['created_at']),
                        last_used=datetime.fromisoformat(api_key_data['last_used']) if api_key_data['last_used'] else None
                    )
                    self.user_api_keys[user.id] = user_api_key
                    
        except Exception as e:
            self.logger.error(f"Error loading user API keys: {e}")
    
    def get_user_api_stats(self, user_id: int) -> Dict:
        """Get API usage statistics for a user"""
        try:
            rate_data = self.rate_limit_cache.get(user_id, {})
            user_api_key = self.user_api_keys.get(user_id)
            
            return {
                'user_id': user_id,
                'has_api_key': user_id in self.user_api_keys,
                'api_key_status': user_api_key.status.value if user_api_key else 'none',
                'requests_last_minute': rate_data.get('requests_last_minute', 0),
                'requests_today': rate_data.get('requests_today', 0),
                'requests_this_month': rate_data.get('requests_this_month', 0),
                'minute_limit': self.REQUESTS_PER_MINUTE,
                'daily_limit': self.REQUESTS_PER_DAY,
                'monthly_limit': self.REQUESTS_PER_MONTH,
                'last_request': rate_data.get('last_request_time'),
                'can_make_request': self.check_user_rate_limit(user_id)['can_make_request']
            }
            
        except Exception as e:
            self.logger.error(f"Error getting API stats for user {user_id}: {e}")
            return {}

# Global instance
api_manager = MultiUserAPIManager()

def init_api_manager():
    """Initialize the API manager with app context"""
    try:
        api_manager.load_user_api_keys()
    except Exception as e:
        api_manager.logger.error(f"Error initializing API manager: {e}")

def add_user_api_key(user_id: int, api_key: str, api_key_name: str = None) -> bool:
    """Add API key for a user"""
    return api_manager.add_user_api_key(user_id, api_key, api_key_name)

def get_user_api_key(user_id: int) -> Optional[str]:
    """Get API key for a user"""
    return api_manager.get_user_api_key(user_id)

def check_user_rate_limit(user_id: int) -> Dict:
    """Check rate limit for a user"""
    return api_manager.check_user_rate_limit(user_id)

def record_user_request(user_id: int):
    """Record API request for a user"""
    api_manager.record_user_request(user_id)

def get_user_api_stats(user_id: int) -> Dict:
    """Get API usage stats for a user"""
    return api_manager.get_user_api_stats(user_id)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Multi-User API Key Management')
    parser.add_argument('--add-key', action='store_true', help='Add API key for user')
    parser.add_argument('--user-id', type=int, required=True, help='User ID')
    parser.add_argument('--api-key', type=str, help='API key to add')
    parser.add_argument('--key-name', type=str, help='API key name')
    parser.add_argument('--check-limit', action='store_true', help='Check rate limit')
    parser.add_argument('--get-stats', action='store_true', help='Get API stats')
    
    args = parser.parse_args()
    
    if args.add_key and args.api_key:
        success = add_user_api_key(args.user_id, args.api_key, args.key_name)
        print(f"API key addition: {'Success' if success else 'Failed'}")
    
    if args.check_limit:
        limit_status = check_user_rate_limit(args.user_id)
        print(f"Rate limit status: {limit_status}")
    
    if args.get_stats:
        stats = get_user_api_stats(args.user_id)
        print(f"API stats: {stats}") 