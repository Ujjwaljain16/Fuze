"""Failed fetches are recorded honestly, retried when that can help, and nothing stays stuck."""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from scrapers.models import (ContentDocument, FetchMetadata, NormalizedMetadata, QualityMetrics,
                             RawFetchResult, compute_content_hash)


def _failed_doc(status, retryable, outcome='failed'):
    return ContentDocument(
        url='https://example.com/a', canonical_url='https://example.com/a', content_hash=compute_content_hash(''),
        markdown_content='', metadata=NormalizedMetadata(title='Failed to Acquire Content'), provider_raw_payload={},
        quality_metrics=QualityMetrics(score=0, has_title=False, has_article_body=False, word_count=0,
                                       hydration_detected=False, challenge_detected=True),
        fetch_metadata=FetchMetadata(strategy='HTTP', attempts=1, http_status=status, redirected=False),
        outcome=outcome, retryable=retryable)


@pytest.fixture
def saved_bookmark(app, test_user):
    from models import db, SavedContent
    with app.app_context():
        bm = SavedContent(user_id=test_user['id'], url='https://example.com/a', title='My own title',
                          notes='why I saved it', extracted_text='earlier text', content_hash='earlier-hash')
        db.session.add(bm)
        db.session.commit()
        yield bm.id


def _bookmark(app, bookmark_id):
    from models import db, SavedContent
    with app.app_context():
        db.session.expire_all()
        return db.session.get(SavedContent, bookmark_id)


@pytest.mark.parametrize('status,retryable', [(503, True), (404, False)])
def test_failed_fetch_keeps_user_data_and_is_marked_failed(app, test_user, saved_bookmark, status, retryable):
    from services.bookmark_processing_service import TransientFetchError, process_bookmark_content_task
    with patch('services.bookmark_processing_service.extract_article_content', return_value=_failed_doc(status, retryable)), \
         patch('services.pipeline_orchestrator.PipelineOrchestrator.request_embedding') as request_embedding, \
         app.app_context():
        if retryable:
            with pytest.raises(TransientFetchError):  # RQ retries the job
                process_bookmark_content_task(saved_bookmark, 'https://example.com/a', test_user['id'])
        else:
            process_bookmark_content_task(saved_bookmark, 'https://example.com/a', test_user['id'])

    bm = _bookmark(app, saved_bookmark)
    assert bm.scrape_status == 'FAILED_FETCH'
    assert bm.title == 'My own title' and bm.extracted_text == 'earlier text' and bm.content_hash == 'earlier-hash'
    request_embedding.assert_called_once()  # still searchable by title/notes


def test_challenge_page_is_marked_blocked(app, test_user, saved_bookmark):
    from services.bookmark_processing_service import process_bookmark_content_task
    with patch('services.bookmark_processing_service.extract_article_content',
               return_value=_failed_doc(200, False, outcome='blocked')), \
         patch('services.pipeline_orchestrator.PipelineOrchestrator.request_embedding'), app.app_context():
        process_bookmark_content_task(saved_bookmark, 'https://example.com/a', test_user['id'])
    assert _bookmark(app, saved_bookmark).scrape_status == 'BLOCKED'


def test_article_mentioning_access_denied_is_not_a_challenge_page():
    from scrapers.quality_evaluator import QualityEvaluator
    article = ("When S3 returns Access Denied, check the bucket policy and the IAM role. " * 60)
    html = f"<html><body><article><h1>Fixing S3 403 Forbidden</h1><p>{article}</p></article></body></html>"
    metrics = QualityEvaluator().evaluate(html=html, clean_text=article, title="Fixing S3 403 Forbidden errors")
    assert not metrics.challenge_detected and metrics.score >= 70

    short = QualityEvaluator().evaluate(html="<html><title>Just a moment...</title></html>",
                                        clean_text="Checking your browser before accessing", title="Just a moment...")
    assert short.challenge_detected


