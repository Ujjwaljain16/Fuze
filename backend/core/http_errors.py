"""One shape for every error the API returns.

Every non-2xx JSON body is ``{"error": "<snake_case_code>", "message": "<human sentence>"}``.
``error`` is the stable, machine-readable code clients branch on; ``message`` is for people and
may be reworded at any time. Extra fields are allowed where a client needs them (``suggestions``
on a username conflict, ``retry_after`` on a 429).
"""
import re

from flask import jsonify

_CODE = re.compile(r'^[a-z][a-z0-9_]*$')

# The code a bare HTTP error gets when nothing more specific applies.
DEFAULT_CODES = {
    400: 'bad_request',
    401: 'unauthorized',
    403: 'forbidden',
    404: 'not_found',
    405: 'method_not_allowed',
    409: 'conflict',
    413: 'payload_too_large',
    422: 'unprocessable_entity',
    429: 'rate_limit_exceeded',
    500: 'internal_error',
    502: 'bad_gateway',
    503: 'service_unavailable',
    504: 'gateway_timeout',
}


def error_body(code: str, message: str, /, **extra) -> dict:
    if not _CODE.match(code or ''):
        raise ValueError(f"error code must be snake_case, got {code!r}")
    reserved = {'error', 'message'} & extra.keys()
    if reserved:
        raise ValueError(f"extra fields may not override {sorted(reserved)}")
    body = {'error': code, 'message': message}
    body.update(extra)
    return body


def error_response(code: str, message: str, status: int, /, **extra):
    """Return a ``(response, status)`` pair in the standard error envelope."""
    if status < 400:
        raise ValueError(f"error_response is for 4xx/5xx statuses, got {status}")
    return jsonify(error_body(code, message, **extra)), status


def rate_limit_response(e):
    """429 for Flask-Limiter's RateLimitExceeded (and any other 429 HTTPException).

    ``retry_after`` is the limit that was hit (e.g. "30 per 1 minute"), which is what the old
    handler sent; the Retry-After header, when the limiter sets one, carries the seconds.
    """
    limit = getattr(e, 'description', None) or '60'
    return error_response(
        'rate_limit_exceeded',
        'Too many requests. Please slow down and try again later.',
        429,
        retry_after=limit,
    )
