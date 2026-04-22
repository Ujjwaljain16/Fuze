import pytest
from unittest.mock import MagicMock
from services.recommendation_service import RecommendationService
from services.content_service import ContentService
from uow.unit_of_work import UnitOfWork
from core.events import RecommendationFeedbackRecorded, GeminiAnalysisTriggered

@pytest.fixture
def mock_uow():
    uow = MagicMock(spec=UnitOfWork)
    uow.recommendations = MagicMock()
    return uow

def test_feedback_records_event(mock_uow):
    """Verify that recording feedback emits a Domain Event"""
    service = RecommendationService(mock_uow)
    
    service.record_feedback(
        user_id=1,
        content_id=101,
        feedback_type="helpful",
        recommendation_id=505
    )
    
    # Verify DB record was added
    mock_uow.recommendations.add_feedback.assert_called_once()
    
    # Verify event was emitted
    mock_uow.emit.assert_called_once()
    emitted_event = mock_uow.emit.call_args[0][0]
    assert isinstance(emitted_event, RecommendationFeedbackRecorded)
    assert emitted_event.user_id == 1
    assert emitted_event.feedback_type == "helpful"

def test_analysis_trigger_emits_event(mock_uow):
    """Verify that triggering an analysis emits a Domain Event"""
    service = ContentService(mock_uow)
    
    # Mock content existence check
    mock_bookmark = MagicMock()
    mock_bookmark.user_id = 1
    mock_uow.recommendations.get_bookmark_by_id.return_value = mock_bookmark
    
    service.trigger_analysis(user_id=1, content_id=202)
    
    # Verify event was emitted
    mock_uow.emit.assert_called_once()
    emitted_event = mock_uow.emit.call_args[0][0]
    assert isinstance(emitted_event, GeminiAnalysisTriggered)
    assert emitted_event.content_id == 202