@pytest.mark.parametrize('status,retryable', [(404, False), (503, True), (429, True)])
def test_engine_reports_fetch_failures(status, retryable):
    from scrapers.acquisition_engine import ContentAcquisitionEngine
    meta = FetchMetadata(strategy='HTTP', attempts=1, http_status=status, redirected=False)
    page = RawFetchResult(url='https://example.com/x', final_url='https://example.com/x', http_status=status,
                          headers={}, raw_content=b'<html><body><h1>Error</h1><p>Not here</p></body></html>',
                          fetch_metadata=meta)
    engine = ContentAcquisitionEngine()
    with patch('scrapers.acquisition_engine.is_safe_url', return_value=True), \
         patch('scrapers.rate_limiter.DomainRateLimiter.acquire', return_value=(True, 0.0)), \
         patch('scrapers.robots_manager.RobotsManager.can_fetch', return_value=True), \
         patch('core.circuit_breaker.RedisCircuitBreaker.allow_request', return_value=True), \
         patch('scrapers.source_adapters.fetch_from_source', return_value=None), \
         patch.object(engine.fetchers['HTTP'], 'fetch', return_value=page):
        doc = engine.acquire_and_normalize('https://example.com/x')
    assert doc.outcome == 'failed' and doc.retryable is retryable
    assert doc.markdown_content == ''  # the error page is not stored as the bookmark's content


class _FakeRedis:
    def __init__(self):
        self.data = {}

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.data:
            return False
        self.data[key] = value
        return True

    def get(self, key):
        return self.data.get(key)

    def incr(self, key):
        self.data[key] = int(self.data.get(key, 0)) + 1
        return self.data[key]

    def expire(self, key, seconds):
        return True

    def delete(self, key):
        return 1 if self.data.pop(key, None) is not None else 0


def test_reconciler_requeues_stuck_and_failed_work(app, test_user):
    from models import db, SavedContent
    from services import pipeline_reconciler
    now = datetime.utcnow()
    with app.app_context():
        rows = {
            'stuck_pending': SavedContent(user_id=test_user['id'], url='https://e.com/1', title='1',
                                          scrape_status='PENDING', saved_at=now - timedelta(hours=1)),
            'fresh_pending': SavedContent(user_id=test_user['id'], url='https://e.com/2', title='2',
                                          scrape_status='PENDING', saved_at=now),
            'failed_due': SavedContent(user_id=test_user['id'], url='https://e.com/3', title='3',
                                       scrape_status='FAILED_FETCH', saved_at=now - timedelta(days=1),
                                       scraped_at=now - timedelta(hours=2), embedding_status='SUCCESS'),
            'failed_recent': SavedContent(user_id=test_user['id'], url='https://e.com/4', title='4',
                                          scrape_status='FAILED_FETCH', saved_at=now - timedelta(days=1),
                                          scraped_at=now - timedelta(minutes=5), embedding_status='SUCCESS'),
            'not_embedded': SavedContent(user_id=test_user['id'], url='https://e.com/5', title='5',
                                         scrape_status='SUCCESS', embedding_status='FAILED',
                                         saved_at=now - timedelta(hours=1), scraped_at=now - timedelta(hours=1)),
        }
        db.session.add_all(rows.values())
        db.session.commit()
        ids = {name: row.id for name, row in rows.items()}

        fake = _FakeRedis()
        with patch.object(pipeline_reconciler, '_redis', return_value=fake), \
             patch('services.task_queue.enqueue_bookmark_processing', return_value=MagicMock()) as enqueue_fetch, \
             patch('services.pipeline_orchestrator.PipelineOrchestrator.request_embedding', return_value=True) as embed:
            counts = pipeline_reconciler.reconcile(now)
            requeued = {call.args[0] for call in enqueue_fetch.call_args_list}
            embedded = {call.args[0] for call in embed.call_args_list}

            # a second pass inside the same interval is a no-op (lock)
            assert pipeline_reconciler.reconcile(now) == {k: 0 for k in counts}

    assert requeued == {ids['stuck_pending'], ids['failed_due']}
    assert ids['not_embedded'] in embedded
    assert ids['fresh_pending'] not in requeued and ids['failed_recent'] not in requeued


