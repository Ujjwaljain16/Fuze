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

import ipaddress
import socket
from urllib.parse import urlparse

from core.logging_config import get_logger

logger = get_logger(__name__)

ALLOWED_SCHEMES = {"http", "https"}


def _is_unsafe_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # unparseable -> treat as unsafe

    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def is_safe_url(url: str) -> bool:
    """Return True only if `url` uses http(s) and every address its host
    resolves to is a public, routable address."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except Exception as e:
        logger.warning("url_safety_dns_resolution_failed", extra={"url": url, "error": str(e)})
        return False

    if not addr_infos:
        return False

    for info in addr_infos:
        ip_str = info[4][0]
        if _is_unsafe_ip(ip_str):
            logger.warning("url_safety_blocked_unsafe_target", extra={"url": url, "resolved_ip": ip_str})
            return False

    return True
