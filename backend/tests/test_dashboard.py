"""
Unit tests for dashboard blueprint
"""

import pytest

@pytest.mark.unit
@pytest.mark.requires_db
class TestDashboard:
    """Test dashboard summary endpoint"""

    def test_get_dashboard_summary_success(self, client, auth_headers, test_user):
        """Test getting aggregated dashboard summary"""
        response = client.get('/api/dashboard/summary', headers=auth_headers)
        assert response.status_code == 200
        data = response.json

        assert 'profile' in data
        assert data['profile']['id'] == test_user['id']
        assert 'apiKeyStatus' in data
        assert 'stats' in data
        assert 'recentBookmarks' in data
        assert 'recentProjects' in data
        assert 'totalBookmarks' in data
        assert 'totalProjects' in data
