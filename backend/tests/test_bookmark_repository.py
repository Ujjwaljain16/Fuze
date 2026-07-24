import pytest
from models import SavedContent, db
from repositories.bookmark_repository import BookmarkRepository


@pytest.mark.unit
@pytest.mark.requires_db
def test_bookmark_repository_crud(test_user, app):
    with app.app_context():
        repo = BookmarkRepository(db.session)

        # 1. Create / Add
        bookmark = SavedContent(
            user_id=test_user['id'],
            url='https://github.com/openai/gpt-4',
            title='GPT-4 Repository',
            category='ai'
        )
        repo.add(bookmark)
        db.session.commit()

        # 2. Get by ID (using session.get)
        fetched = repo.get_by_id(bookmark.id)
        assert fetched is not None
        assert fetched.title == 'GPT-4 Repository'

        # 3. Similar domain path matching with exact boundary checks
        similar = repo.get_similar_by_domain_path(test_user['id'], 'https://github.com/openai/gpt-4')
        assert len(similar) == 1

        # False positive check: https://github.com/openai/gpt-45 should NOT match https://github.com/openai/gpt-4
        bookmark2 = SavedContent(
            user_id=test_user['id'],
            url='https://github.com/openai/gpt-45',
            title='GPT-45'
        )
        repo.add(bookmark2)
        db.session.commit()

        similar_strict = repo.get_similar_by_domain_path(test_user['id'], 'https://github.com/openai/gpt-4')
        assert len(similar_strict) == 1
        assert similar_strict[0].url == 'https://github.com/openai/gpt-4'

        # 4. Top categories check
        top_cats = repo.get_top_categories(test_user['id'])
        assert len(top_cats) >= 1
        assert top_cats[0][0] == 'ai'
