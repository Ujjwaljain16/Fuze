"""Inputs longer than their columns are rejected with a 400 or trimmed, never a 500."""
import pytest


def test_project_title_over_the_column_is_a_400(client, auth_headers):
    response = client.post('/api/projects', json={'title': 'x' * 101, 'description': 'd'}, headers=auth_headers)
    assert response.status_code == 400


def test_task_title_over_the_column_is_a_400(client, auth_headers, app, test_user):
    from models import db, Project
    with app.app_context():
        project = Project(user_id=test_user['id'], title='p')
        db.session.add(project)
        db.session.commit()
        project_id = project.id
    response = client.post('/api/tasks', json={'project_id': project_id, 'title': 'x' * 101}, headers=auth_headers)
    assert response.status_code == 400


def test_over_long_url_is_a_400(client, auth_headers):
    url = 'https://example.com/?q=' + 'a' * 3000
    response = client.post('/api/bookmarks', json={'url': url, 'title': 't'}, headers=auth_headers)
    assert response.status_code == 400


def test_derived_values_are_trimmed_to_their_columns(app, test_user):
    """e.g. an arXiv paper with 40 authors joined into one string, or a 300-char page title."""
    from models import db, SavedContent
    with app.app_context():
        bm = SavedContent(user_id=test_user['id'], url='https://arxiv.org/abs/1', title='T' * 300,
                          author=', '.join(['Author Name'] * 40), category='c' * 150)
        db.session.add(bm)
        db.session.commit()
        db.session.refresh(bm)
        assert len(bm.title) == 200 and len(bm.author) == 255 and len(bm.category) == 100
        bm.author = 'A' * 400
        db.session.commit()
        db.session.refresh(bm)
        assert len(bm.author) == 255
