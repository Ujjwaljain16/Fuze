"""
Unit tests for bookmarks blueprint
"""
import pytest
import os
from unittest.mock import patch

@pytest.mark.unit
@pytest.mark.requires_db
class TestBookmarks:
    """Test bookmark endpoints"""
    
    def test_save_bookmark_success(self, client, auth_headers):
        """Test saving a bookmark successfully"""
        with patch('blueprints.bookmarks.scrape_url_summary') as mock_scrape:
            mock_scrape.return_value = {
                'title': 'Test Article',
                'content': 'Test content',
                'headings': ['Heading 1'],
                'meta_description': 'Test description',
                'quality_score': 8
            }
            
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

    def test_list_bookmarks_returns_same_fields_without_loading_text_or_embedding(
            self, client, auth_headers, test_user, app):
        """The list query defers extracted_text/embedding but the response is unchanged."""
        from sqlalchemy import event
        from models import db, SavedContent

        with app.app_context():
            db.session.add_all([
                SavedContent(user_id=test_user['id'], url='https://example.com/with-text',
                             title='With text', notes='n1', category='tech',
                             extracted_text='Body ' * 1000, embedding=[0.1] * 384),
                SavedContent(user_id=test_user['id'], url='https://example.com/empty-text',
                             title='Empty text', extracted_text=''),
                SavedContent(user_id=test_user['id'], url='https://example.com/no-text', title='No text'),
            ])
            db.session.commit()
            engine = db.engine

        statements = []
        def capture(conn, cursor, statement, *args):
            if 'saved_content' in statement:
                statements.append(statement)

        event.listen(engine, 'before_cursor_execute', capture)
        try:
            response = client.get('/api/bookmarks?per_page=10', headers=auth_headers)
        finally:
            event.remove(engine, 'before_cursor_execute', capture)

        assert response.status_code == 200
        by_url = {b['url']: b for b in response.json['bookmarks']}
        assert set(by_url) == {'https://example.com/with-text', 'https://example.com/empty-text',
                               'https://example.com/no-text'}
        expected_keys = {'id', 'url', 'title', 'description', 'saved_at', 'category', 'has_content'}
        assert all(set(b) == expected_keys for b in by_url.values())
        first = by_url['https://example.com/with-text']
        assert first['has_content'] is True
        assert first['title'] == 'With text' and first['description'] == 'n1' and first['category'] == 'tech'
        assert by_url['https://example.com/empty-text']['has_content'] is False
        assert by_url['https://example.com/no-text']['has_content'] is False

        # paginate()'s SELECT count(*) FROM (subquery) names every column, but the planner never
        # reads columns the outer count doesn't use; only the row fetch matters here.
        selects = [s for s in statements if s.lstrip().upper().startswith('SELECT')
                   and not s.lstrip().upper().startswith('SELECT COUNT')]
        assert selects, "list endpoint should have queried saved_content"
        for s in selects:
            assert 'saved_content.extracted_text AS' not in s
            assert 'saved_content.embedding AS' not in s

    def test_bulk_import_skips_existing_urls(self, client, auth_headers, test_user, app):
        from models import db, SavedContent

        with app.app_context():
            db.session.add(SavedContent(user_id=test_user['id'], url='https://example.com/already',
                                        title='Already', extracted_text='x' * 5000))
            db.session.commit()

        response = client.post('/api/bookmarks/import', json=[
            {'url': 'https://example.com/already?utm_source=x', 'title': 'Again'},
            {'url': 'https://example.com/new', 'title': 'New'},
        ], headers=auth_headers)
        assert response.status_code == 200
        assert response.json['added'] == 1
        assert response.json['skip_reasons'].get('duplicate') == 1

    def test_list_bookmarks_pagination(self, client, auth_headers, test_user, app):
        """Test bookmark pagination"""
        from models import db, SavedContent
        
        with app.app_context():
            # CRITICAL SAFETY: Verify we're using test database before deleting
            db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '') or os.environ.get('DATABASE_URL', '')
            if db_url and 'sqlite' not in db_url.lower():
                production_indicators = ['supabase.co', 'amazonaws.com', 'azure.com', 'gcp.com', 'heroku.com']
                if any(indicator in db_url.lower() for indicator in production_indicators):
                    pytest.skip("Skipping test that deletes data - production database detected!")
            
            # Clean up any existing bookmarks for this user first
            # Use delete() with synchronize_session=False for better performance
            # CRITICAL: Double-check user_id before deleting
            user_id_to_delete = test_user['id']
            assert user_id_to_delete is not None, "test_user['id'] is None - cannot safely delete"
            
            # Verify we're only deleting test user's bookmarks
            count_before = SavedContent.query.filter_by(user_id=user_id_to_delete).count()
            deleted = SavedContent.query.filter_by(user_id=user_id_to_delete).delete(synchronize_session=False)
            db.session.commit()
            
            # Safety check: verify we didn't delete more than expected
            if deleted > count_before + 10:  # Allow some margin for race conditions
                db.session.rollback()
                pytest.fail(f"SAFETY CHECK FAILED: Attempted to delete {deleted} bookmarks, but only {count_before} existed for user {user_id_to_delete}. This might indicate a query bug!")
            
            # Flush to ensure cleanup is complete
            db.session.flush()
            
            # Create 15 bookmarks with unique URLs to avoid conflicts
            import uuid
            base_uuid = str(uuid.uuid4())[:8]
            bookmarks = []
            for i in range(15):
                bookmark = SavedContent(
                    user_id=test_user['id'],
                    url=f'https://example.com/{base_uuid}/{i}',
                    title=f'Bookmark {i}',
                    extracted_text='Content'
                )
                bookmarks.append(bookmark)
                db.session.add(bookmark)
            # Flush before commit to ensure objects are persisted
            db.session.flush()
            db.session.commit()
            
            # Refresh the session to ensure we see the committed data
            db.session.expire_all()
            
            # Verify all 15 were created
            count = SavedContent.query.filter_by(user_id=test_user['id']).count()
            assert count == 15, f"Expected 15 bookmarks, but found {count}. Deleted {deleted} existing bookmarks."
            
            # Verify the bookmarks we just created exist
            created_ids = [b.id for b in bookmarks]
            existing = SavedContent.query.filter(
                SavedContent.user_id == test_user['id'],
                SavedContent.id.in_(created_ids)
            ).count()
            assert existing == 15, f"Expected 15 of our bookmarks to exist, found {existing}"
            
            # Clear Redis cache for this user's bookmarks to ensure fresh data
            from utils.redis_utils import redis_cache
            try:
                # Invalidate all bookmark caches for this user
                redis_cache.invalidate_query_cache(f"bookmarks:{test_user['id']}:*")
            except Exception:
                # If Redis is not available or fails, continue (cache might not be used)
                pass
        
        # First page - verify we get exactly 10
        # Clear cache before making request to ensure fresh data
        response = client.get('/api/bookmarks?page=1&per_page=10', headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json}"
        data = response.json
        
        # Debug: If we don't get 15, check what we actually have
        if data.get('total', 0) != 15:
            with app.app_context():
                all_bookmarks = SavedContent.query.filter_by(user_id=test_user['id']).all()
                actual_count = len(all_bookmarks)
                actual_ids = [b.id for b in all_bookmarks]
                raise AssertionError(
                    f"Expected 15 bookmarks total, got {data.get('total', 0)}. "
                    f"Database has {actual_count} bookmarks for user {test_user['id']} with IDs: {actual_ids}"
                )
        
        assert len(data['bookmarks']) == 10, f"Expected 10 bookmarks on first page, got {len(data['bookmarks'])}. Total: {data.get('total', 'unknown')}"
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
        
        with patch('blueprints.bookmarks.scrape_url_summary') as mock_scrape:
            mock_scrape.return_value = {
                'title': 'Scraped Title',
                'content': 'Scraped content',
                'headings': [],
                'meta_description': 'Scraped description',
                'quality_score': 8
            }
            
            response = client.post('/api/bookmarks/import', 
                                 json=bookmarks_data,
                                 headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json
            assert data['total'] == 3
            assert data['added'] == 3

    def test_bulk_import_conflicting_row_does_not_lose_the_others(self, client, auth_headers, test_user, app, monkeypatch):
        """A URL that lands in the DB after the import read the user's bookmarks hits the unique
        constraint; only that row is skipped, the rest of the batch is still saved."""
        from models import db, SavedContent
        from utils.redis_utils import redis_cache

        with app.app_context():
            db.session.add(SavedContent(user_id=test_user['id'], url='https://example.com/raced', title='Raced'))
            db.session.commit()

        # A stale bookmark cache that predates the conflicting row, as when another request saves it mid-import.
        monkeypatch.setattr(redis_cache, 'get_cached_user_bookmarks',
                            lambda user_id: [{'url': 'https://example.com/older', 'title': 'Older', 'id': 0}])
        progress = {}
        monkeypatch.setattr(redis_cache, 'set_cache', lambda key, data, ttl=3600: progress.__setitem__(key, data) or True)
        monkeypatch.setattr('blueprints.bookmarks.process_bookmark_content_async', lambda *a, **k: None)

        response = client.post('/api/bookmarks/import', json=[
            {'url': 'https://example.com/fresh-1', 'title': 'Fresh 1'},
            {'url': 'https://example.com/raced', 'title': 'Raced again'},
            {'url': 'https://example.com/fresh-2', 'title': 'Fresh 2'},
        ], headers=auth_headers)

        assert response.status_code == 200
        data = response.json
        assert data['total'] == 3
        assert data['added'] == 2
        assert data['skipped'] == 1
        assert data['skip_reasons'] == {'duplicate': 1}
        assert progress[f"import_progress:{test_user['id']}"]['status'] == 'completed'

        with app.app_context():
            urls = {bm.url for bm in SavedContent.query.filter_by(user_id=test_user['id']).all()}
        assert {'https://example.com/fresh-1', 'https://example.com/fresh-2', 'https://example.com/raced'} <= urls

    def test_bulk_import_progress_is_terminal_after_an_exception(self, client, auth_headers, test_user, monkeypatch):
        """The extension polls the progress key; it must not stay 'processing' for an hour when the import fails."""
        from utils.redis_utils import redis_cache

        progress = {}
        monkeypatch.setattr(redis_cache, 'set_cache', lambda key, data, ttl=3600: progress.__setitem__(key, data) or True)

        def boom(user_id):
            raise RuntimeError('redis went away')
        monkeypatch.setattr(redis_cache, 'get_cached_user_bookmarks', boom)

        response = client.post('/api/bookmarks/import', json=[
            {'url': 'https://example.com/a', 'title': 'A'},
        ], headers=auth_headers)

        assert response.status_code == 500
        assert progress[f"import_progress:{test_user['id']}"]['status'] == 'failed'

    def test_check_duplicate_endpoint(self, client, auth_headers, test_user, app):
        """Test check-duplicate endpoint signature fix and functionality"""
        from models import db, SavedContent
        
        with app.app_context():
            bookmark = SavedContent(
                user_id=test_user['id'],
                url='https://example.com/check-dup',
                title='Check Dup Title'
            )
            db.session.add(bookmark)
            db.session.commit()
            
        response = client.post('/api/bookmarks/check-duplicate', 
                               json={'url': 'https://example.com/check-dup'},
                               headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert data['isDuplicate'] is True
        assert data['existingBookmark']['title'] == 'Check Dup Title'

    def test_url_normalization_case_preserves_path(self):
        """Test URL normalization lowercases scheme/netloc but preserves path case"""
        from blueprints.bookmarks import normalize_url
        url = "https://GitHub.com/OpenAI/GPT-4?utm_source=test"
        normalized = normalize_url(url)
        assert normalized.startswith("https://github.com/OpenAI/GPT-4")
        assert "OpenAI/GPT-4" in normalized
