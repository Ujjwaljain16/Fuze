from typing import Optional
from models import TokenFamily

class TokenFamilyRepository:
    """Repository for TokenFamily persistence"""
    
    def __init__(self, session):
        self.session = session

    def get_family(self, family_id: str, lock: bool = False) -> Optional[TokenFamily]:
        query = self.session.query(TokenFamily).filter_by(family_id=family_id)
        if lock:
            query = query.with_for_update()
        return query.first()

    def add(self, token_family: TokenFamily):
        self.session.add(token_family)
        return token_family

    def revoke_family(self, family_id: str, reason: str):
        family = self.get_family(family_id)
        if family:
            family.revoked = True
            family.revoked_reason = reason

    def update_current_jti(self, family_id: str, jti: str):
        family = self.get_family(family_id)
        if family:
            family.current_jti = jti
