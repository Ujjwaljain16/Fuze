"""End-to-end journeys through the bookmark pipeline on Postgres + pgvector (release gate 9).

The worker jobs run inline in the test process: the web request, the fetch job, the embedding job,
the reconciler and search all use the real code and the real database. Only the network edges are
replaced: the page fetch, Gemini, the embedding model (a deterministic fake) and the Redis queue.
Skipped on SQLite (the default lane); run with TEST_DATABASE_URL=postgresql://...
"""
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from scrapers.models import ContentDocument, FetchMetadata, NormalizedMetadata, QualityMetrics, compute_content_hash
from tests.test_pipeline_recovery import _FakeRedis, _failed_doc

TERMINAL_FETCH_STATES = {'FAILED_FETCH', 'BLOCKED', 'DISALLOWED'}
FAKE_MODEL_NAME = 'test-topic-model'


@pytest.fixture(autouse=True)
def postgres_only(app):
    from models import db
    with app.app_context():
        if db.engine.dialect.name != 'postgresql':
            pytest.skip('needs Postgres (run with TEST_DATABASE_URL=postgresql://...localhost...)')


class _TopicModel:
    """Deterministic stand-in for the sentence-transformer: a fixed unit vector per topic word.

    Text mentioning 'pgvector' maps to e0, 'sourdough' to e1, 'kayak' to e2, anything else to e3,
    so a query about pgvector is nearest (cosine 1.0) to the bookmark about pgvector and orthogonal
    to everything else. Never returns a zero vector, which the pipeline rejects.
    """
    TOPICS = ('pgvector', 'sourdough', 'kayak')

    def encode(self, texts, **kwargs):
        if isinstance(texts, str):
            texts = [texts]
        out = np.zeros((len(texts), 384), dtype=np.float32)
        for i, text in enumerate(texts):
            low = text.lower()
            out[i, next((k for k, word in enumerate(self.TOPICS) if word in low), len(self.TOPICS))] = 1.0
        return out


@pytest.fixture
def topic_embeddings(monkeypatch):
    """Install the fake as the loaded model. get_embedding, embed_query, get_embeddings_batch and
    active_embedding_model_name all read this singleton, including in modules that imported those
    functions by name, so stored and query vectors carry one consistent model name."""
    from utils import embedding_utils
    monkeypatch.setattr(embedding_utils, '_embedding_model', _TopicModel())
    monkeypatch.setattr(embedding_utils, '_embedding_model_initialized', True)
    monkeypatch.setattr(embedding_utils, '_embedding_model_name', FAKE_MODEL_NAME)


@pytest.fixture
def stub_analysis():
    with patch('services.background_analysis_service.analyze_content', return_value={'status': 'stubbed'}) as stub:
        yield stub


def _article(url, title, topic):
    paragraphs = [f'{title}. This article is about {topic} and nothing else.'] + [
        f'Section {n} goes deeper into {topic}: setup, trade-offs, measurements and the mistakes worth '
        f'avoiding when you rely on {topic} every day.' for n in range(1, 9)]
    text = '\n\n'.join(paragraphs)
    return ContentDocument(
        url=url, canonical_url=url, content_hash=compute_content_hash(text), markdown_content=text,
        metadata=NormalizedMetadata(title=title, description=f'A guide to {topic}', author='A. Writer',
                                    language='en', reading_time_minutes=4),
        provider_raw_payload={'og:title': title, 'og:type': 'article'},
        quality_metrics=QualityMetrics(score=88, has_title=True, has_article_body=True,
                                       word_count=len(text.split()), hydration_detected=False,
                                       challenge_detected=False),
        fetch_metadata=FetchMetadata(strategy='HTTP', attempts=1, http_status=200, redirected=False))


