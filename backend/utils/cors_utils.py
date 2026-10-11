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

import os
import re
from typing import List, Optional, Union

from core.app_env import is_production
from core.logging_config import get_logger

logger = get_logger(__name__)

PRODUCTION_ORIGINS: List[Union[str, "re.Pattern"]] = [
    'https://itsfuze.vercel.app',
    # This project's Vercel preview deployments only (itsfuze-<hash>-<team>, itsfuze-git-<branch>-<team>).
    # Any *.vercel.app would let every other Vercel-hosted site make credentialed requests, and
    # anyone can create a project named itsfuze-<anything>, so the team suffix is required.
    re.compile(r"^https://itsfuze-[a-z0-9-]+-ujjwaljain16s-projects\.vercel\.app$"),
]

# Dev servers. Never allowed in production: any process on a visitor's machine can listen there.
LOCAL_ORIGINS = ['http://localhost:3000', 'http://localhost:5173', 'http://127.0.0.1:5173']

_cached_origins: Optional[List[Union[str, "re.Pattern"]]] = None


def _configured_origins() -> List[str]:
    """Exact origins from CORS_ORIGINS. flask-cors treats anything with '*' as a regex
    ('chrome-extension://*' matched every extension), so wildcard entries are ignored."""
    origins = []
    for origin in os.getenv('CORS_ORIGINS', '').split(','):
        origin = origin.strip().rstrip('/')
        if not origin:
            continue
        if any(ch in origin for ch in '*?[]^$\\'):
            logger.warning("cors_wildcard_origin_ignored", extra={"origin": origin})
            continue
        origins.append(origin)
    return origins


def get_allowed_cors_origins() -> List[Union[str, "re.Pattern"]]:
    """Build (and cache) the full CORS allowlist."""
    global _cached_origins
    if _cached_origins is not None:
        return _cached_origins

    origins: List[Union[str, "re.Pattern"]] = list(PRODUCTION_ORIGINS)
    if not is_production():
        origins.extend(LOCAL_ORIGINS)
    # The extension calls the API with host_permissions, which bypass CORS; a specific
    # extension origin is only needed for pages that call the API without them.
    extension_id = os.getenv('EXTENSION_ID', '').strip()
    if extension_id:
        origins.append(f'chrome-extension://{extension_id}')
    for origin in _configured_origins():
        if origin not in origins:
            origins.append(origin)

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
