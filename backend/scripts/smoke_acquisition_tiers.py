#!/usr/bin/env python3
"""
Live smoke test of the content acquisition tiers (not part of pytest: it uses the network).

For each URL it runs every tier on its own, then the whole engine, and prints what each
produced:

    cd backend && python scripts/smoke_acquisition_tiers.py [url ...]

Tiers: API (official adapters), HTTP (our fetch), READER (remote reader service), ARCHIVE
(Wayback Machine), then ENGINE (the real escalation path). READER and ARCHIVE run only when
robots.txt allows our bot, like the engine. Keep runs small: the reader allows 20 requests a
minute per IP without READER_API_KEY, and each URL here can use two.

Redis is pinned to a local test database so the per-domain limits and breakers never touch
the production Redis in .env.
"""

import argparse
import os
import sys
import time

os.environ["REDIS_URL"] = os.getenv("SMOKE_REDIS_URL", "redis://127.0.0.1:6379/15")
os.environ.setdefault("ENABLE_READER_FALLBACK", "true")
os.environ.setdefault("ENABLE_ARCHIVE_FALLBACK", "true")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging  # noqa: E402

import structlog  # noqa: E402

if "--verbose" not in sys.argv:
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.ERROR))

from scrapers.acquisition_engine import ContentAcquisitionEngine  # noqa: E402
from scrapers.decision_engine import DecisionEngine  # noqa: E402
from scrapers.fetchers.archive_fetcher import ArchiveFetcher  # noqa: E402
from scrapers.fetchers.reader_fetcher import ReaderFetcher  # noqa: E402
from scrapers.source_adapters import adapter_for, fetch_from_source  # noqa: E402

DEFAULT_URLS = [
    "https://excalidraw.com/",                                  # client-rendered app
    "https://www.npmjs.com/package/react",                      # often a bot challenge
    "https://www.instagram.com/nasa/",                          # login wall
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",              # adapter: oEmbed + JSON-LD
    "https://x.com/jack/status/20",                             # adapter: oEmbed
    "https://www.reddit.com/r/Python/comments/1c5jvai/",        # adapter: .json, else oEmbed
    "https://medium.com/@netflixtechblog",                      # not a story: falls through
    "https://developer.mozilla.org/en-US/docs/Web/API/Navigator/registerContentHandler",  # 404, archived
    "https://www.python.org/this-page-does-not-exist-xyz",      # 404, never archived
]


def words(text: str) -> int:
    return len((text or "").split())


def run(url: str, engine: ContentAcquisitionEngine) -> None:
    print(f"\n=== {url}")
    adapter = adapter_for(url)
    if adapter:
        content = fetch_from_source(url)
        print(f"  API      {adapter.__name__:10} -> " + (
            f"ok, {words(content.text)} words, title={content.title[:60]!r}" if content else "none (falls through)"))

    raw = engine.fetchers["HTTP"].fetch(url)
    if raw.http_status >= 400 or not raw.raw_content:
        print(f"  HTTP     status {raw.http_status} -> no page")
    else:
        norm, quality, _ = engine._extract(raw, None)
        decision = DecisionEngine().evaluate(quality, "HTTP", ["READER", "ARCHIVE"])
        print(f"  HTTP     status {raw.http_status} -> {quality.word_count} words, score {quality.score}, "
              f"challenge={quality.challenge_detected}, hydration={quality.hydration_detected} "
              f"=> {decision.action} {decision.next_strategy or ''} ({decision.reason})")

    if not engine.robots_manager.can_fetch(url):
        print("  READER   skipped: robots.txt disallows our bot")
        print("  ARCHIVE  skipped: robots.txt disallows our bot")
    else:
        result = ReaderFetcher().fetch(url)
        print("  READER   " + (
            f"ok, target {result.http_status}, {words(result.content)} words, title={result.title[:60]!r}, "
            f"{result.latency_ms} ms" if result.ok else
            f"failed: {result.error} (target {result.http_status}, retryable={result.retryable}, "
            f"{result.latency_ms} ms)"))
        archived = ArchiveFetcher().fetch(url)
        print("  ARCHIVE  " + (
            f"snapshot {archived.snapshot.archived_at}, {len(archived.page.raw_content)} bytes"
            if archived else "no usable snapshot"))

    doc = engine.acquire_and_normalize(url)
    archive = doc.provider_raw_payload.get("archive") if isinstance(doc.provider_raw_payload, dict) else None
    print(f"  ENGINE   outcome={doc.outcome} strategy={doc.fetch_metadata.strategy} retryable={doc.retryable} "
          f"words={doc.quality_metrics.word_count} title={doc.metadata.title[:60]!r}"
          + (f" archived_at={archive['archived_at']}" if archive else ""))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("urls", nargs="*", default=DEFAULT_URLS)
    parser.add_argument("--pause", type=float, default=4.0, help="seconds between URLs (reader rate limit)")
    parser.add_argument("--verbose", action="store_true", help="also print the pipeline's logs")
    args = parser.parse_args()
    engine = ContentAcquisitionEngine()
    for i, url in enumerate(args.urls):
        if i:
            time.sleep(args.pause)
        try:
            run(url, engine)
        except Exception as e:  # a smoke test reports and moves on
            print(f"  ERROR    {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
