"""Import enqueues its new bookmarks in one Redis transaction, not several round trips each."""
from unittest.mock import MagicMock, patch


def _import(client, auth_headers, n=3):
    return client.post('/api/bookmarks/import', headers=auth_headers, json=[
        {'url': f'https://example.com/bulk-{i}', 'title': f'Bulk {i}'} for i in range(n)])


def test_import_enqueues_all_new_bookmarks_in_one_call(client, auth_headers):
    with patch('services.task_queue.is_rq_available', return_value=True), \
         patch('services.task_queue.enqueue_bookmarks_bulk', return_value=3) as bulk, \
         patch('blueprints.bookmarks.process_bookmark_content_async') as one_by_one:
        resp = _import(client, auth_headers)
    assert resp.status_code == 200 and resp.json['added'] == 3
    assert bulk.call_count == 1
    assert len(list(bulk.call_args.args[0])) == 3
    one_by_one.assert_not_called()


def test_import_falls_back_to_one_at_a_time_when_the_batch_fails(client, auth_headers):
    with patch('services.task_queue.is_rq_available', return_value=True), \
         patch('services.task_queue.enqueue_bookmarks_bulk', return_value=0), \
         patch('blueprints.bookmarks.process_bookmark_content_async') as one_by_one:
        resp = _import(client, auth_headers)
    assert resp.status_code == 200 and resp.json['added'] == 3
    assert one_by_one.call_count == 3


def test_bulk_enqueue_uses_one_pipeline_with_stable_job_ids():
    from services import task_queue
    queue = MagicMock()
    pipe = queue.connection.pipeline.return_value.__enter__.return_value
    queue.enqueue_many.side_effect = lambda datas, pipeline: [object() for _ in datas]
    with patch.object(task_queue, 'get_queue', return_value=queue):
        count = task_queue.enqueue_bookmarks_bulk([(11, 'https://a.example', 2), (12, 'https://b.example', 2)])
    assert count == 2
    datas = queue.enqueue_many.call_args.args[0]
    assert [d.job_id for d in datas] == ['bookmark_process_11', 'bookmark_process_12']
    assert queue.enqueue_many.call_args.kwargs['pipeline'] is pipe
    pipe.execute.assert_called_once()


def test_bulk_enqueue_reports_zero_when_redis_fails():
    from services import task_queue
    queue = MagicMock()
    queue.enqueue_many.side_effect = ConnectionError('redis down')
    with patch.object(task_queue, 'get_queue', return_value=queue):
        assert task_queue.enqueue_bookmarks_bulk([(1, 'https://a.example', 2)]) == 0
