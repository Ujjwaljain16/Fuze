"""One user must never see another user's data through any endpoint."""
import uuid

import pytest
from flask_jwt_extended import create_access_token


@pytest.fixture
def other_user(app):
    from models import db, User
    from blueprints.auth import hash_password
    with app.app_context():
        tag = uuid.uuid4().hex[:8]
        user = User(username=f'victim_{tag}', email=f'victim_{tag}@example.com', password_hash=hash_password('pw123456'))
        db.session.add(user)
        db.session.commit()
        yield {'id': user.id}
        db.session.delete(user)
        db.session.commit()


def test_feedback_cannot_reference_another_users_project(client, app, test_user, other_user):
    from models import db, Project, SavedContent, UserFeedback
    with app.app_context():
        victim_project = Project(user_id=other_user['id'], title='Secret launch', description='Unreleased plans',
                                 technologies='internal-stack')
        own_bookmark = SavedContent(user_id=test_user['id'], url='https://example.com/a', title='A')
        db.session.add_all([victim_project, own_bookmark])
        db.session.commit()
        project_id, bookmark_id = victim_project.id, own_bookmark.id
        headers = {'Authorization': f"Bearer {create_access_token(identity=str(test_user['id']))}"}

    response = client.post('/api/recommendations/feedback', headers=headers, json={
        'recommendation_id': bookmark_id, 'feedback_type': 'positive',
        'feedback_data': {'project_id': project_id, 'source': 'recommendations_page', 'nested': {'x': 1}},
    })
    assert response.status_code == 200

    with app.app_context():
        stored = db.session.get(UserFeedback, response.json['feedback_id']).context_data
    assert stored == {'source': 'recommendations_page'}

    response = client.get('/api/recommendations/suggested-contexts', headers=headers)
    assert 'Secret launch' not in response.get_data(as_text=True)


def test_suggested_contexts_ignore_foreign_project_ids_already_stored(client, app, test_user, other_user):
    """Rows written before the write-side check must not leak either."""
    from models import db, Project, SavedContent, UserFeedback
    with app.app_context():
        victim_project = Project(user_id=other_user['id'], title='Secret launch')
        own_bookmark = SavedContent(user_id=test_user['id'], url='https://example.com/b', title='B')
        db.session.add_all([victim_project, own_bookmark])
        db.session.commit()
        db.session.add(UserFeedback(user_id=test_user['id'], content_id=own_bookmark.id, feedback_type='helpful',
                                    context_data={'project_id': victim_project.id}))
        db.session.commit()
        headers = {'Authorization': f"Bearer {create_access_token(identity=str(test_user['id']))}"}

    response = client.get('/api/recommendations/suggested-contexts', headers=headers)
    assert response.status_code == 200
    assert 'Secret launch' not in response.get_data(as_text=True)


def test_feedback_keeps_own_project_reference(client, app, test_user):
    from models import db, Project, SavedContent, UserFeedback
    with app.app_context():
        project = Project(user_id=test_user['id'], title='Mine')
        bookmark = SavedContent(user_id=test_user['id'], url='https://example.com/c', title='C')
        db.session.add_all([project, bookmark])
        db.session.commit()
        project_id, bookmark_id = project.id, bookmark.id
        headers = {'Authorization': f"Bearer {create_access_token(identity=str(test_user['id']))}"}

    response = client.post('/api/recommendations/feedback', headers=headers, json={
        'recommendation_id': bookmark_id, 'feedback_type': 'positive', 'feedback_data': {'project_id': project_id}})
    with app.app_context():
        assert db.session.get(UserFeedback, response.json['feedback_id']).context_data == {'project_id': project_id}