def test_reconciler_gives_up_after_the_backoff_schedule(app, test_user):
    from models import db, SavedContent
    from services import pipeline_reconciler
    now = datetime.utcnow()
    with app.app_context():
        row = SavedContent(user_id=test_user['id'], url='https://e.com/dead', title='dead',
                           scrape_status='FAILED_FETCH', embedding_status='SUCCESS',
                           saved_at=now - timedelta(days=5), scraped_at=now - timedelta(days=2))
        db.session.add(row)
        db.session.commit()
        row_id = row.id
        fake = _FakeRedis()
        fake.data[pipeline_reconciler._ATTEMPTS_KEY.format(row_id)] = len(pipeline_reconciler.FETCH_RETRY_BACKOFF)
        with patch.object(pipeline_reconciler, '_redis', return_value=fake), \
             patch('services.task_queue.enqueue_bookmark_processing') as enqueue_fetch:
            counts = pipeline_reconciler.reconcile(now)
    enqueue_fetch.assert_not_called()
    assert counts['fetch_gave_up'] >= 1
    with app.app_context():
        assert db.session.get(SavedContent, row_id).scrape_status == 'FAILED'  # out of the retry window


def _analysis_row(test_user, url, now, **fields):
    from models import SavedContent
    values = dict(user_id=test_user['id'], url=url, title='t', scrape_status='SUCCESS',
                  embedding_status='SUCCESS', extracted_text='article text', analysis_status='PENDING',
                  saved_at=now - timedelta(days=1), scraped_at=now - timedelta(days=1),
                  embedded_at=now - timedelta(hours=1))
    values.update(fields)
    return SavedContent(**values)


def _run_analysis_pass(fake, now, allowance=True):
    """One reconcile pass with every queue mocked; returns (counts, analysed bookmark ids)."""
    from services import pipeline_reconciler
    from services.pipeline_reconciler import _LOCK_KEY
    fake.data.pop(_LOCK_KEY, None)  # each call is a new interval
    queue = MagicMock()
    queue.__len__.return_value = 0
    with patch.object(pipeline_reconciler, '_redis', return_value=fake), \
         patch('services.task_queue.enqueue_bookmark_processing', return_value=MagicMock()), \
         patch('services.pipeline_orchestrator.PipelineOrchestrator.request_embedding', return_value=True), \
         patch('services.task_queue.get_queue', return_value=queue), \
         patch('services.multi_user_api_manager.has_gemini_allowance', return_value=allowance), \
         patch('services.task_queue.enqueue_unique', return_value=MagicMock()) as enqueue:
        counts = pipeline_reconciler.reconcile(now)
    analysed = set()
    for call in enqueue.call_args_list:
        assert call.args[1] == pipeline_reconciler.ANALYSIS_TASK
        assert call.args[2] == f"analyze_bookmark_{call.kwargs['kwargs']['bookmark_id']}"
        analysed.add(call.kwargs['kwargs']['bookmark_id'])
    return counts, analysed


def test_reconciler_retries_failed_and_deferred_analyses(app, test_user):
    from models import db
    now = datetime.utcnow()
    with app.app_context():
        rows = {
            'pending': _analysis_row(test_user, 'https://e.com/a1', now),  # deferred: daily allowance ran out
            'failed': _analysis_row(test_user, 'https://e.com/a2', now, analysis_status='FAILED'),
            'fresh': _analysis_row(test_user, 'https://e.com/a3', now, embedded_at=now - timedelta(minutes=2)),
            'no_text': _analysis_row(test_user, 'https://e.com/a4', now, extracted_text=None),
            'not_embedded': _analysis_row(test_user, 'https://e.com/a5', now, embedding_status='PENDING'),
            'done': _analysis_row(test_user, 'https://e.com/a6', now, analysis_status='SUCCESS'),
        }
        db.session.add_all(rows.values())
        db.session.commit()
        ids = {name: row.id for name, row in rows.items()}

        counts, analysed = _run_analysis_pass(_FakeRedis(), now)

    assert {ids['pending'], ids['failed']} <= analysed
    assert not analysed & {ids['fresh'], ids['no_text'], ids['not_embedded'], ids['done']}
    assert counts['analysis_requeued'] >= 2


def test_analysis_retries_back_off_then_give_up(app, test_user):
    from models import db
    from services import pipeline_reconciler
    now = datetime.utcnow()
    with app.app_context():
        row = _analysis_row(test_user, 'https://e.com/flaky', now, analysis_status='FAILED',
                            saved_at=now + timedelta(days=1))  # newest, so it is always in the window
        db.session.add(row)
        db.session.commit()
        row_id = row.id
        fake = _FakeRedis()

        schedule = [now]
        for wait in pipeline_reconciler.ANALYSIS_RETRY_BACKOFF:
            schedule.append(schedule[-1] + wait)
        for attempt_at in schedule:
            # just before the backoff has passed: not yet
            if attempt_at != now:
                assert row_id not in _run_analysis_pass(fake, attempt_at - timedelta(minutes=1))[1]
            assert row_id in _run_analysis_pass(fake, attempt_at)[1]

        counts, analysed = _run_analysis_pass(fake, schedule[-1] + timedelta(days=7))
    assert row_id not in analysed
    assert counts['analysis_gave_up'] >= 1


