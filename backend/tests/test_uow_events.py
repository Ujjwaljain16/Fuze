import pytest
from unittest.mock import MagicMock, patch
from core.events import Event
from uow.unit_of_work import UnitOfWork


class DummyEvent(Event):
    def __init__(self):
        super().__init__()


@pytest.mark.unit
def test_uow_events_cleared_after_dispatch():
    mock_session = MagicMock()
    uow = UnitOfWork(session=mock_session)

    event = DummyEvent()
    uow.emit(event)
    assert len(uow.events) == 1

    with patch('services.handlers.EVENT_HANDLERS', {DummyEvent: [MagicMock()]}):
        with uow:
            pass  # Normal commit + dispatch

    # Events list should be cleared after dispatch
    assert len(uow.events) == 0


@pytest.mark.unit
def test_uow_analysis_repository_integration():
    mock_session = MagicMock()
    uow = UnitOfWork(session=mock_session)

    repo = uow.analyses
    assert repo.__class__.__name__ == 'AnalysisRepository'
    assert repo.session == mock_session


@pytest.mark.unit
def test_uow_commit_and_post_commit_dispatch_isolation():
    mock_session = MagicMock()
    uow = UnitOfWork(session=mock_session)

    event = DummyEvent()
    uow.emit(event)

    failing_handler = MagicMock(side_effect=RuntimeError("Handler crashed"))

    with patch('services.handlers.EVENT_HANDLERS', {DummyEvent: [failing_handler]}):
        with uow:
            pass

    # Commit should succeed
    mock_session.commit.assert_called_once()
    # Rollback should NOT be called since commit succeeded
    mock_session.rollback.assert_not_called()
    # Events should be cleared
    assert len(uow.events) == 0
