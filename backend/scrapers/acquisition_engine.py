"""
Content Acquisition Engine (5-Stage Architecture)
Single-responsibility engine that reliably acquires, parses, quality-evaluates, and normalizes web content
into an immutable ContentDocument DTO.
"""

import time
from dataclasses import dataclass, field, replace
from urllib.parse import urlparse
from typing import Dict, List, Optional, Tuple
from scrapers.robots_manager import RobotsManager
from scrapers.rate_limiter import DomainRateLimiter
from scrapers.fetch_policy import FetchPolicy
from scrapers.fetchers.http_fetcher import HTTPFetcher
from scrapers.fetchers.reader_fetcher import ReaderFetcher
from scrapers.fetchers.archive_fetcher import ArchiveFetcher
from scrapers.extractor_pipeline import ExtractorPipeline
from scrapers.normalizer import MetadataNormalizer
from scrapers.quality_evaluator import QualityEvaluator
from scrapers.decision_engine import DecisionEngine
from scrapers.event_publisher import ScrapingEventPublisher
from scrapers.url_safety import is_safe_url, is_unresolved_host
from scrapers.models import (ContentDocument, RawFetchResult, NormalizedDocument, QualityMetrics, compute_content_hash)
from core.circuit_breaker import RedisCircuitBreaker
from core.job_timeout import JobTimeoutException
from core.events import (
    FetchStarted, FetchCompleted, ParsingStarted, ParsingCompleted, NormalizationCompleted
)
from core.logging_config import get_logger

logger = get_logger(__name__)

# Error statuses whose body is worth checking for a bot challenge (Cloudflare and friends answer
# challenges with 403 or 503).
CHALLENGE_STATUSES = (403, 503)
CHALLENGE_SNIFF_BYTES = 200_000


@dataclass
class _Attempt:
    """What one tier of the strategy plan produced."""
    strategy: str
    norm_doc: Optional[NormalizedDocument] = None  # set when the tier produced a page
    quality: Optional[QualityMetrics] = None
    http_status: Optional[int] = None  # the target page's status as the tier saw it; None: no answer
    challenge: bool = False  # an error status whose body is a bot challenge
    retryable: bool = False  # the tier failed for a reason that may pass (timeout, 5xx, 429)
    plugin_versions: Dict[str, str] = field(default_factory=dict)


def _ranking(attempt: _Attempt) -> Tuple[bool, int]:
    """Best content so far: anything that is not a challenge page, then the most words."""
    return (not attempt.quality.challenge_detected, attempt.quality.word_count)


