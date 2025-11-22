"""
Unit tests for recommendations blueprint
"""
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.unit
@pytest.mark.requires_db
class TestRecommendations:
    """Test recommendation endpoints"""
    
    def test_get_recommendations_success(self, client, auth_headers, test_user, app):
        """Test getting recommendations successfully"""
        from models import db, SavedContent
        
        with app.app_context():
            # Create some saved content for recommendations
            for i in range(5):
                bookmark = SavedContent(
                    user_id=test_user['id'],
                    url=f'https://example.com/{i}',
                    title=f'Content {i}',
                    extracted_text=f'Content about topic {i}',
                    quality_score=8
                )
                db.session.add(bookmark)
            db.session.commit()
        
        with patch('ml.unified_recommendation_orchestrator.get_unified_orchestrator') as mock_orch:
            from ml.unified_recommendation_orchestrator import UnifiedRecommendationResult
            
            mock_engine = MagicMock()
            # Create proper UnifiedRecommendationResult objects
            mock_rec1 = UnifiedRecommendationResult(
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
                basic_summary='Summary 1',
                context_summary='Context 1',
                cached=False
            )
            mock_rec2 = UnifiedRecommendationResult(
                id=2,
                title='Rec 2',
                url='https://example.com/2',
                score=0.8,
                reason='Test reason 2',
                content_type='article',
                difficulty='beginner',
                technologies=['Flask'],
                key_concepts=['concept2'],
                quality_score=7.0,
                engine_used='test',
                confidence=0.8,
                metadata={},
                basic_summary='Summary 2',
                context_summary='Context 2',
                cached=False
            )
            mock_engine.get_recommendations.return_value = [mock_rec1, mock_rec2]
            # Mock generate_context_summaries to return the same list
            mock_engine.generate_context_summaries.return_value = [mock_rec1, mock_rec2]
            # Mock get_performance_metrics
            mock_engine.get_performance_metrics.return_value = {}
            mock_orch.return_value = mock_engine
            
            response = client.post('/api/recommendations/unified-orchestrator',
                                 json={
                                     'title': 'Test Project',
                                     'technologies': 'Python, Flask',
                                     'description': 'Test description'
                                 },
                                 headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json
            assert 'recommendations' in data
    
    def test_get_recommendations_no_content(self, client, auth_headers):
        """Test getting recommendations with no saved content"""
        response = client.post('/api/recommendations/unified-orchestrator',
                             json={
                                 'title': 'Test Project',
                                 'technologies': 'Python'
                             },
                             headers=auth_headers)
        
        # Should still return 200, but with empty or limited recommendations
        assert response.status_code in [200, 404]
    
    def test_get_engine_status(self, client):
        """Test getting engine status"""
        response = client.get('/api/recommendations/status')
        assert response.status_code == 200
        data = response.json
        assert 'unified_orchestrator_available' in data
        assert 'total_engines_available' in data

