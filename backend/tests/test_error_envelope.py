"""Every error the API returns has the same shape: {"error": <snake_case code>, "message": <sentence>}.

Clients branch on ``error`` and show ``message``. Before this was standardized, blueprints answered
with {'message'}, {'error': <sentence>} or {'success': False, 'error': <sentence>}, so a client had
to know which shape each endpoint used.
"""
import re
import types
from datetime import timedelta

import pytest

CODE = re.compile(r'^[a-z][a-z0-9_]*$')


def assert_envelope(response, status, code):
    assert response.status_code == status, response.get_data(as_text=True)
    assert response.is_json, response.get_data(as_text=True)
    body = response.get_json()
    assert body['error'] == code, body
    assert CODE.match(body['error'])
    assert isinstance(body['message'], str) and body['message'].strip()
    assert 'success' not in body
    return body


# (id, method, path, json body, authenticated, expected status, expected code)
CASES = [
    # auth
    ('auth-check-username', 'POST', '/api/auth/check-username', {}, False, 400, 'username_required'),
    ('auth-register-empty', 'POST', '/api/auth/register', {}, False, 400, 'missing_body'),
    ('auth-register-bad-email', 'POST', '/api/auth/register',
     {'username': 'someone', 'email': 'nope', 'password': 'Passw0rd!x'}, False, 400, 'invalid_email'),
    ('auth-login-unknown', 'POST', '/api/auth/login',
     {'email': 'nobody-envelope@example.com', 'password': 'whatever-1A!'}, False, 401, 'invalid_credentials'),
    ('auth-refresh-missing', 'POST', '/api/auth/refresh', None, False, 401, 'invalid_refresh_token'),
    ('auth-oauth-no-token', 'POST', '/api/auth/supabase-oauth', {}, False, 400, 'access_token_required'),
    # account
    ('account-delete-no-password', 'DELETE', '/api/account', {}, True, 400, 'password_required'),
    # bookmarks
    ('bookmarks-save-no-url', 'POST', '/api/bookmarks', {'title': 'x'}, True, 400, 'missing_fields'),
    ('bookmarks-quick-save-no-url', 'POST', '/api/bookmarks/quick-save', {'url': ''}, True, 400, 'url_required'),
    ('bookmarks-import-not-list', 'POST', '/api/bookmarks/import', {'url': 'x'}, True, 400, 'invalid_import_payload'),
    ('bookmarks-delete-missing', 'DELETE', '/api/bookmarks/987654321', None, True, 404, 'bookmark_not_found'),
    ('bookmarks-stream-no-auth', 'GET', '/api/bookmarks/import/progress/stream', None, False, 401,
     'authorization_required'),
    # events
    ('events-stream-no-ticket', 'GET', '/api/realtime/stream', None, False, 401, 'authorization_required'),
    # linkedin
    ('linkedin-extract-no-url', 'POST', '/api/linkedin/extract', {}, True, 400, 'linkedin_url_required'),
    ('linkedin-delete-missing', 'DELETE', '/api/linkedin/extract/987654321', None, True, 404, 'extraction_not_found'),
    # profile
    ('profile-other-user', 'PUT', '/api/users/987654321', {'username': 'x'}, True, 403, 'forbidden'),
    ('profile-bad-username', 'PUT', '/api/profile', {'username': '!'}, True, 400, 'invalid_username'),
    # projects
    ('projects-missing', 'GET', '/api/projects/987654321', None, True, 404, 'project_not_found'),
    ('projects-create-empty', 'POST', '/api/projects', {}, True, 400, 'title_required'),
    # recommendations
    ('recommendations-feedback-no-body', 'POST', '/api/recommendations/feedback', None, True, 400, 'missing_body'),
    ('recommendations-task-missing', 'POST', '/api/recommendations/task/987654321', {}, True, 404, 'task_not_found'),
    # search
    ('search-semantic-empty', 'POST', '/api/search/semantic', {}, True, 400, 'query_required'),
    # tasks
    ('tasks-create-empty', 'POST', '/api/tasks', {}, True, 400, 'missing_fields'),
    ('tasks-update-missing', 'PUT', '/api/tasks/987654321', {'title': 'x'}, True, 404, 'task_not_found'),
    ('tasks-subtask-missing', 'DELETE', '/api/tasks/subtasks/987654321', None, True, 404, 'subtask_not_found'),
    # user api key
    ('api-key-bad-format', 'POST', '/api/user/api-key', {'api_key': 'not-a-key'}, True, 400, 'invalid_api_key_format'),
    # global handlers and JWT callbacks
    ('global-404', 'GET', '/api/no-such-endpoint', None, False, 404, 'not_found'),
    ('global-405', 'DELETE', '/api/health', None, False, 405, 'method_not_allowed'),
    ('jwt-missing-token', 'GET', '/api/projects', None, False, 401, 'authorization_required'),
]


