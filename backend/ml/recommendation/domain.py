"""
Recommendation Domain Model & DDD Bounded Contexts.
Defines explicit Entities, Value Objects, Aggregates, Invariants, and RecommendationExplanation context.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import uuid
import numpy as np


@dataclass(frozen=True)
class UserIntent:
    """Immutable Value Object: User intent parameters."""
    primary_domain: str = "general"
    difficulty_level: str = "intermediate"
    target_focus: str = ""


@dataclass(frozen=True)
class Embedding:
    """Immutable Value Object: Dense vector embedding wrapper enforcing L2 normalization."""
    vector: np.ndarray

    def __post_init__(self):
        if not isinstance(self.vector, np.ndarray):
            object.__setattr__(self, 'vector', np.array(self.vector, dtype=np.float32))
        norm = np.linalg.norm(self.vector)
        if norm > 0 and not np.isclose(norm, 1.0):
            object.__setattr__(self, 'vector', self.vector / norm)


@dataclass(frozen=True)
class ScoreBreakdown:
    """Immutable Value Object: Component scoring metrics."""
    vector_similarity: float = 0.0
    bm25_relevance: float = 0.0
    technology_match: float = 0.0
    recency_decay: float = 1.0


@dataclass(frozen=True)
class ReasonTag:
    """Immutable Value Object: Explainability tag."""
    tag: str
    description: str


@dataclass(frozen=True)
class RecommendationExplanation:
    """Bounded Context: Separated LLM/Rule-based explanation payload."""
    provider: str  # e.g., 'gemini', 'openai', 'rule_based', 'none'
    summary: str
    key_reasons: List[str] = field(default_factory=list)


@dataclass
class RecommendationRequest:
    """Entity: Standardized recommendation request."""
    user_id: int
    title: str
    description: str = ""
    technologies: str = ""
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    subtask_id: Optional[int] = None
    max_recommendations: int = 10
    intent: Optional[UserIntent] = None
    query_embedding: Optional[Embedding] = None
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        if self.max_recommendations > 100:
            self.max_recommendations = 100


@dataclass
class RecommendationCandidate:
    """Entity: Un-scored recommendation candidate."""
    candidate_id: int
    content_type: str  # 'bookmark' or 'project'
    title: str
    url: str
    notes: str = ""
    extracted_text: str = ""
    technologies: List[str] = field(default_factory=list)
    embedding: Optional[Embedding] = None

    def __post_init__(self):
        if not self.candidate_id or not self.content_type:
            raise ValueError("Candidate candidate_id and content_type are required invariants")


@dataclass
class CandidateSet:
    """Aggregate: Container for un-scored candidates."""
    candidates: List[RecommendationCandidate] = field(default_factory=list)

    def __len__(self):
        return len(self.candidates)


@dataclass
class RecommendationScore:
    """Entity: Computed score bound to a candidate."""
    candidate_id: int
    total_score: float
    breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    reason_tags: List[ReasonTag] = field(default_factory=list)

    def __post_init__(self):
        # Enforce Invariant 1: 0.0 <= total_score <= 1.0
        self.total_score = max(0.0, min(1.0, float(self.total_score)))


@dataclass
class RecommendationResult:
    """Entity: Ranked output recommendation item."""
    candidate_id: int
    title: str
    url: str
    score: float
    reason: str
    content_type: str
    technologies: List[str] = field(default_factory=list)
    explanation: Optional[RecommendationExplanation] = None

    def __post_init__(self):
        self.score = max(0.0, min(1.0, float(self.score)))


@dataclass
class RecommendationSession:
    """Aggregate Root: Coordinates request lifecycle state and outputs."""
    request: RecommendationRequest
    candidate_set: CandidateSet = field(default_factory=CandidateSet)
    scores: List[RecommendationScore] = field(default_factory=list)
    results: List[RecommendationResult] = field(default_factory=list)

    def finalize_results(self):
        """Enforce Invariant 4: Sort results strictly descending by score."""
        self.results.sort(key=lambda r: r.score, reverse=True)
