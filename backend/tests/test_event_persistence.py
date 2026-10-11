"""Pipeline events are persisted to bookmark_events (the audit trail and SSE replay fallback)."""


def test_published_events_are_stored(app, test_user):
    from models import db, BookmarkEvent, SavedContent
    from utils.event_bus import publish_pipeline_event
    with app.app_context():
        bm = SavedContent(user_id=test_user['id'], url='https://e.com/evt', title='e')
        db.session.add(bm)
        db.session.commit()
        before = BookmarkEvent.query.filter_by(bookmark_id=bm.id).count()
        publish_pipeline_event(event_type='bookmark.pipeline.scraping.started', bookmark_id=bm.id,
                               user_id=test_user['id'], pipeline_run_id='run-1', sequence=1)
        db.session.expire_all()
        assert BookmarkEvent.query.filter_by(bookmark_id=bm.id).count() == before + 1
