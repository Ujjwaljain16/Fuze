from unittest.mock import MagicMock, patch

import pytest
import requests

from scrapers import source_adapters as sa


def _resp(json_data=None, text="", content=b""):
    r = MagicMock()
    r.json.return_value = json_data
    r.text = text
    r.content = content
    return r


@pytest.mark.parametrize("url,expected", [
    ("https://github.com/psf/requests", sa.github),
    ("https://www.github.com/psf/requests/issues/1", sa.github),
    ("https://arxiv.org/abs/1706.03762", sa.arxiv),
    ("https://en.wikipedia.org/wiki/Vector_database", sa.wikipedia),
    ("https://stackoverflow.com/questions/231767/what-does-yield-do", sa.stackexchange),
    ("https://unix.stackexchange.com/questions/1/x", sa.stackexchange),
    ("https://dev.to/user/my-post-1a2b", sa.devto),
    ("https://news.ycombinator.com/item?id=8863", sa.hackernews),
    ("https://example.com/blog/post", None),
])
def test_routing(url, expected):
    assert sa.adapter_for(url) is expected


def test_github_repo_uses_description_and_readme():
    calls = {
        "https://api.github.com/repos/psf/requests": _resp({"full_name": "psf/requests", "description": "HTTP for Humans",
                                                            "topics": ["http"], "owner": {"login": "psf"},
                                                            "html_url": "https://github.com/psf/requests"}),
        "https://api.github.com/repos/psf/requests/readme": _resp(text="# Requests\nSend HTTP requests easily."),
    }
    with patch.object(sa, "_get", side_effect=lambda url, **kw: calls[url]):
        c = sa.fetch_from_source("https://github.com/psf/requests")
    assert c.source == "github" and c.title == "psf/requests"
    assert c.text.startswith("HTTP for Humans") and "Send HTTP requests easily." in c.text
    assert c.keywords == ["http"]


def test_github_reserved_paths_fall_back():
    assert sa.github("https://github.com/settings/profile") is None


