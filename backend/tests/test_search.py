"""
Unit tests for search blueprint
"""
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.unit
@pytest.mark.requires_db
class TestSearch:
    """Test search endpoints"""
    
    def test_semantic_search(self, client, auth_headers, test_user, app):
        """Test semantic search"""
        from models import db, SavedContent
        
        with app.app_context():
            # Create test bookmarks with embeddings
            bookmark = SavedContent(
                user_id=test_user['id'],
                url='https://example.com/python',
                title='Python Tutorial',
                extracted_text='Learn Python programming',
                embedding=[0.1] * 384  # Mock embedding
            )
            db.session.add(bookmark)
            db.session.commit()
        
        with patch('blueprints.search.get_embedding') as mock_embedding:
            mock_embedding.return_value = [0.1] * 384
            
            response = client.post('/api/search/semantic', json={
                'query': 'Python programming',
                'limit': 10
            }, headers=auth_headers)
            
            # May return 200 with results or 404 if no matches
            assert response.status_code in [200, 404]
            if response.status_code == 200:
                data = response.json
                assert 'results' in data or 'bookmarks' in data
    
    def test_semantic_search_empty_query(self, client, auth_headers):
        """Test semantic search with empty query"""
        response = client.post('/api/search/semantic', json={
            'query': '',
            'limit': 10
        }, headers=auth_headers)
        
        assert response.status_code == 400
    
    def test_text_search(self, client, auth_headers, test_user, app):
        """Test text search"""
        from models import db, SavedContent
        
        with app.app_context():
            bookmark = SavedContent(
                user_id=test_user['id'],
                url='https://example.com/test',
                title='Test Article',
                extracted_text='This is a test article about Python'
            )
            db.session.add(bookmark)
            db.session.commit()
        
        response = client.get('/api/search/text?q=Python', headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert 'results' in data or 'bookmarks' in data

