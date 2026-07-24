import pytest
from unittest.mock import MagicMock
from models import SavedContent
from services.recommendation_service import RecommendationService


@pytest.mark.unit
def test_recommendation_service_feedback_validation():
    mock_uow = MagicMock()
    service = RecommendationService(mock_uow)

    # 1. Invalid feedback_type raises ValueError
    with pytest.raises(ValueError) as exc_info:
        service.record_feedback(user_id=1, content_id=10, feedback_type="invalid_type")
    assert "Invalid feedback_type" in str(exc_info.value)

    # 2. Non-existent content raises ValueError
    mock_uow.bookmarks.get_by_id.return_value = None
    with pytest.raises(ValueError) as exc_info:
        service.record_feedback(user_id=1, content_id=999, feedback_type="helpful")
    assert "Content 999 not found" in str(exc_info.value)

    # 3. Cross-tenant feedback raises PermissionError
    foreign_content = SavedContent(id=10, user_id=2)  # Belongs to user 2
    mock_uow.bookmarks.get_by_id.return_value = foreign_content

    with pytest.raises(PermissionError) as exc_info:
        service.record_feedback(user_id=1, content_id=10, feedback_type="helpful")
    assert "does not belong to user 1" in str(exc_info.value)

    # 4. Valid feedback succeeds and emits event
    own_content = SavedContent(id=10, user_id=1)
    mock_uow.bookmarks.get_by_id.return_value = own_content

    feedback = service.record_feedback(user_id=1, content_id=10, feedback_type="helpful")
    assert feedback.feedback_type == "helpful"
    assert mock_uow.recommendations.add_feedback.call_count == 1
    assert mock_uow.emit.call_count == 1
    event = mock_uow.emit.call_args[0][0]
    assert event.__class__.__name__ == 'RecommendationFeedbackRecorded'
