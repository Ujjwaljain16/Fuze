"""Duplicate detection must treat query params that identify a resource as part of its identity."""
import pytest


def _save(app, user_id, url):
    from models import db, SavedContent
    with app.app_context():
        db.session.add(SavedContent(user_id=user_id, url=url, title=url))
        db.session.commit()


def _check(client, auth_headers, url):
    response = client.post('/api/bookmarks/check-duplicate', json={'url': url}, headers=auth_headers)
    assert response.status_code == 200
    return response.json


@pytest.mark.parametrize('saved,candidate', [
    ('https://www.youtube.com/watch?v=AAA', 'https://www.youtube.com/watch?v=BBB'),
    ('https://news.ycombinator.com/item?id=1', 'https://news.ycombinator.com/item?id=2'),
    ('https://example.com/search?q=rust', 'https://example.com/search'),
])
def test_different_resources_are_not_duplicates(client, auth_headers, test_user, app, saved, candidate):
    _save(app, test_user['id'], saved)
    assert _check(client, auth_headers, candidate)['isDuplicate'] is False


@pytest.mark.parametrize('saved,candidate', [
    ('https://www.youtube.com/watch?v=AAA', 'https://www.youtube.com/watch?v=AAA&utm_source=twitter'),
    ('https://www.youtube.com/watch?v=AAA&utm_source=twitter', 'https://www.youtube.com/watch?v=AAA'),
    ('https://example.com/post', 'https://Example.com/post/#comments'),
    ('https://example.com/list?a=1&b=2', 'https://example.com/list?b=2&a=1'),
])
def test_variants_of_the_same_resource_are_duplicates(client, auth_headers, test_user, app, saved, candidate):
    _save(app, test_user['id'], saved)
    data = _check(client, auth_headers, candidate)
    assert data['isDuplicate'] is True
    assert data['existingBookmark']['url'] == saved


def test_saving_a_different_video_creates_a_new_bookmark(client, auth_headers, test_user, app):
    from unittest.mock import patch
    _save(app, test_user['id'], 'https://www.youtube.com/watch?v=AAA')
    with patch('blueprints.bookmarks.process_bookmark_content_async'):
        response = client.post('/api/bookmarks', json={'url': 'https://www.youtube.com/watch?v=BBB', 'title': 'B'},
                               headers=auth_headers)
    assert response.status_code == 201
    assert response.json['bookmark']['url'] == 'https://www.youtube.com/watch?v=BBB'
