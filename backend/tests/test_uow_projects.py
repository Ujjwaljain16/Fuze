import os
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def test_app(app):
    """The suite's shared app: a second app here re-bound the engine and dropped the shared tables."""
    return app


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
    import uuid
    from models import db, User
    uid = uuid.uuid4().hex[:8]
    with test_app.app_context():
        user = User(username=f'user_{uid}', email=f'user_{uid}@example.com', password_hash='hash')
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


def test_service_create_project_orchestration(uow, test_user):
    """Verify ProjectService creates a project and emits a domain event via UoW."""
    from models import db, Project
    from services.project_service import ProjectService
    from uow.unit_of_work import UnitOfWork

    # Suppress handler dispatch so test doesn't hit real ML/cache side-effects
    with patch.object(UnitOfWork, '_dispatch_events'):
        service = ProjectService(uow)
        project = service.create_project(
            user_id=test_user.id,
            title="Service Project",
            description="Built by service",
        )

        assert project.id is not None

    # The commit should have persisted the project
    saved = db.session.query(Project).filter_by(title="Service Project").first()
    assert saved is not None


def test_post_commit_hook_failure_isolation(test_app, test_user):
    """Verify that if an event handler fails, UoW still commits the transaction."""
    from models import db, Project
    from core.events import ProjectCreated
    from uow.unit_of_work import UnitOfWork
    from unittest.mock import MagicMock, patch

    failing_handler = MagicMock(side_effect=Exception("Hook failed"))
    failing_handler.__name__ = "failing_handler"

    with patch.dict('services.handlers.EVENT_HANDLERS', {ProjectCreated: [failing_handler]}):
        with test_app.app_context():
            with UnitOfWork(db.session) as u:
                project = Project(user_id=test_user.id, title="HookTest", description="...")
                u.projects.add(project)
                u.emit(ProjectCreated(
                    project_id=1, user_id=test_user.id,
                    title="HookTest", description="...", technologies=""
                ))

            # UoW should have committed even though handler raised
            saved = db.session.query(Project).filter_by(title="HookTest").first()
            assert saved is not None
            failing_handler.assert_called_once()
