"""Live pipeline events reach SSE clients, and a reconnect resumes right after the last one seen."""
import json
import os

import pytest
import redis

from utils.event_bus import read_user_stream, valid_stream_id

REDIS_URL = os.getenv('LIVE_REDIS_URL', 'redis://localhost:56379/14')


@pytest.fixture
def real_redis():
    client = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=1)
    try:
        client.ping()
    except redis.RedisError:
        pytest.skip(f'needs a Redis server at {REDIS_URL}')
    client.delete('fuze:events:stream:42')
    yield client
    client.delete('fuze:events:stream:42')


def _publish(client, event_type, bookmark_id=1):
    payload = {"event_id": f"e-{event_type}", "type": event_type, "bookmark_id": bookmark_id, "data": {}}
    return client.xadd('fuze:events:stream:42', {"event": json.dumps(payload)}).decode()


def test_events_written_by_producers_are_read_by_the_stream(real_redis):
    first = _publish(real_redis, 'bookmark.pipeline.scraping.started')
    second = _publish(real_redis, 'bookmark.pipeline.scraping.completed')
    entries = read_user_stream(real_redis, 42, '0-0', block_ms=100)
    assert [sid for sid, _ in entries] == [first, second]
    assert entries[1][1]['type'] == 'bookmark.pipeline.scraping.completed'
    assert entries[1][1]['category'] == 'success'


def test_reconnect_with_last_event_id_replays_only_what_was_missed(real_redis):
    seen = _publish(real_redis, 'bookmark.pipeline.scraping.started')
    missed = _publish(real_redis, 'bookmark.pipeline.embedding.completed')
    entries = read_user_stream(real_redis, 42, seen, block_ms=100)
    assert [sid for sid, _ in entries] == [missed]


def test_new_connection_waits_for_new_events_only(real_redis):
    _publish(real_redis, 'bookmark.pipeline.scraping.started')
    assert read_user_stream(real_redis, 42, '$', block_ms=100) == []


@pytest.mark.parametrize('value,ok', [('1700000000000-0', True), ('5f3c-uuid', False), (None, False), ('', False)])
def test_only_stream_ids_are_accepted_as_cursors(value, ok):
    assert valid_stream_id(value) is ok
