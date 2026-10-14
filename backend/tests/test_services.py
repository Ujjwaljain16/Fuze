"""
Unit tests for backend services
"""
import pytest
from unittest.mock import patch, MagicMock, Mock

@pytest.mark.unit
class TestBackgroundAnalysisService:
    """Test background analysis service"""
    
    @patch('services.background_analysis_service.get_app')
    def test_process_content_analysis(self, mock_get_app, app):
        """Test processing content analysis"""
        from services.background_analysis_service import BackgroundAnalysisService
        from models import db, SavedContent, User
        import uuid
        
        mock_get_app.return_value = app
        
        with app.app_context():
            unique_id = str(uuid.uuid4())[:8]
            user = User(
                username=f'testuser_{unique_id}',
                email=f'test_{unique_id}@example.com',
                password_hash='hash'
            )
            db.session.add(user)
            db.session.commit()
            
            content = SavedContent(
                user_id=user.id,
                url='https://example.com',
                title='Test',
                extracted_text='Content about Python and Flask'
            )
            db.session.add(content)
            db.session.commit()
            
            with patch('services.background_analysis_service.GeminiAnalyzer') as mock_gemini:
                mock_analyzer = MagicMock()
                mock_analyzer.generate_json.return_value = {
                    'summary': 'Python Flask content',
                    'use_when': 'When building a Flask web app',
                    'key_concepts': ['Python', 'Flask'],
                    'audience_level': 'intermediate',
                    'content_type': 'article',
                    'technologies': ['Python', 'Flask'],
                    'teaches_or_solves': ['routing'],
                }
                mock_gemini.return_value = mock_analyzer
                
                with patch('services.multi_user_api_manager.get_user_api_key') as mock_api_key:
                    mock_api_key.return_value = 'test-api-key'
                    
                    service = BackgroundAnalysisService()
                    # Use _analyze_single_content instead of _process_content_analysis
                    service._analyze_single_content(content, user.id)
                    
                    # Verify analysis was created
                    from models import ContentAnalysis
                    analysis = ContentAnalysis.query.filter_by(content_id=content.id).first()
                    assert analysis is not None
                    assert analysis.key_concepts is not None

@pytest.mark.unit
class TestCacheInvalidationService:
    """Test cache invalidation service"""
    
    @patch('services.cache_invalidation_service.redis_cache')
    @patch('models.db')
    @patch('run_production.app')
    def test_invalidate_recommendation_cache(self, mock_app, mock_db, mock_redis_cache):
        """Test invalidating recommendation cache"""
        
        # Mock the redis_cache methods that are actually used
        mock_redis_cache.invalidate_recommendation_cache.return_value = True
        mock_redis_cache.delete_keys_pattern.return_value = 0
        
        # Mock the database operations to avoid actual DB calls
        mock_app.app_context.return_value.__enter__ = Mock(return_value=None)
        mock_app.app_context.return_value.__exit__ = Mock(return_value=None)
        
        mock_session = MagicMock()
        mock_db.session = mock_session
        mock_session.query.return_value.filter.return_value.update.return_value = 0
        mock_session.commit.return_value = None
        
        from services.cache_invalidation_service import cache_invalidator
        result = cache_invalidator.invalidate_recommendation_cache(1)
        
        # Should call invalidate_recommendation_cache
        assert mock_redis_cache.invalidate_recommendation_cache.called
        assert result is True
    
    @patch('services.cache_invalidation_service.redis_cache')
    def test_invalidate_user_cache(self, mock_redis_cache):
        """Test invalidating user cache"""
        from services.cache_invalidation_service import cache_invalidator
        
        # Mock the redis_cache methods that are actually used
        mock_redis_cache.invalidate_user_bookmarks.return_value = True
        mock_redis_cache.invalidate_recommendation_cache.return_value = True
        mock_redis_cache.invalidate_analysis_cache.return_value = True
        mock_redis_cache.delete_keys_pattern.return_value = 0
        
        result = cache_invalidator.invalidate_user_cache(1)
        
        # Should call various invalidation methods
        mock_redis_cache.invalidate_query_cache.assert_any_call('bookmarks:1:*')
        assert result is True