class _Worker:
    """Captures what the web tier and the reconciler enqueue, then runs those jobs inline, the way
    an RQ worker would: a job that raises is recorded as failed and the next one runs."""

    def __init__(self, pages, user_id):
        self.pages = pages  # url -> ContentDocument returned by the fetch
        self.user_id = user_id
        self.fetch_jobs, self.embedding_jobs = [], []

    def enqueue_fetch(self, bookmark_id, url, user_id, *args, **kwargs):
        self.fetch_jobs.append((bookmark_id, url, user_id))
        return MagicMock(id=f'bookmark_process_{bookmark_id}')

    def request_embedding(self, bookmark_id, user_id):  # replaces PipelineOrchestrator.request_embedding
        self.embedding_jobs.append((bookmark_id, user_id))
        return True

    def queue_patches(self):
        worker = self
        return [patch('services.task_queue.enqueue_bookmark_processing', side_effect=self.enqueue_fetch),
                patch('services.pipeline_orchestrator.PipelineOrchestrator.request_embedding',
                      autospec=True, side_effect=lambda _self, b, u: worker.request_embedding(b, u))]

    def drain(self, app):
        """Run queued jobs (fetches, then the embeddings they request) until none are left.
        Jobs for other users' rows (left by other tests in this database) are not ours to run."""
        from services.bookmark_processing_service import (TransientFetchError, generate_embedding_task,
                                                          process_bookmark_content_task)
        ran = {'fetch': 0, 'embed': 0, 'transient': 0}
        extract = patch('services.bookmark_processing_service.extract_article_content',
                        side_effect=lambda url: self.pages[url])
        with extract, app.app_context():
            while self.fetch_jobs or self.embedding_jobs:
                if self.fetch_jobs:
                    bookmark_id, url, user_id = self.fetch_jobs.pop(0)
                    if user_id != self.user_id:
                        continue
                    try:
                        process_bookmark_content_task(bookmark_id, url, user_id)
                    except TransientFetchError:
                        ran['transient'] += 1  # RQ would retry later; the row is already FAILED_FETCH
                    ran['fetch'] += 1
                else:
                    bookmark_id, user_id = self.embedding_jobs.pop(0)
                    if user_id != self.user_id:
                        continue
                    generate_embedding_task(bookmark_id=bookmark_id, user_id=user_id)
                    ran['embed'] += 1
        return ran


def _rows(app, user_id):
    from models import db, SavedContent
    with app.app_context():
        db.session.expire_all()
        return {r.url: {'id': r.id, 'title': r.title, 'scrape': r.scrape_status, 'embed': r.embedding_status,
                        'model': (r.embedding_metadata or {}).get('model'), 'has_vector': r.embedding is not None}
                for r in SavedContent.query.filter_by(user_id=user_id)}


def _chunk_count(app, bookmark_id):
    from sqlalchemy import text
    from models import db
    with app.app_context():
        return db.session.execute(text('SELECT count(*) FROM content_chunks WHERE content_id = :id AND embedding_model = :m'),
                                  {'id': bookmark_id, 'm': FAKE_MODEL_NAME}).scalar()


def test_save_process_embed_then_semantic_search_finds_it(app, client, test_user, auth_headers,
                                                         topic_embeddings, stub_analysis):
    tag = uuid.uuid4().hex[:8]
    target = f'https://blog-{tag}.example.com/pgvector-hnsw-tuning'
    pages = {
        target: _article(target, 'Tuning HNSW indexes in pgvector', 'pgvector'),
        f'https://bake-{tag}.example.com/starter': _article(f'https://bake-{tag}.example.com/starter',
                                                            'Keeping a sourdough starter alive', 'sourdough'),
        f'https://paddle-{tag}.example.com/rolls': _article(f'https://paddle-{tag}.example.com/rolls',
                                                            'Learning the kayak roll', 'kayak'),
    }
    worker = _Worker(pages, test_user['id'])

    # 1. Save through the API; the web tier only enqueues.
    with patch('services.task_queue.is_rq_available', return_value=True), \
            patch('services.task_queue.enqueue_bookmark_processing', side_effect=worker.enqueue_fetch):
        for url in pages:
            resp = client.post('/api/bookmarks', json={'url': url}, headers=auth_headers)
            assert resp.status_code == 201, resp.get_json()
    rows = _rows(app, test_user['id'])
    assert {row['scrape'] for row in rows.values()} == {'PENDING'}
    assert sorted(job[0] for job in worker.fetch_jobs) == sorted(row['id'] for row in rows.values())

    # 2-3. The worker fetches each page, which requests the embedding, which the worker runs.
    # The embedding job enqueues the AI analysis as a job of its own (it no longer runs inline); capture
    # those too, to run them below the way a worker would.
    analysis_jobs = []

    def capture_analysis(queue, func, job_id, *, args=(), kwargs=None, **options):
        analysis_jobs.append((func, job_id, kwargs))
        return MagicMock(id=job_id)

    patches = worker.queue_patches()[1:] + [
        patch('services.task_queue.get_queue', return_value=MagicMock()),
        patch('services.task_queue.enqueue_unique', side_effect=capture_analysis)]
    for p in patches:
        p.start()
    try:
        ran = worker.drain(app)
    finally:
        for p in patches:
            p.stop()
    assert ran == {'fetch': 3, 'embed': 3, 'transient': 0}
    assert stub_analysis.call_count == 0  # embedding no longer waits for Gemini
    assert sorted(job_id for _, job_id, _ in analysis_jobs) ==         sorted(f"analyze_bookmark_{row['id']}" for row in _rows(app, test_user['id']).values())

    rows = _rows(app, test_user['id'])
    for url, row in rows.items():
        assert (row['scrape'], row['embed'], row['model'], row['has_vector']) == \
            ('SUCCESS', 'SUCCESS', FAKE_MODEL_NAME, True), url
        assert _chunk_count(app, row['id']) > 0, url
    assert rows[target]['title'] == 'Tuning HNSW indexes in pgvector'  # 'Untitled' replaced by the page title
    from services.bookmark_processing_service import analyze_bookmark_task
    with app.app_context():
        for _, _, job_kwargs in analysis_jobs:
            analyze_bookmark_task(**job_kwargs)  # the queued analysis jobs, run as the worker would
    assert stub_analysis.call_count == 3  # Gemini analysis was triggered, and stubbed

    # 4. Semantic search over the user's bookmarks ranks the pgvector article first.
    resp = client.post('/api/search/semantic', json={'query': 'how do I speed up pgvector queries'},
                       headers=auth_headers)
    assert resp.status_code == 200, resp.get_json()
    results = resp.get_json()['results']
    assert results and results[0]['id'] == rows[target]['id'], results
    assert results[0]['url'] == target


