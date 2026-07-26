"""
Tier 3: Dynamic Browser Fetcher Implementation
Uses Scrapling's DynamicFetcher (Chromium client-side JS rendering) or Playwright fallback.
"""

import time
from scrapers.fetchers.base import BaseFetcher
from scrapers.models import RawFetchResult, FetchMetadata
from core.logging_config import get_logger

logger = get_logger(__name__)

SCRAPLING_DYNAMIC_AVAILABLE = False
DynamicFetcherClass = None

try:
    from scrapling.fetchers import DynamicFetcher as DynamicFetcherClass
    SCRAPLING_DYNAMIC_AVAILABLE = True
except Exception:
    SCRAPLING_DYNAMIC_AVAILABLE = False


class DynamicFetcher(BaseFetcher):
    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    @property
    def strategy_name(self) -> str:
        return "DYNAMIC"

    def fetch(self, url: str) -> RawFetchResult:
        start_time = time.time()

        if SCRAPLING_DYNAMIC_AVAILABLE and DynamicFetcherClass is not None:
            try:
                fetcher = DynamicFetcherClass()
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
                logger.warning("scrapling_dynamic_fetch_failed", extra={"url": url, "error": str(e)})

        # Fallback to Playwright if available
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")
                content = page.content()
                browser.close()

                latency_ms = int((time.time() - start_time) * 1000)
                meta = FetchMetadata(
                    strategy=self.strategy_name,
                    attempts=1,
                    http_status=200,
                    redirected=False,
                    fetch_latency_ms=latency_ms
                )
                return RawFetchResult(
                    url=url,
                    final_url=url,
                    http_status=200,
                    headers={},
                    raw_content=content.encode('utf-8'),
                    fetch_metadata=meta
                )
        except Exception as e:
            logger.warning("playwright_dynamic_fetch_failed", extra={"url": url, "error": str(e)})

        # Final fallback to StealthFetcher
        from scrapers.fetchers.stealth_fetcher import StealthFetcher
        fallback = StealthFetcher(timeout=self.timeout)
        result = fallback.fetch(url)
        meta = FetchMetadata(
            strategy=self.strategy_name,
            attempts=1,
            http_status=result.http_status,
            redirected=result.fetch_metadata.redirected,
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