def test_analysis_retry_waits_for_the_users_gemini_allowance(app, test_user):
    from models import db
    from services import pipeline_reconciler
    now = datetime.utcnow()
    with app.app_context():
        row = _analysis_row(test_user, 'https://e.com/over-quota', now)
        db.session.add(row)
        db.session.commit()
        row_id = row.id
        fake = _FakeRedis()

        counts, analysed = _run_analysis_pass(fake, now, allowance=False)
        assert row_id not in analysed and counts['deferred'] >= 1
        # a skipped pass doesn't use up an attempt
        assert fake.get(pipeline_reconciler._ANALYSIS_ATTEMPTS_KEY.format(row_id)) is None

        assert row_id in _run_analysis_pass(fake, now + timedelta(minutes=5))[1]


def test_analysis_retries_are_capped_per_pass(app, test_user, monkeypatch):
    from models import db
    from services import pipeline_reconciler
    monkeypatch.setattr(pipeline_reconciler, 'ANALYSIS_BATCH_LIMIT', 2)
    now = datetime.utcnow()
    with app.app_context():
        db.session.add_all(_analysis_row(test_user, f'https://e.com/many-{i}', now) for i in range(5))
        db.session.commit()
        counts, analysed = _run_analysis_pass(_FakeRedis(), now)
    assert len(analysed) == 2 and counts['analysis_requeued'] == 2


def test_analyze_bookmark_task_runs_the_analysis():
    from services.bookmark_processing_service import analyze_bookmark_task
    with patch('services.background_analysis_service.analyze_content') as analyze:
        analyze_bookmark_task(bookmark_id=12, user_id=3)
    analyze.assert_called_once_with(12, 3)


def test_gemini_allowance_check_spends_nothing(monkeypatch):
    from services import multi_user_api_manager as m
    monkeypatch.setenv('GEMINI_API_KEY', 'system-key')
    manager = m.MultiUserAPIManager.__new__(m.MultiUserAPIManager)
    uses = {}
    client = MagicMock()
    client.get.side_effect = lambda key: uses.get(key)
    manager.redis = MagicMock(redis_client=client, connected=True)
    monkeypatch.setattr(manager, 'check_user_rate_limit', lambda user_id: {'can_make_request': True})
    monkeypatch.setattr(manager, 'get_user_api_key', lambda user_id, for_use=True: 'system-key')

    assert manager.has_gemini_allowance(5) is True
    client.incr.assert_not_called()
    uses[m._system_key_uses_key(5)] = str(m.SYSTEM_KEY_DAILY_LIMIT)
    assert manager.has_gemini_allowance(5) is False

    monkeypatch.setattr(manager, 'get_user_api_key', lambda user_id, for_use=True: 'own-key')
    assert manager.has_gemini_allowance(5) is True  # their own key isn't limited by the shared allowance
    monkeypatch.setattr(manager, 'check_user_rate_limit', lambda user_id: {'can_make_request': False})
    assert manager.has_gemini_allowance(5) is False


def _event_ids(app):
    from models import db, BookmarkEvent
    with app.app_context():
        # Only this test's rows: real pipeline events from other tests are persisted too.
        return {row.event_id for row in db.session.query(BookmarkEvent.event_id)
                .filter(BookmarkEvent.type == 'bookmark.pipeline.test')}


