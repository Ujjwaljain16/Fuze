import pytest
from unittest.mock import MagicMock, patch
from services.task_queue import (
    get_redis_connection,
    enqueue_bookmark_processing,
    get_job_status,
    is_rq_available
)


@pytest.mark.unit
def test_task_queue_lazy_connection():
    import services.task_queue as tq
    tq._redis_conn = None  # Reset global state
    
    with patch('services.task_queue._create_redis_connection') as mock_create:
        mock_conn = MagicMock()
        mock_create.return_value = mock_conn

        conn = get_redis_connection()
        assert conn == mock_conn


@pytest.mark.unit
def test_enqueue_bookmark_uses_one_job_per_bookmark():
    """A fixed job id per bookmark: retries, the reconciler and a re-save can't double-run it."""
    from rq.exceptions import NoSuchJobError
    from rq.job import JobStatus
    mock_queue = MagicMock()
    mock_queue.enqueue_call.return_value = MagicMock(id="bookmark_process_10")

    with patch('services.task_queue.get_queue', return_value=mock_queue),          patch('services.task_queue.Job.fetch', side_effect=NoSuchJobError):
        job = enqueue_bookmark_processing(bookmark_id=10, url="https://example.com", user_id=1)
    assert job is not None
    assert mock_queue.enqueue_call.call_args.kwargs['job_id'] == "bookmark_process_10"

    waiting = MagicMock()
    waiting.get_status.return_value = JobStatus.QUEUED
    mock_queue.enqueue_call.reset_mock()
    with patch('services.task_queue.get_queue', return_value=mock_queue),          patch('services.task_queue.Job.fetch', return_value=waiting):
        assert enqueue_bookmark_processing(bookmark_id=10, url="https://example.com", user_id=1) is waiting
    mock_queue.enqueue_call.assert_not_called()


@pytest.mark.unit
def test_get_job_status_sanitization():
    mock_conn = MagicMock()
    mock_job = MagicMock()
    mock_job.id = "job_123"
    mock_job.get_status.return_value = "failed"
    mock_job.created_at = None
    mock_job.started_at = None
    mock_job.ended_at = None
    mock_job.result = "Heavy result payload" * 100
    mock_job.is_failed = True
    mock_job.exc_info = "Traceback (most recent call last):\n  File 'app.py', line 10\nValueError: Sensitive trace info"

    with patch('services.task_queue.get_redis_connection', return_value=mock_conn), \
         patch('rq.job.Job.fetch', return_value=mock_job):

        status = get_job_status("job_123")
        assert status is not None
        assert status['status'] == "failed"
        # Verify result is truncated
        assert len(status['result_summary']) <= 200
        # Verify traceback is sanitized to last line
        assert status['failed_reason'] == "ValueError: Sensitive trace info"


@pytest.mark.unit
def test_is_rq_available():
    mock_conn = MagicMock()
    mock_conn.ping.return_value = True

    with patch('services.task_queue.get_redis_connection', return_value=mock_conn):
        assert is_rq_available() is True
