"""Escalation tiers after our own fetch: the remote reader. All network calls are mocked."""
from contextlib import ExitStack
from unittest.mock import patch

import pytest
import requests

from scrapers.fetchers import reader_fetcher as rf
from scrapers.fetchers.reader_fetcher import ReaderFetcher, ReaderResult
from scrapers.models import FetchMetadata, RawFetchResult
from scrapers.safe_http import SafeResponse
from scrapers.url_safety import is_shareable_with_third_party

ARTICLE = " ".join(["Vector indexes trade a little recall for a lot of speed on large embedding sets."] * 30)
JS_SHELL = b'<html><head><title>App</title></head><body><div id="root"></div><script>window.__NEXT_DATA__={}</script></body></html>'
CHALLENGE = b"<html><head><title>Just a moment...</title></head><body>Checking your browser before accessing</body></html>"


def _page(body: bytes, status: int = 200, url: str = "https://example.com/post") -> RawFetchResult:
    meta = FetchMetadata(strategy="HTTP", attempts=1, http_status=status, redirected=False)
    return RawFetchResult(url=url, final_url=url, http_status=status, headers={}, raw_content=body, fetch_metadata=meta)


def _reader_ok(content=ARTICLE, title="Vector indexes", **kw) -> ReaderResult:
    return ReaderResult(ok=True, content=content, title=title, final_url="https://example.com/post",
                        http_status=200, **kw)


@pytest.fixture
def tiers_on(monkeypatch):
    monkeypatch.setenv("ENABLE_READER_FALLBACK", "true")


def _engine(stack: ExitStack, http_page: RawFetchResult, reader_result=None, robots_ok=True):
    from scrapers.acquisition_engine import ContentAcquisitionEngine
    engine = ContentAcquisitionEngine()
    stack.enter_context(patch("scrapers.acquisition_engine.is_safe_url", return_value=True))
    stack.enter_context(patch("scrapers.source_adapters.fetch_from_source", return_value=None))
    stack.enter_context(patch.object(engine.robots_manager, "can_fetch", return_value=robots_ok))
    stack.enter_context(patch("scrapers.rate_limiter.DomainRateLimiter.acquire", return_value=(True, 0.0)))
    stack.enter_context(patch("core.circuit_breaker.RedisCircuitBreaker.allow_request", return_value=True))
    stack.enter_context(patch.object(engine.fetchers["HTTP"], "fetch", return_value=http_page))
    reader = stack.enter_context(patch.object(engine.reader, "fetch", return_value=reader_result or _reader_ok()))
    return engine, reader


# --- what may be sent to a third party ------------------------------------------------------

@pytest.mark.parametrize("url,shareable", [
    ("https://example.com/post?utm_source=x&page=2", True),
    ("https://example.com/post?author=jane&design=dark", True),
    ("https://bucket.s3.amazonaws.com/f.pdf?X-Amz-Signature=abc&X-Amz-Credential=k", False),
    ("https://example.com/reset?token=abc", False),
    ("https://docs.example.com/d/1?key=abc", False),
    ("https://example.com/share?access_token=abc", False),
    ("https://example.com/cb?code=abc", False),
    ("https://user:pw@example.com/", False),
    ("ftp://example.com/file", False),
])
def test_only_urls_without_secrets_are_shared(url, shareable):
    assert is_shareable_with_third_party(url) is shareable


# --- the reader fetcher ---------------------------------------------------------------------

def _json_response(payload, status=200):
    import json
    return SafeResponse(url="https://r.jina.ai/x", status_code=status,
                        headers={"Content-Type": "application/json"}, content=json.dumps(payload).encode())


@pytest.fixture
def public_url():
    with patch("scrapers.url_safety.is_safe_url", return_value=True):
        yield


def test_reader_sends_only_the_url_with_privacy_headers(public_url, monkeypatch):
    monkeypatch.setenv("READER_API_KEY", "test-reader-key")
    payload = {"code": 200, "data": {"title": "Post", "content": ARTICLE, "url": "https://example.com/post",
                                     "httpStatus": 200, "publishedTime": "2026-01-02",
                                     "metadata": {"author": "Jane", "og:image": "https://example.com/i.png"}}}
    with patch.object(rf, "safe_get", return_value=_json_response(payload)) as get:
        result = ReaderFetcher().fetch("https://example.com/post?page=2#comments")
    assert result.ok and result.title == "Post" and result.author == "Jane" and result.published_at == "2026-01-02"
    url = get.call_args.args[0]
    assert url == "https://r.jina.ai/https://example.com/post?page=2"  # no fragment
    headers = get.call_args.kwargs["headers"]
    assert headers["X-No-Cache"] == "true" and headers["DNT"] == "1" and headers["X-Robots-Txt"] == "FuzeBot"
    assert headers["Authorization"] == "Bearer test-reader-key"
    assert get.call_args.kwargs["max_bytes"] == rf.MAX_READER_BYTES
    assert get.call_args.kwargs["timeout"] == rf.DEFAULT_TIMEOUT_SECONDS


