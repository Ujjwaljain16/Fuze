"""
Content Acquisition Engine (5-Stage Architecture)
Single-responsibility engine that reliably acquires, parses, quality-evaluates, and normalizes web content
into an immutable ContentDocument DTO.
"""

from urllib.parse import urlparse
from typing import Dict, Optional, Tuple
from scrapers.cache_manager import CacheManager
from scrapers.robots_manager import RobotsManager
from scrapers.rate_limiter import DomainRateLimiter
from scrapers.fetch_policy import FetchPolicy
from scrapers.fetchers.http_fetcher import HTTPFetcher
from scrapers.fetchers.stealth_fetcher import StealthFetcher
from scrapers.fetchers.dynamic_fetcher import DynamicFetcher
from scrapers.extractor_pipeline import ExtractorPipeline
from scrapers.normalizer import MetadataNormalizer
from scrapers.quality_evaluator import QualityEvaluator
from scrapers.decision_engine import DecisionEngine
from scrapers.event_publisher import ScrapingEventPublisher
from scrapers.models import ContentDocument, RawFetchResult, ParsedDocument, NormalizedDocument, Decision, compute_content_hash
from core.circuit_breaker import RedisCircuitBreaker
from core.events import (
    FetchStarted, FetchCompleted, ParsingStarted, ParsingCompleted, NormalizationCompleted
)
from core.logging_config import get_logger

logger = get_logger(__name__)


