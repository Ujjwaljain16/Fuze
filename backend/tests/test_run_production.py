import pytest
from werkzeug.exceptions import NotFound, Unauthorized
from run_production import sanitize_headers, create_app


@pytest.mark.unit
def test_sanitize_headers_redacts_tokens():
    raw_headers = {
        'Host': 'localhost:5000',
        'Authorization': 'Bearer secret_jwt_token_123',
        'Cookie': 'session=abc123secret',
        'X-API-Key': 'gemini_secret_key',
        'Content-Type': 'application/json'
    }

    clean = sanitize_headers(raw_headers)
    assert clean['Authorization'] == '[REDACTED]'
    assert clean['Cookie'] == '[REDACTED]'
    assert clean['X-API-Key'] == '[REDACTED]'
    assert clean['Host'] == 'localhost:5000'
    assert clean['Content-Type'] == 'application/json'


@pytest.mark.unit
def test_create_app_health_endpoint():
    app = create_app('testing')
    client = app.test_client()

    response = client.get('/api/health')
    assert response.status_code in (200, 500)
    data = response.get_json()
    assert 'database' in data
    assert 'status' in data


@pytest.mark.unit
def test_httpexception_passthrough():
    app = create_app('testing')
    client = app.test_client()

    # Non-existent endpoint should return 404, not 500
    response = client.get('/api/non_existent_route_12345')
    assert response.status_code == 404
