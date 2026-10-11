from scrapers.extractor_pipeline import ExtractorPipeline
from scrapers.models import FetchMetadata, RawFetchResult

ARTICLE = " ".join(["Vector databases store embeddings and answer nearest-neighbour queries efficiently."] * 12)
HTML = f"""<html><head><title>Vector DBs explained</title></head><body>
<nav><ul><li><a href="/">Home</a></li><li><a href="/pricing">Pricing</a></li><li><a href="/login">Sign in</a></li></ul></nav>
<header><h2>Subscribe to our newsletter</h2></header>
<article><h1>Vector DBs explained</h1><p>{ARTICLE}</p><h2>HNSW</h2><p>{ARTICLE}</p></article>
<footer><h3>Company</h3><ul><li>About</li><li>Careers</li><li>Terms of service</li></ul></footer>
</body></html>"""


def _fetch(html):
    meta = FetchMetadata(strategy="HTTP", attempts=1, http_status=200, redirected=False)
    return RawFetchResult(url="https://example.com/vector-dbs", final_url="https://example.com/vector-dbs",
                          http_status=200, headers={}, raw_content=html.encode(), fetch_metadata=meta)


def test_body_is_main_content_without_navigation_or_footer():
    doc = ExtractorPipeline().process(_fetch(HTML))
    body = doc.markdown_body
    assert "nearest-neighbour queries" in body and "HNSW" in body
    for junk in ("Pricing", "Sign in", "Careers", "Terms of service", "Subscribe to our newsletter"):
        assert junk not in body, junk


def test_falls_back_when_page_has_too_little_text():
    doc = ExtractorPipeline().process(_fetch("<html><body><p>Short.</p></body></html>"))
    assert "Short." in doc.markdown_body
