"""
Golden Dataset Recommendation Quality Regression Test.
Loads backend/tests/golden/golden_recommendations.json and asserts NDCG@10 >= 0.85 and MRR >= 0.85.
Guarantees that architectural refactoring never regresses recommendation relevance quality.
"""

import os
import json
import pytest
from ml.recommendation.domain import (
    RecommendationRequest,
    RecommendationCandidate,
    CandidateSet
)
from ml.engines.smart_engine import SmartEngine
from ml.recommendation.shadow_evaluator import ShadowEvaluator


@pytest.fixture
def golden_dataset():
    golden_path = os.path.join(os.path.dirname(__file__), 'golden', 'golden_recommendations.json')
    assert os.path.exists(golden_path), f"Golden dataset file missing at {golden_path}"
    with open(golden_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_golden_dataset_quality_benchmarks(golden_dataset):
    engine = SmartEngine()
    evaluator = ShadowEvaluator()

    mrr_scores = []
    ndcg_scores = []

    for item in golden_dataset.get("benchmark_queries", []):
        req_data = item["request"]
        expected_candidates = item["expected_relevant_candidates"]

        req = RecommendationRequest(
            user_id=1,
            title=req_data["title"],
            description=req_data["description"],
            technologies=req_data["technologies"],
            max_recommendations=10
        )

        # Build candidate pool containing expected candidates + noise candidates
        candidates = []
        relevance_map = {}

        for exp in expected_candidates:
            cid = exp["id"]
            title = exp["title"]
            rank = exp["expected_rank"]
            rel_score = max(1.0, 4.0 - rank)  # Convert rank 1->3.0, 2->2.0, 3->1.0
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

        # Add distractor / noise candidates
        for noise_id in range(900, 905):
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
        results = engine.generate(req, candidate_set)
        ranked_ids = [r.candidate_id for r in results]

        # Evaluate MRR for top expected candidate
        top_expected_id = expected_candidates[0]["id"]
        mrr = evaluator.compute_mrr(ranked_ids, top_expected_id)
        mrr_scores.append(mrr)

        # Evaluate NDCG@10
        ndcg = evaluator.compute_ndcg_at_k(ranked_ids, relevance_map, k=10)
        ndcg_scores.append(ndcg)

    avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0.0
    avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0

    print(f"\n[Golden Quality Benchmark] Avg MRR: {avg_mrr:.4f}, Avg NDCG@10: {avg_ndcg:.4f}")

    # Enforce quality gates
    assert avg_mrr >= 0.85, f"Average MRR {avg_mrr:.4f} fell below production gate of 0.85"
    assert avg_ndcg >= 0.85, f"Average NDCG@10 {avg_ndcg:.4f} fell below production gate of 0.85"
