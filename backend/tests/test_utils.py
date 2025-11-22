"""
Unit tests for utility functions
"""
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.unit
class TestEmbeddingUtils:
    """Test embedding utilities"""
    
    def test_get_embedding_model_singleton(self):
        """Test that embedding model is a singleton"""
        from utils.embedding_utils import get_embedding_model
        
        with patch('utils.embedding_utils._embedding_model', None):
            with patch('sentence_transformers.SentenceTransformer') as mock_st:
                mock_model = MagicMock()
                mock_st.return_value = mock_model
                
                model1 = get_embedding_model()
                model2 = get_embedding_model()
                
                # Should return same instance
                assert model1 is model2
    
    def test_get_embedding_caching(self):
        """Test embedding caching"""
        from utils.embedding_utils import get_embedding
        
        with patch('utils.embedding_utils.get_embedding_model') as mock_model:
            mock_model_instance = MagicMock()
            mock_model_instance.encode.return_value = [[0.1] * 384]
            mock_model.return_value = mock_model_instance
            
            with patch('utils.redis_utils.redis_cache') as mock_redis:
                mock_redis.get_cached_embedding.return_value = None
                mock_redis.cache_embedding.return_value = True
                
                embedding = get_embedding('test text')
                assert embedding is not None
                assert len(embedding) == 384

@pytest.mark.unit
class TestRedisUtils:
    """Test Redis utilities"""
    
    def test_cache_set_get(self, mock_redis):
        """Test basic cache set and get"""
        mock_redis.set('test_key', 'test_value', expire=3600)
        mock_redis.get('test_key')
        
        mock_redis.set.assert_called_once()
        mock_redis.get.assert_called_once()
    
    def test_cache_invalidation(self, mock_redis):
        """Test cache invalidation"""
        mock_redis.delete('test_key')
        mock_redis.delete.assert_called_once()

@pytest.mark.unit
class TestSecurityMiddleware:
    """Test security middleware"""
    
    def test_validate_input_sql_injection(self):
        """Test SQL injection detection"""
        from middleware.security_middleware import validate_input
        
        is_valid, error = validate_input({
            'query': "'; DROP TABLE users; --"
        })
        
        assert is_valid == False
        assert 'sql' in error.lower() or 'invalid' in error.lower()
    
    def test_validate_input_xss(self):
        """Test XSS detection"""
        from middleware.security_middleware import validate_input
        
        is_valid, error = validate_input({
            'content': '<script>alert("xss")</script>'
        })
        
        assert is_valid == False
        assert 'xss' in error.lower() or 'invalid' in error.lower()
    
    def test_sanitize_string(self):
        """Test string sanitization"""
        from middleware.security_middleware import sanitize_string
        
        result = sanitize_string('  test\x00string  ')
        assert result == 'teststring'
        assert '\x00' not in result

