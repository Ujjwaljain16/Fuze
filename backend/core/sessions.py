"""
Ending sessions.

A session is a refresh-token family (TokenFamily). Revoking it in the database stops future
refreshes, but access tokens already issued from it would keep working until they expire.
A short-lived Redis marker per revoked family closes that gap: the JWT blocklist check rejects
any token carrying a revoked family_id. The marker only needs to outlive the longest access
token, after which expiry does the job.
"""

from datetime import timedelta
from typing import Optional

from core.logging_config import get_logger

logger = get_logger(__name__)

_FAMILY_KEY = "revoked_family:{}"


def _access_token_ttl_seconds() -> int:
    try:
        from flask import current_app
        expires = current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES')
        if isinstance(expires, timedelta):
            return max(int(expires.total_seconds()), 60)
    except RuntimeError:
        pass
    return 24 * 3600


def mark_family_revoked(family_id: str) -> None:
    from utils.redis_utils import redis_cache
    try:
        redis_cache.client.setex(_FAMILY_KEY.format(family_id), _access_token_ttl_seconds(), "1")
    except Exception as e:
        logger.warning("revoked_family_marker_failed", extra={"family_id": family_id, "error": str(e)})


def is_family_revoked(redis_client, family_id: Optional[str]) -> bool:
    return bool(family_id) and redis_client.exists(_FAMILY_KEY.format(family_id)) == 1


def revoke_user_sessions(uow, user_id: int, keep_family_id: Optional[str] = None,
                         reason: str = 'password_changed') -> int:
    """Revoke every active session of `user_id` except `keep_family_id`; returns how many."""
    revoked = 0
    for family in uow.token_families.list_active_for_user(user_id):
        if family.family_id == keep_family_id:
            continue
        uow.token_families.revoke_family(family.family_id, reason)
        mark_family_revoked(family.family_id)
        revoked += 1
    return revoked
