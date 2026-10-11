import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def test_app(app):
    """The suite's shared app: a second app here re-bound the engine and dropped the shared tables."""
    return app


@pytest.fixture
def test_user(test_app):
    from models import db, User
    with test_app.app_context():
        user = User.query.filter_by(email='test_events_idempotency@example.com').first()
        if not user:
            user = User(username='testuser_events_idempotency', email='test_events_idempotency@example.com', password_hash='hash')
            db.session.add(user)
            db.session.commit()
        yield user

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
            uow = UnitOfWork(db.session)
            with uow:
                service = ProjectService(uow)
                project = service.create_project(test_user.id, "Fact Recording", "Recording a fact")

            mock_handler.assert_called_once()
            event = mock_handler.call_args[0][0]
            assert isinstance(event, ProjectCreated)
            assert event.project_id == project.id
            assert hasattr(event, 'event_id')
