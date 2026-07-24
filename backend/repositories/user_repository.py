from typing import Optional, List, Set
from sqlalchemy import func
from sqlalchemy.orm import Session
from models import User


class UserRepository:
    """Repository for User access and identity lookups"""

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _normalize(value: Optional[str]) -> str:
        """Centralized string normalization (lowercase and stripped)."""
        if not value:
            return ""
        return value.lower().strip()

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Fetch user by ID using modern SQLAlchemy session.get()"""
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        """Fetch user by email using case-insensitive lookup."""
        clean_email = self._normalize(email)
        if not clean_email:
            return None
        return self.session.query(User).filter(func.lower(User.email) == clean_email).first()

    def get_by_provider_id(self, provider_id: str, provider_name: str = "google") -> Optional[User]:
        """Fetch user by OAuth provider ID and provider name."""
        if not provider_id:
            return None
        return self.session.query(User).filter(
            User.provider_user_id == provider_id,
            User.provider_name == provider_name
        ).first()

    def get_by_identifier(self, identifier: str) -> Optional[User]:
        """
        Robust lookup by either email or username with strict precedence.
        """
        clean_id = self._normalize(identifier)
        if not clean_id:
            return None

        user = self.session.query(User).filter(func.lower(User.email) == clean_id).first()
        if user:
            return user

        return self.session.query(User).filter(func.lower(User.username) == clean_id).first()

    def is_email_available(self, email: str) -> bool:
        """Check email availability using EXISTS-like first() check instead of COUNT(*)"""
        clean_email = self._normalize(email)
        if not clean_email:
            return False
        return self.session.query(User.id).filter(func.lower(User.email) == clean_email).first() is None

    def is_username_available(self, username: str) -> bool:
        """Check username availability using EXISTS-like first() check instead of COUNT(*)"""
        clean_username = self._normalize(username)
        if not clean_username:
            return False
        return self.session.query(User.id).filter(func.lower(User.username) == clean_username).first() is None

    def get_existing_usernames(self, candidate_usernames: List[str]) -> Set[str]:
        """
        Batch query to check which candidate usernames already exist in the DB.
        Deduplicates candidate names using a set before executing single SQL IN query.
        """
        if not candidate_usernames:
            return set()
        clean_candidates = {self._normalize(name) for name in candidate_usernames if name and self._normalize(name)}
        if not clean_candidates:
            return set()

        results = self.session.query(func.lower(User.username)).filter(
            func.lower(User.username).in_(clean_candidates)
        ).all()
        return {r[0] for r in results if r[0]}

    def add(self, user: User) -> User:
        """Persist a new user."""
        self.session.add(user)
        return user
