"""GET /api/bookmarks/lookup?url=...: exact-URL lookup the extension uses before deleting by id."""
import uuid
from urllib.parse import quote

from flask_jwt_extended import create_access_token


def _headers(app, user_id):
    with app.app_context():
        return {'Authorization': f'Bearer {create_access_token(identity=str(user_id))}'}


def _make_user(app, tag):
    from models import db, User
    from blueprints.auth import hash_password
    with app.app_context():
        user = User(username=f'lookup_{tag}', email=f'lookup_{tag}@example.com', password_hash=hash_password('pw-123456'))
        db.session.add(user)
        db.session.commit()
        return user.id


def _save(app, user_id, url, title='Saved'):
    from models import db, SavedContent
    with app.app_context():
        bookmark = SavedContent(user_id=user_id, url=url, title=title)
        db.session.add(bookmark)
        db.session.commit()
        return bookmark.id


def test_lookup_matches_the_exact_url_without_lowercasing(app, client, test_user):
    url = f'https://Example.com/Docs/{uuid.uuid4().hex}/Page%20One?Id=7&b=2'
    bookmark_id = _save(app, test_user['id'], url)
    headers = _headers(app, test_user['id'])

    resp = client.get(f'/api/bookmarks/lookup?url={quote(url, safe="")}', headers=headers)
    assert resp.status_code == 200, resp.get_json()
    assert resp.json['bookmark']['id'] == bookmark_id
    assert resp.json['bookmark']['url'] == url

    # A different spelling of the same resource is a different URL here.
    assert client.get(f'/api/bookmarks/lookup?url={quote(url.lower(), safe="")}', headers=headers).status_code == 404


def test_lookup_never_returns_another_users_bookmark(app, client, test_user):
    other_id = _make_user(app, uuid.uuid4().hex[:8])
    url = f'https://example.com/private/{uuid.uuid4().hex}'
    _save(app, other_id, url, title='Their bookmark')

    resp = client.get(f'/api/bookmarks/lookup?url={quote(url, safe="")}', headers=_headers(app, test_user['id']))
    assert resp.status_code == 404
    assert 'Their bookmark' not in resp.get_data(as_text=True)


def test_lookup_requires_a_url(app, client, test_user):
    assert client.get('/api/bookmarks/lookup', headers=_headers(app, test_user['id'])).status_code == 400


def test_lookup_requires_auth(client):
    assert client.get('/api/bookmarks/lookup?url=https%3A%2F%2Fexample.com').status_code == 401


def test_delete_by_url_path_keeps_percent_escapes_in_the_saved_url(app, client, test_user):
    """The path is decoded once by the server; a second decode turned '%20' into ' ' and missed."""
    from models import db, SavedContent
    url = f'https://example.com/docs/{uuid.uuid4().hex}/Page%20One?q=a%2Fb'
    bookmark_id = _save(app, test_user['id'], url)
    headers = _headers(app, test_user['id'])

    resp = client.delete(f'/api/bookmarks/url/{quote(url, safe="")}', headers=headers)
    assert resp.status_code == 200, resp.get_json()
    with app.app_context():
        assert db.session.get(SavedContent, bookmark_id) is None


def test_delete_by_url_path_repairs_a_collapsed_scheme(app, client, test_user):
    """A proxy that merges '//' leaves 'https:/host/...' in the path."""
    from models import db, SavedContent
    url = f'https://example.com/{uuid.uuid4().hex}'
    bookmark_id = _save(app, test_user['id'], url)
    headers = _headers(app, test_user['id'])

    collapsed = url.replace('https://', 'https:/')
    resp = client.delete(f'/api/bookmarks/url/{collapsed}', headers=headers)
    assert resp.status_code == 200, resp.get_json()
    with app.app_context():
        assert db.session.get(SavedContent, bookmark_id) is None
