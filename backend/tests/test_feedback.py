"""
Unit tests for feedback blueprint
"""
import pytest

@pytest.mark.unit
@pytest.mark.requires_db
class TestFeedback:
    """Test feedback endpoints"""
    
    def test_submit_feedback(self, client, auth_headers, test_user, app):
        """Test submitting feedback"""
        from models import db, SavedContent
        
        with app.app_context():
            bookmark = SavedContent(
                user_id=test_user['id'],
                url='https://example.com/test',
                title='Test Article',
                extracted_text='Content'
            )
            db.session.add(bookmark)
            db.session.commit()
            content_id = bookmark.id
        
        response = client.post('/api/feedback', json={
            'content_id': content_id,
            'feedback_type': 'relevant'
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json
        assert 'message' in data
    
    def test_submit_feedback_invalid_type(self, client, auth_headers):
        """Test submitting feedback with invalid type"""
        response = client.post('/api/feedback', json={
            'content_id': 1,
            'feedback_type': 'invalid'
        }, headers=auth_headers)
        
        assert response.status_code == 400
    
    def test_submit_feedback_missing_fields(self, client, auth_headers):
        """Test submitting feedback with missing fields"""
        response = client.post('/api/feedback', json={
            'content_id': 1
        }, headers=auth_headers)
        
        assert response.status_code == 400
    
    def test_update_feedback(self, client, auth_headers, test_user, app):
        """Test updating existing feedback"""
        from models import db, SavedContent, Feedback
        
        with app.app_context():
            bookmark = SavedContent(
                user_id=test_user['id'],
                url='https://example.com/test',
                title='Test Article',
                extracted_text='Content'
            )
            db.session.add(bookmark)
            db.session.commit()
            content_id = bookmark.id
            
            # Create initial feedback
            feedback = Feedback(
                user_id=test_user['id'],
                content_id=content_id,
                feedback_type='relevant'
            )
            db.session.add(feedback)
            db.session.commit()
        
        # Update feedback
        response = client.post('/api/feedback', json={
            'content_id': content_id,
            'feedback_type': 'not_relevant'
        }, headers=auth_headers)
        
        assert response.status_code == 200

