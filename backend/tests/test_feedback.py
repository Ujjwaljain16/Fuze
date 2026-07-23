"""
Unit tests for feedback blueprint
"""

import pytest

@pytest.mark.unit
@pytest.mark.requires_db
class TestFeedback:
    """Test feedback endpoint"""

    def test_submit_feedback_success(self, client, auth_headers, test_user, app):
        """Test submitting feedback for user content"""
        from models import db, SavedContent

        with app.app_context():
            bookmark = SavedContent(
                user_id=test_user['id'],
                url='https://example.com/fb-test',
                title='Feedback Test Title'
            )
            db.session.add(bookmark)
            db.session.commit()
            content_id = bookmark.id

        response = client.post('/api/feedback', json={
            'content_id': content_id,
            'feedback_type': 'relevant'
        }, headers=auth_headers)

        assert response.status_code == 200
        assert response.json['message'] == 'Feedback recorded'

    def test_submit_feedback_invalid_content(self, client, auth_headers):
        """Test submitting feedback for non-existent content returns 404"""
        response = client.post('/api/feedback', json={
            'content_id': 999999,
            'feedback_type': 'relevant'
        }, headers=auth_headers)

        assert response.status_code == 404
        assert response.json['message'] == 'Content not found'

    def test_submit_feedback_invalid_type(self, client, auth_headers):
        """Test submitting invalid feedback type returns 400"""
        response = client.post('/api/feedback', json={
            'content_id': 1,
            'feedback_type': 'super_awesome'
        }, headers=auth_headers)

        assert response.status_code == 400
