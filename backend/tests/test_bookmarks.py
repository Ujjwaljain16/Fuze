"""
Unit tests for bookmarks blueprint
"""
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.unit
@pytest.mark.requires_db
class TestBookmarks:
    """Test bookmark endpoints"""
    
    def test_save_bookmark_success(self, client, auth_headers):
        """Test saving a bookmark successfully"""
        with patch('blueprints.bookmarks.scrape_url_enhanced') as mock_scrape, \
             patch('blueprints.bookmarks.get_embedding') as mock_embedding:
            mock_scrape.return_value = {
                'title': 'Test Article',
                'content': 'Test content',
                'headings': ['Heading 1'],
                'meta_description': 'Test description',
                'quality_score': 8
            }
            mock_embedding.return_value = [0.1] * 384  # Mock embedding vector
            
            response = client.post('/api/bookmarks', json={
                'url': 'https://example.com/article',
                'title': 'Test Article',
                'description': 'Test description',
                'category': 'tech'
            }, headers=auth_headers)
            
            assert response.status_code == 201
            data = response.json
            assert 'bookmark' in data
            assert data['bookmark']['url'] == 'https://example.com/article'
    
    def test_save_bookmark_duplicate(self, client, auth_headers, test_user, app):
        """Test saving duplicate bookmark"""
        from models import db, SavedContent
        
        with app.app_context():
            # Create existing bookmark
            bookmark = SavedContent(
                user_id=test_user['id'],
                url='https://example.com/existing',
                title='Existing',
                extracted_text='Content'
            )
            db.session.add(bookmark)
            db.session.commit()
        
        response = client.post('/api/bookmarks', json={
            'url': 'https://example.com/existing',
            'title': 'New Title',
            'description': 'New description'
        }, headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json.get('wasDuplicate') == True
    
    def test_list_bookmarks(self, client, auth_headers, test_user, app):
        """Test listing bookmarks"""
        from models import db, SavedContent
        
        with app.app_context():
            # Create test bookmarks
            for i in range(5):
                bookmark = SavedContent(
                    user_id=test_user['id'],
                    url=f'https://example.com/{i}',
                    title=f'Bookmark {i}',
                    extracted_text='Content'
                )
                db.session.add(bookmark)
            db.session.commit()
        
        response = client.get('/api/bookmarks', headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert 'bookmarks' in data
        assert len(data['bookmarks']) == 5
    
    def test_list_bookmarks_pagination(self, client, auth_headers, test_user, app):
        """Test bookmark pagination"""
        from models import db, SavedContent
        
        with app.app_context():
            # Clean up any existing bookmarks for this user first
            SavedContent.query.filter_by(user_id=test_user['id']).delete()
            db.session.commit()
            
            # Create 15 bookmarks
            for i in range(15):
                bookmark = SavedContent(
                    user_id=test_user['id'],
                    url=f'https://example.com/{i}',
                    title=f'Bookmark {i}',
                    extracted_text='Content'
                )
                db.session.add(bookmark)
            db.session.commit()
            
            # Verify all 15 were created
            count = SavedContent.query.filter_by(user_id=test_user['id']).count()
            assert count == 15, f"Expected 15 bookmarks, but found {count}"
        
        # First page
        response = client.get('/api/bookmarks?page=1&per_page=10', headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert len(data['bookmarks']) == 10, f"Expected 10 bookmarks on first page, got {len(data['bookmarks'])}"
        assert data['total'] == 15, f"Expected total of 15, got {data['total']}"
        
        # Second page
        response = client.get('/api/bookmarks?page=2&per_page=10', headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert len(data['bookmarks']) == 5
    
    def test_list_bookmarks_search(self, client, auth_headers, test_user, app):
        """Test bookmark search"""
        from models import db, SavedContent
        
        with app.app_context():
            bookmark1 = SavedContent(
                user_id=test_user['id'],
                url='https://example.com/python',
                title='Python Tutorial',
                extracted_text='Content'
            )
            bookmark2 = SavedContent(
                user_id=test_user['id'],
                url='https://example.com/javascript',
                title='JavaScript Guide',
                extracted_text='Content'
            )
            db.session.add_all([bookmark1, bookmark2])
            db.session.commit()
        
        response = client.get('/api/bookmarks?search=python', headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert len(data['bookmarks']) == 1
        assert 'python' in data['bookmarks'][0]['title'].lower()
    
    def test_delete_bookmark(self, client, auth_headers, test_user, app):
        """Test deleting a bookmark"""
        from models import db, SavedContent
        
        with app.app_context():
            bookmark = SavedContent(
                user_id=test_user['id'],
                url='https://example.com/delete',
                title='To Delete',
                extracted_text='Content'
            )
            db.session.add(bookmark)
            db.session.commit()
            bookmark_id = bookmark.id
        
        response = client.delete(f'/api/bookmarks/{bookmark_id}', headers=auth_headers)
        assert response.status_code == 200
        
        # Verify deleted
        with app.app_context():
            deleted = SavedContent.query.get(bookmark_id)
            assert deleted is None
    
    def test_bulk_import_bookmarks(self, client, auth_headers):
        """Test bulk importing bookmarks"""
        bookmarks_data = [
            {'url': 'https://example.com/1', 'title': 'Bookmark 1'},
            {'url': 'https://example.com/2', 'title': 'Bookmark 2'},
            {'url': 'https://example.com/3', 'title': 'Bookmark 3'}
        ]
        
        with patch('blueprints.bookmarks.scrape_url_enhanced') as mock_scrape, \
             patch('blueprints.bookmarks.get_embedding') as mock_embedding:
            mock_scrape.return_value = {
                'title': 'Scraped Title',
                'content': 'Scraped content',
                'headings': [],
                'meta_description': 'Scraped description',
                'quality_score': 8
            }
            mock_embedding.return_value = [0.1] * 384  # Mock embedding vector
            
            response = client.post('/api/bookmarks/import', 
                                 json=bookmarks_data,
                                 headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json
            assert data['total'] == 3
            assert data['added'] == 3

