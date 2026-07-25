import pytest
from ml.recommendation.domain import (
    RecommendationRequest,
    RecommendationCandidate,
    CandidateSet
)
from ml.engines.smart_engine import SmartEngine


def test_smart_engine_generate():
    engine = SmartEngine()
    req = RecommendationRequest(
        user_id=1,
        title="React 19 State Management",
        description="Redux Toolkit and Zustand",
        technologies="React, TypeScript",
        max_recommendations=5
    )

    cand1 = RecommendationCandidate(
        candidate_id=1,
        content_type="bookmark",
        title="Zustand Guide",
        url="http://example.com/zustand",
        technologies=["React", "TypeScript"]
    )

    cand2 = RecommendationCandidate(
        candidate_id=2,
        content_type="bookmark",
        title="Python Asyncio",
        url="http://example.com/python",
        technologies=["Python"]
    )

    candidate_set = CandidateSet(candidates=[cand1, cand2])
    results = engine.generate(req, candidate_set)

    assert len(results) == 2
    # Candidate 1 (React, TypeScript) should rank higher than Candidate 2 (Python)
    assert results[0].candidate_id == 1
    assert results[0].score > results[1].score
    assert results[0].explanation is not None
    assert results[0].explanation.provider == "rule_based"
