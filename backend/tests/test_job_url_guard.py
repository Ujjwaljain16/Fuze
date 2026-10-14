"""A processing job always fetches the bookmark's own URL, never the one the job happens to carry."""
import uuid
from unittest.mock import patch

import pytest

from scrapers.models import (ContentDocument, FetchMetadata, NormalizedMetadata, QualityMetrics,
                             RawFetchResult, compute_content_hash)  # noqa: F401


def _failed(url):
    return ContentDocument(
        url=url, canonical_url=url, content_hash=compute_content_hash(''), markdown_content='',
        metadata=NormalizedMetadata(title='x'), provider_raw_payload={},
        quality_metrics=QualityMetrics(score=0, has_title=False, has_article_body=False, word_count=0,
                                       hydration_detected=False, challenge_detected=True),
        fetch_metadata=FetchMetadata(strategy='HTTP', attempts=1, http_status=404, redirected=False),
        outcome='failed', retryable=False)


@pytest.fixture
def bookmark(app, test_user):
    from models import db, SavedContent
    with app.app_context():
        tag = uuid.uuid4().hex[:6]
        row = SavedContent(user_id=test_user['id'], url=f'https://own.example/{tag}', title='Mine')
        db.session.add(row)
        db.session.commit()
        yield {'id': row.id, 'url': row.url}


def test_the_stored_url_wins_over_the_jobs(app, test_user, bookmark):
    from services.bookmark_processing_service import process_bookmark_content_task
    fetched = []

    def fake_extract(url):
        fetched.append(url)
        return _failed(url)

    with patch('services.bookmark_processing_service.extract_article_content', side_effect=fake_extract), \
         patch('services.pipeline_orchestrator.PipelineOrchestrator.request_embedding'), app.app_context():
        process_bookmark_content_task(bookmark['id'], 'https://neighbour.example/other-page', test_user['id'])
    assert fetched == [bookmark['url']]


def test_a_job_for_someone_elses_bookmark_does_nothing(app, test_user, bookmark):
    from services.bookmark_processing_service import process_bookmark_content_task
    with patch('services.bookmark_processing_service.extract_article_content') as extract, app.app_context():
        process_bookmark_content_task(bookmark['id'], bookmark['url'], test_user['id'] + 999)
    extract.assert_not_called()
