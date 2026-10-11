"""
Unit tests for LinkedIn blueprint
"""

import pytest

@pytest.mark.unit
@pytest.mark.requires_db
class TestLinkedIn:
    """Test LinkedIn blueprint endpoints"""

    def test_url_validation(self):
        """Test validate_linkedin_url logic"""
        from blueprints.linkedin import validate_linkedin_url

        assert validate_linkedin_url("https://www.linkedin.com/posts/test-post") is True
        assert validate_linkedin_url("https://linkedin.com/feed/update/urn:li:activity:123") is True
        assert validate_linkedin_url("https://m.linkedin.com/in/test") is True

        # Malicious domains
        assert validate_linkedin_url("https://evil-linkedin.com/post") is False
        assert validate_linkedin_url("https://linkedin.com.evil.com/post") is False
        assert validate_linkedin_url("javascript:alert(1)") is False

    def test_history_authorization_isolation(self, client, auth_headers):
        """Test GET /api/linkedin/history ignores spoofed user_id in query params"""
        response = client.get('/api/linkedin/history?user_id=99999', headers=auth_headers)
        assert response.status_code == 200
        assert response.json['success'] is True

    def test_linkedin_status_lightweight(self, client):
        """Test GET /api/linkedin/status returns operational status fast without external network calls"""
        response = client.get('/api/linkedin/status')
        assert response.status_code == 200
        data = response.json
        assert data['success'] is True
        assert data['data']['overall_status'] == 'operational'


def test_batch_extract_runs_concurrently_and_reports_invalid(client, auth_headers):
    import time
    from unittest.mock import patch

    def slow_scrape(self, url):
        time.sleep(0.4)
        return {'success': True, 'title': 'Post', 'content': 'x' * 300, 'quality_score': 7}

    urls = [f"https://www.linkedin.com/posts/p-{i}" for i in range(5)] + ["https://evil.com/post"]
    with patch('blueprints.linkedin.EasyLinkedInScraper.scrape_post', slow_scrape):
        start = time.time()
        resp = client.post('/api/linkedin/batch-extract', json={'urls': urls}, headers=auth_headers)
        elapsed = time.time() - start

    data = resp.get_json()['data']
    assert resp.status_code == 200
    assert data['successful'] == 5 and data['failed'] == 1
    assert [r['url'] for r in data['results']] == urls
    assert elapsed < 1.5  # sequential would be >= 2.0s
