import pytest
from models import TokenFamily, db
from repositories.token_family_repository import TokenFamilyRepository


@pytest.mark.unit
@pytest.mark.requires_db
def test_token_family_repository_operations(test_user, app):
    with app.app_context():
        repo = TokenFamilyRepository(db.session)

        # 1. Add TokenFamily
        family = TokenFamily(
            user_id=test_user['id'],
            family_id='fam-12345',
            current_jti='jti-init'
        )
        repo.add(family)
        db.session.commit()

        # 2. Get family with lock check
        tf = repo.get_family('fam-12345', lock=False)
        assert tf is not None
        assert tf.current_jti == 'jti-init'

        # 3. Update JTI
        updated = repo.update_current_jti('fam-12345', 'jti-new')
        assert updated is True
        db.session.commit()

        tf2 = repo.get_family('fam-12345')
        assert tf2.current_jti == 'jti-new'

        # 4. Revoke Family
        revoked = repo.revoke_family('fam-12345', 'logout')
        assert revoked is True
        db.session.commit()

        tf3 = repo.get_family('fam-12345')
        assert tf3.revoked is True
        assert tf3.revoked_reason == 'logout'

        # 5. Non-existent family operations return False
        assert repo.revoke_family('non-existent', 'logout') is False
        assert repo.update_current_jti('non-existent', 'new-jti') is False

        # 6. Invalid inputs raise ValueError
        with pytest.raises(ValueError):
            repo.update_current_jti('fam-12345', '')
