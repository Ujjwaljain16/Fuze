"""A later server fetch must not replace what the extension captured with something worse."""
from unittest.mock import patch

import pytest

from tests.test_captured_content import ARTICLE_WORDS, _bookmark, _url, no_queue  # noqa: F401 (fixture)


def _fetched(text, outcome='ok', challenge=False, retryable=False):
    from scrapers.models import ContentDocument, FetchMetadata, NormalizedMetadata, QualityMetrics, compute_content_hash
    return ContentDocument(
        url='https://example.com', canonical_url='https://example.com', content_hash=compute_content_hash(text),
        markdown_content=text, metadata=NormalizedMetadata(title='Fetched'), provider_raw_payload={},
        quality_metrics=QualityMetrics(score=10 if challenge else 80, has_title=True, has_article_body=True,
                                       word_count=len(text.split()), hydration_detected=False,
                                       challenge_detected=challenge),
        fetch_metadata=FetchMetadata(strategy='HTTP', attempts=1, http_status=200 if outcome == 'ok' else 503,
                                     redirected=False),
        outcome=outcome, retryable=retryable,
    )


@pytest.fixture
def captured_bookmark(app, client, auth_headers, no_queue):  # noqa: F811 -- fixture imported above
    resp = client.post('/api/bookmarks', headers=auth_headers, json={
        'url': _url(), 'title': 'Members only', 'captured': {'text': ARTICLE_WORDS},
    })
    assert resp.status_code == 201
    return _bookmark(app, resp.json['bookmark']['id'])


def _run_fetch(app, bookmark, fetched):
    from services.bookmark_processing_service import process_bookmark_content_task
    with patch('services.bookmark_processing_service.extract_article_content', return_value=fetched), \
         patch('services.pipeline_orchestrator.PipelineOrchestrator.request_embedding', return_value=True):
        with app.app_context():
            process_bookmark_content_task(bookmark.id, bookmark.url, bookmark.user_id)
    return _bookmark(app, bookmark.id)


@pytest.mark.parametrize('fetched', [
    _fetched('Please sign in to continue reading.'),
    _fetched(' '.join(['word'] * 400), challenge=True),
    _fetched(' '.join(['word'] * 400)),  # more words, but not clearly more
])
def test_worse_server_fetch_keeps_the_capture(app, captured_bookmark, fetched):
    bm = _run_fetch(app, captured_bookmark, fetched)
    assert bm.extracted_text == ARTICLE_WORDS
    assert bm.strategy_used == 'EXTENSION'
    assert bm.content_hash == captured_bookmark.content_hash
    assert bm.scrape_status == 'SUCCESS'


def test_failed_server_fetch_keeps_the_capture_and_does_not_retry(app, captured_bookmark):
    # A retryable failure would normally raise TransientFetchError so RQ retries; not here.
    bm = _run_fetch(app, captured_bookmark, _fetched('', outcome='failed', retryable=True))
    assert bm.scrape_status == 'SUCCESS'
    assert bm.strategy_used == 'EXTENSION'
    assert bm.extracted_text == ARTICLE_WORDS


def test_clearly_better_server_fetch_replaces_the_capture(app, captured_bookmark):
    full = ' '.join(f'full{i}' for i in range(2000))
    bm = _run_fetch(app, captured_bookmark, _fetched(full))
    assert bm.extracted_text == full
    assert bm.strategy_used == 'HTTP'
