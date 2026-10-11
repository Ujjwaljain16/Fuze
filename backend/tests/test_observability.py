"""Request ids reach the logs and the response; queue stats count real failures."""
from unittest.mock import MagicMock, patch


def test_request_id_is_echoed_and_bound_into_logs(client):
    with patch('core.logging_config.bind_request_context') as bind:
        response = client.get('/health/liveness', headers={'X-Request-ID': 'abc-123'})
    assert response.headers['X-Request-ID'] == 'abc-123'
    assert bind.call_args.kwargs['correlation_id'] == 'abc-123'


def test_garbage_request_ids_are_replaced(client):
    response = client.get('/health/liveness', headers={'X-Request-ID': 'x' * 500 + '<script>'})
    assert len(response.headers['X-Request-ID']) == 32


def test_failed_count_comes_from_the_failed_job_registry():
    from services import task_queue
    with patch.object(task_queue, 'get_redis_connection', return_value=MagicMock()), \
         patch.object(task_queue, 'Queue') as queue_cls, \
         patch('rq.Worker.all', return_value=[]), \
         patch('rq.registry.FailedJobRegistry') as registry:
        queue_cls.return_value.__len__.return_value = 0
        registry.return_value.count = 7
        assert task_queue.get_queue_stats()['failed_count'] == 7