def test_reader_never_sees_internal_or_secret_urls():
    with patch.object(rf, "safe_get") as get:
        # A real DNS check: localhost is internal.
        assert ReaderFetcher().fetch("http://localhost:6379/").error == "url_not_shareable"
        with patch("scrapers.url_safety.is_safe_url", return_value=True):
            assert ReaderFetcher().fetch("https://example.com/r?token=abc").error == "url_not_shareable"
    get.assert_not_called()


@pytest.mark.parametrize("side_effect,status,retryable", [
    (requests.Timeout("read timed out"), None, True),
    (requests.ConnectionError("reset"), None, True),
    (None, 429, True),
    (None, 503, True),
    (None, 402, False),  # out of balance: retrying won't help
    (None, 422, False),
])
def test_reader_failures_and_retryability(public_url, side_effect, status, retryable):
    response = None if side_effect else _json_response({"code": status, "message": "nope", "data": None}, status)
    with patch.object(rf, "safe_get", side_effect=side_effect, return_value=response):
        result = ReaderFetcher().fetch("https://example.com/post")
    assert not result.ok and result.retryable is retryable


def test_reader_reports_the_target_status(public_url):
    payload = {"code": 200, "data": {"title": "Home", "content": "fallback page", "httpStatus": 404}}
    with patch.object(rf, "safe_get", return_value=_json_response(payload)):
        result = ReaderFetcher().fetch("https://example.com/gone")
    assert not result.ok and result.http_status == 404 and not result.retryable


# --- escalation in the engine ---------------------------------------------------------------

@pytest.mark.parametrize("http_page,reason", [
    (_page(JS_SHELL), "hydration shell"),
    (_page(b"<html><head><title>Hi</title></head><body><p>Loading...</p></body></html>"), "thin"),
    (_page(CHALLENGE), "challenge page"),
    (_page(CHALLENGE, status=403), "challenge served as 403"),
    (_page(b"Forbidden", status=403), "bot UA refused"),
])
def test_reader_recovers_pages_our_fetch_could_not(tiers_on, http_page, reason):
    with ExitStack() as stack:
        engine, reader = _engine(stack, http_page)
        doc = engine.acquire_and_normalize("https://example.com/post")
    reader.assert_called_once_with("https://example.com/post")
    assert doc.outcome == "ok", reason
    assert doc.fetch_metadata.strategy == "READER"
    assert doc.metadata.field_provenance["body"] == "READER" and doc.metadata.field_provenance["title"] == "READER"
    assert "Vector indexes trade" in doc.markdown_content
    assert doc.provider_raw_payload["reader"]["service"] == "jina"


def test_good_pages_never_reach_the_reader(tiers_on):
    html = f"<html><head><title>Post</title></head><body><article><h1>Post</h1><p>{ARTICLE}</p></article></body></html>"
    with ExitStack() as stack:
        engine, reader = _engine(stack, _page(html.encode()))
        doc = engine.acquire_and_normalize("https://example.com/post")
    reader.assert_not_called()
    assert doc.outcome == "ok" and doc.fetch_metadata.strategy == "HTTP"


@pytest.mark.parametrize("status", [404, 410, 500, 503, 429])
def test_gone_and_erroring_pages_skip_the_reader(tiers_on, status):
    with ExitStack() as stack:
        engine, reader = _engine(stack, _page(b"<html><body>Error</body></html>", status=status))
        doc = engine.acquire_and_normalize("https://example.com/post")
    reader.assert_not_called()
    assert doc.outcome == "failed" and doc.retryable is (status >= 500 or status == 429)


def test_robots_disallow_is_not_bypassed_by_the_reader(tiers_on):
    with ExitStack() as stack:
        engine, reader = _engine(stack, _page(JS_SHELL), robots_ok=False)
        doc = engine.acquire_and_normalize("https://example.com/post")
    reader.assert_not_called()
    assert doc.outcome == "disallowed"