@pytest.mark.parametrize('method,path,body,authed,status,code', [c[1:] for c in CASES], ids=[c[0] for c in CASES])
def test_failing_calls_use_the_error_envelope(client, auth_headers, method, path, body, authed, status, code):
    kwargs = {'headers': auth_headers if authed else {}}
    if body is not None:
        kwargs['json'] = body
    response = client.open(path, method=method, **kwargs)
    assert_envelope(response, status, code)


def test_username_conflict_keeps_suggestions(client, test_user):
    response = client.post('/api/auth/register', json={
        'username': test_user['username'], 'email': 'fresh-envelope@example.com', 'password': 'Sup3r-Secret!pw'})
    body = assert_envelope(response, 409, 'account_exists')
    assert isinstance(body.get('suggestions', []), list)


def test_check_username_keeps_available_flag(client):
    body = assert_envelope(client.post('/api/auth/check-username', json={'username': '!!'}), 400, 'invalid_username')
    assert body['available'] is False


def test_invalid_token(client):
    response = client.get('/api/projects', headers={'Authorization': 'Bearer not.a.jwt'})
    assert response.status_code in (401, 422)
    assert_envelope(response, response.status_code, response.get_json()['error'])


def test_expired_token(app, client, test_user):
    from flask_jwt_extended import create_access_token
    with app.app_context():
        token = create_access_token(identity=str(test_user['id']), expires_delta=timedelta(seconds=-60))
    response = client.get('/api/projects', headers={'Authorization': f'Bearer {token}'})
    assert_envelope(response, 401, 'token_expired')


def test_revoked_token_callback(app):
    jwt_manager = app.extensions['flask-jwt-extended']
    with app.test_request_context():
        response, status = jwt_manager._revoked_token_callback({}, {})
        assert status == 401
        assert response.get_json() == {'error': 'token_revoked', 'message': 'Token has been revoked'}


def test_rate_limit_handler(app):
    from werkzeug.exceptions import TooManyRequests
    with app.test_request_context():
        response = app.make_response(app.handle_http_exception(TooManyRequests('5 per 1 minute')))
    body = assert_envelope(response, 429, 'rate_limit_exceeded')
    assert body['retry_after'] == '5 per 1 minute'


def test_payload_too_large_handler(app):
    from werkzeug.exceptions import RequestEntityTooLarge
    with app.test_request_context():
        response = app.make_response(app.handle_http_exception(RequestEntityTooLarge()))
    assert_envelope(response, 413, 'payload_too_large')


def test_unhandled_exception_is_500_envelope(client, auth_headers, monkeypatch):
    import blueprints.dashboard as dashboard

    def boom(_user_id):
        raise RuntimeError('database exploded')

    monkeypatch.setattr(dashboard, 'cache_keys', types.SimpleNamespace(dashboard_summary=boom))
    body = assert_envelope(client.get('/api/dashboard/summary', headers=auth_headers), 500, 'internal_error')
    assert 'exploded' not in body['message']


def test_uncaught_exception_reaches_global_handler(client, auth_headers, monkeypatch):
    import blueprints.auth as auth

    def boom():
        raise RuntimeError('secret detail')

    monkeypatch.setattr(auth, 'UnitOfWork', boom)
    body = assert_envelope(client.post('/api/auth/verify-token', headers=auth_headers), 500, 'internal_error')
    assert 'secret' not in body['message']


def test_error_response_rejects_non_snake_case_codes(app):
    from core.http_errors import error_response
    with app.app_context():
        with pytest.raises(ValueError):
            error_response('Internal server error', 'x', 500)
        with pytest.raises(ValueError):
            error_response('ok', 'x', 200)
        with pytest.raises(ValueError):
            error_response('bad', 'x', 400, message='override')
        response, status = error_response('bad', 'x', 400, status='kept')
        assert response.get_json() == {'error': 'bad', 'message': 'x', 'status': 'kept'}
