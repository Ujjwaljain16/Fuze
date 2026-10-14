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


@pytest.mark.unit
class TestStatChanges:
    """The change line under the stat cards must say only what the numbers support."""

    def test_a_bulk_import_in_the_first_week_is_not_called_plus_100_percent(self):
        from blueprints.dashboard import stat_changes
        changes = stat_changes(saved_this_week=238, saved_last_week=0)
        assert changes['total_bookmarks'] == {'change': '+238 this week', 'change_value': 238}
        assert changes['weekly_saves'] == {'change': '', 'change_value': 0}   # no earlier week to compare with

    def test_weekly_saves_compare_with_the_week_before(self):
        from blueprints.dashboard import stat_changes
        assert stat_changes(15, 10)['weekly_saves'] == {'change': '+50% vs last week', 'change_value': 50}
        assert stat_changes(5, 10)['weekly_saves'] == {'change': '-50% vs last week', 'change_value': -50}
        assert stat_changes(10, 10)['weekly_saves'] == {'change': '+0% vs last week', 'change_value': 0}

    def test_a_quiet_week_shows_no_change(self):
        from blueprints.dashboard import stat_changes
        changes = stat_changes(0, 0)
        assert changes['total_bookmarks']['change'] == '' and changes['weekly_saves']['change'] == ''
        assert stat_changes(0, 8)['weekly_saves'] == {'change': '-100% vs last week', 'change_value': -100}
