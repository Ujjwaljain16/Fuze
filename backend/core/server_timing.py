"""Per-request timing breakdown, returned as a `Server-Timing` header when (and only when) asked for.

A benchmark that only sees total latency cannot tell a slow query from a slow network from a slow model.
With `X-Server-Timing: 1` on the request, the response carries, for example:

    Server-Timing: total;dur=2154.0, embed;dur=640.2, db;dur=1083.5, dbn;desc="5 statements"

  total  the whole request inside this process, in milliseconds
  embed  time spent turning the query into a vector (the embedding model)
  db     time the application waited for the database, as it sees it: network round trips included
  dbn    how many SQL statements ran (each one is a round trip)

Normal requests get no header, so nothing about the internals is exposed to ordinary clients.
"""

import time
from contextlib import contextmanager

from flask import g, has_request_context, request
from sqlalchemy import event

REQUEST_HEADER = "X-Server-Timing"


def record(name: str, milliseconds: float) -> None:
    """Add to this request's `name` total. A no-op outside a request."""
    if has_request_context():
        timings = g.setdefault("server_timings", {})
        timings[name] = timings.get(name, 0.0) + milliseconds


@contextmanager
def timed(name: str):
    started = time.perf_counter()
    try:
        yield
    finally:
        record(name, (time.perf_counter() - started) * 1000)


def total_ms(request_started: float, first_statement_started, now: float) -> float:
    """Milliseconds the request took, counted from the earlier of its start and its first SQL statement.

    Other request hooks (authentication, session checks) can query the database before this module's own
    hook runs; counting only from that hook would leave `db` larger than `total`.
    """
    start = request_started if first_statement_started is None else min(request_started, first_statement_started)
    return (now - start) * 1000


def header_value(timings: dict, total_ms: float) -> str:
    parts = [f"total;dur={total_ms:.1f}"]
    for name in ("embed", "db"):
        if name in timings:
            parts.append(f"{name};dur={timings[name]:.1f}")
    count = int(timings.get("db_statements", 0))
    if count:
        parts.append(f'dbn;desc="{count} statements"')
    return ", ".join(parts)


def install(app, engine) -> None:
    """Measure SQL time per request on `engine` and add the header when the request asks for it."""

    @event.listens_for(engine, "before_cursor_execute")
    def _start(conn, cursor, statement, parameters, context, executemany):
        started = time.perf_counter()
        conn.info.setdefault("timing_starts", []).append(started)
        if has_request_context():
            g.setdefault("server_timing_first_statement", started)

    @event.listens_for(engine, "after_cursor_execute")
    def _stop(conn, cursor, statement, parameters, context, executemany):
        starts = conn.info.get("timing_starts")
        if starts:
            record("db", (time.perf_counter() - starts.pop()) * 1000)
            record("db_statements", 1)

    @app.before_request
    def _begin():
        g.server_timing_started = time.perf_counter()

    @app.after_request
    def _add_header(response):
        if request.headers.get(REQUEST_HEADER) == "1" and hasattr(g, "server_timing_started"):
            total = total_ms(g.server_timing_started, g.get("server_timing_first_statement"), time.perf_counter())
            response.headers["Server-Timing"] = header_value(g.get("server_timings", {}), total)
        return response
