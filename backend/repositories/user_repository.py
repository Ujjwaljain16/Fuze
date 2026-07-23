from typing import Optional, List, Set
from sqlalchemy import func
from models import User

class UserRepository:
    """Repository for User access and identity lookups"""
    
    def __init__(self, session):
        self.session = session

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.session.query(User).get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        if not email:
            return None
        return self.session.query(User).filter(func.lower(User.email) == email.lower().strip()).first()

    def get_by_provider_id(self, provider_id: str, provider_name: str = "google") -> Optional[User]:
        if not provider_id:
            return None
        return self.session.query(User).filter(
            User.provider_user_id == provider_id,
            User.provider_name == provider_name
        ).first()

    def get_by_identifier(self, identifier: str) -> Optional[User]:
        """
        Robust lookup by either email or username.
        Normalization: email (lowercase), username (lowercase if needed).
        """
        if not identifier:
            return None
            
        # Try email match first (strict precedence)
        identifier_clean = identifier.lower().strip()
        user = self.session.query(User).filter(func.lower(User.email) == identifier_clean).first()
        if user:
            return user
            
        # Fallback to username match
        return self.session.query(User).filter(func.lower(User.username) == identifier_clean).first()

    def is_email_available(self, email: str) -> bool:
        if not email:
            return False
        clean_email = email.lower().strip()
        return self.session.query(User).filter(func.lower(User.email) == clean_email).count() == 0

    def is_username_available(self, username: str) -> bool:
        if not username:
            return False
        clean_username = username.lower().strip()
        return self.session.query(User).filter(func.lower(User.username) == clean_username).count() == 0

    def get_existing_usernames(self, candidate_usernames: List[str]) -> Set[str]:
        """
        Batch query to check which candidate usernames already exist in the DB.
        Executes a single SQL query with IN (...) for efficiency.
        """
        if not candidate_usernames:
            return set()
        clean_candidates = [name.lower().strip() for name in candidate_usernames if name]
        if not clean_candidates:
            return set()
            
        results = self.session.query(func.lower(User.username)).filter(
            func.lower(User.username).in_(clean_candidates)
        ).all()
        return {r[0] for r in results if r[0]}

    def add(self, user: User):
        self.session.add(user)
        return user