def test_old_bookmark_events_are_pruned_once_a_day(app, test_user, saved_bookmark, monkeypatch):
    from models import db, BookmarkEvent
    from services import pipeline_reconciler
    monkeypatch.setenv('BOOKMARK_EVENTS_RETENTION_DAYS', '30')
    now = datetime(2026, 10, 12, 3, 0, 0)
    ages = {'old-1': 400, 'old-2': 31, 'old-3': 30.01, 'new-1': 28.5, 'new-2': 1, 'new-3': 0}
    with app.app_context():
        db.session.add_all(BookmarkEvent(event_id=name, bookmark_id=saved_bookmark, user_id=test_user['id'],
                                         pipeline_run_id='run', type='bookmark.pipeline.test',
                                         created_at=now - timedelta(days=days))
                           for name, days in ages.items())
        db.session.commit()

    fake = _FakeRedis()
    with patch.object(pipeline_reconciler, '_redis', return_value=fake):
        with app.app_context():
            assert pipeline_reconciler.prune_bookmark_events(now, batch_size=2) == 3  # several batches
        assert _event_ids(app) == {'new-1', 'new-2', 'new-3'}

        # Later the same day nothing runs, even though another row has aged out by then.
        with app.app_context():
            db.session.add(BookmarkEvent(event_id='old-4', bookmark_id=saved_bookmark, user_id=test_user['id'],
                                         pipeline_run_id='run', type='bookmark.pipeline.test',
                                         created_at=now - timedelta(days=90)))
            db.session.commit()
            assert pipeline_reconciler.prune_bookmark_events(now + timedelta(hours=20)) is None
        assert 'old-4' in _event_ids(app)

        # The next day it runs again.
        with app.app_context():
            assert pipeline_reconciler.prune_bookmark_events(now + timedelta(days=1)) == 1
        assert _event_ids(app) == {'new-1', 'new-2', 'new-3'}


def test_event_retention_can_be_disabled(app, monkeypatch):
    from services import pipeline_reconciler
    monkeypatch.setenv('BOOKMARK_EVENTS_RETENTION_DAYS', '0')
    with patch.object(pipeline_reconciler, '_redis', return_value=_FakeRedis()), app.app_context():
        assert pipeline_reconciler.prune_bookmark_events() is None


def test_backpressure_defers_instead_of_dropping():
    from services.pipeline_orchestrator import PipelineOrchestrator
    queue = MagicMock()
    queue.__len__.return_value = 10_000
    with patch('services.pipeline_orchestrator.get_queue', return_value=queue), \
         patch('services.pipeline_orchestrator.enqueue_unique') as enqueue, \
         patch('services.pipeline_orchestrator.publish_pipeline_event'):
        assert PipelineOrchestrator().request_embedding(1, 1) is False
    enqueue.assert_not_called()  # embedding_status stays PENDING for the reconciler


def _engine_with(robots_ok=True, rate_ok=True):
    from scrapers.acquisition_engine import ContentAcquisitionEngine
    engine = ContentAcquisitionEngine()
    patches = [
        patch('scrapers.acquisition_engine.is_safe_url', return_value=True),
        patch('scrapers.source_adapters.fetch_from_source', return_value=None),
        patch.object(engine.robots_manager, 'can_fetch', return_value=robots_ok),
        patch.object(engine.rate_limiter, 'acquire', return_value=(rate_ok, 0.0 if rate_ok else 30.0)),
        patch.object(engine.fetchers['HTTP'], 'fetch'),
    ]
    return engine, patches


@pytest.mark.parametrize('robots_ok,rate_ok,outcome,retryable', [
    (False, True, 'disallowed', False),
    (True, False, 'failed', True),
])
def test_robots_and_rate_limits_are_enforced_not_just_logged(robots_ok, rate_ok, outcome, retryable):
    engine, patches = _engine_with(robots_ok, rate_ok)
    for p in patches:
        p.start()
    try:
        doc = engine.acquire_and_normalize('https://example.com/page')
        fetch = engine.fetchers['HTTP'].fetch
        assert doc.outcome == outcome and doc.retryable is retryable
        fetch.assert_not_called()
    finally:
        for p in patches:
            p.stop()


def test_robots_disallowed_bookmark_is_marked_and_still_embedded(app, test_user, saved_bookmark):
    from services.bookmark_processing_service import process_bookmark_content_task
    with patch('services.bookmark_processing_service.extract_article_content',
               return_value=_failed_doc(0, False, outcome='disallowed')), \
         patch('services.pipeline_orchestrator.PipelineOrchestrator.request_embedding') as request_embedding, \
         app.app_context():
        process_bookmark_content_task(saved_bookmark, 'https://example.com/a', test_user['id'])
    assert _bookmark(app, saved_bookmark).scrape_status == 'DISALLOWED'
    request_embedding.assert_called_once()
