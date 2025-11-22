"""
Unit tests for backend services
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime

@pytest.mark.unit
class TestBackgroundAnalysisService:
    """Test background analysis service"""
    
    def test_get_unanalyzed_content(self, app):
        """Test getting unanalyzed content"""
        from services.background_analysis_service import BackgroundAnalysisService
        from models import db, SavedContent, User
        import uuid
        
        with app.app_context():
            # Create test user and content with unique identifiers
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
                extracted_text='Content'
            )
            db.session.add(content)
            db.session.commit()
            
            # Store content ID and user ID before calling service (to avoid DetachedInstanceError)
            content_id = content.id
            user_id = user.id
            
            # Clean up ALL other unanalyzed content from ALL users to ensure our content is returned
            # The service groups by user and returns first user's content, so we need to clean all
            # This ensures the test is isolated from other test data
            all_other_content = SavedContent.query.filter(
                SavedContent.id != content_id,
                SavedContent.extracted_text.isnot(None),
                SavedContent.extracted_text != ''
            ).all()
            for oc in all_other_content:
                db.session.delete(oc)
            db.session.commit()
            
            # Verify only our content exists
            remaining = SavedContent.query.filter(
                SavedContent.extracted_text.isnot(None),
                SavedContent.extracted_text != ''
            ).all()
            assert len(remaining) == 1, f"Expected 1 unanalyzed content after cleanup, found {len(remaining)}"
            assert remaining[0].id == content_id, f"Expected content ID {content_id}, found {remaining[0].id}"
            
            service = BackgroundAnalysisService()
            # _get_unanalyzed_content() groups by user and returns first user's content
            # Since we cleaned up all other content, our content should be returned
            unanalyzed = service._get_unanalyzed_content()
            
            assert len(unanalyzed) >= 1, f"Expected at least 1 unanalyzed content, got {len(unanalyzed)}"
            # Check if our content is in the results
            # Access id while still in app context to avoid DetachedInstanceError
            content_ids = [c.id for c in unanalyzed]
            assert content_id in content_ids, f"Content ID {content_id} not found in {content_ids}"
    
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
                mock_analyzer.analyze_bookmark_content.return_value = {
                    'summary': 'Python Flask content',
                    'key_concepts': ['Python', 'Flask'],
                    'difficulty': 'intermediate',
                    'content_type': 'article',
                    'technologies': ['Python', 'Flask'],
                    'relevance_score': 0.8
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
    @patch('ml.unified_recommendation_orchestrator.clear_gemini_analyzer_cache')
    @patch('models.db')
    @patch('run_production.app')
    def test_invalidate_recommendation_cache(self, mock_app, mock_db, mock_clear_gemini, mock_redis_cache):
        """Test invalidating recommendation cache"""
        from services.cache_invalidation_service import CacheInvalidationService
        
        # Mock the redis_cache methods that are actually used
        mock_redis_cache.invalidate_user_recommendations.return_value = True
        mock_redis_cache.delete_keys_pattern.return_value = 0
        mock_clear_gemini.return_value = 0
        
        # Mock the database operations to avoid actual DB calls
        mock_app_context = MagicMock()
        mock_app.app_context.return_value.__enter__ = Mock(return_value=None)
        mock_app.app_context.return_value.__exit__ = Mock(return_value=None)
        
        mock_session = MagicMock()
        mock_db.session = mock_session
        mock_query = MagicMock()
        mock_session.query.return_value.filter.return_value.update.return_value = 0
        mock_session.commit.return_value = None
        
        result = CacheInvalidationService.invalidate_recommendation_cache(1)
        
        # Should call invalidate_user_recommendations
        assert mock_redis_cache.invalidate_user_recommendations.called
        assert result is True
    
    @patch('services.cache_invalidation_service.redis_cache')
    def test_invalidate_user_cache(self, mock_redis_cache):
        """Test invalidating user cache"""
        from services.cache_invalidation_service import CacheInvalidationService
        
        # Mock the redis_cache methods that are actually used
        mock_redis_cache.invalidate_user_bookmarks.return_value = True
        mock_redis_cache.invalidate_user_recommendations.return_value = True
        mock_redis_cache.invalidate_analysis_cache.return_value = True
        mock_redis_cache.delete_keys_pattern.return_value = 0
        
        result = CacheInvalidationService.invalidate_user_cache(1)
        
        # Should call various invalidation methods
        assert mock_redis_cache.invalidate_user_bookmarks.called
        assert result is True

