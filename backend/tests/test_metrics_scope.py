"""The performance metrics endpoint reports the caller's own counts, not every user's."""
import uuid

import pytest


@pytest.fixture
def stranger(app):
    from models import db, User
    from blueprints.auth import hash_password
    with app.app_context():
        tag = uuid.uuid4().hex[:8]
        user = User(username=f'met_{tag}', email=f'met_{tag}@example.com', password_hash=hash_password('pw123456'))
        db.session.add(user)
        db.session.commit()
        yield {'id': user.id}
        db.session.delete(user)
        db.session.commit()


@pytest.fixture(autouse=True)
def plain_cache_stats(monkeypatch):
    """The test Redis is a mock; its stats object cannot be turned into JSON."""
    from utils.redis_utils import redis_cache
    monkeypatch.setattr(redis_cache, 'get_cache_stats', lambda: {}, raising=False)


def _metrics(client, auth_headers):
    response = client.get('/api/recommendations/performance-metrics', headers=auth_headers)
    assert response.status_code == 200, response.get_json()
    return response.get_json()['database']


def test_other_users_bookmarks_are_not_counted(app, client, auth_headers, test_user, stranger):
    from models import db, SavedContent
    before = _metrics(client, auth_headers)['total_content']
    with app.app_context():
        tag = uuid.uuid4().hex[:6]
        db.session.add_all(SavedContent(user_id=stranger['id'], url=f'https://e.com/{tag}/{i}', title=f'Theirs {i}',
                                        extracted_text='x') for i in range(3))
        db.session.add(SavedContent(user_id=test_user['id'], url=f'https://e.com/{tag}/mine', title='Mine',
                                    extracted_text='y'))
        db.session.commit()
    after = _metrics(client, auth_headers)
    assert after['total_content'] == before + 1     # only the caller's new bookmark
    assert 0 <= after['analysis_coverage'] <= 100
