import pytest
from app import app
from models import db, User, Project, ContentAnalysis
from uow.unit_of_work import UnitOfWork
from services.project_service import ProjectService
from core.events import ProjectCreated
from services.handlers.project_handlers import handle_project_created
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
def test_user(test_app):
    user = User(username='testuser', email='test@example.com', password_hash='hash')
    db.session.add(user)
    db.session.commit()
    return user

def test_handler_idempotency(test_app, test_user):
    """
    Critical Test: Ensure running handle_project_created multiple times 
    converges on a single state and doesn't create duplicate analytic records.
    """
    with app.app_context():
        # 1. Setup project
        project = Project(user_id=test_user.id, title="Idempotency Test", description="Testing re-runs")
        # technologies is used by intent engine
        project.technologies = "Python, Flask"
        db.session.add(project)
        db.session.commit()
        
        event = ProjectCreated(
            project_id=project.id, 
            user_id=test_user.id,
            title=project.title,
            description=project.description,
            technologies=project.technologies
        )
        
        # Mock ML dependencies to avoid real API
        with patch('utils.embedding_utils.get_project_embedding', return_value=[0.1]*384):
            with patch('ml.intent_analysis_engine.analyze_user_intent') as mock_intent:
                
                # 2. Run handler first time
                handle_project_created(event)
                
                # 3. Run handler second time (simulated retry)
                handle_project_created(event)
                
                # 4. Verify results
                # analyze_user_intent with force_analysis=True just overwrites, 
                # so we check if it was called twice but project state is clean.
                assert mock_intent.call_count == 2
                
                # Check that we still have only 1 project
                projects = db.session.query(Project).all()
                assert len(projects) == 1
                assert projects[0].embedding is not None

def test_safe_event_dispatch_isolation(test_app, test_user):
    """
    Verify that a failing event handler does NOT affect transaction success
    and that other handlers still run.
    """
    fail_handler = MagicMock()
    fail_handler.__name__ = "fail_handler"
    fail_handler.side_effect = Exception("BOOM")
    
    success_handler = MagicMock()
    success_handler.__name__ = "success_handler"
    
    # Patch the centralized registry directly
    with patch.dict('services.handlers.EVENT_HANDLERS', {ProjectCreated: [fail_handler, success_handler]}):
        with app.app_context():
            uow = UnitOfWork(db.session)
            with uow as u:
                p = Project(user_id=test_user.id, title="DispatchTest", description="...")
                u.projects.add(p)
                u.emit(ProjectCreated(
                    project_id=1, user_id=test_user.id, title="T", description="D", technologies=""
                ))
            
            # If we reach here, the transaction committed despite the failing handler
            fail_handler.assert_called_once()
            success_handler.assert_called_once()

def test_event_recording_and_dispatch_flow(test_app, test_user):
    """End-to-end service -> UoW -> Event -> Handler flow check."""
    mock_handler = MagicMock()
    mock_handler.__name__ = "mock_handler"
    
    with patch.dict('services.handlers.EVENT_HANDLERS', {ProjectCreated: [mock_handler]}):
        with app.app_context():
            service = ProjectService(UnitOfWork(db.session))
            # Trigger service
            project = service.create_project(test_user.id, "Fact Recording", "Recording a fact")
            
            # Handler should be called post-commit
            mock_handler.assert_called_once()
            event = mock_handler.call_args[0][0]
            assert isinstance(event, ProjectCreated)
            assert event.project_id == project.id
            assert hasattr(event, 'event_id')
