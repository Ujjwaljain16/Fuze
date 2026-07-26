"""
Unit & Integration Tests for 5-Stage Content Acquisition Engine & Pipeline Sub-Components.
"""

import pytest
from unittest.mock import MagicMock
from scrapers.models import (
    QualityMetrics, Decision, FetchMetadata, RawFetchResult,
    ParsedDocument, NormalizedDocument, ContentDocument, compute_content_hash
)
from scrapers.quality_evaluator import QualityEvaluator
from scrapers.decision_engine import DecisionEngine
from scrapers.fetch_policy import FetchPolicy
from scrapers.extractors.base import ExtractorPlugin
from scrapers.extractors.registry import ExtractorRegistry
from scrapers.extractors.opengraph_plugin import OpenGraphPlugin
from scrapers.extractors.jsonld_plugin import JSONLDPlugin
from scrapers.extractors.readability_plugin import ReadabilityPlugin
from scrapers.extractors.markdown_plugin import MarkdownPlugin
from scrapers.extractor_pipeline import ExtractorPipeline
from scrapers.normalizer import MetadataNormalizer
from scrapers.acquisition_engine import ContentAcquisitionEngine
from services.pipeline_orchestrator import PipelineOrchestrator
from core.events import ScrapingCompleted


def test_content_hash_computation():
    text1 = "  # Sample Article\n\nThis is a test article content.  "
    text2 = "# Sample Article\n\nThis is a test article content."
    assert compute_content_hash(text1) == compute_content_hash(text2)
    assert len(compute_content_hash(text1)) == 64


def test_quality_evaluator_multidimensional():
    html = """
    <html>
      <head><title>Clean Engineering Article</title></head>
      <body>
        <article>
          <h1>Clean Engineering Article</h1>
          <p>""" + ("This is high quality article body text with lots of detail. " * 30) + """</p>
        </article>
      </body>
    </html>
    """
    clean_text = "Clean Engineering Article " + ("This is high quality article body text with lots of detail. " * 30)
    evaluator = QualityEvaluator()
    metrics = evaluator.evaluate(html, clean_text, title="Clean Engineering Article")

    assert metrics.score >= 70
    assert metrics.content_density == 100
    assert metrics.metadata_completeness == 100
    assert metrics.structure_quality == 100
    assert metrics.has_title is True
    assert metrics.has_article_body is True
    assert metrics.challenge_detected is False


def test_quality_evaluator_cloudflare_challenge():
    html = "<html><head><title>Just a moment...</title></head><body>Checking your browser before accessing example.com</body></html>"
    evaluator = QualityEvaluator()
    metrics = evaluator.evaluate(html, "Checking your browser before accessing example.com", title="Just a moment...")

    assert metrics.score <= 10
    assert metrics.challenge_detected is True


def test_decision_engine_escalation():
    engine = DecisionEngine(quality_threshold=70)

    metrics_challenge = QualityMetrics(score=10, has_title=False, has_article_body=False, word_count=10, hydration_detected=False, challenge_detected=True)
    decision1 = engine.evaluate(metrics_challenge, current_strategy="HTTP")
    assert decision1.action == "ESCALATE"
    assert decision1.next_strategy == "STEALTH"

    decision2 = engine.evaluate(metrics_challenge, current_strategy="STEALTH")
    assert decision2.action == "ESCALATE"
    assert decision2.next_strategy == "DYNAMIC"

    metrics_high = QualityMetrics(score=95, has_title=True, has_article_body=True, word_count=500, hydration_detected=False, challenge_detected=False)
    decision3 = engine.evaluate(metrics_high, current_strategy="HTTP")
    assert decision3.action == "ACCEPT"


def test_fetch_policy_matching():
    policy = FetchPolicy()
    assert policy.get_strategy_plan("https://medium.com/@user/story") == ["STEALTH", "DYNAMIC"]
    assert policy.get_strategy_plan("https://devdocs.io/javascript") == ["DYNAMIC"]
    assert policy.get_strategy_plan("https://example.com/blog/post") == ["HTTP", "STEALTH", "DYNAMIC"]


