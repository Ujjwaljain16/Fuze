"""Google sign-in must never hand an existing password account to whoever controls the Google identity, or vice versa."""
from unittest.mock import MagicMock, patch

import pytest

CONFIRMED = '2026-01-01T00:00:00Z'


@pytest.fixture(autouse=True)
def supabase_env(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://supabase.example')
    monkeypatch.setenv('SUPABASE_ANON_KEY', 'anon')


def _supabase_returns(user_payload, status=200):
    resp = MagicMock(status_code=status)
    resp.json.return_value = user_payload
    return patch('blueprints.auth.requests.get', return_value=resp)


def _oauth(client, payload):
    with _supabase_returns(payload):
        return client.post('/api/auth/supabase-oauth', json={'access_token': 'supa-token'})


def test_pre_registered_password_account_is_not_taken_over(client, test_user):
    """Attacker registers the victim's email with a password; the victim then uses Google."""
    response = _oauth(client, {'id': 'google-victim', 'email': test_user['email'], 'email_confirmed_at': CONFIRMED})
    assert response.status_code == 409
    assert response.json['error'] == 'account_link_required'
    assert 'access_token' not in response.json


def test_unverified_provider_email_is_rejected(client):
    response = _oauth(client, {'id': 'google-x', 'email': 'new-person@example.com'})
    assert response.status_code == 403


def test_new_google_user_is_created_then_signs_back_in(client):
    payload = {'id': 'google-new', 'email': 'brand-new@example.com', 'email_confirmed_at': CONFIRMED}
    first = _oauth(client, payload)
    second = _oauth(client, payload)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json['user']['id'] == second.json['user']['id']
    assert second.json['refresh_token']


def test_owner_links_google_after_signing_in_with_password(client, login_headers, test_user):
    payload = {'id': 'google-owner', 'email': test_user['email'], 'email_confirmed_at': CONFIRMED}
    with _supabase_returns(payload):
        linked = client.post('/api/auth/link-oauth', json={'access_token': 'supa-token'}, headers=login_headers)
    assert linked.status_code == 200

    response = _oauth(client, payload)
    assert response.status_code == 200
    assert response.json['user']['id'] == test_user['id']


def test_link_rejects_a_google_account_with_another_email(client, login_headers):
    payload = {'id': 'google-other', 'email': 'someone-else@example.com', 'email_confirmed_at': CONFIRMED}
    with _supabase_returns(payload):
        response = client.post('/api/auth/link-oauth', json={'access_token': 'supa-token'}, headers=login_headers)
    assert response.status_code == 403


def test_link_requires_a_session(client):
    with _supabase_returns({'id': 'g', 'email': 'a@example.com', 'email_confirmed_at': CONFIRMED}):
        response = client.post('/api/auth/link-oauth', json={'access_token': 'supa-token'})
    assert response.status_code == 401
