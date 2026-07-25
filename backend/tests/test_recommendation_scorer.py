import pytest
import numpy as np
from ml.recommendation.domain import (
    RecommendationRequest,
    RecommendationCandidate,
    Embedding
)
from ml.recommendation.scorer import RecommendationScorer


def test_compute_vector_similarity_pure():
    scorer = RecommendationScorer()
    vec_a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    vec_b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    sim = scorer.compute_vector_similarity(vec_a, vec_b)
    assert np.isclose(sim, 1.0)

    vec_c = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    sim_orthogonal = scorer.compute_vector_similarity(vec_a, vec_c)
    assert np.isclose(sim_orthogonal, 0.0)


def test_compute_technology_overlap_pure():
    scorer = RecommendationScorer()
    req_techs = ["React", "TypeScript", "Tailwind"]
    cand_techs = ["React", "Python", "Tailwind"]

    overlap = scorer.compute_technology_overlap(req_techs, cand_techs)
    # Intersection: {"react", "tailwind"} (2), Union: {"react", "typescript", "tailwind", "python"} (4) -> 2/4 = 0.5
    assert np.isclose(overlap, 0.5)


def test_compute_bm25_score_pure():
    scorer = RecommendationScorer()
    query = ["React", "dashboard"]
    doc = ["Building", "a", "React", "19", "analytics", "dashboard"]

    bm25 = scorer.compute_bm25_score(query, doc)
    assert 0.0 <= bm25 <= 1.0
    assert bm25 > 0.5


def test_score_candidate_integration_pure():
    scorer = RecommendationScorer()
    req = RecommendationRequest(
        user_id=1,
        title="React Frontend",
        description="Dashboard UI",
        technologies="React, TypeScript"
    )
    cand = RecommendationCandidate(
        candidate_id=101,
        content_type="bookmark",
        title="React 19 State Patterns",
        url="http://example.com/react",
        technologies=["React", "TypeScript"]
    )

    score = scorer.score_candidate(req, cand)
    assert score.candidate_id == 101
    assert 0.0 <= score.total_score <= 1.0
    assert score.breakdown.technology_match == 1.0
