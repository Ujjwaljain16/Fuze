import pytest
from flask import Response
from middleware.security_middleware import (
    validate_input,
    sanitize_string,
    add_security_headers,
    validate_user_owns_resource
)


def test_validate_input_natural_text_allowed():
    """Verify natural technical text containing SQL keywords is NOT falsely flagged"""
    is_valid, error = validate_input({
        'title': 'How SELECT and JOIN work in PostgreSQL',
        'description': 'Tutorial about SQL queries'
    })
    assert is_valid is True
    assert error == ""


def test_validate_input_list_recursion():
    """Verify recursive list validation catches malicious XSS inside nested arrays"""
    is_valid, error = validate_input({
        'tasks': [
            {'title': 'Valid Task'},
            {'title': '<script>alert("xss")</script>'}
        ]
    })
    assert is_valid is False
    assert 'xss' in error.lower() or 'invalid' in error.lower()


def test_add_security_headers():
    """Verify modern security headers are added to response"""
    resp = Response("OK")
    resp = add_security_headers(resp)
    assert resp.headers.get('X-Content-Type-Options') == 'nosniff'
    assert resp.headers.get('X-Frame-Options') == 'DENY'
    assert 'max-age=31536000' in resp.headers.get('Strict-Transport-Security', '')
    assert 'same-origin' in resp.headers.get('Cross-Origin-Opener-Policy', '')
    assert 'X-XSS-Protection' not in resp.headers


def test_validate_user_owns_resource():
    assert validate_user_owns_resource(10, 10) is True
    assert validate_user_owns_resource(10, 20) is False