def test_arxiv_parses_atom_feed():
    feed = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry>
      <title>Attention Is
       All You Need</title><summary> The dominant sequence transduction models...</summary>
      <published>2017-06-12T17:57:34Z</published><author><name>Ashish Vaswani</name></author>
    </entry></feed>"""
    with patch.object(sa, "_get", return_value=_resp(content=feed)):
        c = sa.fetch_from_source("https://arxiv.org/pdf/1706.03762v7.pdf")
    assert c.title == "Attention Is All You Need"
    assert c.text.startswith("The dominant sequence") and c.author == "Ashish Vaswani"
    assert c.canonical_url == "https://arxiv.org/abs/1706.03762"


def test_wikipedia_skips_special_pages_and_missing():
    assert sa.wikipedia("https://en.wikipedia.org/wiki/Special:Random") is None
    with patch.object(sa, "_get", return_value=_resp({"query": {"pages": [{"missing": True}]}})):
        assert sa.fetch_from_source("https://en.wikipedia.org/wiki/Nope_nope") is None


def test_stackexchange_orders_accepted_answer_first():
    q = {"items": [{"title": "What does &quot;yield&quot; do?", "body": "<p>Explain yield.</p>",
                    "tags": ["python"], "link": "https://stackoverflow.com/q/231767", "owner": {"display_name": "A"}}]}
    answers = {"items": [{"body": "<p>High score.</p>", "score": 50, "is_accepted": False},
                         {"body": "<p>Accepted one.</p>", "score": 10, "is_accepted": True}]}
    with patch.object(sa, "_get", side_effect=[_resp(q), _resp(answers)]):
        c = sa.fetch_from_source("https://stackoverflow.com/questions/231767/what-does-yield-do")
    assert c.title == 'What does "yield" do?'
    assert c.text.index("Accepted answer") < c.text.index("Answer (50 votes)")
    assert "Explain yield." in c.text and c.keywords == ["python"]


def test_hackernews_story_with_link():
    item = {"type": "story", "title": "Show HN: X", "by": "pg", "url": "https://x.dev", "score": 10}
    with patch.object(sa, "_get", return_value=_resp(item)):
        c = sa.fetch_from_source("https://news.ycombinator.com/item?id=8863")
    assert c.title == "Show HN: X" and "Link: https://x.dev" in c.text


def test_api_errors_fall_back_to_page_extraction():
    with patch.object(sa, "_get", side_effect=requests.HTTPError("403 rate limited")):
        assert sa.fetch_from_source("https://github.com/psf/requests") is None


def test_acquisition_engine_prefers_source_api():
    from scrapers.acquisition_engine import ContentAcquisitionEngine
    content = sa.SourceContent("arxiv", "Attention Is All You Need", "The dominant sequence transduction models " * 40,
                               author="Ashish Vaswani", canonical_url="https://arxiv.org/abs/1706.03762")
    engine = ContentAcquisitionEngine()
    with patch("scrapers.acquisition_engine.is_safe_url", return_value=True), \
         patch("scrapers.source_adapters.fetch_from_source", return_value=content), \
         patch.object(engine.fetchers["HTTP"], "fetch") as http_fetch:
        doc = engine.acquire_and_normalize("https://arxiv.org/abs/1706.03762")
    http_fetch.assert_not_called()
    assert doc.fetch_metadata.strategy == "API:arxiv"
    assert doc.metadata.title == "Attention Is All You Need" and doc.metadata.author == "Ashish Vaswani"
    assert doc.markdown_content.startswith("The dominant sequence")


def test_link_posts_store_the_linked_article():
    from scrapers.acquisition_engine import ContentAcquisitionEngine
    from scrapers.models import FetchMetadata, RawFetchResult
    hn = sa.SourceContent("hackernews", "Show HN: Vector search in Postgres", "Link: https://example.com/post",
                          raw={"id": 1}, follow_url="https://example.com/post")
    article = " ".join(["pgvector adds approximate nearest neighbour search to Postgres with HNSW indexes."] * 15)
    html = f"<html><body><nav>Home Pricing</nav><article><h1>Postgres vectors</h1><p>{article}</p></article></body></html>"
    meta = FetchMetadata(strategy="HTTP", attempts=1, http_status=200, redirected=False)
    page = RawFetchResult(url="https://example.com/post", final_url="https://example.com/post", http_status=200,
                          headers={}, raw_content=html.encode(), fetch_metadata=meta)
    engine = ContentAcquisitionEngine()
    with patch("scrapers.acquisition_engine.is_safe_url", return_value=True), \
         patch("scrapers.rate_limiter.DomainRateLimiter.acquire", return_value=(True, 0.0)), \
         patch("scrapers.robots_manager.RobotsManager.can_fetch", return_value=True), \
         patch("core.circuit_breaker.RedisCircuitBreaker.allow_request", return_value=True), \
         patch("scrapers.source_adapters.fetch_from_source", side_effect=lambda u: hn if "ycombinator" in u else None), \
         patch.object(engine.fetchers["HTTP"], "fetch", return_value=page):
        doc = engine.acquire_and_normalize("https://news.ycombinator.com/item?id=1")
    assert doc.metadata.title == "Show HN: Vector search in Postgres"
    assert "nearest neighbour search" in doc.markdown_content and "Link:" not in doc.markdown_content
    assert doc.url == "https://news.ycombinator.com/item?id=1"


def test_clean_body_drops_badges_html_and_layout_pipes():
    from scrapers.text_cleanup import clean_body
    raw = "| | |\n# Requests\n[![Version](https://img.shields.io/x.svg)](https://pypi.org)\n<p align=\"center\">Fast</p>\n\n\n\nBody"
    assert clean_body(raw) == "# Requests\n\nFast\n\nBody"
