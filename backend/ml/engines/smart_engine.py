"""
SmartEngine: Recommendation strategy combining candidate vector math, BM25 text relevance, and tech overlap.
Operates strictly on RecommendationRequest, CandidateSet, and RecommendationScorer without DB or network side-effects.
"""

from typing import List, Optional
import time
import logging
from ml.engines.base_engine import BaseRecommendationEngine
from ml.recommendation.domain import (
    RecommendationRequest,
    CandidateSet,
    RecommendationResult,
    RecommendationExplanation
)
from ml.recommendation.scorer import RecommendationScorer

logger = logging.getLogger(__name__)


class SmartEngine(BaseRecommendationEngine):
    """Hybrid Vector + BM25 + Tech Overlap Recommendation Strategy."""

    def __init__(self, scorer: Optional[RecommendationScorer] = None):
        super().__init__(scorer=scorer)
        self.name = "SmartEngine"

    def generate(
        self,
        request: RecommendationRequest,
        candidates: CandidateSet
    ) -> List[RecommendationResult]:
        """
        Generate ranked recommendation results for the candidate set.
        """
        start_time = time.time()
        results: List[RecommendationResult] = []

        if not candidates or len(candidates) == 0:
            logger.debug(f"[{self.name}] Empty candidate set provided; returning empty results.")
            return []

        try:
            for candidate in candidates.candidates:
                # 1. Score candidate using pure RecommendationScorer
                score_entity = self.scorer.score_candidate(request, candidate)

                # 2. Build human-readable reason string from reason tags
                reasons = [tag.description for tag in score_entity.reason_tags]
                reason_str = "; ".join(reasons) if reasons else "Relevant content match"

                # 3. Create RecommendationResult domain entity
                result = RecommendationResult(
                    candidate_id=candidate.candidate_id,
                    title=candidate.title,
                    url=candidate.url,
                    score=score_entity.total_score,
                    reason=reason_str,
                    content_type=candidate.content_type,
                    technologies=candidate.technologies,
                    explanation=RecommendationExplanation(
                        provider="rule_based",
                        summary=f"Matched with score {score_entity.total_score:.2f}",
                        key_reasons=reasons
                    )
                )
                results.append(result)

            # Sort descending by score (Invariant 4)
            results.sort(key=lambda r: r.score, reverse=True)

            # Cap to request limit
            results = results[:request.max_recommendations]

            elapsed_ms = (time.time() - start_time) * 1000
            logger.debug(f"[{self.name}] Generated {len(results)} recommendations in {elapsed_ms:.1f}ms")

        except Exception as e:
            logger.error(f"[{self.name}] Execution error: {e}", exc_info=True)

        return results
