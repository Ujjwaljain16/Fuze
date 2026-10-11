"""
Stream tickets must be single-use, including when two requests present the same ticket at once.
"""
import pytest
import redis

from utils.redis_utils import redis_cache
from utils.stream_tickets import mint_stream_ticket, consume_stream_ticket


class TicketRedis:
    """Minimal in-memory Redis with a hook that runs between a GET and whatever follows it."""

    def __init__(self, has_getdel=True):
        self.store = {}
        self.has_getdel = has_getdel
        self.on_get = None

    def ping(self):
        return True

    def setex(self, key, ttl, value):
        self.store[key] = value
        return True

    def get(self, key):
        value = self.store.get(key)
        hook, self.on_get = self.on_get, None
        if hook:
            hook()
        return value

    def delete(self, *keys):
        return sum(1 for key in keys if self.store.pop(key, None) is not None)

    def getdel(self, key):
        if not self.has_getdel:
            raise redis.exceptions.ResponseError("unknown command 'GETDEL'")
        return self.store.pop(key, None)

    def eval(self, script, numkeys, key):
        return self.store.pop(key, None)


@pytest.fixture
def ticket_redis(monkeypatch):
    fake = TicketRedis()
    monkeypatch.setattr(redis_cache, 'redis_client', fake)
    monkeypatch.setattr(redis_cache, 'connected', True)
    return fake


def test_ticket_is_single_use(ticket_redis):
    ticket = mint_stream_ticket(42)
    assert consume_stream_ticket(ticket) == 42
    assert consume_stream_ticket(ticket) is None


def test_racing_consumers_cannot_both_use_a_ticket(ticket_redis):
    ticket = mint_stream_ticket(42)
    racer = []
    # A second request presents the same ticket right after the first one reads it.
    ticket_redis.on_get = lambda: racer.append(consume_stream_ticket(ticket))

    first = consume_stream_ticket(ticket)
    if not racer:  # the consume never issued a GET, so nothing could interleave; race it afterwards
        racer.append(consume_stream_ticket(ticket))

    assert sorted([first, racer[0]], key=lambda v: v is None) == [42, None]


def test_ticket_consume_falls_back_when_getdel_is_missing(ticket_redis):
    ticket_redis.has_getdel = False
    ticket = mint_stream_ticket(7)
    assert consume_stream_ticket(ticket) == 7
    assert consume_stream_ticket(ticket) is None


def test_unknown_ticket_is_rejected(ticket_redis):
    assert consume_stream_ticket('not-a-ticket') is None
    assert consume_stream_ticket('') is None
