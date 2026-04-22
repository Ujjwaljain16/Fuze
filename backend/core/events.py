from dataclasses import dataclass, field
import uuid
from typing import Optional, Dict, Any

@dataclass(kw_only=True)
class Event:
    """Base Domain Event with unique identity for tracking and idempotency"""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)

@dataclass(kw_only=True)
class ProjectCreated(Event):
    project_id: int
    user_id: int
    title: str
    description: str
    technologies: str

@dataclass(kw_only=True)
class ProjectUpdated(Event):
    project_id: int
    user_id: int
    title_changed: bool = False
    description_changed: bool = False
    technologies_changed: bool = False

@dataclass(kw_only=True)
class ProjectDeleted(Event):
    project_id: int
    user_id: int

# --- Auth Domain Events ---

@dataclass(kw_only=True)
class UserRegistered(Event):
    user_id: Optional[int]
    email: str

# --- Recommendation & Content Domain Events ---

@dataclass(kw_only=True)
class RecommendationFeedbackRecorded(Event):
    user_id: int
    content_id: int
    recommendation_id: Optional[int]
    feedback_type: str

@dataclass(kw_only=True)
class GeminiAnalysisTriggered(Event):
    user_id: int
    content_id: int
