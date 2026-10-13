"""Job timeouts must surface as job failures, not be absorbed by fetch/analysis error handling."""
from unittest.mock import patch

import pytest

from core.job_timeout import JobTimeoutException


def test_http_fetcher_lets_job_timeouts_through():
    from scrapers.fetchers.http_fetcher import HTTPFetcher
    with patch('scrapers.fetchers.http_fetcher.safe_get', side_effect=JobTimeoutException('timeout')):
        with pytest.raises(JobTimeoutException):
            HTTPFetcher().fetch('https://example.com/')


def test_http_fetcher_still_absorbs_ordinary_errors():
    from scrapers.fetchers.http_fetcher import HTTPFetcher
    with patch('scrapers.fetchers.http_fetcher.safe_get', side_effect=ConnectionError('reset')):
        assert HTTPFetcher().fetch('https://example.com/').http_status == 500


def test_worker_has_no_per_second_scheduler_and_a_long_idle_ttl():
    """RQ's scheduler wakes every second (two Redis commands each time, all day, per worker) and used up
    Upstash's free 500,000 commands a month in a day or two. Due retries are moved by the pipeline
    reconciler instead (services.pipeline_reconciler.move_due_retries), every few minutes."""
    import ast
    import inspect
    import worker
    tree = ast.parse(inspect.getsource(worker))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, 'attr', None) == 'work']
    assert calls and all(k.value.value is False for c in calls for k in c.keywords if k.arg == 'with_scheduler')
    assert any(k.arg == 'with_scheduler' for k in calls[0].keywords)        # stated, not left to the default
    assert worker.WORKER_TTL_SECONDS >= 900
    source = inspect.getsource(worker.run_single_worker)
    assert 'build_worker(' in source and 'run_forever' in source   # the reconciler runs in this worker


def test_the_worker_can_be_constructed_with_the_pinned_rq():
    """A deploy crash-looped both workers with 'unexpected keyword argument worker_ttl': the keyword exists in
    the newest RQ and not in the pinned 1.15.1, and no test ever built a worker."""
    from unittest.mock import MagicMock
    import worker
    built = worker.build_worker('default', MagicMock(), 'fuze-worker-test')
    assert built.queue_names() == ['default']
    assert built.worker_ttl == worker.WORKER_TTL_SECONDS


def test_forked_work_horses_drop_the_inherited_db_pool():
    """A forked job must not share the parent's pooled sockets (the reconciler thread uses them)."""
    import inspect
    import worker
    source = inspect.getsource(worker.run_single_worker)
    assert 'register_at_fork' in source and 'dispose(close=False)' in source
