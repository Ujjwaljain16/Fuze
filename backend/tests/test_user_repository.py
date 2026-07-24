import pytest
from models import User, db
from repositories.user_repository import UserRepository


@pytest.mark.unit
@pytest.mark.requires_db
def test_user_repository_operations(test_user, app):
    with app.app_context():
        repo = UserRepository(db.session)

        # 1. Fetch by ID (session.get)
        user = repo.get_by_id(test_user['id'])
        assert user is not None
        assert user.username == test_user['username']

        # 2. Case-insensitive email availability check (EXISTS optimization)
        assert repo.is_email_available(test_user['email']) is False
        assert repo.is_email_available('new_unique_user@example.com') is True

        # 3. Case-insensitive username availability check
        assert repo.is_username_available(test_user['username'].upper()) is False
        assert repo.is_username_available('brand_new_user') is True

        # 4. Batch candidate username deduplication
        existing = repo.get_existing_usernames([
            test_user['username'],
            test_user['username'].upper(),
            '  ' + test_user['username'] + '  ',
            'non_existent_123'
        ])
        assert len(existing) == 1
        assert test_user['username'].lower() in existing

        # 5. Identifier lookup
        found_by_email = repo.get_by_identifier(test_user['email'].upper())
        assert found_by_email is not None
        assert found_by_email.id == test_user['id']
