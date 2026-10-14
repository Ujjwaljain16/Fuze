"""Users can take their data with them and delete their account, leaving nothing behind."""
import json
import time
import uuid
from unittest.mock import patch

import pytest
from flask_jwt_extended import create_access_token

from blueprints.auth import RECENT_SIGN_IN_SECONDS

SECRET_API_KEY = 'gAAAA-encrypted-gemini-key-must-not-leak'


def _make_user(app, **overrides):
    from models import db, User
    from blueprints.auth import hash_password
    with app.app_context():
        tag = uuid.uuid4().hex[:8]
        fields = dict(username=f'acct_{tag}', email=f'acct_{tag}@example.com',
                      password_hash=hash_password('pw-for-other-123'))
        fields.update(overrides)
        user = User(**fields)
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def other_user(app):
    user_id = _make_user(app)
    yield {'id': user_id}
    from models import db, User
    with app.app_context():
        user = db.session.get(User, user_id)
        if user:
            from services.account_service import AccountService
            from uow.unit_of_work import UnitOfWork
            with UnitOfWork() as uow:
                AccountService(uow).delete_account(user_id)


def _bearer(app, user_id):
    with app.app_context():
        return {'Authorization': f"Bearer {create_access_token(identity=str(user_id))}"}


def _populate(app, user_id, tag):
    """One row in every table a user's data lives in."""
    from models import (db, BookmarkEvent, BookmarkMetadata, ContentAnalysis, ContentChunk,
                        Project, SavedContent, Subtask, Task, TokenFamily, User, UserFeedback)
    with app.app_context():
        user = db.session.get(User, user_id)
        user.user_metadata = {'api_key': {'encrypted_key': SECRET_API_KEY, 'api_key_hash': 'hash-' + tag}}
        bookmark = SavedContent(user_id=user_id, url=f'https://example.com/{tag}', title=f'Bookmark {tag}',
                                notes=f'notes {tag}', tags='python,flask', category='tutorial',
                                extracted_text=f'full text of {tag}', scrape_status='SUCCESS')
        project = Project(user_id=user_id, title=f'Project {tag}', description='desc', technologies='python')
        db.session.add_all([bookmark, project])
        db.session.flush()
        task = Task(project_id=project.id, title=f'Task {tag}', description='task desc')
        db.session.add(task)
        db.session.flush()
        unique = uuid.uuid4().int % 10**12
        db.session.add_all([
            Subtask(task_id=task.id, title=f'Subtask {tag}', completed=1),
            ContentChunk(id=unique, content_id=bookmark.id, user_id=user_id, chunk_index=0,
                         text='chunk', embedding_model='test-model'),
            BookmarkMetadata(bookmark_id=bookmark.id, jsonb_payload={'og': tag}),
            ContentAnalysis(content_id=bookmark.id, analysis_data={'summary': tag}),
            UserFeedback(user_id=user_id, content_id=bookmark.id, feedback_type='positive',
                         context_data={'source': 'recommendations_page'}),
            TokenFamily(user_id=user_id, family_id=str(uuid.uuid4()), current_jti=str(uuid.uuid4())),
            BookmarkEvent(id=unique, event_id=uuid.uuid4().hex, bookmark_id=bookmark.id, user_id=user_id,
                          pipeline_run_id='run', type='bookmark.scraped'),
        ])
        db.session.commit()


def _row_counts(app, user_id):
    from sqlalchemy import func, select
    from models import (db, BookmarkEvent, BookmarkMetadata, ContentAnalysis, ContentChunk,
                        Project, SavedContent, Subtask, Task, TokenFamily, User, UserFeedback)
    with app.app_context():
        content_ids = select(SavedContent.id).where(SavedContent.user_id == user_id)
        project_ids = select(Project.id).where(Project.user_id == user_id)
        queries = {
            'users': select(func.count()).select_from(User).where(User.id == user_id),
            'saved_content': select(func.count()).select_from(SavedContent).where(SavedContent.user_id == user_id),
            'content_chunks': select(func.count()).select_from(ContentChunk).where(ContentChunk.user_id == user_id),
            'bookmark_metadata': select(func.count()).select_from(BookmarkMetadata)
                                 .where(BookmarkMetadata.bookmark_id.in_(content_ids)),
            'content_analysis': select(func.count()).select_from(ContentAnalysis)
                                .where(ContentAnalysis.content_id.in_(content_ids)),
            'user_feedback': select(func.count()).select_from(UserFeedback).where(UserFeedback.user_id == user_id),
            'projects': select(func.count()).select_from(Project).where(Project.user_id == user_id),
            'tasks': select(func.count()).select_from(Task).where(Task.project_id.in_(project_ids)),
            'subtasks': select(func.count()).select_from(Subtask).join(Task, Subtask.task_id == Task.id)
                        .where(Task.project_id.in_(project_ids)),
            'token_families': select(func.count()).select_from(TokenFamily).where(TokenFamily.user_id == user_id),
            'bookmark_events': select(func.count()).select_from(BookmarkEvent).where(BookmarkEvent.user_id == user_id),
        }
        return {name: db.session.scalar(query) for name, query in queries.items()}


