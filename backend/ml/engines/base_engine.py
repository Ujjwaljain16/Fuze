"""
BaseRecommendationEngine Contract Specification.
Abstract base class defining strict input/output contracts for all engine strategies.
Enforces ADR-005 boundaries: engines operate strictly on Domain Entities (RecommendationRequest, CandidateSet)
and RecommendationScorer. Engines MUST NOT accept raw repositories, SQLAlchemy sessions, or Redis clients.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import logging
from ml.recommendation.domain import (
    RecommendationRequest,
    CandidateSet,
    RecommendationResult
)
from ml.recommendation.scorer import RecommendationScorer

logger = logging.getLogger(__name__)


class BaseRecommendationEngine(ABC):
    """Abstract Base Recommendation Engine Contract."""

    def __init__(self, scorer: Optional[RecommendationScorer] = None):
        self.scorer = scorer or RecommendationScorer()

    @abstractmethod
    def generate(
        self,
        request: RecommendationRequest,
        candidates: CandidateSet
    ) -> List[RecommendationResult]:
        """
        Generate ranked recommendation results given request and candidate set.

        Inputs:
            request: RecommendationRequest (Domain Entity)
            candidates: CandidateSet (Aggregate)

        Returns:
            List[RecommendationResult]: Ranked recommendation results sorted descending by score.
        """
        pass
