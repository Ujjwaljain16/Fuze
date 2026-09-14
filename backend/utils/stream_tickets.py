"""
Short-lived, single-use tickets for authenticating SSE (EventSource) connections.

Browsers' EventSource API cannot set custom headers, so /api/realtime/stream
can't be authenticated via a normal Authorization header the way every other
endpoint is. The previous approach accepted the actual JWT access token as a
query parameter -- which puts a long-lived, fully-privileged credential into
the URL, where it lands in server/proxy access logs, browser history, and is
readable via performance.getEntriesByType('resource') from any script on the
page.

Instead, the frontend calls POST /api/realtime/stream-ticket (a normal
Authorization-header-authenticated request, so the real token never touches a
URL) to mint a random, single-use ticket good for a few seconds, then opens
the EventSource with that ticket in the query string instead. Even if a
ticket leaks via logs, it's already been consumed (or expired) by the time
anyone could reuse it.
"""

import secrets
from typing import Optional

from utils.redis_utils import redis_cache
from core.logging_config import get_logger

logger = get_logger(__name__)

TICKET_TTL_SECONDS = 30
_TICKET_KEY_PREFIX = "stream_ticket:"


def mint_stream_ticket(user_id: int) -> Optional[str]:
    """Create a single-use ticket bound to user_id, valid for TICKET_TTL_SECONDS."""
    ticket = secrets.token_urlsafe(32)
    key = f"{_TICKET_KEY_PREFIX}{ticket}"
    if not redis_cache.setex(key, TICKET_TTL_SECONDS, user_id):
        logger.error("stream_ticket_mint_failed", extra={"user_id": user_id})
        return None
    return ticket


def consume_stream_ticket(ticket: str) -> Optional[int]:
    """Validate and immediately invalidate a ticket, returning the bound user_id if valid."""
    if not ticket:
        return None
    key = f"{_TICKET_KEY_PREFIX}{ticket}"
    user_id = redis_cache.get(key)
    if user_id is None:
        return None
    redis_cache.delete_cache(key)
    try:
        return int(user_id)
    except (TypeError, ValueError):
        return None
