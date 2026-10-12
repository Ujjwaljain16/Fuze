"""
Refuse to run a destructive script against a database it was not meant for.

The developer's .env points DATABASE_URL at the production database, so a script that
deletes, truncates or creates tables runs against production unless something stops it.
A test run once dropped production tables exactly this way.

A run is allowed without ceremony only when the process is in development or testing AND
the database lives on this machine (localhost, 127.0.0.1, ::1, a unix socket or SQLite).
Anything else needs the operator to type the database host back:

    python scripts/reindex_content.py --i-know=db.abcd.supabase.co

Call require_safe_target() at the very start of the script, before any connection is made.
Messages name the host and the environment only, never the URL: it carries the password.
"""

import os
import sys
from typing import Optional, Sequence, Tuple

from core.app_env import DEVELOPMENT, TESTING, app_env

FLAG = '--i-know'
LOCAL_HOSTS = ('localhost', '127.0.0.1', '::1')


def database_host(database_url: str) -> Tuple[Optional[str], bool]:
    """(host to show and type back, is it on this machine). Host is None when the URL is unusable."""
    from sqlalchemy.engine import make_url
    try:
        url = make_url(database_url)
    except Exception:
        return None, False
    if url.get_backend_name() == 'sqlite':
        return 'sqlite', True
    host = url.host
    if not host:
        # libpq: no host means a unix socket on this machine, unless ?host= names one.
        socket_host = url.query.get('host')
        if isinstance(socket_host, tuple):
            socket_host = socket_host[0] if socket_host else None
        if not socket_host or socket_host.startswith('/'):
            return 'localhost', True
        host = socket_host
    host = host.strip('[]').lower()
    return host, host in LOCAL_HOSTS


def configured_database_url() -> str:
    """The URL create_app() will connect to: TestingConfig reads TEST_DATABASE_URL, the rest DATABASE_URL."""
    if app_env() == TESTING:
        return os.environ.get('TEST_DATABASE_URL') or 'sqlite:///:memory:'
    return os.environ.get('DATABASE_URL', '')


def _typed_host(argv: Sequence[str]) -> Optional[str]:
    """The value of --i-know=<host> (or --i-know <host>) in argv, if given."""
    args = list(argv or ())
    for i, arg in enumerate(args):
        if arg.startswith(FLAG + '='):
            return arg[len(FLAG) + 1:]
        if arg == FLAG and i + 1 < len(args):
            return args[i + 1]
    return None


def check_target(database_url: str, argv: Sequence[str] = ()) -> Tuple[bool, str]:
    """(allowed, reason). Pure: no exit, no output, no connection."""
    env = app_env()
    if not database_url:
        return False, 'no database URL is configured (DATABASE_URL is empty)'
    host, local = database_host(database_url)
    if host is None:
        return False, 'the database URL could not be parsed'
    if env in (DEVELOPMENT, TESTING) and local:
        return True, f'{env} environment, local database ({host})'

    typed = _typed_host(argv)
    if typed is not None and typed.strip().strip('[]').lower() == host:
        return True, f'operator confirmed database host {host} in {env}'

    why = f'database host is {host}' if not local else f'environment is {env}'
    if typed is not None:
        return False, f'{why}, but {FLAG} named a different host ({typed!r})'
    return False, why


def require_safe_target(database_url: str, argv: Optional[Sequence[str]] = None) -> Optional[str]:
    """Exit non-zero unless the target is safe or the operator typed its host back. Returns the host."""
    argv = sys.argv[1:] if argv is None else argv
    allowed, reason = check_target(database_url, argv)
    host, _ = database_host(database_url) if database_url else (None, False)
    if allowed:
        print(f'[destructive-guard] allowed: {reason}', file=sys.stderr)
        return host
    target = host or '<unknown>'
    sys.stderr.write(
        f'[destructive-guard] REFUSED: {reason}.\n'
        f'  This script deletes or rewrites data. It runs without confirmation only when\n'
        f'  APP_ENV is development or testing AND the database is local (localhost, 127.0.0.1,\n'
        f'  ::1 or SQLite). Current environment: {app_env()}; database host: {target}.\n'
        f'  If you really mean this database, re-run with {FLAG}={target}\n'
    )
    raise SystemExit(2)
