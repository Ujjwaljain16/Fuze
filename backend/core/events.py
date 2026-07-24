from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid
from typing import Optional, Union


class FeedbackType(str, Enum):
    """Canonical feedback types for recommendation events."""
    LIKE = "like"
    DISLIKE = "dislike"
    HELPFUL = "helpful"
    NOT_RELEVANT = "not_relevant"
    CLICKED = "clicked"
    SAVED = "saved"
    COMPLETED = "completed"


@dataclass(frozen=True, kw_only=True)
class Event:
    """
    Base Immutable Domain Event with unique identity, UTC timestamp, schema versioning,
    and correlation tracking for audit trails and distributed tracing.
    """
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_version: int = 1
    correlation_id: Optional[str] = None


# --- Project Domain Events ---

@dataclass(frozen=True, kw_only=True)
class ProjectCreated(Event):
    project_id: int
    user_id: int
    title: str
    description: str
    technologies: str


@dataclass(frozen=True, kw_only=True)
class ProjectUpdated(Event):
    project_id: int
    user_id: int
    title: str
    description: str
    technologies: str
    title_changed: bool = False
    description_changed: bool = False
    technologies_changed: bool = False


@dataclass(frozen=True, kw_only=True)
class ProjectDeleted(Event):
    project_id: int
    user_id: int


# --- Auth Domain Events ---

@dataclass(frozen=True, kw_only=True)
class UserRegistered(Event):
    user_id: Optional[int] = None
    email: str = ""


# --- Recommendation & Content Domain Events ---

@dataclass(frozen=True, kw_only=True)
class RecommendationFeedbackRecorded(Event):
    user_id: int
    content_id: int
    recommendation_id: Optional[int] = None
    feedback_type: Union[FeedbackType, str] = FeedbackType.HELPFUL


@dataclass(frozen=True, kw_only=True)
class GeminiAnalysisTriggered(Event):
    user_id: int
    content_id: int


# --- Bookmark Domain Events ---

@dataclass(frozen=True, kw_only=True)
class BookmarkCreated(Event):
    bookmark_id: int
    user_id: int
    url: str


@dataclass(frozen=True, kw_only=True)
class BookmarkDeleted(Event):
    bookmark_id: int
    user_id: int
