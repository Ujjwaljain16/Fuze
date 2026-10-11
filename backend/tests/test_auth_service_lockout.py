import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from models import User
from services.auth_service import AuthService, AuthenticationFailed


@pytest.mark.unit
def test_account_lockout_enforcement():
    mock_uow = MagicMock()
    service = AuthService(mock_uow)

    # Locked user
    user = User(id=1, username='locked_user', email='locked@example.com', password_hash='$2b$12$test')
    user.account_locked_until = datetime.utcnow() + timedelta(minutes=15)
    mock_uow.users.get_by_identifier.return_value = user

    # 1. authenticate() on locked account raises AuthenticationFailed
    with pytest.raises(AuthenticationFailed) as exc_info:
        service.authenticate('locked_user', 'password123')
    assert 'temporarily locked' in str(exc_info.value)

    # 2. A password lockout does not block Google sign-in (otherwise anyone could lock the
    #    owner out of every sign-in method with five wrong passwords)
    mock_uow.users.get_by_provider_id.return_value = user
    with patch('flask_jwt_extended.create_access_token', return_value='access'),          patch('flask_jwt_extended.create_refresh_token', return_value='refresh'),          patch('flask_jwt_extended.decode_token', return_value={'jti': 'jti-1'}):
        signed_in, _, _ = service.handle_supabase_oauth({'email': 'locked@example.com', 'id': 'supa_123',
                                                         'email_confirmed_at': '2026-01-01T00:00:00Z'})
    assert signed_in is user


@pytest.mark.unit
def test_oauth_emits_user_registered_event():
    mock_uow = MagicMock()
    service = AuthService(mock_uow)

    mock_uow.users.get_by_email.return_value = None
    mock_uow.users.get_by_provider_id.return_value = None
    mock_uow.users.get_existing_usernames.return_value = set()

    with patch('flask_jwt_extended.create_access_token', return_value='access'), \
         patch('flask_jwt_extended.create_refresh_token', return_value='refresh'), \
         patch('flask_jwt_extended.decode_token', return_value={'jti': 'jti-123'}):

        user, access, refresh = service.handle_supabase_oauth({'email': 'new_oauth@example.com', 'id': 'supa_999',
                                                                 'email_confirmed_at': '2026-01-01T00:00:00Z'})
        assert user is not None
        assert access == 'access'
        # Verify emit was called for UserRegistered
        mock_uow.emit.assert_called_once()
        event = mock_uow.emit.call_args[0][0]
        assert event.__class__.__name__ == 'UserRegistered'
        assert event.email == 'new_oauth@example.com'