class ContentAcquisitionEngine:
    """
    Production-grade 5-Stage Content Acquisition Engine.
    """
    def __init__(self):
        self.cache_manager = CacheManager()
        self.robots_manager = RobotsManager()
        self.rate_limiter = DomainRateLimiter()
        self.fetch_policy = FetchPolicy()

        self.fetchers = {
            "HTTP": HTTPFetcher(),
            "STEALTH": StealthFetcher(),
            "DYNAMIC": DynamicFetcher()
        }

        self.extractor_pipeline = ExtractorPipeline()
        self.normalizer = MetadataNormalizer()
        self.quality_evaluator = QualityEvaluator()
        self.decision_engine = DecisionEngine()
        self.event_publisher = ScrapingEventPublisher()

    def acquire_and_normalize(self, url: str, bookmark_id: Optional[int] = None) -> ContentDocument:
        """
        Execute 5-stage acquisition & normalization pipeline on target URL.
        """
        # --- STAGE 1: Acquisition Manager (Cache, Robots, Rate Limit, Circuit Breaker, Policy) ---
        cached_html = self.cache_manager.get_raw_html_cache(url)

        if not self.robots_manager.can_fetch(url):
            logger.warning("acquisition_blocked_by_robots", extra={"url": url})

        allowed, wait_time = self.rate_limiter.acquire(url)
        if not allowed:
            logger.warning("acquisition_rate_limited", extra={"url": url, "wait_time": wait_time})

        domain = urlparse(url).netloc.lower()
        circuit_breaker = RedisCircuitBreaker(name=f"domain_{domain}", failure_threshold=5, recovery_timeout=300)

        strategy_plan = self.fetch_policy.get_strategy_plan(url)
        
        raw_result: Optional[RawFetchResult] = None
        decision: Optional[Decision] = None
        final_norm_doc: Optional[NormalizedDocument] = None
        plugin_versions: Dict[str, str] = {}

        # --- STAGE 2: Adaptive Fetch Loop & STAGE 3: Extraction & STAGE 4: Quality Evaluation ---
        for strategy in strategy_plan:
            fetcher = self.fetchers.get(strategy, self.fetchers["HTTP"])
            
            if not circuit_breaker.allow_request():
                logger.error("circuit_breaker_open_skipping_fetch", extra={"url": url, "strategy": strategy})
                continue

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
            except Exception as fetch_err:
                circuit_breaker.record_failure()
                self.fetch_policy.record_failure(url, strategy)
                logger.error("fetcher_exception", extra={"url": url, "strategy": strategy, "error": str(fetch_err)})
                continue

            if bookmark_id and raw_result:
                self.event_publisher.publish(
                    FetchCompleted(
                        bookmark_id=bookmark_id,
                        strategy=strategy,
                        http_status=raw_result.http_status,
                        latency_ms=raw_result.fetch_metadata.fetch_latency_ms
                    )
                )

            if not raw_result or not raw_result.raw_content:
                continue

            # Stage 3: Extraction
            if bookmark_id:
                self.event_publisher.publish(ParsingStarted(bookmark_id=bookmark_id, plugins_count=len(self.extractor_pipeline.plugins)))

            parsed_doc = self.extractor_pipeline.process(raw_result)

            # Record plugin versions
            for res in parsed_doc.plugin_results:
                plugin_versions[res.plugin_name] = res.plugin_version

            if bookmark_id:
                succeeded = sum(1 for r in parsed_doc.plugin_results if r.success)
                self.event_publisher.publish(ParsingCompleted(bookmark_id=bookmark_id, plugins_succeeded=succeeded))

            # Stage 4: Normalization
            norm_doc = self.normalizer.normalize(parsed_doc)

            # Stage 4: Quality Evaluation & Decision Engine
            quality_metrics = self.quality_evaluator.evaluate(
                html=parsed_doc.raw_html,
                clean_text=parsed_doc.clean_text,
                title=norm_doc.metadata.title
            )

            decision = self.decision_engine.evaluate(quality_metrics, strategy)

            content_hash = compute_content_hash(norm_doc.markdown_content)
            if bookmark_id:
                self.event_publisher.publish(
                    NormalizationCompleted(bookmark_id=bookmark_id, content_hash=content_hash, quality_score=quality_metrics.score)
                )

            final_norm_doc = norm_doc
            final_quality = quality_metrics

            if decision.action == "ACCEPT":
                logger.info("acquisition_decision_accepted", extra={"url": url, "strategy": strategy, "score": quality_metrics.score})
                break
            elif decision.action == "ESCALATE":
                logger.info("acquisition_decision_escalating", extra={"url": url, "reason": decision.reason, "next": decision.next_strategy})
                continue
            elif decision.action == "FAIL":
                logger.warning("acquisition_decision_failed", extra={"url": url, "reason": decision.reason})
                break

        # Fallback if no fetch result produced
        if not final_norm_doc or not raw_result:
            from scrapers.models import FetchMetadata, NormalizedMetadata, QualityMetrics
            meta = FetchMetadata(strategy="HTTP", attempts=1, http_status=500, redirected=False)
            norm_meta = NormalizedMetadata(title="Failed to Acquire Content")
            final_norm_doc = NormalizedDocument(
                url=url,
                canonical_url=url,
                markdown_content="",
                metadata=norm_meta,
                provider_raw_payload={},
                fetch_metadata=meta
            )
            final_quality = QualityMetrics(
                score=0, has_title=False, has_article_body=False, word_count=0,
                hydration_detected=False, challenge_detected=True, evaluation_notes=["Fetch failed"]
            )

        # --- STAGE 5: Commit DTO & Cache Raw HTML & Normalized Document ---
        final_hash = compute_content_hash(final_norm_doc.markdown_content)

        if raw_result and raw_result.raw_content:
            self.cache_manager.set_raw_html_cache(url, raw_result.raw_content)

        return ContentDocument(
            url=url,
            canonical_url=final_norm_doc.canonical_url,
            content_hash=final_hash,
            markdown_content=final_norm_doc.markdown_content,
            metadata=final_norm_doc.metadata,
            provider_raw_payload=final_norm_doc.provider_raw_payload,
            quality_metrics=final_quality,
            fetch_metadata=final_norm_doc.fetch_metadata,
            plugin_versions=plugin_versions
        )
