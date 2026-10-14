"""A body over MAX_REQUEST_BYTES is refused with 413, not turned into a 500 by a handler's broad except."""
import pytest


@pytest.fixture
def small_limit(app):
    previous = app.config.get('MAX_CONTENT_LENGTH')
    app.config['MAX_CONTENT_LENGTH'] = 1000
    yield 1000
    app.config['MAX_CONTENT_LENGTH'] = previous


@pytest.mark.parametrize('path', ['/api/auth/login', '/api/auth/register', '/api/bookmarks'])
def test_oversized_bodies_get_413_on_every_kind_of_route(client, small_limit, path):
    response = client.post(path, data='x' * (small_limit + 1), content_type='application/json')
    assert response.status_code == 413, (path, response.status_code, response.get_data(as_text=True)[:200])
    assert response.get_json()['error'] == 'payload_too_large'


def test_a_body_within_the_limit_still_reaches_the_handler(client, small_limit):
    response = client.post('/api/auth/login', json={'email': 'nobody@example.com', 'password': 'wrongwrong1'})
    assert response.status_code in (400, 401, 429)      # handled by the login route, not refused by size
