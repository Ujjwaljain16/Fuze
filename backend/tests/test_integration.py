"""
Integration tests for API endpoints
"""
import pytest
from unittest.mock import patch

@pytest.mark.integration
@pytest.mark.requires_db
class TestAPIIntegration:
    """Integration tests for complete API flows"""
    
    def test_complete_user_flow(self, client):
        """Test complete user registration and usage flow"""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        # 1. Register user
        register_response = client.post('/api/auth/register', json={
            'username': f'integration_user_{unique_id}',
            'email': f'integration_{unique_id}@example.com',
            'password': 'SecurePass123!',
            'name': 'Integration User'
        })
        assert register_response.status_code == 201
        
        # 2. Login to get token
        login_response = client.post('/api/auth/login', json={
            'email': f'integration_{unique_id}@example.com',
            'password': 'SecurePass123!'
        })
        assert login_response.status_code == 200
        token = login_response.json['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        # 2. Get profile
        profile_response = client.get('/api/profile', headers=headers)
        assert profile_response.status_code == 200
        
        # 3. Create project
        project_response = client.post('/api/projects', json={
            'title': 'Integration Project',
            'description': 'Test project',
            'technologies': 'Python'
        }, headers=headers)
        assert project_response.status_code == 201
        
        # 4. Save bookmark
        with patch('blueprints.bookmarks.scrape_url_summary') as mock_scrape:
            mock_scrape.return_value = {
                'title': 'Test Article',
                'content': 'Content',
                'headings': [],
                'meta_description': 'Description',
                'quality_score': 8
            }
            
            bookmark_response = client.post('/api/bookmarks', json={
                'url': 'https://example.com/article',
                'title': 'Test Article',
                'description': 'Description'
            }, headers=headers)
            assert bookmark_response.status_code == 201
        
        # 5. Get recommendations
        rec_response = client.post('/api/recommendations/unified-orchestrator',
                                 json={
                                     'title': 'Integration Project',
                                     'technologies': 'Python'
                                 },
                                 headers=headers)
        # May return 200 or 404 depending on content
        assert rec_response.status_code in [200, 404]
    
    def test_bookmark_to_recommendation_flow(self, client, test_user, app):
        """Test flow from saving bookmark to getting recommendations"""
        from models import db, SavedContent
        
        # Login
        login_response = client.post('/api/auth/login', json={
            'email': test_user['email'],
            'password': test_user['password']
        })
        token = login_response.json['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        # Save multiple bookmarks
        with app.app_context():
            for i in range(5):
                bookmark = SavedContent(
                    user_id=test_user['id'],
                    url=f'https://example.com/{i}',
                    title=f'Python Tutorial {i}',
                    extracted_text=f'Content about Python programming {i}',
                    quality_score=8
                )
                db.session.add(bookmark)
            db.session.commit()
        
        # Get recommendations
        fake = {"results": [{"id": 1, "title": "Rec 1", "url": "https://example.com/1", "score": 90.0,
                             "confidence": 90.0, "reason": "r", "basic_summary": "s", "content_type": "tutorial",
                             "difficulty": "beginner", "technologies": ["Python"], "key_concepts": [],
                             "quality_score": 8, "engine_used": "intent_engine", "metadata": {}}],
                "intent": {}, "cached": False}
        with patch('ml.intent_engine.engine.recommend', return_value=fake):
            response = client.post('/api/recommendations/unified-orchestrator',
                                 json={
                                     'title': 'Learn Python',
                                     'technologies': 'Python'
                                 },
                                 headers=headers)
            
            assert response.status_code == 200

