"""Races that only a real database can show. Skipped on SQLite (the default lane)."""
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def postgres_only(app):
    from models import db
    with app.app_context():
        if db.engine.dialect.name != 'postgresql':
            pytest.skip('needs Postgres (run with TEST_DATABASE_URL=postgresql://...localhost...)')


def _parallel(app, fn, n):
    def run(_):
        with app.test_client() as c:
            return fn(c)
    with ThreadPoolExecutor(max_workers=n) as pool:
        return list(pool.map(run, range(n)))


def test_concurrent_saves_of_one_url_create_one_bookmark(app, test_user, auth_headers):
    from models import SavedContent
    url = 'https://example.com/raced-save'
    with patch('blueprints.bookmarks.process_bookmark_content_async'):
        responses = _parallel(app, lambda c: c.post('/api/bookmarks', json={'url': url, 'title': 'Race'},
                                                    headers=auth_headers), 6)
    assert sorted({r.status_code for r in responses}) <= [200, 201], [r.get_json() for r in responses]
    with app.app_context():
        assert SavedContent.query.filter_by(user_id=test_user['id'], url=url).count() == 1
    ids = {r.get_json()['bookmark']['id'] for r in responses}
    assert len(ids) == 1


def test_concurrent_refreshes_mint_at_most_one_new_pair(app, client, test_user):
    login = client.post('/api/auth/login', json={'email': test_user['email'], 'password': test_user['password']})
    refresh = login.get_json()['refresh_token']
    responses = _parallel(app, lambda c: c.post('/api/auth/refresh', headers={'Authorization': f'Bearer {refresh}'}), 4)
    assert [r.status_code for r in responses].count(200) <= 1


def test_connections_carry_a_statement_timeout(app):
    """A runaway query is cancelled by Postgres instead of holding a worker and a connection."""
    from sqlalchemy import text
    from models import db
    with app.app_context():
        with db.engine.connect() as conn:
            assert conn.execute(text('SHOW statement_timeout')).scalar() == '15s'
