import pytest
import numpy as np
from ml.recommendation.domain import (
    RecommendationRequest,
    RecommendationCandidate,
    CandidateSet,
    RecommendationScore,
    RecommendationResult,
    RecommendationSession,
    Embedding,
    UserIntent
)


def test_embedding_normalization_invariant():
    unnormalized = np.array([3.0, 4.0], dtype=np.float32)
    emb = Embedding(vector=unnormalized)
    assert np.isclose(np.linalg.norm(emb.vector), 1.0)


def test_score_bounding_invariant():
    score_high = RecommendationScore(candidate_id=1, total_score=1.5)
    assert score_high.total_score == 1.0

    score_low = RecommendationScore(candidate_id=2, total_score=-0.5)
    assert score_low.total_score == 0.0


def test_candidate_validation_invariant():
    with pytest.raises(ValueError):
        RecommendationCandidate(candidate_id=0, content_type="", title="Invalid", url="http://invalid.com")


def test_recommendation_session_results_sorting_invariant():
    req = RecommendationRequest(user_id=1, title="Test Query")
    session = RecommendationSession(request=req)

    res1 = RecommendationResult(candidate_id=101, title="A", url="http://a.com", score=0.4, reason="R", content_type="bookmark")
    res2 = RecommendationResult(candidate_id=102, title="B", url="http://b.com", score=0.9, reason="R", content_type="bookmark")
    res3 = RecommendationResult(candidate_id=103, title="C", url="http://c.com", score=0.7, reason="R", content_type="bookmark")

    session.results = [res1, res2, res3]
    session.finalize_results()

    assert session.results[0].candidate_id == 102
    assert session.results[1].candidate_id == 103
    assert session.results[2].candidate_id == 101
