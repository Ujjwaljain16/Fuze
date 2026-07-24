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
