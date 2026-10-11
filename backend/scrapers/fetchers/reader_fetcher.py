"""
Tier READER: a remote reader service renders the page (JavaScript included) and returns it as
markdown. No browser runs on our servers; the service's does.

Default service: Jina Reader (https://r.jina.ai). Without a key it allows 20 requests a minute
per IP; a free key (READER_API_KEY) raises that to hundreds. See docs/CONTENT_ACQUISITION.md.

What the service receives: the page's URL. Not the user, not their notes, not cookies. The
caller only hands over URLs that passed the SSRF check and `is_shareable_with_third_party`,
and only after our own robots.txt check allowed the fetch; the service is also asked to obey
the site's robots.txt for our bot name.
"""

import os
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urldefrag

import requests

from core.job_timeout import JobTimeoutException
from core.logging_config import get_logger
from scrapers import url_safety
from scrapers.safe_http import UnsafeURLError, safe_get

logger = get_logger(__name__)

DEFAULT_READER_URL = "https://r.jina.ai/"
DEFAULT_TIMEOUT_SECONDS = 20
MAX_READER_BYTES = 10 * 1024 * 1024  # same cap as our own page fetch
ROBOTS_BOT_NAME = "FuzeBot"
USER_AGENT = "FuzeBot/1.0 (+https://itsfuze.vercel.app; bookmark content extraction on user request)"


def reader_base_url() -> str:
    return (os.getenv("READER_BASE_URL") or DEFAULT_READER_URL).strip()


def reader_api_key() -> Optional[str]:
    return (os.getenv("READER_API_KEY") or "").strip() or None


def reader_timeout() -> float:
    try:
        return max(1.0, float(os.getenv("READER_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)))
    except ValueError:
        return float(DEFAULT_TIMEOUT_SECONDS)


def reader_requests_per_minute() -> int:
    """Our own ceiling, kept under the service's limit (20/min per IP without a key)."""
    default = 300 if reader_api_key() else 15
    try:
        return max(1, int(os.getenv("READER_RPM", default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class ReaderResult:
    ok: bool
    content: str = ""
    title: str = ""
    description: Optional[str] = None
    author: Optional[str] = None
    image_url: Optional[str] = None
    published_at: Optional[str] = None
    final_url: Optional[str] = None
    # The target page's status as the reader saw it; None when the reader gave no verdict.
    http_status: Optional[int] = None
    # The failure may pass on a retry (timeout, the service's 5xx or 429).
    retryable: bool = False
    error: Optional[str] = None
    latency_ms: int = 0


class ReaderFetcher:
    strategy_name = "READER"

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None,
                 timeout: Optional[float] = None):
        self._base_url = base_url
        self._api_key = api_key
        self._timeout = timeout

    def _headers(self) -> dict:
        headers = {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            # Fetch fresh: a cached copy can be stale, or something another client planted.
            "X-No-Cache": "true",
            # Ask the service not to keep the result.
            "DNT": "1",
            # The service checks the site's robots.txt for our bot name too.
            "X-Robots-Txt": ROBOTS_BOT_NAME,
            "X-Retain-Images": "none",
        }
        key = self._api_key or reader_api_key()
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    def fetch(self, url: str) -> ReaderResult:
        started = time.time()

        def done(**kwargs) -> ReaderResult:
            return ReaderResult(latency_ms=int((time.time() - started) * 1000), **kwargs)

        # Never send an internal address, or a URL that carries a secret, to an outside service.
        if not url_safety.is_safe_url(url) or not url_safety.is_shareable_with_third_party(url):
            return done(ok=False, error="url_not_shareable")

        base = self._base_url or reader_base_url()
        # The service takes the target as the path: https://r.jina.ai/https://example.com/a?b=1
        # (its ?url= form rejects URLs with their own query string). The fragment never leaves
        # the browser anyway.
        reader_url = base.rstrip("/") + "/" + urldefrag(url)[0]
        try:
            resp = safe_get(reader_url, headers=self._headers(), timeout=self._timeout or reader_timeout(),
                            max_bytes=MAX_READER_BYTES, max_redirects=0)
        except JobTimeoutException:
            raise
        except UnsafeURLError as e:
            return done(ok=False, error=f"reader_unsafe: {e}")
        except requests.Timeout:
            logger.warning("reader_timeout", extra={"url": url})
            return done(ok=False, retryable=True, error="reader_timeout")
        except requests.RequestException as e:
            logger.warning("reader_request_failed", extra={"url": url, "error": str(e)})
            return done(ok=False, retryable=True, error="reader_unreachable")

        if resp.status_code == 429 or resp.status_code >= 500:
            logger.warning("reader_unavailable", extra={"url": url, "status": resp.status_code})
            return done(ok=False, retryable=True, error=f"reader_http_{resp.status_code}")
        if resp.truncated:
            return done(ok=False, error="reader_response_too_large")

        try:
            payload = resp.json()
        except ValueError:
            return done(ok=False, error=f"reader_bad_response_{resp.status_code}")
        if resp.status_code >= 400:
            # 401/402: key or balance problem (ours); 422/451: the service refused the target.
            logger.warning("reader_refused", extra={"url": url, "status": resp.status_code,
                                                    "message": str(payload.get("message", ""))[:200]})
            return done(ok=False, error=f"reader_http_{resp.status_code}")

        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            return done(ok=False, error="reader_bad_response")
        target_status = data.get("httpStatus")
        target_status = target_status if isinstance(target_status, int) else None
        if target_status is not None and target_status >= 400:
            return done(ok=False, http_status=target_status, error=f"target_http_{target_status}")

        content = (data.get("content") or "").strip()
        if not content:
            return done(ok=False, http_status=target_status, error="reader_empty")
        meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        return done(ok=True, content=content, title=(data.get("title") or "").strip(),
                    description=(data.get("description") or "").strip() or None,
                    author=_text(meta.get("author") or meta.get("article:author")),
                    image_url=_text(meta.get("og:image")),
                    published_at=_text(data.get("publishedTime") or meta.get("article:published_time")),
                    final_url=data.get("url") or url, http_status=target_status or 200)


def _text(value) -> Optional[str]:
    """Metadata values are strings, or lists of them when a tag repeats."""
    if isinstance(value, list):
        value = value[0] if value else None
    if not isinstance(value, str):
        return None
    return value.strip() or None
