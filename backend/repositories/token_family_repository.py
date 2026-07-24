from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import TokenFamily


class TokenFamilyRepository:
    """Repository for TokenFamily persistence and refresh token rotation."""

    def __init__(self, session: Session):
        self.session = session

    def get_family(self, family_id: str, lock: bool = False) -> Optional[TokenFamily]:
        """Fetch token family by ID with optional FOR UPDATE lock."""
        if not family_id:
            return None
        query = self.session.query(TokenFamily).filter_by(family_id=family_id)
        if lock:
            query = query.with_for_update()
        return query.first()

    def add(self, token_family: TokenFamily) -> TokenFamily:
        """Persist a new token family."""
        if not token_family:
            raise ValueError("token_family is required")
        self.session.add(token_family)
        return token_family

    def revoke_family(self, family_id: str, reason: str = 'revoked') -> bool:
        """
        Revoke a token family by family_id.
        Returns True if family was found and revoked, False otherwise.
        """
        if not family_id:
            raise ValueError("family_id is required")

        family = self.get_family(family_id)
        if not family:
            return False

        family.revoked = True
        family.revoked_reason = reason
        family.last_used_at = func.now()
        return True

    def update_current_jti(self, family_id: str, jti: str) -> bool:
        """
        Update current_jti for a token family upon rotation.
        Returns True if family was updated, False if not found.
        """
        if not family_id:
            raise ValueError("family_id is required")
        if not jti:
            raise ValueError("jti is required")

        family = self.get_family(family_id)
        if not family:
            return False

        family.current_jti = jti
        family.last_used_at = func.now()
        return True
