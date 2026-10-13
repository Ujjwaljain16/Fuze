"""A thumbs up is "useful for THIS project": the project is stored with the feedback."""
import uuid

import pytest
from sqlalchemy import select, text


@pytest.fixture
def other_user(app):
    from models import db, User
    from blueprints.auth import hash_password
    with app.app_context():
        tag = uuid.uuid4().hex[:8]
        user = User(username=f'fb_other_{tag}', email=f'fb_other_{tag}@example.com',
                    password_hash=hash_password('pw123456'))
        db.session.add(user)
        db.session.commit()
        yield {'id': user.id}
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def first_new_id(app):
    """Feedback ids at or below this existed before the test: SQLite reuses ids and does not cascade
    deletes, so rows of earlier tests could otherwise show up under a reused bookmark id."""
    from models import db, UserFeedback
    from sqlalchemy import func
    with app.app_context():
        return (db.session.scalar(select(func.max(UserFeedback.id))) or 0) + 1


def _make(app, user_id, tag):
    from models import db, Project, SavedContent
    with app.app_context():
        bookmark = SavedContent(user_id=user_id, url=f'https://example.com/{tag}-{uuid.uuid4().hex[:6]}',
                                title=f'Bookmark {tag}')
        project = Project(user_id=user_id, title=f'Project {tag}', description='d', technologies='python')
        db.session.add_all([bookmark, project])
        db.session.commit()
        return bookmark.id, project.id


def _rows(app, user_id, bookmark_id, first_new_id):
    """(project_id, context) of this user's feedback on one bookmark given in this test, oldest first."""
    from models import db, UserFeedback
    with app.app_context():
        db.session.expire_all()
        return [(f.project_id, f.context_data or {}) for f in db.session.scalars(
            select(UserFeedback).where(UserFeedback.user_id == user_id, UserFeedback.content_id == bookmark_id,
            UserFeedback.id >= first_new_id)
            .order_by(UserFeedback.id))]


def _send(client, headers, bookmark_id, feedback_type, data):
    return client.post('/api/recommendations/feedback', headers=headers, json={
        'recommendation_id': bookmark_id, 'feedback_type': feedback_type, 'feedback_data': data})


def test_feedback_is_stored_with_the_project_it_was_given_for(app, client, test_user, auth_headers, first_new_id):
    bookmark, project = _make(app, test_user['id'], 'own')
    response = _send(client, auth_headers, bookmark, 'positive',
                     {'project_id': project, 'position': 3, 'score': 82.5, 'source': 'recommendations_page'})
    assert response.status_code == 200, response.get_json()
    [(project_id, context)] = _rows(app, test_user['id'], bookmark, first_new_id)
    assert project_id == project
    assert context['position'] == 3 and context['score'] == 82.5   # rank and score, for position-aware metrics


def test_the_same_bookmark_can_be_judged_differently_for_two_projects(app, client, test_user, auth_headers, first_new_id):
    bookmark, first = _make(app, test_user['id'], 'a')
    _, second = _make(app, test_user['id'], 'b')
    _send(client, auth_headers, bookmark, 'positive', {'project_id': first})
    _send(client, auth_headers, bookmark, 'negative', {'project_id': second})
    assert [p for p, _ in _rows(app, test_user['id'], bookmark, first_new_id)] == [first, second]


def test_a_project_the_user_does_not_own_is_never_stored(app, client, test_user, other_user, auth_headers, first_new_id):
    bookmark, _ = _make(app, test_user['id'], 'mine')
    _, someone_elses = _make(app, other_user['id'], 'theirs')
    _send(client, auth_headers, bookmark, 'positive', {'project_id': someone_elses})
    [(project_id, context)] = _rows(app, test_user['id'], bookmark, first_new_id)
    assert project_id is None and 'project_id' not in context


def test_feedback_without_a_project_still_works(app, client, test_user, auth_headers, first_new_id):
    bookmark, _ = _make(app, test_user['id'], 'plain')
    assert _send(client, auth_headers, bookmark, 'negative', {'source': 'recommendations_page'}).status_code == 200
    [(project_id, _)] = _rows(app, test_user['id'], bookmark, first_new_id)
    assert project_id is None


def test_deleting_a_project_keeps_the_judgment_of_the_bookmark(app, client, test_user, auth_headers, first_new_id):
    from models import db
    with app.app_context():
        if db.engine.dialect.name != 'postgresql':
            pytest.skip('needs Postgres: SQLite does not enforce ON DELETE SET NULL here')
    bookmark, project = _make(app, test_user['id'], 'del')
    _send(client, auth_headers, bookmark, 'positive', {'project_id': project})
    with app.app_context():
        db.session.execute(text('DELETE FROM projects WHERE id = :p'), {'p': project})
        db.session.commit()
    [(project_id, _)] = _rows(app, test_user['id'], bookmark, first_new_id)
    assert project_id is None
