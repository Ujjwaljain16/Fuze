"""
Tier 1: Fast HTTP Fetcher Implementation
Uses lightweight HTTP requests with browser headers for high-speed fetching.
"""

import time
import requests
from scrapers.fetchers.base import BaseFetcher
from scrapers.models import RawFetchResult, FetchMetadata
from core.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_TIMEOUT = 8


class HTTPFetcher(BaseFetcher):
    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive"
        })

    @property
    def strategy_name(self) -> str:
        return "HTTP"

    def fetch(self, url: str) -> RawFetchResult:
        start_time = time.time()
        try:
            resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            latency_ms = int((time.time() - start_time) * 1000)
            
            redirect_chain = [r.url for r in resp.history]
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
