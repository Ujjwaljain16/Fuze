"""Authenticated surfaces must not accept the wrong token type or leak server-side fields."""
from datetime import timedelta

import pytest
from flask_jwt_extended import create_access_token, create_refresh_token


def test_verify_returns_only_public_profile_fields(client, app, test_user):
    from models import db, User
    with app.app_context():
        user = db.session.get(User, test_user['id'])
        user.user_metadata = {'api_key': {'encrypted': 'ciphertext', 'hash': 'abc'}}
        user.failed_login_count = 3
        db.session.commit()
        token = create_access_token(identity=str(test_user['id']))
    body = client.get('/api/auth/verify', headers={'Authorization': f'Bearer {token}'}).json['user']
    assert set(body) == set(User.PUBLIC_FIELDS)
    assert 'ciphertext' not in str(body)


@pytest.mark.parametrize('path', ['/api/bookmarks/import/progress/stream', '/api/bookmarks/analysis/progress/stream'])
def test_progress_streams_reject_refresh_tokens_and_query_tokens(client, app, test_user, path):
    with app.app_context():
        refresh = create_refresh_token(identity=str(test_user['id']))
        access = create_access_token(identity=str(test_user['id']))
        expired = create_access_token(identity=str(test_user['id']), expires_delta=timedelta(seconds=-1))
    assert client.get(path, headers={'Authorization': f'Bearer {refresh}'}).status_code == 401
    assert client.get(path, headers={'Authorization': f'Bearer {expired}'}).status_code == 401
    assert client.get(f'{path}?token={access}').status_code == 401


@pytest.mark.parametrize('path', ['/api/health', '/api/health/database'])
def test_public_health_does_not_leak_details(client, path):
    text = client.get(path).get_data(as_text=True)
    for secret_ish in ('sqlite', 'postgresql', 'host', 'error', 'environment'):
        assert secret_ish not in text.lower()


@pytest.mark.parametrize('path', ['/api/health/queue', '/api/health/detailed', '/metrics'])
def test_operational_endpoints_are_closed_without_a_token(client, monkeypatch, path):
    monkeypatch.delenv('INTERNAL_HEALTH_TOKEN', raising=False)
    monkeypatch.delenv('METRICS_AUTH_TOKEN', raising=False)
    assert client.get(path).status_code == 404


def test_sse_auth_accepts_access_token_header_and_single_use_ticket(app, test_user):
    from unittest.mock import patch
    from blueprints.bookmarks import _sse_user_id
    with app.app_context():
        access = create_access_token(identity=str(test_user['id']))
    with app.test_request_context(headers={'Authorization': f'Bearer {access}'}):
        assert _sse_user_id() == test_user['id']
    with patch('utils.stream_tickets.consume_stream_ticket', return_value=str(test_user['id'])) as consume:
        with app.test_request_context('/?ticket=t-123'):
            assert _sse_user_id() == test_user['id']
    consume.assert_called_once_with('t-123')
