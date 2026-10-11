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
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", sa.youtube),
    ("https://youtu.be/dQw4w9WgXcQ", sa.youtube),
    ("https://www.reddit.com/r/Python/comments/abc123/title/", sa.reddit),
    ("https://medium.com/@jane/a-story-516d5a29b252", sa.medium),
    ("https://jane.medium.com/a-story-516d5a29b252", sa.medium),
    ("https://x.com/jack/status/20", sa.twitter),
    ("https://twitter.com/jack/status/20", sa.twitter),
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


YT_OEMBED = {"title": "Never Gonna Give You Up", "author_name": "Rick Astley",
             "author_url": "https://www.youtube.com/@RickAstleyYT",
             "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"}
YT_PAGE = """<html><head><meta name="description" content="Short meta description.">
<script type="application/ld+json">{"@context": "https://schema.org", "@type": "VideoObject",
 "name": "Never Gonna Give You Up", "uploadDate": "2009-10-24T23:57:33-07:00",
 "description": "The official video, remastered in 4K."}</script></head><body></body></html>"""


@pytest.mark.parametrize("url", [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s",
    "https://youtu.be/dQw4w9WgXcQ?si=abc",
    "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/shorts/dQw4w9WgXcQ",
])
def test_youtube_uses_oembed_and_the_pages_json_ld(url):
    calls = []

    def fake_get(u, params=None, accept=None):
        calls.append((u, params))
        return _resp(YT_OEMBED) if u.endswith("/oembed") else _resp(text=YT_PAGE)

    with patch.object(sa, "_get", side_effect=fake_get), \
         patch("scrapers.robots_manager.RobotsManager.can_fetch", return_value=True):
        c = sa.fetch_from_source(url)
    assert sa.adapter_for(url) is sa.youtube
    assert calls[0] == ("https://www.youtube.com/oembed",
                        {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "json"})
    assert c.source == "youtube" and c.title == "Never Gonna Give You Up" and c.author == "Rick Astley"
    assert c.text == "The official video, remastered in 4K." and c.published_at.startswith("2009-10-24")
    assert c.canonical_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert c.raw["thumbnail_url"].endswith("hqdefault.jpg")


