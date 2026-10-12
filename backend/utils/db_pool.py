"""Check a pooled connection only when it has been idle, instead of before every use.

SQLAlchemy's pool_pre_ping sends `SELECT 1` each time a connection is taken from the pool: one network
round trip per request, about 250 ms between a Hugging Face Space and a Supabase project in another
region. A connection that was returned to the pool a moment ago is not stale, so it is trusted; one
that has sat unused for longer than `idle_seconds` is pinged first, and replaced if the ping fails
(the server or the pooler may have closed it meanwhile).
"""

import time

from sqlalchemy import event, exc


def install_idle_ping(engine, idle_seconds: float) -> None:
    """Replace per-checkout pre-ping on `engine` with a ping after `idle_seconds` of disuse.

    The engine must be created with pool_pre_ping=False, or the ping happens twice.
    """
    if idle_seconds <= 0:
        return

    @event.listens_for(engine, "checkin")
    def _remember_last_use(dbapi_connection, connection_record):
        connection_record.info["last_checkin"] = time.monotonic()

    @event.listens_for(engine, "checkout")
    def _ping_if_idle(dbapi_connection, connection_record, connection_proxy):
        last = connection_record.info.get("last_checkin")
        if last is not None and time.monotonic() - last < idle_seconds:
            return
        try:
            alive = engine.dialect.do_ping(dbapi_connection)
        except Exception:
            alive = False
        if not alive:
            # SQLAlchemy discards this connection, opens a new one and retries the checkout.
            raise exc.DisconnectionError("pooled connection was closed while idle")