class ContentAcquisitionEngine:
    """
    Production-grade 5-Stage Content Acquisition Engine.
    """
    def __init__(self):
        self.robots_manager = RobotsManager()
        self.rate_limiter = DomainRateLimiter()
        self.fetch_policy = FetchPolicy()

        self.fetchers = {
            "HTTP": HTTPFetcher()
        }
        self.reader = ReaderFetcher()
        self.archive = ArchiveFetcher()

        self.extractor_pipeline = ExtractorPipeline()
        self.normalizer = MetadataNormalizer()
        self.quality_evaluator = QualityEvaluator()
        self.decision_engine = DecisionEngine()
        self.event_publisher = ScrapingEventPublisher()

    def _acquire_from_source_api(self, url: str, bookmark_id: Optional[int],
                                 _depth: int = 0) -> Optional[ContentDocument]:
        """Use the site's official API when there is one (GitHub, arXiv, Wikipedia, Stack Exchange, ...)."""
        from scrapers.source_adapters import fetch_from_source
        from scrapers.models import FetchMetadata, NormalizedMetadata

        started = time.time()
        content = fetch_from_source(url)
        if content is None:
            return None

        # e.g. a Hacker News link post: the linked article is what was saved.
        if content.follow_url and _depth == 0 and is_safe_url(content.follow_url):
            linked = self.acquire_and_normalize(content.follow_url, bookmark_id=bookmark_id, _depth=1)
            if linked.markdown_content.strip():
                own_text = "" if content.text.startswith("Link:") else content.text
                body = "\n\n".join(p for p in (own_text, linked.markdown_content) if p)
                return replace(
                    linked,
                    url=url,
                    markdown_content=body,
                    content_hash=compute_content_hash(body),
                    metadata=replace(linked.metadata, title=content.title or linked.metadata.title),
                    provider_raw_payload={"source_api": content.source, **content.raw,
                                          "linked": linked.provider_raw_payload},
                )
        strategy = f"API:{content.source}"[:20]
        fetch_meta = FetchMetadata(strategy=strategy, attempts=1, http_status=200, redirected=False,
                                   fetch_latency_ms=int((time.time() - started) * 1000))
        if bookmark_id:
            self.event_publisher.publish(FetchStarted(bookmark_id=bookmark_id, strategy=strategy, url=url))
            self.event_publisher.publish(FetchCompleted(bookmark_id=bookmark_id, strategy=strategy, http_status=200,
                                                        latency_ms=fetch_meta.fetch_latency_ms))
        words = len(content.text.split())
        metadata = NormalizedMetadata(
            title=content.title or url,
            description=content.description,
            author=content.author,
            published_at=content.published_at,
            canonical_url=content.canonical_url,
            reading_time_minutes=max(1, round(words / 200)) if words else 0,
            keywords=list(content.keywords or []),
            field_provenance={"title": strategy, "body": strategy},
        )
        quality = self.quality_evaluator.evaluate(html="", clean_text=content.text, title=content.title)
        return ContentDocument(
            url=url,
            canonical_url=content.canonical_url or url,
            content_hash=compute_content_hash(content.text),
            markdown_content=content.text,
            metadata=metadata,
            provider_raw_payload={"source_api": content.source, **content.raw},
            quality_metrics=quality,
            fetch_metadata=fetch_meta,
            plugin_versions={"source_adapter": "1.0.0"},
        )

    def _unfetched(self, url: str, outcome: str, retryable: bool, note: str) -> ContentDocument:
        """A document for a page that was deliberately not fetched."""
        from scrapers.models import FetchMetadata, NormalizedMetadata, QualityMetrics
        return ContentDocument(
            url=url, canonical_url=url, content_hash=compute_content_hash(""), markdown_content="",
            metadata=NormalizedMetadata(title=""), provider_raw_payload={},
            quality_metrics=QualityMetrics(score=0, has_title=False, has_article_body=False, word_count=0,
                                           hydration_detected=False, challenge_detected=False,
                                           evaluation_notes=[note]),
            fetch_metadata=FetchMetadata(strategy="HTTP", attempts=0, http_status=0, redirected=False),
            outcome=outcome, retryable=retryable,
        )

    def _looks_like_challenge(self, body: bytes) -> bool:
        """An error page (403/503) that is a bot challenge rather than a plain refusal."""
        if not body:
            return False
        from bs4 import BeautifulSoup
        html = body[:CHALLENGE_SNIFF_BYTES].decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        return self.quality_evaluator.evaluate(html=html, clean_text=soup.get_text(" ", strip=True),
                                               title=title).challenge_detected

    def _attempt_http(self, url: str, bookmark_id: Optional[int],
                      circuit_breaker: RedisCircuitBreaker) -> _Attempt:
        """Tier HTTP: fetch the page ourselves, then extract, normalize and score it."""
        strategy = "HTTP"
        fetcher = self.fetchers["HTTP"]

        if not circuit_breaker.allow_request():
            logger.error("circuit_breaker_open_skipping_fetch", extra={"url": url, "strategy": strategy})
            return _Attempt(strategy, http_status=None, retryable=True)

        if bookmark_id:
            self.event_publisher.publish(FetchStarted(bookmark_id=bookmark_id, strategy=strategy, url=url))

        try:
            raw_result = fetcher.fetch(url)
            if raw_result and raw_result.http_status < 400:
                circuit_breaker.record_success()
                self.fetch_policy.record_success(url, strategy)
            else:
                circuit_breaker.record_failure()
                self.fetch_policy.record_failure(url, strategy)
        except JobTimeoutException:
            raise
        except Exception as fetch_err:
            circuit_breaker.record_failure()
            self.fetch_policy.record_failure(url, strategy)
            logger.error("fetcher_exception", extra={"url": url, "strategy": strategy, "error": str(fetch_err)})
            return _Attempt(strategy, http_status=None, retryable=True)

        if not raw_result:
            return _Attempt(strategy, http_status=None, retryable=True)

        if bookmark_id:
            self.event_publisher.publish(
                FetchCompleted(
                    bookmark_id=bookmark_id,
                    strategy=strategy,
                    http_status=raw_result.http_status,
                    latency_ms=raw_result.fetch_metadata.fetch_latency_ms
                )
            )

        status = raw_result.http_status
        # An error status page (404, 403, 503 ...) is not the bookmarked content.
        if status >= 400 or not raw_result.raw_content:
            challenge = status in CHALLENGE_STATUSES and self._looks_like_challenge(raw_result.raw_content)
            return _Attempt(strategy, http_status=status, challenge=challenge,
                            retryable=status >= 500 or status == 429)

        # Stage 3: Extraction
        if bookmark_id:
            self.event_publisher.publish(ParsingStarted(bookmark_id=bookmark_id, plugins_count=len(self.extractor_pipeline.plugins)))
        norm_doc, quality_metrics, plugin_versions = self._extract(raw_result, bookmark_id)
        return _Attempt(strategy, norm_doc=norm_doc, quality=quality_metrics, http_status=status,
                        plugin_versions=plugin_versions)

    def _extract(self, raw_result: RawFetchResult,
                 bookmark_id: Optional[int]) -> Tuple[NormalizedDocument, QualityMetrics, Dict[str, str]]:
        """Stages 3-4 for an HTML page: extractor plugins, normalization, quality score."""
        parsed_doc = self.extractor_pipeline.process(raw_result)
        plugin_versions = {res.plugin_name: res.plugin_version for res in parsed_doc.plugin_results}

        if bookmark_id:
            succeeded = sum(1 for r in parsed_doc.plugin_results if r.success)
            self.event_publisher.publish(ParsingCompleted(bookmark_id=bookmark_id, plugins_succeeded=succeeded))

        norm_doc = self.normalizer.normalize(parsed_doc)
        quality_metrics = self.quality_evaluator.evaluate(
            html=parsed_doc.raw_html,
            clean_text=parsed_doc.clean_text,
            title=norm_doc.metadata.title
        )
        if bookmark_id:
            self.event_publisher.publish(
                NormalizationCompleted(bookmark_id=bookmark_id,
                                       content_hash=compute_content_hash(norm_doc.markdown_content),
                                       quality_score=quality_metrics.score)
            )
        return norm_doc, quality_metrics, plugin_versions

    def _attempt_reader(self, url: str, bookmark_id: Optional[int]) -> _Attempt:
        """Tier READER: a remote reader service renders the page and returns markdown."""
        from scrapers.fetchers.reader_fetcher import reader_requests_per_minute
        from scrapers.models import FetchMetadata, NormalizedMetadata
        from scrapers.text_cleanup import clean_body
        strategy = "READER"

        # The service's own trouble (outage, quota) must not count against the target's domain.
        breaker = RedisCircuitBreaker(name="reader_service", failure_threshold=5, recovery_timeout=300)
        if not breaker.allow_request():
            logger.warning("reader_circuit_open", extra={"url": url})
            return _Attempt(strategy, retryable=True)
        # One shared ceiling for all workers, under the service's per-minute limit.
        allowed, _ = DomainRateLimiter(max_requests=reader_requests_per_minute(),
                                       window_seconds=60).acquire("https://reader-quota.invalid/")
        if not allowed:
            logger.info("reader_rate_limited", extra={"url": url})
            return _Attempt(strategy, retryable=True)

        if bookmark_id:
            self.event_publisher.publish(FetchStarted(bookmark_id=bookmark_id, strategy=strategy, url=url))
        result = self.reader.fetch(url)
        if result.retryable:
            breaker.record_failure()
        elif result.ok or result.http_status is not None:
            breaker.record_success()
        if bookmark_id:
            self.event_publisher.publish(FetchCompleted(bookmark_id=bookmark_id, strategy=strategy,
                                                        http_status=result.http_status or 0,
                                                        latency_ms=result.latency_ms))
        if not result.ok:
            logger.info("reader_no_content", extra={"url": url, "error": result.error,
                                                    "http_status": result.http_status})
            return _Attempt(strategy, http_status=result.http_status, retryable=result.retryable)

        body = clean_body(result.content)
        words = len(body.split())
        provenance = {name: strategy for name, value in (
            ("title", result.title), ("description", result.description), ("author", result.author),
            ("image_url", result.image_url), ("published_at", result.published_at)) if value}
        provenance["body"] = strategy
        metadata = NormalizedMetadata(
            title=result.title,
            description=result.description,
            image_url=result.image_url,
            author=result.author,
            published_at=result.published_at,
            canonical_url=result.final_url,
            reading_time_minutes=max(1, round(words / 200)) if words else 0,
            field_provenance=provenance,
        )
        norm_doc = NormalizedDocument(
            url=url,
            canonical_url=result.final_url or url,
            markdown_content=body,
            metadata=metadata,
            provider_raw_payload={"reader": {"service": "jina", "final_url": result.final_url}},
            fetch_metadata=FetchMetadata(strategy=strategy, attempts=1, http_status=result.http_status or 200,
                                         redirected=bool(result.final_url and result.final_url != url),
                                         fetch_latency_ms=result.latency_ms),
        )
        quality = self.quality_evaluator.evaluate(html="", clean_text=body, title=result.title)
        return _Attempt(strategy, norm_doc=norm_doc, quality=quality, http_status=result.http_status,
                        plugin_versions={"reader": "1.0.0"})

    def _attempt_archive(self, url: str, bookmark_id: Optional[int]) -> _Attempt:
        """Tier ARCHIVE: the most recent Wayback Machine snapshot of a gone or blocked page."""
        strategy = "ARCHIVE"
        if bookmark_id:
            self.event_publisher.publish(FetchStarted(bookmark_id=bookmark_id, strategy=strategy, url=url))
        result = self.archive.fetch(url)
        if result is None:
            # Opportunistic: a page that is gone stays gone, so archive trouble is not retried.
            return _Attempt(strategy)
        page = result.page
        if bookmark_id:
            self.event_publisher.publish(FetchCompleted(bookmark_id=bookmark_id, strategy=strategy,
                                                        http_status=page.http_status,
                                                        latency_ms=page.fetch_metadata.fetch_latency_ms))
            self.event_publisher.publish(ParsingStarted(bookmark_id=bookmark_id,
                                                        plugins_count=len(self.extractor_pipeline.plugins)))
        norm_doc, quality, plugin_versions = self._extract(page, bookmark_id)

        snapshot = result.snapshot
        canonical = norm_doc.canonical_url
        if not canonical or "web.archive.org" in canonical:
            canonical = url
        # The UI says the content came from the archive, and from when.
        archive_info = {"source": "wayback", "snapshot_url": snapshot.snapshot_url,
                        "timestamp": snapshot.timestamp, "archived_at": snapshot.archived_at}
        norm_doc = replace(
            norm_doc,
            canonical_url=canonical,
            metadata=replace(norm_doc.metadata, canonical_url=canonical,
                             field_provenance={**norm_doc.metadata.field_provenance, "body": strategy}),
            provider_raw_payload={**norm_doc.provider_raw_payload, "archive": archive_info},
        )
        return _Attempt(strategy, norm_doc=norm_doc, quality=quality, http_status=page.http_status,
                        plugin_versions=plugin_versions)

    def _run_tier(self, strategy: str, url: str, bookmark_id: Optional[int],
                  circuit_breaker: RedisCircuitBreaker) -> _Attempt:
        if strategy == "READER":
            return self._attempt_reader(url, bookmark_id)
        if strategy == "ARCHIVE":
            return self._attempt_archive(url, bookmark_id)
        return self._attempt_http(url, bookmark_id, circuit_breaker)

    def acquire_and_normalize(self, url: str, bookmark_id: Optional[int] = None, _depth: int = 0) -> ContentDocument:
        """
        Execute 5-stage acquisition & normalization pipeline on target URL.
        """
        # --- STAGE 1: Acquisition Manager (Robots, Rate Limit, Circuit Breaker, Policy) ---
        domain = urlparse(url).netloc.lower()
        circuit_breaker = RedisCircuitBreaker(name=f"domain_{domain}", failure_threshold=5, recovery_timeout=300)

        # SSRF guard: never let a user-supplied URL that resolves to an
        # internal/loopback/link-local address reach any fetcher or third-party tier. Leaving
        # strategy_plan empty routes straight to the "fetch failed" fallback below.
        if is_safe_url(url):
            # Official APIs first: they are meant to be called and don't fall under robots.txt.
            source_doc = self._acquire_from_source_api(url, bookmark_id, _depth)
            if source_doc is not None:
                return source_doc
            # Both checks used to be logged and then ignored. A disallow also rules out every
            # later tier: the reader and the archive must not be a way around it.
            # robots.txt is itself a request to the user's host, so it comes after the address check.
            if not self.robots_manager.can_fetch(url):
                logger.info("acquisition_disallowed_by_robots", extra={"url": url})
                return self._unfetched(url, "disallowed", retryable=False, note="Disallowed by robots.txt")
            allowed, wait_time = self.rate_limiter.acquire(url)
            if not allowed:
                logger.info("acquisition_rate_limited", extra={"url": url, "wait_time": wait_time})
                return self._unfetched(url, "failed", retryable=True, note="Per-domain rate limit")
            strategy_plan = self.fetch_policy.get_strategy_plan(url)
        elif is_unresolved_host(url):
            # A DNS failure says nothing about the site: retry later instead of blocking it.
            logger.warning("acquisition_dns_failed_will_retry", extra={"url": url})
            return self._unfetched(url, "failed", retryable=True, note="Host name did not resolve")
        else:
            logger.error("acquisition_blocked_unsafe_url", extra={"url": url})
            strategy_plan = []

        # --- STAGE 2-4: tiered fetch, extraction and quality evaluation ---
        # Each tier either produces a page (scored and judged by the decision engine) or fails
        # (judged by how it failed). ESCALATE moves on to the tier the engine names.
        attempts: List[_Attempt] = []
        accepted: Optional[_Attempt] = None
        best: Optional[_Attempt] = None  # the best page seen, in case no tier is accepted
        plugin_versions: Dict[str, str] = {}
        page_blocked = False
        next_strategy = strategy_plan[0] if strategy_plan else None

        while next_strategy is not None:
            strategy, next_strategy = next_strategy, None
            remaining = strategy_plan[strategy_plan.index(strategy) + 1:]
            attempt = self._run_tier(strategy, url, bookmark_id, circuit_breaker)
            attempts.append(attempt)
            plugin_versions.update(attempt.plugin_versions)

            if attempt.norm_doc is not None:
                decision = self.decision_engine.evaluate(attempt.quality, strategy, remaining)
                if best is None or _ranking(attempt) > _ranking(best):
                    best = attempt
                page_blocked = page_blocked or attempt.quality.challenge_detected
            else:
                decision = self.decision_engine.evaluate_failure(attempt.http_status, attempt.challenge,
                                                                 remaining, page_blocked)
                page_blocked = page_blocked or attempt.challenge or attempt.http_status in (401, 403)

            if decision.action == "ACCEPT":
                logger.info("acquisition_decision_accepted",
                            extra={"url": url, "strategy": strategy, "score": attempt.quality.score})
                accepted = attempt
                break
            if decision.action == "ESCALATE":
                logger.info("acquisition_decision_escalating",
                            extra={"url": url, "strategy": strategy, "reason": decision.reason,
                                   "next": decision.next_strategy})
                next_strategy = decision.next_strategy
                continue
            logger.warning("acquisition_decision_failed",
                           extra={"url": url, "strategy": strategy, "reason": decision.reason})

        # A later tier that timed out or was rate limited may work on a retry.
        tier_retryable = any(a.retryable for a in attempts[1:])
        outcome, retryable = "ok", False
        final = accepted or best
        if final is not None:
            final_norm_doc, final_quality = final.norm_doc, final.quality
            if accepted is None and final_quality.challenge_detected:
                outcome, retryable = "blocked", tier_retryable
        else:
            outcome = "failed"
            # The page's own answer decides: no response, a server error or rate limiting may
            # pass later; 4xx (404, 410, 403) won't.
            direct_status = attempts[0].http_status if attempts else None
            retryable = (direct_status is None or direct_status >= 500 or direct_status == 429
                         or tier_retryable)
            from scrapers.models import FetchMetadata, NormalizedMetadata
            meta = FetchMetadata(strategy="HTTP", attempts=len(attempts) or 1,
                                 http_status=direct_status if direct_status is not None else 500,
                                 redirected=False)
            final_norm_doc = NormalizedDocument(
                url=url,
                canonical_url=url,
                markdown_content="",
                metadata=NormalizedMetadata(title="Failed to Acquire Content"),
                provider_raw_payload={},
                fetch_metadata=meta
            )
            final_quality = QualityMetrics(
                score=0, has_title=False, has_article_body=False, word_count=0,
                hydration_detected=False, challenge_detected=True, evaluation_notes=["Fetch failed"]
            )

        # --- STAGE 5: Commit DTO ---
        return ContentDocument(
            url=url,
            canonical_url=final_norm_doc.canonical_url,
            content_hash=compute_content_hash(final_norm_doc.markdown_content),
            markdown_content=final_norm_doc.markdown_content,
            metadata=final_norm_doc.metadata,
            provider_raw_payload=final_norm_doc.provider_raw_payload,
            quality_metrics=final_quality,
            fetch_metadata=final_norm_doc.fetch_metadata,
            plugin_versions=plugin_versions,
            outcome=outcome,
            retryable=retryable,
        )