def test_extractor_registry():
    registered_names = ExtractorRegistry.list_registered_names()
    assert "opengraph" in registered_names
    assert "json_ld" in registered_names
    assert "readability" in registered_names
    assert "markdown" in registered_names

    plugins = ExtractorRegistry.get_all_plugins()
    assert len(plugins) >= 4


def test_provenance_and_confidence_resolution():
    html = """
    <html>
      <head>
        <title>OG Title</title>
        <meta property="og:title" content="OpenGraph Title">
        <meta property="og:description" content="OpenGraph Description">
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Article",
          "headline": "Schema JSON-LD Title",
          "author": {"@type": "Person", "name": "Jane Doe"}
        }
        </script>
      </head>
      <body><main><h1>HTML Heading Title</h1><p>Body text...</p></main></body>
    </html>
    """
    pipeline = ExtractorPipeline()
    meta = FetchMetadata(strategy="HTTP", attempts=1, http_status=200, redirected=False)
    raw_res = RawFetchResult(url="https://example.com", final_url="https://example.com", http_status=200, headers={}, raw_content=html.encode('utf-8'), fetch_metadata=meta)
    
    parsed = pipeline.process(raw_res)
    normalizer = MetadataNormalizer()
    norm_doc = normalizer.normalize(parsed)

    # JSON-LD headline confidence (0.98) beats OpenGraph title (0.9)
    assert norm_doc.metadata.title == "Schema JSON-LD Title"
    assert norm_doc.metadata.field_provenance["title"] == "json_ld"
    assert norm_doc.metadata.field_confidence["title"] == 0.98
    assert norm_doc.metadata.author == "Jane Doe"
    assert norm_doc.metadata.field_provenance["author"] == "json_ld"


def test_orchestrator_backpressure():
    orchestrator = PipelineOrchestrator(max_backlog=2)
    mock_queue = MagicMock()
    mock_queue.__len__.return_value = 5  # Exceeds max_backlog 2

    orchestrator._get_queue = MagicMock(return_value=mock_queue)

    event = ScrapingCompleted(
        bookmark_id=1, user_id=10, url="https://example.com",
        content_hash="abc", quality_score=90, strategy_used="HTTP"
    )
    result = orchestrator.handle_event(event)

    # Backpressure should defer downstream enqueue
    assert result is False
    mock_queue.enqueue.assert_not_called()


def test_acquisition_engine_integration(mocker):
    from scrapers.models import RawFetchResult, FetchMetadata
    html_bytes = """
    <html>
      <head>
        <title>Integration Test Title</title>
        <meta property="og:title" content="OG Title" />
      </head>
      <body>
        <article><p>This is a high quality article body content for testing the acquisition engine pipeline integration.</p></article>
      </body>
    </html>
    """.encode('utf-8')

    mock_fetch_result = RawFetchResult(
        url="https://fuze-test.org/test-article",
        final_url="https://fuze-test.org/test-article",
        http_status=200,
        headers={"content-type": "text/html"},
        raw_content=html_bytes,
        fetch_metadata=FetchMetadata(strategy="HTTP", attempts=1, http_status=200, redirected=False, redirect_chain=[], cache_hit=False, robots_checked=True, fetch_latency_ms=45)
    )

    mocker.patch("scrapers.rate_limiter.DomainRateLimiter.acquire", return_value=(True, 0.0))
    mocker.patch("scrapers.robots_manager.RobotsManager.can_fetch", return_value=True)
    mocker.patch("core.circuit_breaker.RedisCircuitBreaker.allow_request", return_value=True)

    engine = ContentAcquisitionEngine()
    mocker.patch.object(engine.fetchers["HTTP"], "fetch", return_value=mock_fetch_result)

    doc = engine.acquire_and_normalize("https://fuze-test.org/test-article")

    assert isinstance(doc, ContentDocument)
    assert doc.url == "https://fuze-test.org/test-article"
    assert len(doc.content_hash) == 64
    assert doc.fetch_metadata.strategy in ("HTTP", "STEALTH", "DYNAMIC")
    assert "opengraph" in doc.plugin_versions
    assert "title" in doc.metadata.field_provenance
