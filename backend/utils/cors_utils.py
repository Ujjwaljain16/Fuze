"""
Shared CORS origin allowlist and validation.

Single source of truth for "which origins may receive credentialed
cross-origin responses". Anything that manually sets
Access-Control-Allow-Origin (outside of flask-cors itself) MUST validate
against get_allowed_cors_origins() via is_allowed_origin() rather than
echoing the request's Origin header verbatim -- doing that with
Access-Control-Allow-Credentials: true lets ANY website read authenticated
responses on behalf of a logged-in user.
"""

import re
from typing import List, Optional, Union

from utils.unified_config import UnifiedConfig

DEFAULT_ALLOWED_ORIGINS: List[Union[str, "re.Pattern"]] = [
    'https://itsfuze.vercel.app',
    'http://localhost:3000',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    re.compile(r"^https://.*\.vercel\.app$"),
]

_cached_origins: Optional[List[Union[str, "re.Pattern"]]] = None


def get_allowed_cors_origins() -> List[Union[str, "re.Pattern"]]:
    """Build (and cache) the full CORS allowlist: configured origins + defaults."""
    global _cached_origins
    if _cached_origins is not None:
        return _cached_origins

    origins = UnifiedConfig().cors.origins.copy()
    for allowed in DEFAULT_ALLOWED_ORIGINS:
        if allowed not in origins:
            origins.append(allowed)

    _cached_origins = origins
    return origins


def is_allowed_origin(origin: Optional[str]) -> bool:
    """Check whether `origin` is on the CORS allowlist (exact string or regex match)."""
    if not origin:
        return False
    for allowed in get_allowed_cors_origins():
        if isinstance(allowed, str):
            if origin == allowed:
                return True
        elif hasattr(allowed, 'match') and allowed.match(origin):
            return True
    return False
