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


def test_worker_runs_with_the_scheduler():
    """Retry(interval=...) jobs only come back from the ScheduledJobRegistry if a scheduler runs."""
    import ast
    import inspect
    import worker
    calls = [n for n in ast.walk(ast.parse(inspect.getsource(worker))) if isinstance(n, ast.Call)
             and getattr(n.func, 'attr', None) == 'work']
    assert calls and any(k.arg == 'with_scheduler' and k.value.value is True for k in calls[0].keywords)


def test_the_scheduler_checks_for_due_retries_rarely_not_every_second():
    """Every pass costs Redis commands; at RQ's default of one per second an idle worker used up Upstash's
    free monthly allowance in a day or two. The shortest retry wait in the app is 10 seconds."""
    import worker
    from rq.worker import base
    from rq.scheduler import RQScheduler
    from unittest.mock import MagicMock
    assert base.RQScheduler is worker.PacedScheduler
    assert 10 <= worker.SCHEDULER_INTERVAL_SECONDS <= 30
    scheduler = worker.PacedScheduler(['default'], connection=MagicMock())
    assert scheduler.interval == worker.SCHEDULER_INTERVAL_SECONDS
    assert RQScheduler(['default'], connection=MagicMock()).interval == 1    # the library default we replaced
    assert worker.PacedScheduler(['default'], connection=MagicMock(), interval=5).interval == 5   # an explicit choice wins


def test_forked_work_horses_drop_the_inherited_db_pool():
    """A forked job must not share the parent's pooled sockets (the reconciler thread uses them)."""
    import inspect
    import worker
    source = inspect.getsource(worker.run_single_worker)
    assert 'register_at_fork' in source and 'dispose(close=False)' in source
