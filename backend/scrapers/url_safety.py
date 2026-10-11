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
