"""Sentry error tracking for the web app and the RQ workers, switched on only by SENTRY_DSN.

Nothing is imported or sent when SENTRY_DSN is unset, so local runs and tests never report.
Events carry no request bodies, user details or credentials: send_default_pii is off, and the
headers below are scrubbed from every event and transaction before it leaves the process.
"""

import os
from typing import Optional

from core.logging_config import get_logger

logger = get_logger(__name__)

# Compared lower-cased: a client may send `authorization` or `COOKIE`.
SCRUBBED_HEADERS = frozenset({
    'authorization', 'proxy-authorization', 'cookie', 'set-cookie',
    'x-api-key', 'x-internal-token', 'x-csrf-token',
})
REDACTED = '[Filtered]'

# The deploy (sync-to-hf-space.yml) writes the commit SHA here: HF builds the image from the
# Space's repository, so the SHA can't be passed as a build argument or env var.
RELEASE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'RELEASE')

_initialized = False


def release() -> Optional[str]:
    """The deployed commit: GIT_SHA if set, else the RELEASE file, else None (Sentry's default)."""
    sha = os.environ.get('GIT_SHA', '').strip()
    if sha:
        return sha
    try:
        with open(RELEASE_FILE, encoding='utf-8') as fh:
            return fh.read().strip() or None
    except OSError:
        return None


def _scrub_header_map(headers):
    if isinstance(headers, dict):
        for key in list(headers):
            if str(key).lower() in SCRUBBED_HEADERS:
                headers[key] = REDACTED
        return headers
    if isinstance(headers, list):  # [[name, value], ...]
        return [
            [pair[0], REDACTED] if len(pair) == 2 and str(pair[0]).lower() in SCRUBBED_HEADERS else pair
            for pair in headers
        ]
    return headers


def scrub_event(event, hint=None):
    """before_send / before_send_transaction hook: drop credentials from the request data."""
    request = event.get('request')
    if isinstance(request, dict):
        if 'headers' in request:
            request['headers'] = _scrub_header_map(request['headers'])
        if request.get('cookies'):
            request['cookies'] = REDACTED
    return event


def init_sentry(component: str) -> bool:
    """Initialise Sentry once per process. Returns True when it is (now or already) enabled."""
    global _initialized
    if _initialized:
        return True
    dsn = os.environ.get('SENTRY_DSN', '').strip()
    if not dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.rq import RqIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from core.app_env import app_env

        sentry_sdk.init(
            dsn=dsn,
            environment=app_env(),
            release=release(),
            integrations=[FlaskIntegration(), RqIntegration(), SqlalchemyIntegration()],
            send_default_pii=False,
            traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
            before_send=scrub_event,
            before_send_transaction=scrub_event,
        )
        # The global scope reaches every thread and request, unlike the current isolation scope.
        sentry_sdk.get_global_scope().set_tag('component', component)
    except Exception as e:
        # Error tracking must never stop the app from starting.
        logger.warning("sentry_init_failed", error=str(e))
        return False
    _initialized = True
    logger.info("sentry_initialized", component=component, release=release())
    return True
