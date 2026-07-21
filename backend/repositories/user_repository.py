from typing import Optional
from models import User

class UserRepository:
    """Repository for User access and identity lookups"""
    
    def __init__(self, session):
        self.session = session

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.session.query(User).get(user_id)

    def get_by_identifier(self, identifier: str) -> Optional[User]:
        """
        Robust lookup by either email or username.
        Normalization: email (lowercase), username (lowercase if needed).
        """
        if not identifier:
            return None
            
        # Try email match first (strict precedence)
        identifier_clean = identifier.lower().strip()
        user = self.session.query(User).filter(User.email == identifier_clean).first()
        if user:
            return user
            
        # Fallback to username match
        return self.session.query(User).filter(User.username == identifier_clean).first()

    def is_email_available(self, email: str) -> bool:
        if not email:
            return False
        return self.session.query(User).filter_by(email=email.lower().strip()).count() == 0

    def is_username_available(self, username: str) -> bool:
        if not username:
            return False
        return self.session.query(User).filter_by(username=username.lower().strip()).count() == 0

    def add(self, user: User):
        self.session.add(user)
        return user
