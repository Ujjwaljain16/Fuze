"""
Integration tests for API endpoints
"""
import pytest
from unittest.mock import patch, MagicMock

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
        project_id = project_response.json['project']['id']
        
        # 4. Save bookmark
        with patch('blueprints.bookmarks.scrape_url_enhanced') as mock_scrape, \
             patch('blueprints.bookmarks.get_embedding') as mock_embedding:
            mock_scrape.return_value = {
                'title': 'Test Article',
                'content': 'Content',
                'headings': [],
                'meta_description': 'Description',
                'quality_score': 8
            }
            mock_embedding.return_value = [0.1] * 384  # Mock embedding vector
            
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
        with patch('ml.unified_recommendation_orchestrator.get_unified_orchestrator') as mock_orch:
            from ml.unified_recommendation_orchestrator import UnifiedRecommendationResult
            
            mock_engine = MagicMock()
            # Create proper UnifiedRecommendationResult object
            mock_rec = UnifiedRecommendationResult(
                id=1,
                title='Rec 1',
                url='https://example.com/1',
                score=0.9,
                reason='Test reason',
                content_type='article',
                difficulty='intermediate',
                technologies=['Python'],
                key_concepts=['concept1'],
                quality_score=8.0,
                engine_used='test',
                confidence=0.9,
                metadata={},
                basic_summary='Summary',
                context_summary='Context',
                cached=False
            )
            mock_engine.get_recommendations.return_value = [mock_rec]
            mock_engine.generate_context_summaries.return_value = [mock_rec]
            mock_engine.get_performance_metrics.return_value = {}
            mock_orch.return_value = mock_engine
            
            response = client.post('/api/recommendations/unified-orchestrator',
                                 json={
                                     'title': 'Learn Python',
                                     'technologies': 'Python'
                                 },
                                 headers=headers)
            
            assert response.status_code == 200

