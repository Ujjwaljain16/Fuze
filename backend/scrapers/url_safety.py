"""
SSRF guard for outbound content-acquisition fetches.

Bookmark/LinkedIn URLs are supplied by users and fetched SERVER-SIDE by
scrapers/fetchers/*. Without validation, a user could submit
"http://169.254.169.254/latest/meta-data/", "http://localhost:6379/",
a decimal-encoded loopback IP, etc. as a "bookmark" and have this backend
fetch it and return the response back into the stored content -- a classic
SSRF. This module rejects any URL whose scheme isn't http(s), or that
resolves to a private/loopback/link-local/reserved address.

Must be re-checked on every redirect hop, not just the original URL --
otherwise a URL that resolves to a public IP can 302 to an internal one
and slip through (DNS-rebinding-style bypass via HTTP redirect).
"""

import re
from urllib.parse import parse_qsl, urlparse

from core.logging_config import get_logger
from scrapers.safe_http import UnsafeURLError, check_url

logger = get_logger(__name__)


def is_safe_url(url: str) -> bool:
    """True only if `url` is http(s) without credentials and every address its host resolves
    to is public. Fetch with scrapers.safe_http.safe_get, which also pins the checked address."""
    try:
        check_url(url)
        return True
    except UnsafeURLError as e:
        logger.warning("url_safety_blocked_unsafe_target", extra={"url": url, "reason": str(e)})
        return False
    except Exception:
        return False


# Query parameters that usually carry a secret: signed links, share tokens, session ids.
_SECRET_SUBSTRINGS = ("token", "secret", "passw", "apikey", "api_key", "access_key", "signature",
                      "credential", "session", "x-amz-", "x-goog-")
_SECRET_WORDS = {"key", "code", "sig", "auth", "sid", "ticket", "otp", "pwd", "jwt", "private", "invite"}


def _is_secret_param(name: str) -> bool:
    lowered = name.lower()
    if any(s in lowered for s in _SECRET_SUBSTRINGS):
        return True
    return any(word in _SECRET_WORDS for word in re.split(r"[^a-z0-9]+", lowered))


def is_shareable_with_third_party(url: str) -> bool:
    """True if `url` may be sent to an outside service (the reader, the Wayback Machine).

    Those services see the URL itself, nothing else. A URL with credentials or a query parameter
    that looks like a secret (a signed S3 link, a share token, a password-reset code) stays on
    our servers: handing it over would hand over access to whatever it unlocks.
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False
    for name, _ in parse_qsl(parsed.query, keep_blank_values=True):
        if _is_secret_param(name):
            return False
    return True
