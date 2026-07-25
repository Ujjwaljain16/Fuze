import pytest
import numpy as np
from ml.recommendation.domain import RecommendationResult
from ml.recommendation.shadow_evaluator import ShadowEvaluator


def test_shadow_evaluator_overlap_metrics():
    evaluator = ShadowEvaluator()
    leg_ids = [101, 102, 103, 104, 105]

    res1 = RecommendationResult(candidate_id=101, title="A", url="http://a.com", score=0.9, reason="", content_type="bookmark")
    res2 = RecommendationResult(candidate_id=102, title="B", url="http://b.com", score=0.8, reason="", content_type="bookmark")
    res3 = RecommendationResult(candidate_id=103, title="C", url="http://c.com", score=0.7, reason="", content_type="bookmark")

    new_results = [res1, res2, res3]

    metrics = evaluator.evaluate_shadow_run(
        legacy_results=[{"id": i} for i in leg_ids],
        new_results=new_results,
        legacy_latency_ms=150.0,
        new_latency_ms=120.0
    )

    assert metrics["overlap_at_1"] == 1.0
    assert metrics["overlap_at_3"] == 1.0
    assert metrics["latency_delta_ms"] == -30.0  # New pipeline is 30ms faster


def test_ndcg_calculation():
    evaluator = ShadowEvaluator()
    ranked_ids = [101, 102, 103]
    rel_map = {101: 3.0, 102: 2.0, 103: 1.0}

    ndcg = evaluator.compute_ndcg_at_k(ranked_ids, rel_map, k=3)
    assert np.isclose(ndcg, 1.0)
