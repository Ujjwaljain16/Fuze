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
def test_user(test_app):
    from models import db, User
    with test_app.app_context():
        user = User(username='testuser', email='test@example.com', password_hash='hash')
        db.session.add(user)
        db.session.commit()
        yield user


def test_handler_idempotency(test_app, test_user):
    """
    Critical Test: Ensure running handle_project_created multiple times
    converges on a single state and doesn't create duplicate analytic records.
    """
    from models import db, Project
    from core.events import ProjectCreated
    from services.handlers.project_handlers import handle_project_created

    with test_app.app_context():
        project = Project(user_id=test_user.id, title="Idempotency Test", description="Testing re-runs")
        project.technologies = "Python, Flask"
        db.session.add(project)
        db.session.commit()

        event = ProjectCreated(
            project_id=project.id,
            user_id=test_user.id,
            title=project.title,
            description=project.description,
            technologies=project.technologies,
        )

        with patch('utils.embedding_utils.get_project_embedding', return_value=[0.1] * 384):
            with patch('ml.intent_analysis_engine.analyze_user_intent') as mock_intent:
                handle_project_created(event)
                handle_project_created(event)

                assert mock_intent.call_count == 2

                projects = db.session.query(Project).all()
                assert len(projects) == 1
                assert projects[0].embedding is not None


def test_safe_event_dispatch_isolation(test_app, test_user):
    """
    Verify that a failing event handler does NOT affect transaction success
    and that other handlers still run.
    """
    from models import db, Project
    from core.events import ProjectCreated
    from uow.unit_of_work import UnitOfWork

    fail_handler = MagicMock()
    fail_handler.__name__ = "fail_handler"
    fail_handler.side_effect = Exception("BOOM")

    success_handler = MagicMock()
    success_handler.__name__ = "success_handler"

    with patch.dict('services.handlers.EVENT_HANDLERS', {ProjectCreated: [fail_handler, success_handler]}):
        with test_app.app_context():
            uow = UnitOfWork(db.session)
            with uow as u:
                p = Project(user_id=test_user.id, title="DispatchTest", description="...")
                u.projects.add(p)
                u.emit(ProjectCreated(
                    project_id=1, user_id=test_user.id, title="T", description="D", technologies=""
                ))

            fail_handler.assert_called_once()
            success_handler.assert_called_once()


def test_event_recording_and_dispatch_flow(test_app, test_user):
    """End-to-end service -> UoW -> Event -> Handler flow check."""
    from models import db
    from core.events import ProjectCreated
    from uow.unit_of_work import UnitOfWork
    from services.project_service import ProjectService

    mock_handler = MagicMock()
    mock_handler.__name__ = "mock_handler"

    with patch.dict('services.handlers.EVENT_HANDLERS', {ProjectCreated: [mock_handler]}):
        with test_app.app_context():
            service = ProjectService(UnitOfWork(db.session))
            project = service.create_project(test_user.id, "Fact Recording", "Recording a fact")

            mock_handler.assert_called_once()
            event = mock_handler.call_args[0][0]
            assert isinstance(event, ProjectCreated)
            assert event.project_id == project.id
            assert hasattr(event, 'event_id')
