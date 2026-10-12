"""Connections are pinged only after sitting idle, not on every checkout (each ping is a network round trip)."""
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DisconnectionError  # noqa: F401  (documents what the listener raises)

from utils import db_pool


@pytest.fixture
def engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'pool.db'}", pool_size=2, max_overflow=0)
    yield engine
    engine.dispose()


def _use(engine):
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def test_a_busy_connection_is_not_pinged_again_and_an_idle_one_is(engine):
    db_pool.install_idle_ping(engine, 15)
    clock = [1000.0]
    with patch('utils.db_pool.time.monotonic', side_effect=lambda: clock[0]), \
         patch.object(engine.dialect, 'do_ping', wraps=engine.dialect.do_ping) as ping:
        _use(engine)                    # a connection used for the first time is checked
        assert ping.call_count == 1
        for _ in range(5):              # used again straight away: trusted, no ping
            clock[0] += 1
            _use(engine)
        assert ping.call_count == 1
        clock[0] += 60                  # unused for a minute: checked before use
        _use(engine)
        assert ping.call_count == 2


def test_a_connection_that_died_while_idle_is_replaced_not_handed_out(engine):
    db_pool.install_idle_ping(engine, 15)
    clock = [1000.0]
    with patch('utils.db_pool.time.monotonic', side_effect=lambda: clock[0]):
        _use(engine)
        clock[0] += 60
        real = engine.dialect.do_ping
        calls = []

        def ping(dbapi_connection):
            calls.append(1)
            return False if len(calls) == 1 else real(dbapi_connection)  # the idle one is dead, the new one is fine
        with patch.object(engine.dialect, 'do_ping', side_effect=ping):
            _use(engine)                # must succeed on a fresh connection, not raise
        assert len(calls) == 2


def test_zero_idle_seconds_installs_nothing(engine):
    db_pool.install_idle_ping(engine, 0)
    with patch.object(engine.dialect, 'do_ping') as ping:
        _use(engine)
        _use(engine)
    ping.assert_not_called()


def test_config_swaps_per_checkout_pre_ping_for_the_idle_ping(monkeypatch):
    from utils.unified_config import UnifiedConfig
    monkeypatch.setenv('DATABASE_URL', 'postgresql://u:p@localhost/x')
    monkeypatch.setenv('DB_POOL_PRE_PING', 'true')
    monkeypatch.setenv('DB_PING_IDLE_SECONDS', '15')
    assert UnifiedConfig().get_flask_config()['SQLALCHEMY_ENGINE_OPTIONS']['pool_pre_ping'] is False
    monkeypatch.setenv('DB_PING_IDLE_SECONDS', '0')
    assert UnifiedConfig().get_flask_config()['SQLALCHEMY_ENGINE_OPTIONS']['pool_pre_ping'] is True
