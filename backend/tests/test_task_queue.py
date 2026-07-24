import pytest
from unittest.mock import MagicMock, patch
from services.task_queue import (
    get_redis_connection,
    get_queue,
    enqueue_bookmark_processing,
    get_job_status,
    is_rq_available
)


@pytest.mark.unit
def test_task_queue_lazy_connection():
    with patch('services.task_queue._create_redis_connection') as mock_create:
        mock_conn = MagicMock()
        mock_create.return_value = mock_conn

        conn = get_redis_connection()
        assert conn == mock_conn


@pytest.mark.unit
def test_enqueue_bookmark_unique_job_id():
    mock_queue = MagicMock()
    mock_job = MagicMock()
    mock_job.id = "bookmark_process_10_abc123"
    mock_queue.enqueue.return_value = mock_job

    with patch('services.task_queue.get_queue', return_value=mock_queue):
        job = enqueue_bookmark_processing(bookmark_id=10, url="https://example.com", user_id=1)
        assert job is not None
        mock_queue.enqueue.assert_called_once()
        job_id_arg = mock_queue.enqueue.call_args[1]['job_id']
        assert job_id_arg.startswith("bookmark_process_10_")


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