def _orphan_counts(app):
    """Rows whose parent no longer exists (what a missing cascade would leave)."""
    from sqlalchemy import text
    from models import db
    checks = {
        'content_chunks': 'SELECT COUNT(*) FROM content_chunks c WHERE NOT EXISTS '
                          '(SELECT 1 FROM saved_content s WHERE s.id = c.content_id)',
        'subtasks': 'SELECT COUNT(*) FROM subtasks st WHERE NOT EXISTS (SELECT 1 FROM tasks t WHERE t.id = st.task_id)',
        'tasks': 'SELECT COUNT(*) FROM tasks t WHERE NOT EXISTS (SELECT 1 FROM projects p WHERE p.id = t.project_id)',
        'bookmark_metadata': 'SELECT COUNT(*) FROM bookmark_metadata m WHERE NOT EXISTS '
                             '(SELECT 1 FROM saved_content s WHERE s.id = m.bookmark_id)',
        'content_analysis': 'SELECT COUNT(*) FROM content_analysis a WHERE NOT EXISTS '
                            '(SELECT 1 FROM saved_content s WHERE s.id = a.content_id)',
    }
    with app.app_context():
        return {name: db.session.execute(text(sql)).scalar() for name, sql in checks.items()}


def _login(client, email, password):
    response = client.post('/api/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200, response.json
    return response.json


# --- Re-authentication ---

def test_wrong_password_is_rejected(client, app, test_user, auth_headers):
    response = client.delete('/api/account', json={'password': 'not-my-password'}, headers=auth_headers)
    assert response.status_code == 403  # not 401: that would make the SPA refresh and retry
    assert response.json['error'] == 'invalid_password'
    assert _row_counts(app, test_user['id'])['users'] == 1


def test_password_is_required(client, app, test_user, auth_headers):
    response = client.delete('/api/account', headers=auth_headers)
    assert response.status_code == 400
    assert _row_counts(app, test_user['id'])['users'] == 1


def test_oauth_account_needs_a_recent_sign_in(client, app):
    user_id = _make_user(app, provider_name='google', provider_user_id='google-del',
                         user_metadata={'supabase_user_id': 'supa-del'})
    headers = _bearer(app, user_id)
    later = time.time() + RECENT_SIGN_IN_SECONDS + 60
    with patch('blueprints.account.time.time', return_value=later):
        response = client.delete('/api/account', json={'password': 'anything'}, headers=headers)
    assert response.status_code == 403
    assert response.json['error'] == 'recent_sign_in_required'
    assert _row_counts(app, user_id)['users'] == 1

    # Just signed in: no password to ask for, and none needed.
    response = client.delete('/api/account', headers=headers)
    assert response.status_code == 200
    assert _row_counts(app, user_id)['users'] == 0


def test_refreshing_the_token_does_not_count_as_signing_in(client, app):
    """A refreshed access token has a fresh iat; the session itself began an hour ago."""
    from datetime import datetime, timedelta
    from models import db, TokenFamily
    user_id = _make_user(app, user_metadata={'supabase_user_id': 'supa-old'})
    with app.app_context():
        old, fresh = str(uuid.uuid4()), str(uuid.uuid4())
        db.session.add_all([
            TokenFamily(user_id=user_id, family_id=old, current_jti=str(uuid.uuid4()),
                        created_at=datetime.utcnow() - timedelta(hours=1)),
            TokenFamily(user_id=user_id, family_id=fresh, current_jti=str(uuid.uuid4()),
                        created_at=datetime.utcnow()),
        ])
        db.session.commit()
        stale_session = create_access_token(identity=str(user_id), additional_claims={'family_id': old})
        new_session = create_access_token(identity=str(user_id), additional_claims={'family_id': fresh})

    response = client.delete('/api/account', headers={'Authorization': f'Bearer {stale_session}'})
    assert response.status_code == 403
    assert response.json['error'] == 'recent_sign_in_required'
    assert client.delete('/api/account', headers={'Authorization': f'Bearer {new_session}'}).status_code == 200
    assert _row_counts(app, user_id)['users'] == 0


def test_oauth_account_that_set_a_password_must_give_it(client, app):
    from blueprints.auth import hash_password
    user_id = _make_user(app, password_hash=hash_password('chosen-pass-123'),
                         user_metadata={'supabase_user_id': 'supa-pw', 'password_set': True})
    headers = _bearer(app, user_id)
    assert client.delete('/api/account', headers=headers).status_code == 400
    assert client.delete('/api/account', json={'password': 'chosen-pass-123'}, headers=headers).status_code == 200


# --- Deletion ---

def test_deletion_removes_every_row_and_ends_the_session(client, app, test_user, other_user, patch_redis_for_tests):
    _populate(app, test_user['id'], 'mine')
    _populate(app, other_user['id'], 'theirs')
    session = _login(client, test_user['email'], test_user['password'])
    headers = {'Authorization': f"Bearer {session['access_token']}"}
    assert any(_row_counts(app, test_user['id']).values())

    revoked_keys = set()
    redis_client = patch_redis_for_tests.redis_client
    redis_client.setex.side_effect = lambda key, ttl, value: revoked_keys.add(key)
    redis_client.exists.side_effect = lambda key: int(key in revoked_keys)

    response = client.delete('/api/account', json={'password': test_user['password']}, headers=headers)
    assert response.status_code == 200
    assert 'access_token_cookie=;' in ' '.join(response.headers.getlist('Set-Cookie'))

    assert _row_counts(app, test_user['id']) == {name: 0 for name in _row_counts(app, test_user['id'])}
    assert all(count == 1 for count in _row_counts(app, other_user['id']).values())
    assert not any(_orphan_counts(app).values())

    assert client.get('/api/auth/verify', headers=headers).status_code == 401
    assert client.get('/api/profile', headers=headers).status_code == 401
    refreshed = client.post('/api/auth/refresh', headers={'Authorization': f"Bearer {session['refresh_token']}"})
    assert refreshed.status_code == 401


def test_token_of_a_deleted_user_finds_nothing_even_without_redis(client, app, test_user, auth_headers):
    """The Redis blocklist fails open; the account itself must still be gone."""
    response = client.delete('/api/account', json={'password': test_user['password']}, headers=auth_headers)
    assert response.status_code == 200
    assert client.get('/api/auth/verify', headers=auth_headers).status_code == 404
    assert client.get('/api/profile', headers=auth_headers).status_code == 404


def test_deletion_purges_the_users_redis_data(client, test_user, auth_headers, patch_redis_for_tests):
    uid = test_user['id']
    redis_client = patch_redis_for_tests.redis_client
    scanned = []

    def scan(cursor=0, match=None, count=None):
        scanned.append(match)
        return 0, [match.replace('*', 'found')]
    redis_client.scan.side_effect = scan

    response = client.delete('/api/account', json={'password': test_user['password']}, headers=auth_headers)
    assert response.status_code == 200

    deleted = {key for call in redis_client.delete.call_args_list for key in call.args}
    for key in (f'profile:{uid}', f'dashboard:v1:summary:{uid}', f'dashboard:stats:{uid}',
                f'user_context:{uid}', f'unified_recommendations:{uid}', f'fuze:events:stream:{uid}',
                f'import_progress:{uid}', f'analysis_progress:{uid}'):
        assert key in deleted
    expected_patterns = {f'bookmarks:{uid}:*', f'projects:{uid}:*', f'fuze:rate:{uid}:*',
                         f'fuze:system_key_uses:{uid}:*', f'login_fail:{uid}:*'}
    assert set(scanned) == expected_patterns
    for pattern in expected_patterns:
        assert pattern.replace('*', 'found') in deleted


def test_redis_failure_does_not_block_deletion(client, app, test_user, auth_headers, patch_redis_for_tests):
    redis_client = patch_redis_for_tests.redis_client
    redis_client.delete.side_effect = ConnectionError('redis down')
    redis_client.scan.side_effect = ConnectionError('redis down')
    redis_client.setex.side_effect = ConnectionError('redis down')

    response = client.delete('/api/account', json={'password': test_user['password']}, headers=auth_headers)
    assert response.status_code == 200
    assert _row_counts(app, test_user['id'])['users'] == 0


def test_deletion_requires_a_session(client):
    assert client.delete('/api/account', json={'password': 'x'}).status_code == 401


# --- Export ---

def test_export_contains_the_users_data_and_nothing_else(client, app, test_user, other_user, auth_headers):
    _populate(app, test_user['id'], 'mine')
    _populate(app, other_user['id'], 'theirs')

    response = client.get('/api/account/export', headers=auth_headers)
    assert response.status_code == 200
    disposition = response.headers['Content-Disposition']
    assert disposition.startswith('attachment; filename=fuze-export-') and disposition.endswith('.json')

    raw = response.get_data(as_text=True)
    data = json.loads(raw)
    assert data['profile']['id'] == test_user['id']
    assert data['profile']['email'] == test_user['email']

    [bookmark] = data['bookmarks']
    assert bookmark['url'] == 'https://example.com/mine'
    assert bookmark['notes'] == 'notes mine'
    assert bookmark['extracted_text'] == 'full text of mine'
    assert bookmark['saved_at'].endswith('Z')

    [project] = data['projects']
    [task] = project['tasks']
    [subtask] = task['subtasks']
    assert (project['title'], task['title'], subtask['title']) == ('Project mine', 'Task mine', 'Subtask mine')
    assert subtask['completed'] is True
    assert data['recommendation_feedback'][0]['context'] == {'source': 'recommendations_page'}

    # No secrets, no internals, nothing of anyone else's.
    with app.app_context():
        from models import db, User
        password_hash = db.session.get(User, test_user['id']).password_hash
    for forbidden in (password_hash, SECRET_API_KEY, 'hash-mine', 'password_hash', 'embedding',
                      'family_id', 'current_jti', 'user_metadata', 'theirs'):
        assert forbidden not in raw


def test_export_requires_a_session(client):
    assert client.get('/api/account/export').status_code == 401
