import re
import uuid
import random
import string
import bcrypt
from datetime import datetime, timedelta
from typing import Tuple, Optional, List, Dict, Any
from models import User, TokenFamily
from core.events import UserRegistered
from core.logging_config import get_logger

logger = get_logger(__name__)


class AuthError(Exception):
    """Base exception for authentication errors"""
    pass


class AuthenticationFailed(AuthError):
    """Raised when credentials don't match or account is locked"""
    pass


class RegistrationFailed(AuthError):
    """Raised when registration cannot proceed (e.g. conflict)"""
    pass


class AuthService:
    """
    Standardized Authentication Service.
    Handles credential verification, hashing, registration facts, and OAuth identity creation.
    Enforces account lockout policies and identity facts strictly.
    """

    BCRYPT_WORK_FACTOR = 12

    def __init__(self, uow):
        self.uow = uow

    def hash_password(self, password: str) -> str:
        """Generate memory-hard bcrypt hash"""
        if not password:
            raise ValueError("Password is required")
        if isinstance(password, str):
            password = password.encode('utf-8')

        salt = bcrypt.gensalt(rounds=self.BCRYPT_WORK_FACTOR)
        hashed = bcrypt.hashpw(password, salt)
        return hashed.decode('utf-8')

    def verify_password(self, password_hash: str, password: str) -> bool:
        """Verify password against hash, supporting both legacy werkzeug and bcrypt"""
        if not password or not password_hash:
            return False

        pass_bytes = password.encode('utf-8') if isinstance(password, str) else password

        if password_hash.startswith(('$2b$', '$2a$', '$2y$')):
            hash_bytes = password_hash.encode('utf-8') if isinstance(password_hash, str) else password_hash
            try:
                return bcrypt.checkpw(pass_bytes, hash_bytes)
            except Exception as e:
                logger.error("bcrypt_verification_error", extra={"error": str(e)})
                return False

        try:
            from werkzeug.security import check_password_hash
            pass_str = password.decode('utf-8') if isinstance(password, bytes) else password
            return check_password_hash(password_hash, pass_str)
        except Exception as e:
            logger.error("legacy_password_verification_error", extra={"error": str(e)})
            return False

    def get_user_for_login(self, identifier: str) -> Optional[User]:
        """Pure persistence lookup for authentication workflows."""
        return self.uow.users.get_by_identifier(identifier)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Pure persistence lookup for OAuth identity matching."""
        if not email:
            return None
        return self.uow.users.get_by_email(email.lower().strip())

    def authenticate(self, identifier: str, password: str) -> User:
        """
        Verify credentials and enforce account lockout policies.
        Prevents username enumeration in failure logs.
        """
        user = self.uow.users.get_by_identifier(identifier)
        if not user:
            logger.warning("auth_failed", extra={"reason": "invalid_credentials"})
            raise AuthenticationFailed("Invalid credentials")

        # Enforce Account Lockout Policy
        now = datetime.utcnow()
        if isinstance(user.account_locked_until, datetime) and user.account_locked_until > now:
            logger.warning("auth_failed_account_locked", extra={"user_id": getattr(user, 'id', None)})
            raise AuthenticationFailed("Account is temporarily locked due to failed login attempts. Please try again later.")

        if not self.verify_password(user.password_hash, password):
            logger.warning("auth_failed", extra={"reason": "invalid_credentials"})
            self.record_failed_login(user)
            raise AuthenticationFailed("Invalid credentials")

        self.record_successful_login(user)
        return user

    def register(self, username: str, email: str, password: str) -> User:
        """
        Factual registration. Enforces uniqueness via DB.
        Records UserRegistered event.
        """
        if not username or not email or not password:
            raise RegistrationFailed("All fields are required")

        hashed_password = self.hash_password(password)

        user = User(
            username=username.lower().strip(),
            email=email.lower().strip(),
            password_hash=hashed_password
        )

        self.uow.users.add(user)
        self.uow.flush()

        self.uow.emit(UserRegistered(user_id=user.id, email=user.email))
        return user

    def update_username(self, user: User, new_username: str) -> None:
        """Updates a user's username with input validation."""
        if not new_username or not new_username.strip():
            raise ValueError("New username cannot be empty")
        user.username = new_username.lower().strip()
        self.uow.users.add(user)

    def update_password(self, user_id: int, password_hash: str) -> None:
        """Pure persistence for password updates."""
        user = self.uow.users.get_by_id(user_id)
        if not user:
            raise AuthenticationFailed("User not found")

        user.password_hash = password_hash
        self.uow.users.add(user)

    def create_oauth_user(
        self,
        username: str,
        email: str,
        provider_id: str,
        provider_name: str = "google",
        password_hash: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> User:
        """Pure persistence for OAuth user creation."""
        user = User(
            username=username.lower().strip(),
            email=email.lower().strip(),
            password_hash=password_hash,
            user_metadata=metadata or {},
            provider_name=provider_name,
            provider_user_id=provider_id,
        )
        self.uow.users.add(user)
        self.uow.flush()
        self.uow.emit(UserRegistered(user_id=user.id, email=user.email))
        return user

    def validate_password_strength(self, password: str) -> Tuple[bool, Optional[str]]:
        """Domain-level password complexity rules"""
        if not password or len(password) < 8:
            return False, 'Password must be at least 8 characters long'
        if not re.search(r'[A-Za-z]', password):
            return False, 'Password must contain at least one letter'
        if not re.search(r'[0-9]', password):
            return False, 'Password must contain at least one number'
        return True, None

    def check_username_availability(self, username: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Check username availability using UoW repository layer."""
        if not username:
            return False, None, None

        clean_user = username.strip()

        existing = self.uow.users.get_existing_usernames([clean_user])
        if not existing:
            return True, None, None

        user_obj = self.uow.users.get_by_identifier(clean_user)
        exact_match = user_obj.username if user_obj and user_obj.username == clean_user else None
        case_match = user_obj.username if user_obj else None
        return False, exact_match, case_match

    def generate_username_suggestions(self, base_username: str, count: int = 3) -> list:
        """Efficiently generate available username suggestions using batch DB query."""
        base = re.sub(r'[^a-zA-Z0-9_-]', '', base_username)[:20].strip('_-')
        if not base:
            base = "user"

        candidates = []
        for i in range(1, 20):
            candidates.append(f"{base}{i}")
        for _ in range(10):
            candidates.append(f"{base}{random.randint(10, 99)}")
        for _ in range(5):
            candidates.append(f"{base}_{random.randint(100, 999)}")

        taken_set = self.uow.users.get_existing_usernames(candidates)
        available = [c for c in candidates if c.lower() not in taken_set]
        return available[:count]

    def generate_unique_username(self, base: str) -> str:
        """Generate a unique username sequentially (john -> john1 -> john2)."""
        cleaned_base = re.sub(r'[^a-zA-Z0-9_-]', '', base.split('@')[0])[:44].strip('_-') or 'user'

        candidates = [cleaned_base] + [f"{cleaned_base}{i}" for i in range(1, 100)]
        taken = self.uow.users.get_existing_usernames(candidates)

        for candidate in candidates:
            if candidate.lower() not in taken:
                return candidate

        return f"{cleaned_base}_{uuid.uuid4().hex[:6]}"

    def bulk_check_usernames(self, usernames: list) -> list:
        """Bulk check username availability in 1 single DB query."""
        if not usernames or not isinstance(usernames, list):
            return []

        usernames = usernames[:50]
        taken_set = self.uow.users.get_existing_usernames(usernames)

        results = []
        for raw_name in usernames:
            if not isinstance(raw_name, str) or not raw_name.strip():
                results.append({'username': raw_name, 'available': False, 'reason': 'Invalid format'})
                continue
            name = raw_name.strip()
            is_avail = name.lower() not in taken_set
            results.append({
                'username': name,
                'available': is_avail,
                'reason': 'Available' if is_avail else 'Username is taken'
            })
        return results

    def record_failed_login(self, user: User) -> Dict[str, Any]:
        """Increment failed login count and manage lockout policy within UoW."""
        now = datetime.utcnow()
        user.failed_login_count = (user.failed_login_count or 0) + 1
        user.last_failed_login = now

        is_locked = False
        if user.failed_login_count >= 5:
            user.account_locked_until = now + timedelta(minutes=15)
            is_locked = True

        self.uow.users.add(user)
        return {
            'failed_count': user.failed_login_count,
            'is_locked': is_locked,
            'locked_until': user.account_locked_until
        }

    def record_successful_login(self, user: User) -> None:
        """Reset failed login counters and set last login date within UoW."""
        user.failed_login_count = 0
        user.account_locked_until = None
        user.last_login = datetime.utcnow()
        self.uow.users.add(user)

    def handle_supabase_oauth(self, supa_user: dict) -> Tuple[User, str, str]:
        """
        Full transactional OAuth flow: lookup/creation, provider metadata linking,
        token generation, TokenFamily tracking, and lockout policy enforcement inside UoW.
        """
        from flask_jwt_extended import create_access_token, create_refresh_token, decode_token

        email = supa_user.get('email')
        if not email:
            raise RegistrationFailed("OAuth provider returned no email address")

        email = email.lower().strip()
        provider_id = supa_user.get('id') or (supa_user.get('user') or {}).get('id')

        user = self.uow.users.get_by_email(email)
        if not user and provider_id:
            user = self.uow.users.get_by_provider_id(provider_id, provider_name='google')

        if not user:
            username = self.generate_unique_username(email)
            random_pw = ''.join(random.choices(string.ascii_letters + string.digits, k=24))
            hashed_pw = self.hash_password(random_pw)

            user = User(
                username=username,
                email=email,
                password_hash=hashed_pw,
                provider_name='google',
                provider_user_id=provider_id,
                user_metadata={'supabase_user_id': provider_id}
            )
            self.uow.users.add(user)
            self.uow.flush()
            self.uow.emit(UserRegistered(user_id=user.id, email=user.email))
        else:
            # Enforce Account Lockout Policy on existing user OAuth logins
            now = datetime.utcnow()
            if isinstance(user.account_locked_until, datetime) and user.account_locked_until > now:
                logger.warning("auth_failed_oauth_account_locked", extra={"user_id": getattr(user, 'id', None)})
                raise AuthenticationFailed("Account is temporarily locked. Please try again later.")

            updated = False
            if not getattr(user, 'provider_user_id', None) and provider_id:
                user.provider_user_id = provider_id
                updated = True
            if not getattr(user, 'provider_name', None):
                user.provider_name = 'google'
                updated = True
            if updated:
                self.uow.users.add(user)
                self.uow.flush()

        family_id = str(uuid.uuid4())
        access = create_access_token(identity=str(user.id), additional_claims={'family_id': family_id})
        refresh = create_refresh_token(identity=str(user.id), additional_claims={'family_id': family_id})

        family = TokenFamily(
            user_id=user.id,
            family_id=family_id,
            current_jti=decode_token(refresh)['jti']
        )
        self.uow.token_families.add(family)

        return user, access, refresh
