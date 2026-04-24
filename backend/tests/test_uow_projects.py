import pytest
from app import app
from models import db, User, Project
from uow.unit_of_work import UnitOfWork
from services.project_service import ProjectService
from unittest.mock import patch, MagicMock

@pytest.fixture
def test_app():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def uow(test_app):
    return UnitOfWork(db.session)

@pytest.fixture
def service(uow):
    return ProjectService(uow)

@pytest.fixture
def test_user(test_app):
    user = User(username='testuser', email='test@example.com', password_hash='hash')
    db.session.add(user)
    db.session.commit()
    return user

def test_uow_auto_commit(uow, test_user):
    with uow as u:
        project = Project(user_id=test_user.id, title="Test", description="Desc")
        u.projects.add(project)
    
    # After exit, it should be committed
    saved = db.session.query(Project).filter_by(title="Test").first()
    assert saved is not None
    assert saved.description == "Desc"

def test_uow_rollback_on_exception(uow, test_user):
    try:
        with uow as u:
            project = Project(user_id=test_user.id, title="Fail", description="Fail")
            u.projects.add(project)
            raise ValueError("Forced failure")
    except ValueError:
        pass
    
    # Should be rolled back
    saved = db.session.query(Project).filter_by(title="Fail").first()
    assert saved is None

def test_service_create_project_orchestration(service, test_user):
    # Mock ML assets to avoid real API calls
    with patch.object(ProjectService, '_generate_ml_assets') as mock_ml:
        with patch.object(ProjectService, '_invalidate_cache') as mock_cache:
            project = service.create_project(
                user_id=test_user.id,
                title="Service Project",
                description="Built by service"
            )
            
            assert project.id is not None
            # Verify mocks were called (signaling post-commit hooks ran)
            mock_ml.assert_called_once()
            mock_cache.assert_called_once()

def test_post_commit_hook_failure_isolation(uow, test_user):
    """Verify that if a hook fails, it doesn't crash the UoW exit but is logged."""
    mock_hook = MagicMock(side_effect=Exception("Hook failed"))
    
    with uow as u:
        project = Project(user_id=test_user.id, title="HookTest", description="...")
        u.projects.add(project)
        u.add_event(mock_hook)
        
    # UoW should still finish successfully
    saved = db.session.query(Project).filter_by(title="HookTest").first()
    assert saved is not None
    mock_hook.assert_called_once()
