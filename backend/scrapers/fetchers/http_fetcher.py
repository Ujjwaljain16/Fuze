"""
Tier 1: Fast HTTP Fetcher Implementation
Uses lightweight HTTP requests with browser headers for high-speed fetching.
"""

import time
from scrapers.fetchers.base import BaseFetcher
from scrapers.models import RawFetchResult, FetchMetadata
from scrapers.safe_http import safe_get
from core.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_TIMEOUT = 8
MAX_REDIRECTS = 5
MAX_PAGE_BYTES = 10 * 1024 * 1024


class HTTPFetcher(BaseFetcher):
    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "FuzeBot/1.0 (+https://itsfuze.vercel.app; bookmark content extraction on user request)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    @property
    def strategy_name(self) -> str:
        return "HTTP"

    def fetch(self, url: str) -> RawFetchResult:
        start_time = time.time()
        try:
            # safe_get re-checks every redirect hop, pins the checked IP and caps the body size.
            resp = safe_get(url, headers=self.headers, timeout=self.timeout,
                            max_bytes=MAX_PAGE_BYTES, max_redirects=MAX_REDIRECTS)
            redirect_chain = resp.redirect_chain

            latency_ms = int((time.time() - start_time) * 1000)
            meta = FetchMetadata(
                strategy=self.strategy_name,
                attempts=1,
                http_status=resp.status_code,
                redirected=len(redirect_chain) > 0,
                redirect_chain=redirect_chain,
                fetch_latency_ms=latency_ms
            )

            return RawFetchResult(
                url=url,
                final_url=resp.url,
                http_status=resp.status_code,
                headers=dict(resp.headers),
                raw_content=resp.content,
                fetch_metadata=meta
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning("http_fetch_failed", extra={"url": url, "error": str(e)})
            meta = FetchMetadata(
                strategy=self.strategy_name,
                attempts=1,
                http_status=500,
                redirected=False,
                fetch_latency_ms=latency_ms
            )
            return RawFetchResult(
                url=url,
                final_url=url,
                http_status=500,
                headers={},
                raw_content=b"",
                fetch_metadata=meta
            )
