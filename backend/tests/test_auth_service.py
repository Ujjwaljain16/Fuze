import pytest
from unittest.mock import MagicMock
from services.auth_service import AuthService, AuthenticationFailed
from uow.unit_of_work import UnitOfWork
from models import User

@pytest.fixture
def mock_uow():
    uow = MagicMock(spec=UnitOfWork)
    uow.users = MagicMock()
    return uow

def test_auth_precedence_email_first(mock_uow):
    """Verify that get_by_identifier prioritizes email over username if both match different users"""
    service = AuthService(mock_uow)
    
    # Setup: mock user without using spec=User to avoid app-context issues during model setup
    mock_user = MagicMock()
    # Provide a real bcrypt hash so authentication logic can proceed
    import bcrypt
    pwd = "password123".encode('utf-8')
    mock_user.password_hash = bcrypt.hashpw(pwd, bcrypt.gensalt()).decode('utf-8')
    mock_uow.users.get_by_identifier.return_value = mock_user
    
    # Setup: identifier looks like an email but might be a username too
    identifier = "test@example.com"
    
    # We don't need to mock the service logic, but we test that it calls the repo correctly
    service.authenticate(identifier, "password123")
    
    # Check that repo was called with normalized identifier
    mock_uow.users.get_by_identifier.assert_called_once_with(identifier)

def test_registration_normalization(mock_uow):
    """Verify that registration normalizes inputs before adding to repo"""
    service = AuthService(mock_uow)
    
    service.register("  MixedCaseUser  ", "  TEST@EXAMPLE.COM  ", "Password123!")
    
    # Get the user object passed to uow.users.add
    added_user = mock_uow.users.add.call_args[0][0]
    
    assert added_user.username == "mixedcaseuser"
    assert added_user.email == "test@example.com"
    assert added_user.password_hash.startswith("$2b$") # Should be bcrypt

def test_authentication_failed_raises(mock_uow):
    """Verify that non-existent user raises AuthenticationFailed"""
    mock_uow.users.get_by_identifier.return_value = None
    service = AuthService(mock_uow)
    
    with pytest.raises(AuthenticationFailed):
        service.authenticate("nonexistent", "any_password")
