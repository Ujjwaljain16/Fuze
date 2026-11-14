"""Deleting a bookmark that has been analysed used to return 500: SQLAlchemy tried to set
content_analysis.content_id to NULL (a NOT NULL column) instead of letting the database cascade the delete."""
import uuid

import pytest


def _bookmark_with_children(app, user_id):
    from models import db, SavedContent, ContentAnalysis, UserFeedback, BookmarkEvent, BookmarkMetadata
    with app.app_context():
        bm = SavedContent(user_id=user_id, url='https://example.com/analysed', title='Analysed', extracted_text='text')
        db.session.add(bm)
        db.session.flush()
        db.session.add_all([
            ContentAnalysis(content_id=bm.id, analysis_data={'summary': 's'}),
            UserFeedback(user_id=user_id, content_id=bm.id, feedback_type='positive'),
            BookmarkEvent(event_id=uuid.uuid4().hex, bookmark_id=bm.id, user_id=user_id,
                          pipeline_run_id='run-1', type='BookmarkCreated'),
            BookmarkMetadata(bookmark_id=bm.id, jsonb_payload={'og': {}}),
        ])
        db.session.commit()
        return bm.id


def _count(app, model, column, value):
    from models import db
    with app.app_context():
        return db.session.query(model).filter(column == value).count()


def test_an_analysed_bookmark_can_be_deleted(app, client, auth_headers, test_user):
    from models import SavedContent, ContentAnalysis
    bookmark_id = _bookmark_with_children(app, test_user['id'])

    response = client.delete(f'/api/bookmarks/{bookmark_id}', headers=auth_headers)

    assert response.status_code == 200, response.get_data(as_text=True)
    assert _count(app, SavedContent, SavedContent.id, bookmark_id) == 0
    assert _count(app, ContentAnalysis, ContentAnalysis.content_id, bookmark_id) == 0


def test_deleting_by_url_works_for_an_analysed_bookmark_too(app, client, auth_headers, test_user):
    from models import SavedContent
    bookmark_id = _bookmark_with_children(app, test_user['id'])

    response = client.delete('/api/bookmarks/url/https://example.com/analysed', headers=auth_headers)

    assert response.status_code == 200, response.get_data(as_text=True)
    assert _count(app, SavedContent, SavedContent.id, bookmark_id) == 0


def test_the_database_removes_every_other_child_row(app, client, auth_headers, test_user):
    """Feedback, events and metadata are removed by ON DELETE CASCADE; SQLite does not enforce foreign keys,
    so this is only checked where the database does (the Postgres lane in CI)."""
    from models import db, UserFeedback, BookmarkEvent, BookmarkMetadata
    with app.app_context():
        if db.engine.url.get_backend_name() != 'postgresql':
            pytest.skip('foreign keys are enforced on Postgres only')
    bookmark_id = _bookmark_with_children(app, test_user['id'])

    assert client.delete(f'/api/bookmarks/{bookmark_id}', headers=auth_headers).status_code == 200

    assert _count(app, UserFeedback, UserFeedback.content_id, bookmark_id) == 0
    assert _count(app, BookmarkEvent, BookmarkEvent.bookmark_id, bookmark_id) == 0
    assert _count(app, BookmarkMetadata, BookmarkMetadata.bookmark_id, bookmark_id) == 0
