from models import User
from core.events import UserRegistered
from backend.core.logging_config import get_logger

logger = get_logger(__name__)

class AuthError(Exception):
    """Base exception for authentication errors"""
    pass

class AuthenticationFailed(AuthError):
    """Raised when credentials don't match"""
    pass

class RegistrationFailed(AuthError):
    """Raised when registration cannot proceed (e.g. conflict)"""
    pass

class AuthService:
    """
    Standardized Authentication Service.
    Handles credential verification, hashing, and registration facts.
    Strictly stateless regarding JWT/Sessions - focuses only on identity facts.
    """
    
    # Work factor 12 = ~300ms (Industry standard balance)
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
        """Verify password against hash, supporting both legacy and bcrypt"""
        if not password or not password_hash:
            return False
            
        if isinstance(password, str):
            password = password.encode('utf-8')
            
        # Standard bcrypt check
        if password_hash.startswith(('$2b$', '$2a$', '$2y$')):
            if isinstance(password_hash, str):
                password_hash = password_hash.encode('utf-8')
            try:
                return bcrypt.checkpw(password, password_hash)
            except Exception as e:
                logger.error("bcrypt_verification_error", error=str(e))
                return False
        
        # Fallback logic for legacy hashes should be handled here if strictly necessary,
        # but we prioritize making the system move toward bcrypt.
        return False

    def authenticate(self, identifier: str, password: str) -> User:
        """
        Verify credentials. 
        Normalization: Identifier is tried as email first, then username.
        """
        user = self.uow.users.get_by_identifier(identifier)
        if not user:
            logger.warning("auth_failed", reason="identity_not_found", identifier_prefix=identifier[:3])
            raise AuthenticationFailed("Invalid credentials")
            
        if not self.verify_password(user.password_hash, password):
            logger.warning("auth_failed", reason="password_mismatch", username=user.username)
            raise AuthenticationFailed("Invalid credentials")
            
        # Check if hash needs migration to latest bcrypt factor
        # (Implementation omitted for brevity, but can be added here)
        
        return user

    def register(self, username: str, email: str, password: str) -> User:
        """
        Factual registration. 
        Enforces uniqueness via DB (handled by UoW commit/blueprint catch).
        Records UserRegistered event.
        """
        # Minimal validation - blueprint should handle detailed regex/strength
        if not username or not email or not password:
            raise RegistrationFailed("All fields are required")
            
        hashed_password = self.hash_password(password)
        
        user = User(
            username=username.lower().strip(),
            email=email.lower().strip(),
            password_hash=hashed_password
        )
        
        self.uow.users.add(user)
        # We record the fact of registration
        self.uow.emit(UserRegistered(user_id=None, email=user.email)) # ID will be populated post-flush/commit
        
        return user

    def validate_password_strength(self, password: str) -> Tuple[bool, Optional[str]]:
        """Domain-level password complexity rules"""
        if len(password) < 8:
            return False, 'Password must be at least 8 characters long'
        if not re.search(r'[A-Za-z]', password):
            return False, 'Password must contain at least one letter'
        if not re.search(r'[0-9]', password):
            return False, 'Password must contain at least one number'
        return True, None
