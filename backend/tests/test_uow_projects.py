import os
import pytest
from unittest.mock import patch, MagicMock


def _make_test_app():
    """Create a Flask app for testing without triggering production env validation."""
    os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-ci')
    os.environ.setdefault('JWT_SECRET_KEY', 'test-jwt-secret-key-for-ci')
    os.environ.setdefault('FLASK_ENV', 'testing')
    os.environ.setdefault('TESTING', 'true')
    os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')

    from run_production import create_app
    flask_app = create_app()
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': False,
        'connect_args': {'check_same_thread': False},
    }
    return flask_app


@pytest.fixture
def test_app():
    flask_app = _make_test_app()
    from models import db
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def uow(test_app):
    from models import db
    from uow.unit_of_work import UnitOfWork
    return UnitOfWork(db.session)


@pytest.fixture
def service(uow):
    from services.project_service import ProjectService
    return ProjectService(uow)


@pytest.fixture
def test_user(test_app):
    from models import db, User
    with test_app.app_context():
        user = User(username='testuser', email='test@example.com', password_hash='hash')
        db.session.add(user)
        db.session.commit()
        yield user


def test_uow_auto_commit(uow, test_user):
    from models import db, Project
    with uow as u:
        project = Project(user_id=test_user.id, title="Test", description="Desc")
        u.projects.add(project)

    saved = db.session.query(Project).filter_by(title="Test").first()
    assert saved is not None
    assert saved.description == "Desc"


def test_uow_rollback_on_exception(uow, test_user):
    from models import db, Project
    try:
        with uow as u:
            project = Project(user_id=test_user.id, title="Fail", description="Fail")
            u.projects.add(project)
            raise ValueError("Forced failure")
    except ValueError:
        pass

    saved = db.session.query(Project).filter_by(title="Fail").first()
    assert saved is None


def test_service_create_project_orchestration(service, test_user):
    from services.project_service import ProjectService
    with patch.object(ProjectService, '_generate_ml_assets') as mock_ml:
        with patch.object(ProjectService, '_invalidate_cache') as mock_cache:
            project = service.create_project(
                user_id=test_user.id,
                title="Service Project",
                description="Built by service",
            )

            assert project.id is not None
            mock_ml.assert_called_once()
            mock_cache.assert_called_once()


def test_post_commit_hook_failure_isolation(uow, test_user):
    """Verify that if a hook fails, it doesn't crash the UoW exit but is logged."""
    from models import db, Project

    mock_hook = MagicMock(side_effect=Exception("Hook failed"))

    with uow as u:
        project = Project(user_id=test_user.id, title="HookTest", description="...")
        u.projects.add(project)
        u.add_event(mock_hook)

    saved = db.session.query(Project).filter_by(title="HookTest").first()
    assert saved is not None
    mock_hook.assert_called_once()
