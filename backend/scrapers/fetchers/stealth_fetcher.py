"""
Tier 2: Stealthy Browser Fetcher Implementation
Uses Scrapling's StealthyFetcher (Camoufox TLS fingerprinting) or stealth fallback.
"""

import time
from scrapers.fetchers.base import BaseFetcher
from scrapers.models import RawFetchResult, FetchMetadata
from core.logging_config import get_logger

logger = get_logger(__name__)

# Attempt importing Scrapling StealthyFetcher
SCRAPLING_STEALTH_AVAILABLE = False
StealthyFetcher = None

try:
    from scrapling.fetchers import StealthyFetcher
    SCRAPLING_STEALTH_AVAILABLE = True
except Exception:
    SCRAPLING_STEALTH_AVAILABLE = False


class StealthFetcher(BaseFetcher):
    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    @property
    def strategy_name(self) -> str:
        return "STEALTH"

    def fetch(self, url: str) -> RawFetchResult:
        start_time = time.time()
        
        if SCRAPLING_STEALTH_AVAILABLE and StealthyFetcher is not None:
            try:
                fetcher = StealthyFetcher()
                response = fetcher.fetch(url, timeout=self.timeout)
                latency_ms = int((time.time() - start_time) * 1000)
                
                raw_bytes = getattr(response, 'body', None) or getattr(response, 'content', None) or str(response).encode('utf-8')
                status = getattr(response, 'status', 200)

                meta = FetchMetadata(
                    strategy=self.strategy_name,
                    attempts=1,
                    http_status=status,
                    redirected=False,
                    scrapling_version="0.2.0",
                    fetch_latency_ms=latency_ms
                )
                return RawFetchResult(
                    url=url,
                    final_url=url,
                    http_status=status,
                    headers={},
                    raw_content=raw_bytes if isinstance(raw_bytes, bytes) else str(raw_bytes).encode('utf-8'),
                    fetch_metadata=meta
                )
            except Exception as e:
                logger.warning("scrapling_stealth_fetch_failed", extra={"url": url, "error": str(e)})

        # Fallback to requests with enhanced stealth headers
        from scrapers.fetchers.http_fetcher import HTTPFetcher
        fallback = HTTPFetcher(timeout=self.timeout)
        result = fallback.fetch(url)
        meta = FetchMetadata(
            strategy=self.strategy_name,
            attempts=1,
            http_status=result.http_status,
            redirected=result.fetch_metadata.redirected,
            redirect_chain=result.fetch_metadata.redirect_chain,
            fetch_latency_ms=result.fetch_metadata.fetch_latency_ms
        )
        return RawFetchResult(
            url=url,
            final_url=result.final_url,
            http_status=result.http_status,
            headers=result.headers,
            raw_content=result.raw_content,
            fetch_metadata=meta
        )