def test_unsafe_urls_never_reach_the_reader(tiers_on):
    from scrapers.acquisition_engine import ContentAcquisitionEngine
    engine = ContentAcquisitionEngine()
    with patch.object(engine.reader, "fetch") as reader, patch.object(engine.fetchers["HTTP"], "fetch") as http:
        doc = engine.acquire_and_normalize("http://169.254.169.254/latest/meta-data/")
    reader.assert_not_called()
    http.assert_not_called()
    assert doc.outcome == "failed"


def test_reader_timeout_on_a_blocked_page_is_retryable(tiers_on):
    timeout = ReaderResult(ok=False, retryable=True, error="reader_timeout")
    with ExitStack() as stack:
        engine, _ = _engine(stack, _page(CHALLENGE), reader_result=timeout)
        doc = engine.acquire_and_normalize("https://example.com/post")
    assert doc.outcome == "blocked" and doc.retryable is True


def test_reader_timeout_on_a_403_is_retryable(tiers_on):
    timeout = ReaderResult(ok=False, retryable=True, error="reader_timeout")
    with ExitStack() as stack:
        engine, _ = _engine(stack, _page(b"Forbidden", status=403), reader_result=timeout)
        doc = engine.acquire_and_normalize("https://example.com/post")
    assert doc.outcome == "failed" and doc.retryable is True


def test_reader_refusal_keeps_the_original_verdict(tiers_on):
    refused = ReaderResult(ok=False, http_status=403, error="target_http_403")
    with ExitStack() as stack:
        engine, _ = _engine(stack, _page(b"Forbidden", status=403), reader_result=refused)
        doc = engine.acquire_and_normalize("https://example.com/post")
    assert doc.outcome == "failed" and doc.retryable is False and doc.fetch_metadata.http_status == 403


def test_thin_page_is_kept_when_the_reader_fails(tiers_on):
    thin = b"<html><head><title>Short note</title></head><body><p>Just a short note here.</p></body></html>"
    with ExitStack() as stack:
        engine, reader = _engine(stack, _page(thin), reader_result=ReaderResult(ok=False, retryable=True))
        doc = engine.acquire_and_normalize("https://example.com/post")
    reader.assert_called_once()
    # As before the tiers existed: the thin page is stored rather than failing the bookmark.
    assert doc.outcome == "ok" and doc.fetch_metadata.strategy == "HTTP" and "short note" in doc.markdown_content


def test_reader_challenge_page_is_blocked(tiers_on):
    challenge = _reader_ok(content="Checking your browser before accessing example.com", title="Just a moment...")
    with ExitStack() as stack:
        engine, _ = _engine(stack, _page(b"Forbidden", status=403), reader_result=challenge)
        doc = engine.acquire_and_normalize("https://example.com/post")
    assert doc.outcome == "blocked" and doc.retryable is False


def test_reader_is_rate_limited_by_us(tiers_on):
    with ExitStack() as stack:
        engine, reader = _engine(stack, _page(b"Forbidden", status=403))
        limited = {"https://reader-quota.invalid/": (False, 30.0)}
        # A MagicMock on the class is not bound, so it is called with the URL alone.
        stack.enter_context(patch("scrapers.rate_limiter.DomainRateLimiter.acquire",
                                  side_effect=lambda u: limited.get(u, (True, 0.0))))
        doc = engine.acquire_and_normalize("https://example.com/post")
    reader.assert_not_called()
    assert doc.outcome == "failed" and doc.retryable is True


def test_tiers_disabled_keeps_plain_http_behaviour(monkeypatch):
    monkeypatch.setenv("ENABLE_READER_FALLBACK", "false")
    from scrapers.fetch_policy import FetchPolicy
    assert FetchPolicy().get_strategy_plan("https://example.com/") == ["HTTP"]
    with ExitStack() as stack:
        engine, reader = _engine(stack, _page(CHALLENGE))
        doc = engine.acquire_and_normalize("https://example.com/post")
    reader.assert_not_called()
    assert doc.outcome == "blocked" and doc.retryable is False


def test_reader_is_on_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_READER_FALLBACK", raising=False)
    from scrapers.fetch_policy import FetchPolicy
    assert FetchPolicy().get_strategy_plan("https://example.com/")[:2] == ["HTTP", "READER"]