def test_youtube_falls_back_to_the_meta_description():
    page = '<html><head><meta name="description" content="Short meta description."></head></html>'
    with patch.object(sa, "_get", side_effect=lambda u, **kw: _resp(YT_OEMBED) if u.endswith("/oembed")
                      else _resp(text=page)), \
         patch("scrapers.robots_manager.RobotsManager.can_fetch", return_value=True):
        c = sa.fetch_from_source("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert c.text == "Short meta description."


def test_youtube_skips_the_page_when_robots_disallow_it():
    with patch.object(sa, "_get", return_value=_resp(YT_OEMBED)) as get, \
         patch("scrapers.robots_manager.RobotsManager.can_fetch", return_value=False):
        c = sa.fetch_from_source("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert get.call_count == 1  # oEmbed only
    assert c.title == "Never Gonna Give You Up" and c.text == "YouTube video by Rick Astley: Never Gonna Give You Up"


def test_youtube_page_errors_still_return_oembed_data():
    def fake_get(u, **kw):
        if u.endswith("/oembed"):
            return _resp(YT_OEMBED)
        raise requests.HTTPError("429")
    with patch.object(sa, "_get", side_effect=fake_get), \
         patch("scrapers.robots_manager.RobotsManager.can_fetch", return_value=True):
        c = sa.fetch_from_source("https://youtu.be/dQw4w9WgXcQ")
    assert c.author == "Rick Astley" and c.description is None


@pytest.mark.parametrize("url", ["https://www.youtube.com/@RickAstleyYT", "https://www.youtube.com/watch?v=short",
                                 "https://www.youtube.com/playlist?list=PL123"])
def test_youtube_non_video_urls_fall_back(url):
    with patch.object(sa, "_get") as get:
        assert sa.fetch_from_source(url) is None
    get.assert_not_called()


def test_youtube_oembed_error_falls_back():
    with patch.object(sa, "_get", side_effect=requests.HTTPError("401 embedding disabled")):
        assert sa.fetch_from_source("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is None


REDDIT_LISTING = [
    {"kind": "Listing", "data": {"children": [{"kind": "t3", "data": {
        "title": "Why is asyncio so hard?", "selftext": "I keep mixing threads and tasks.", "is_self": True,
        "author": "pyuser", "subreddit": "Python", "created_utc": 1700000000, "score": 120, "num_comments": 3,
        "permalink": "/r/Python/comments/abc123/why_is_asyncio_so_hard/"}}]}},
    {"kind": "Listing", "data": {"children": [
        {"kind": "t1", "data": {"author": "helper", "body": "Use asyncio.run once.", "score": 50}},
        {"kind": "t1", "data": {"author": "x", "body": "[deleted]", "score": 90}},
        {"kind": "t1", "data": {"author": "top", "body": "Read the docs on task groups.", "score": 80}},
        {"kind": "more", "data": {"children": ["def456"]}},
    ]}},
]


@pytest.mark.parametrize("url", [
    "https://www.reddit.com/r/Python/comments/abc123/why_is_asyncio_so_hard/",
    "https://old.reddit.com/r/Python/comments/abc123/",
    "https://reddit.com/r/Python/comments/abc123",
])
def test_reddit_reads_the_json_listing(url):
    with patch.object(sa, "_get", return_value=_resp(REDDIT_LISTING)) as get:
        c = sa.fetch_from_source(url)
    assert sa.adapter_for(url) is sa.reddit
    assert get.call_args.args[0] == "https://www.reddit.com/r/Python/comments/abc123.json"
    assert c.source == "reddit" and c.title == "Why is asyncio so hard?" and c.author == "pyuser"
    assert c.text.startswith("I keep mixing threads and tasks.")
    assert c.text.index("task groups") < c.text.index("asyncio.run once") and "[deleted]" not in c.text
    assert c.published_at.startswith("2023-11-14") and c.keywords == ["Python"] and c.follow_url is None
    assert c.canonical_url == "https://www.reddit.com/r/Python/comments/abc123/why_is_asyncio_so_hard/"


def test_reddit_link_post_follows_the_link():
    listing = [{"data": {"children": [{"data": {**REDDIT_LISTING[0]["data"]["children"][0]["data"],
                                                "is_self": False, "selftext": "",
                                                "url": "https://blog.example.com/asyncio"}}]}},
               {"data": {"children": []}}]
    with patch.object(sa, "_get", return_value=_resp(listing)):
        c = sa.fetch_from_source("https://www.reddit.com/r/Python/comments/abc123/")
    assert c.follow_url == "https://blog.example.com/asyncio" and "Link: https://blog.example.com/asyncio" in c.text


def test_reddit_refused_json_falls_back_to_oembed():
    oembed = {"title": "Why is asyncio so hard?", "author_name": "pyuser", "provider_name": "reddit"}

    def fake_get(u, **kw):
        if u.endswith(".json"):
            raise requests.HTTPError("403 Blocked")
        assert u == "https://www.reddit.com/oembed"
        assert kw["params"] == {"url": "https://www.reddit.com/r/Python/comments/abc123/"}
        return _resp(oembed)

    with patch.object(sa, "_get", side_effect=fake_get):
        c = sa.fetch_from_source("https://www.reddit.com/r/Python/comments/abc123/why/")
    assert c.title == "Why is asyncio so hard?" and c.author == "pyuser"
    assert c.text == "Reddit post in r/Python by u/pyuser: Why is asyncio so hard?" and c.raw["via"] == "oembed"


def test_reddit_unexpected_shape_falls_back():
    with patch.object(sa, "_get", return_value=_resp({"error": 404})):
        assert sa.fetch_from_source("https://www.reddit.com/r/Python/comments/abc123/") is None


@pytest.mark.parametrize("url", ["https://www.reddit.com/r/Python/", "https://www.reddit.com/user/pyuser"])
def test_reddit_listing_pages_fall_back(url):
    with patch.object(sa, "_get") as get:
        assert sa.fetch_from_source(url) is None
    get.assert_not_called()


MEDIUM_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">
<channel><title>Stories by Jane on Medium</title>
<item><title><![CDATA[Another story]]></title><link>https://medium.com/@jane/another-story-111111111111?source=rss</link>
<guid isPermaLink="false">https://medium.com/p/111111111111</guid><content:encoded><![CDATA[<p>Other.</p>]]></content:encoded></item>
<item><title><![CDATA[Vector search in Postgres]]></title>
<link>https://medium.com/@jane/vector-search-in-postgres-516d5a29b252?source=rss-abc</link>
<guid isPermaLink="false">https://medium.com/p/516d5a29b252</guid>
<category><![CDATA[postgres]]></category><category><![CDATA[ai]]></category>
<dc:creator><![CDATA[Jane Doe]]></dc:creator><pubDate>Fri, 25 Sep 2026 16:01:02 GMT</pubDate>
<content:encoded><![CDATA[<h3>Why pgvector</h3><p>HNSW indexes make approximate search fast.</p>]]></content:encoded>
</item></channel></rss>"""


@pytest.mark.parametrize("url,feed", [
    ("https://medium.com/@jane/vector-search-in-postgres-516d5a29b252", "https://medium.com/feed/@jane"),
    ("https://jane.medium.com/vector-search-in-postgres-516d5a29b252?source=x", "https://medium.com/feed/@jane"),
    ("https://medium.com/better-programming/vector-search-in-postgres-516d5a29b252",
     "https://medium.com/feed/better-programming"),
])
def test_medium_reads_the_story_from_the_rss_feed(url, feed):
    with patch.object(sa, "_get", return_value=_resp(content=MEDIUM_FEED)) as get:
        c = sa.fetch_from_source(url)
    assert sa.adapter_for(url) is sa.medium
    assert get.call_args.args[0] == feed
    assert c.source == "medium" and c.title == "Vector search in Postgres" and c.author == "Jane Doe"
    assert "HNSW indexes make approximate search fast." in c.text and "Other." not in c.text
    assert c.keywords == ["postgres", "ai"] and c.published_at == "2026-09-25T16:01:02+00:00"
    assert c.canonical_url == "https://medium.com/@jane/vector-search-in-postgres-516d5a29b252"


def test_medium_story_not_in_the_feed_falls_back():
    with patch.object(sa, "_get", return_value=_resp(content=MEDIUM_FEED)):
        assert sa.fetch_from_source("https://medium.com/@jane/an-old-story-abcdef123456") is None


@pytest.mark.parametrize("url", ["https://medium.com/@jane", "https://medium.com/tag/python",
                                 "https://medium.com/p/516d5a29b252", "https://medium.com/@jane/about"])
def test_medium_non_story_urls_fall_back(url):
    with patch.object(sa, "_get") as get:
        assert sa.fetch_from_source(url) is None
    get.assert_not_called()


def test_medium_feed_errors_fall_back():
    with patch.object(sa, "_get", return_value=_resp(content=b"<html>not xml")):
        assert sa.fetch_from_source("https://medium.com/@jane/vector-search-in-postgres-516d5a29b252") is None


X_OEMBED = {
    "url": "https://twitter.com/jack/status/20", "author_name": "jack", "author_url": "https://twitter.com/jack",
    "html": '<blockquote class="twitter-tweet"><p lang="en" dir="ltr">just setting up my twttr</p>&mdash; jack '
            '(@jack) <a href="https://twitter.com/jack/status/20?ref_src=twsrc%5Etfw">March 21, 2006</a></blockquote>\n',
    "provider_name": "Twitter", "type": "rich",
}


@pytest.mark.parametrize("url", [
    "https://twitter.com/jack/status/20",
    "https://x.com/jack/status/20?s=46",
    "https://mobile.twitter.com/jack/status/20/photo/1",
])
def test_x_posts_come_from_oembed(url):
    with patch.object(sa, "_get", return_value=_resp(X_OEMBED)) as get:
        c = sa.fetch_from_source(url)
    assert sa.adapter_for(url) is sa.twitter
    assert get.call_args.args[0] == "https://publish.twitter.com/oembed"
    assert get.call_args.kwargs["params"] == {"url": "https://twitter.com/jack/status/20", "omit_script": "true",
                                              "dnt": "true"}
    assert c.source == "twitter" and c.text == "just setting up my twttr" and c.author == "jack"
    assert c.title == 'jack on X: "just setting up my twttr"' and c.published_at == "2006-03-21"
    assert c.canonical_url == "https://twitter.com/jack/status/20"


def test_x_deleted_or_protected_posts_fall_back():
    with patch.object(sa, "_get", side_effect=requests.HTTPError("404 for oembed")):
        assert sa.fetch_from_source("https://x.com/jack/status/20") is None
    with patch.object(sa, "_get", return_value=_resp({"html": ""})):
        assert sa.fetch_from_source("https://x.com/jack/status/20") is None


@pytest.mark.parametrize("url", ["https://x.com/jack", "https://x.com/home", "https://twitter.com/search?q=x"])
def test_x_non_post_urls_fall_back(url):
    with patch.object(sa, "_get") as get:
        assert sa.fetch_from_source(url) is None
    get.assert_not_called()


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


@pytest.mark.parametrize("code", [
    "Use List<String> here", "if a<b and c>d then", "Map<K, V> m", "Vec<u8>", "<T extends Comparable<T>>",
    "std::vector<int> v;",
])
def test_clean_body_keeps_code_that_looks_like_tags(code):
    from scrapers.text_cleanup import clean_body
    assert clean_body(code) == code


def test_clean_body_separates_block_tags():
    from scrapers.text_cleanup import clean_body
    assert clean_body("<details open><summary>More</summary>Body</details>") == "More\nBody"
    assert clean_body('Read <a href="https://x">the docs</a> first') == "Read the docs first"
