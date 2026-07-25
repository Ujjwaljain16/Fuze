"""
Two-Stage Baseline Regression Test for CI (ADR-006 Gate 1).
Compares the output of the two-stage pipeline against the frozen golden baseline artifact.
"""

import os
import json
import pytest
from unittest.mock import MagicMock
from ml.recommendation.domain import (
    RecommendationRequest,
    RecommendationCandidate,
    CandidateSet
)
from ml.recommendation.pipeline import RecommendationPipeline
from ml.recommendation.shadow_evaluator import ShadowEvaluator


@pytest.fixture
def golden_dataset():
    golden_path = os.path.join(os.path.dirname(__file__), 'golden', 'golden_recommendations.json')
    with open(golden_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture
def baseline_artifact():
    baseline_path = os.path.join(os.path.dirname(__file__), 'golden', 'golden_baseline_v1.json')
    assert os.path.exists(baseline_path), "golden_baseline_v1.json missing. Run scripts/generate_golden_baseline.py first."
    with open(baseline_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_two_stage_pipeline_against_baseline(golden_dataset, baseline_artifact, monkeypatch):
    """
    Gate 1 (Static CI):
    MRR Delta >= -0.03
    NDCG@10 Delta >= -0.03
    """
    evaluator = ShadowEvaluator()
    pipeline = RecommendationPipeline()

    mrr_scores = []
    ndcg_scores = []

    # Map baseline results by query id for easy lookup
    baseline_map = {q['query_id']: q for q in baseline_artifact['queries']}

    for item in golden_dataset.get("benchmark_queries", []):
        query_id = item["id"]
        req_data = item["request"]
        expected_candidates = item["expected_relevant_candidates"]

        req = RecommendationRequest(
            user_id=1,
            title=req_data["title"],
            description=req_data["description"],
            technologies=req_data["technologies"],
            max_recommendations=10
        )

        candidates = []
        relevance_map = {}

        for exp in expected_candidates:
            cid = exp["id"]
            title = exp["title"]
            rank = exp["expected_rank"]
            rel_score = max(1.0, 4.0 - rank)
            relevance_map[cid] = rel_score

            candidates.append(
                RecommendationCandidate(
                    candidate_id=cid,
                    content_type="bookmark",
                    title=title,
                    url=f"http://example.com/item/{cid}",
                    notes=title,
                    extracted_text=title,
                    technologies=req_data["technologies"].split(", ")
                )
            )

        for noise_id in range(900, 910):
            candidates.append(
                RecommendationCandidate(
                    candidate_id=noise_id,
                    content_type="bookmark",
                    title=f"Unrelated Topic {noise_id}",
                    url=f"http://example.com/unrelated/{noise_id}",
                    notes="Unrelated content",
                    extracted_text="Unrelated text",
                    technologies=["UnrelatedTech"]
                )
            )

        candidate_set = CandidateSet(candidates=candidates)

        # Mock the data layer to return our static candidate pool (simulating retrieval)
        mock_data_layer = MagicMock()
        mock_data_layer.fetch_candidate_set.return_value = candidate_set
        pipeline.data_layer = mock_data_layer

        # Run pipeline
        results = pipeline.run(req)
        ranked_ids = [r.candidate_id for r in results]

        top_expected_id = expected_candidates[0]["id"]
        mrr = evaluator.compute_mrr(ranked_ids, top_expected_id)
        mrr_scores.append(mrr)

        ndcg = evaluator.compute_ndcg_at_k(ranked_ids, relevance_map, k=10)
        ndcg_scores.append(ndcg)

        # Baseline per-query assertion (optional, but good for debugging)
        base_query = baseline_map[query_id]
        print(f"[{query_id}] New MRR: {mrr:.4f} (Base: {base_query['legacy_mrr']:.4f}), "
              f"New NDCG@10: {ndcg:.4f} (Base: {base_query['legacy_ndcg10']:.4f})")

    avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0.0
    avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0

    base_avg_mrr = baseline_artifact["aggregate"]["avg_mrr"]
    base_avg_ndcg = baseline_artifact["aggregate"]["avg_ndcg10"]

    mrr_delta = avg_mrr - base_avg_mrr
    ndcg_delta = avg_ndcg - base_avg_ndcg

    print(f"\n[Baseline Regression Check]")
    print(f"MRR: Pipeline={avg_mrr:.4f}, Baseline={base_avg_mrr:.4f} (Delta: {mrr_delta:.4f})")
    print(f"NDCG@10: Pipeline={avg_ndcg:.4f}, Baseline={base_avg_ndcg:.4f} (Delta: {ndcg_delta:.4f})")

    # Gate 1 Thresholds
    assert mrr_delta >= -0.03, f"MRR Delta {mrr_delta:.4f} fails Gate 1 threshold of -0.03"
    assert ndcg_delta >= -0.03, f"NDCG@10 Delta {ndcg_delta:.4f} fails Gate 1 threshold of -0.03"
