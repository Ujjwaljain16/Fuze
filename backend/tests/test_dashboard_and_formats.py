"""Dashboard counters reflect real pipeline state; responses carry unambiguous values."""
from datetime import datetime, timezone

from flask_jwt_extended import create_access_token

from utils.timefmt import iso_utc


def test_timestamps_are_marked_utc():
    assert iso_utc(datetime(2026, 10, 12, 10, 0, 0)) == '2026-10-12T10:00:00Z'
    assert iso_utc(datetime(2026, 10, 12, 10, 0, tzinfo=timezone.utc)) == '2026-10-12T10:00:00Z'
    assert iso_utc(None) is None


def test_dashboard_counts_pending_work_and_processed_items(client, app, test_user, patch_redis_for_tests):
    from models import db, SavedContent
    with app.app_context():
        db.session.add_all([
            SavedContent(user_id=test_user['id'], url='https://e.com/1', title='1',
                         scrape_status='SUCCESS', embedding_status='SUCCESS'),
            SavedContent(user_id=test_user['id'], url='https://e.com/2', title='2', scrape_status='PENDING'),
            SavedContent(user_id=test_user['id'], url='https://e.com/3', title='3',
                         scrape_status='SUCCESS', embedding_status='PENDING'),
        ])
        db.session.commit()
        token = create_access_token(identity=str(test_user['id']))
    body = client.get('/api/dashboard/summary', headers={'Authorization': f'Bearer {token}'}).get_json()
    text = str(body)
    assert "'scraping': 1" in text and "'embedding': 1" in text  # used to be 0: RUNNING is never set


def test_json_null_is_not_stored_as_the_string_none(client, auth_headers, app, test_user):
    from unittest.mock import patch
    from models import SavedContent
    with patch('blueprints.bookmarks.process_bookmark_content_async'):
        client.post('/api/bookmarks', json={'url': 'https://e.com/null', 'title': 'T', 'description': None},
                    headers=auth_headers)
    with app.app_context():
        row = SavedContent.query.filter_by(user_id=test_user['id'], url='https://e.com/null').one()
        assert row.notes != 'None'
