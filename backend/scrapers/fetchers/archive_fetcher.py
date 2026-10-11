"""
Tier ARCHIVE: the most recent Wayback Machine snapshot of a page that is gone (404/410) or that
blocks us.

1. The availability API (https://archive.org/wayback/available?url=...) names the closest
   snapshot; with no timestamp that is the most recent one.
2. The snapshot is fetched through safe_http in its raw form (the `id_` flag: the page as it was
   archived, without the Wayback toolbar or rewritten links).

The Internet Archive receives the page's URL only, and only URLs that passed the SSRF check,
robots.txt and `is_shareable_with_third_party`.
"""

import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import requests

from core.job_timeout import JobTimeoutException
from core.logging_config import get_logger
from scrapers import url_safety
from scrapers.models import FetchMetadata, RawFetchResult
from scrapers.safe_http import UnsafeURLError, safe_get

logger = get_logger(__name__)

AVAILABILITY_API = "https://archive.org/wayback/available"
LOOKUP_TIMEOUT_SECONDS = 10
SNAPSHOT_TIMEOUT_SECONDS = 15
MAX_SNAPSHOT_BYTES = 10 * 1024 * 1024  # same cap as our own page fetch
USER_AGENT = "FuzeBot/1.0 (+https://itsfuze.vercel.app; bookmark content extraction on user request)"

_SNAPSHOT_URL = re.compile(r"^https?://web\.archive\.org/web/(\d{14})/(.+)$")


@dataclass(frozen=True)
class Snapshot:
    timestamp: str  # YYYYMMDDhhmmss, as the archive reports it
    snapshot_url: str  # the human-facing Wayback page
    raw_url: str  # the archived bytes, without the Wayback toolbar

    @property
    def archived_at(self) -> str:
        return datetime.strptime(self.timestamp, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).isoformat()


@dataclass(frozen=True)
class ArchiveResult:
    snapshot: Snapshot
    page: RawFetchResult


class ArchiveFetcher:
    strategy_name = "ARCHIVE"

    def lookup(self, url: str) -> Optional[Snapshot]:
        """The most recent snapshot that was archived with status 200, or None."""
        resp = safe_get(AVAILABILITY_API, params={"url": url}, headers={"User-Agent": USER_AGENT},
                        timeout=LOOKUP_TIMEOUT_SECONDS, max_bytes=256 * 1024)
        resp.raise_for_status()
        closest = ((resp.json() or {}).get("archived_snapshots") or {}).get("closest") or {}
        if not closest.get("available") or str(closest.get("status")) != "200":
            return None
        match = _SNAPSHOT_URL.match(closest.get("url") or "")
        if not match:
            return None
        timestamp, original = match.groups()
        return Snapshot(timestamp=timestamp,
                        snapshot_url=f"https://web.archive.org/web/{timestamp}/{original}",
                        raw_url=f"https://web.archive.org/web/{timestamp}id_/{original}")

    def fetch(self, url: str) -> Optional[ArchiveResult]:
        """The archived page, or None (no snapshot, archive unreachable, not shareable)."""
        if not url_safety.is_safe_url(url) or not url_safety.is_shareable_with_third_party(url):
            return None
        started = time.time()
        try:
            snapshot = self.lookup(url)
            if snapshot is None:
                logger.info("archive_no_snapshot", extra={"url": url})
                return None
            resp = safe_get(snapshot.raw_url, headers={"User-Agent": USER_AGENT},
                            timeout=SNAPSHOT_TIMEOUT_SECONDS, max_bytes=MAX_SNAPSHOT_BYTES)
        except JobTimeoutException:
            raise
        except (requests.RequestException, UnsafeURLError, ValueError) as e:
            logger.warning("archive_fetch_failed", extra={"url": url, "error": str(e)})
            return None
        if resp.status_code >= 400 or not resp.content:
            logger.info("archive_snapshot_unavailable", extra={"url": url, "status": resp.status_code})
            return None
        meta = FetchMetadata(strategy=self.strategy_name, attempts=1, http_status=resp.status_code,
                             redirected=bool(resp.redirect_chain), redirect_chain=resp.redirect_chain,
                             fetch_latency_ms=int((time.time() - started) * 1000))
        # url stays the original page, so relative links resolve against it.
        page = RawFetchResult(url=url, final_url=resp.url, http_status=resp.status_code,
                              headers=dict(resp.headers), raw_content=resp.content, fetch_metadata=meta)
        return ArchiveResult(snapshot=snapshot, page=page)
