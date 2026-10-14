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


@pytest.mark.unit
@pytest.mark.requires_db
def test_the_pipeline_counters_add_up_to_the_total(app, client, auth_headers, test_user):
    """Bookmarks whose page could not be read were in no counter, so 207 + 5 showed against a total of 238."""
    from datetime import datetime
    from models import db, SavedContent
    now = datetime.utcnow()
    with app.app_context():
        SavedContent.query.filter_by(user_id=test_user['id']).delete()
        rows = [
            dict(scrape_status='SUCCESS', embedding_status='SUCCESS', analysis_status='SUCCESS', extracted_text='text'),
            dict(scrape_status='SUCCESS', embedding_status='SUCCESS', analysis_status='SUCCESS', extracted_text='text'),
            dict(scrape_status='SUCCESS', embedding_status='SUCCESS', analysis_status='PENDING', extracted_text='text'),
            dict(scrape_status='DISALLOWED', embedding_status='SUCCESS', analysis_status='PENDING', extracted_text=None),
            dict(scrape_status='FAILED_FETCH', embedding_status='SUCCESS', analysis_status='PENDING', extracted_text=''),
            dict(scrape_status='BLOCKED', embedding_status='SUCCESS', analysis_status='PENDING', extracted_text=None),
            dict(scrape_status='PENDING', embedding_status='PENDING', analysis_status='PENDING', extracted_text=None),
            dict(scrape_status='SUCCESS', embedding_status='PENDING', analysis_status='PENDING', extracted_text='text'),
        ]
        for i, fields in enumerate(rows):
            db.session.add(SavedContent(user_id=test_user['id'], url=f'https://e.com/pipeline/{i}', title=f't{i}',
                                        saved_at=now, **fields))
        db.session.commit()
    data = client.get('/api/dashboard/summary', headers=auth_headers).json
    stages = data['pipeline_stats']
    assert stages == {'scraping': 1, 'embedding': 1, 'analyzing': 1, 'analyzed': 2, 'unreadable': 3}
    assert sum(stages.values()) == len(rows) == data['stats']['total_bookmarks']['value']