def test_import_during_redis_outage_self_heals_after_reconcile(app, client, test_user, auth_headers,
                                                               topic_embeddings, stub_analysis, monkeypatch):
    from services import pipeline_reconciler
    tag = uuid.uuid4().hex[:8]
    urls = [f'https://import-{tag}.example.com/article/{i}' for i in range(20)]
    topics = ('pgvector', 'sourdough', 'kayak', 'rust')
    pages = {url: _article(url, f'Imported article {i}', topics[i % len(topics)]) for i, url in enumerate(urls[:16])}
    failures = {
        urls[16]: (_failed_doc(404, False), 'FAILED_FETCH'),         # gone
        urls[17]: (_failed_doc(503, True), 'FAILED_FETCH'),          # transient; RQ retries, reconciler backs off
        urls[18]: (_failed_doc(200, False, outcome='blocked'), 'BLOCKED'),
        urls[19]: (_failed_doc(0, False, outcome='disallowed'), 'DISALLOWED'),
    }
    pages.update({url: doc for url, (doc, _) in failures.items()})
    worker = _Worker(pages, test_user['id'])

    # 1. Redis is down: no connection at all for the queue, the orchestrator or the reconciler.
    with patch('services.task_queue.get_redis_connection', return_value=None):
        resp = client.post('/api/bookmarks/import', headers=auth_headers,
                           json=[{'url': url, 'title': f'Imported article {i}'} for i, url in enumerate(urls)])
        assert resp.status_code == 200, resp.get_json()
        assert resp.get_json()['added'] == 20

        rows = _rows(app, test_user['id'])
        assert sorted(rows) == sorted(urls)
        assert {(row['scrape'], row['embed']) for row in rows.values()} == {('PENDING', 'PENDING')}

        with app.app_context():  # a reconciler pass during the outage changes nothing
            # Nothing left to do: every counter is zero, whatever passes the reconciler grows.
            assert not any(pipeline_reconciler.reconcile().values())

    # 2. Redis is back. The next reconciler pass after the stale window re-enqueues every row.
    monkeypatch.setattr(pipeline_reconciler, 'BATCH_LIMIT', 10_000)  # other tests' rows may share this DB
    later = datetime.utcnow() + timedelta(minutes=20)
    fake_redis = _FakeRedis()
    patches = [patch.object(pipeline_reconciler, '_redis', return_value=fake_redis)] + worker.queue_patches()
    for p in patches:
        p.start()
    try:
        with app.app_context():
            pipeline_reconciler.reconcile(later)
        ours = {row['id'] for row in rows.values()}
        assert {job[0] for job in worker.fetch_jobs if job[0] in ours} == ours

        # 3. The worker runs everything that was enqueued, including the embeddings those jobs request.
        ran = worker.drain(app)
        assert ran['fetch'] == 20 and ran['transient'] == 1

        # 4. A later pass finds nothing of ours left to do: the transient failure waits for its backoff.
        fake_redis.data.pop(pipeline_reconciler._LOCK_KEY, None)
        with app.app_context():
            pipeline_reconciler.reconcile(later + timedelta(minutes=5))
        assert not [job for job in worker.fetch_jobs if job[0] in ours]
        assert not [job for job in worker.embedding_jobs if job[0] in ours]
    finally:
        for p in patches:
            p.stop()

    rows = _rows(app, test_user['id'])
    expected = {url: state for url, (_, state) in failures.items()}
    for url, row in rows.items():
        assert row['scrape'] == expected.get(url, 'SUCCESS'), (url, row)
        assert row['scrape'] in TERMINAL_FETCH_STATES | {'SUCCESS'}
        # Failed fetches are still embedded from title and URL, so every row is searchable.
        assert (row['embed'], row['model'], row['has_vector']) == ('SUCCESS', FAKE_MODEL_NAME, True), (url, row)
    assert not [row for row in rows.values() if row['scrape'] == 'PENDING' or row['embed'] == 'PENDING']
