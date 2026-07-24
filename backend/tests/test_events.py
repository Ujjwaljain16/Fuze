import pytest
from datetime import datetime, timezone
from core.events import (
    Event,
    ProjectCreated,
    UserRegistered,
    RecommendationFeedbackRecorded,
    FeedbackType,
)


def test_event_base_properties():
    event = Event()
    assert event.event_id is not None
    assert isinstance(event.occurred_at, datetime)
    assert event.occurred_at.tzinfo == timezone.utc
    assert event.event_version == 1
    assert event.correlation_id is None


def test_event_immutability():
    event = ProjectCreated(
        project_id=1,
        user_id=10,
        title="Immutable Project",
        description="Desc",
        technologies="Python",
        correlation_id="trace-123"
    )

    assert event.title == "Immutable Project"
    assert event.correlation_id == "trace-123"

    with pytest.raises(Exception):
        event.title = "Mutated Title"


def test_recommendation_feedback_type_enum():
    event = RecommendationFeedbackRecorded(
        user_id=1,
        content_id=100,
        feedback_type=FeedbackType.HELPFUL
    )

    assert event.feedback_type == "helpful"
    assert isinstance(event.feedback_type, FeedbackType)
