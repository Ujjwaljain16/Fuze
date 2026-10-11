"""
Outbound HTTP for URLs that users control (bookmarks, robots.txt of their hosts, API lookups).

`safe_get` closes the gaps a validate-then-fetch check leaves open:

- DNS rebinding: the host is resolved once, every address must be public, and the connection
  is made to that exact IP (Host header and TLS SNI/verification still use the hostname), so
  a second lookup can't swap in 127.0.0.1 between the check and the connect.
- Redirects: followed manually, and each hop goes through the same check.
- Size: the body is streamed and cut off at `max_bytes`, so a huge or endless response can't
  exhaust worker memory.
- Proxies/.netrc from the environment are ignored (trust_env=False).
"""

import ipaddress
import json as _json
import socket
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from requests.adapters import HTTPAdapter
from requests.utils import get_encoding_from_headers

ALLOWED_SCHEMES = {"http", "https"}
MAX_RESPONSE_BYTES = 10 * 1024 * 1024
MAX_REDIRECTS = 5
_CHUNK = 64 * 1024


class UnsafeURLError(ValueError):
    """The URL's scheme or resolved address is not allowed for server-side fetches."""


def is_public_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    # is_global excludes private, loopback, link-local (cloud metadata), CGNAT 100.64/10,
    # benchmarking, documentation and reserved ranges.
    return ip.is_global and not ip.is_multicast


def resolve_public_ip(hostname: str) -> str:
    """Resolve `hostname`; every address must be public. Returns the address to connect to."""
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except OSError as e:
        raise UnsafeURLError(f"cannot resolve {hostname}: {e}") from e
    addresses = [info[4][0] for info in infos]
    if not addresses:
        raise UnsafeURLError(f"{hostname} has no addresses")
    unsafe = [a for a in addresses if not is_public_ip(a)]
    if unsafe:
        raise UnsafeURLError(f"{hostname} resolves to a non-public address ({unsafe[0]})")
    return addresses[0]


def check_url(url: str):
    """Validate scheme and host; returns (parsed, ip) or raises UnsafeURLError."""
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeURLError(f"scheme {parsed.scheme!r} is not allowed")
    if not parsed.hostname:
        raise UnsafeURLError("URL has no host")
    if parsed.username or parsed.password:
        raise UnsafeURLError("credentials in URLs are not allowed")
    return parsed, resolve_public_ip(parsed.hostname)


class _PinnedHostAdapter(HTTPAdapter):
    """Connect to a fixed IP while TLS still verifies the certificate for the real hostname."""

    def __init__(self, hostname: str, **kwargs):
        self._hostname = hostname
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["server_hostname"] = self._hostname
        kwargs["assert_hostname"] = self._hostname
        super().init_poolmanager(*args, **kwargs)


@dataclass
class SafeResponse:
    url: str
    status_code: int
    headers: Dict[str, str]
    content: bytes
    truncated: bool = False
    redirect_chain: List[str] = field(default_factory=list)

    @property
    def is_redirect(self) -> bool:
        return self.status_code in (301, 302, 303, 307, 308)

    @property
    def text(self) -> str:
        encoding = get_encoding_from_headers(self.headers) or "utf-8"
        try:
            return self.content.decode(encoding, errors="replace")
        except LookupError:
            return self.content.decode("utf-8", errors="replace")

    def json(self):
        return _json.loads(self.text)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} for {self.url}")


def _fetch_once(parsed, ip: str, headers: Dict[str, str], timeout: float, max_bytes: int):
    host_header = parsed.netloc.rsplit("@", 1)[-1]
    ip_host = f"[{ip}]" if ":" in ip else ip
    netloc = f"{ip_host}:{parsed.port}" if parsed.port else ip_host
    pinned_url = urlunparse((parsed.scheme, netloc, parsed.path or "/", parsed.params, parsed.query, ""))

    with requests.Session() as session:
        session.trust_env = False
        session.mount(f"{parsed.scheme}://", _PinnedHostAdapter(parsed.hostname))
        with session.get(pinned_url, headers={**headers, "Host": host_header}, timeout=timeout,
                         allow_redirects=False, stream=True) as resp:
            body = bytearray()
            truncated = False
            for chunk in resp.iter_content(_CHUNK):
                body.extend(chunk)
                if len(body) > max_bytes:
                    del body[max_bytes:]
                    truncated = True
                    break
            return resp.status_code, dict(resp.headers), bytes(body), truncated


def safe_get(url: str, *, params: Optional[Dict] = None, headers: Optional[Dict[str, str]] = None,
             timeout: float = 8, max_bytes: int = MAX_RESPONSE_BYTES,
             max_redirects: int = MAX_REDIRECTS) -> SafeResponse:
    """GET a user-controlled URL. Raises UnsafeURLError for disallowed targets."""
    if params:
        url = requests.Request("GET", url, params=params).prepare().url
    headers = dict(headers or {})
    chain: List[str] = []
    current = url
    for _ in range(max_redirects + 1):
        parsed, ip = check_url(current)
        status, resp_headers, body, truncated = _fetch_once(parsed, ip, headers, timeout, max_bytes)
        response = SafeResponse(current, status, resp_headers, body, truncated, list(chain))
        location = resp_headers.get("Location") or resp_headers.get("location")
        if response.is_redirect and location:
            chain.append(current)
            current = urljoin(current, location)
            continue
        return response
    raise UnsafeURLError(f"too many redirects from {url}")
