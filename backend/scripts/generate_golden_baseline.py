#!/usr/bin/env python3
"""
scripts/generate_golden_baseline.py
=====================================
Generates golden_baseline_v1.json by running the validated legacy orchestrator
against the benchmark queries in golden_recommendations.json.

This script must be run ONCE against the legacy orchestrator BEFORE any
two-stage retrieval code is merged. The output is committed to version control
and becomes the permanent frozen regression target for ADR-006 Gate 1.

NEVER regenerate this file from live traffic. It is the static baseline.
To version the baseline, generate golden_baseline_v2.json with a new script
version and create an ADR amendment. Keep v1 archived, not deleted.

Usage:
    cd backend
    python scripts/generate_golden_baseline.py
    python scripts/generate_golden_baseline.py --output tests/golden/golden_baseline_v1.json
    python scripts/generate_golden_baseline.py --user-id 1  # use real user data
    python scripts/generate_golden_baseline.py --dry-run    # compute + print, no write

Output format:
    {
      "version": "1",
      "generated_at": "<ISO timestamp>",
      "generated_from": "unified_recommendation_orchestrator.py",
      "queries": [
        {
          "query_id": "query_frontend_01",
          "query": "React Dashboard with Tailwind CSS",
          "legacy_top10": [101, 102, 103, ...],
          "legacy_mrr": 0.91,
          "legacy_ndcg10": 0.96
        }
      ],
      "aggregate": {
        "avg_mrr": 0.91,
        "avg_ndcg10": 0.95,
        "query_count": 4
      }
    }
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv()

GOLDEN_DATASET_PATH = os.path.join(backend_dir, "tests", "golden", "golden_recommendations.json")
DEFAULT_OUTPUT_PATH = os.path.join(backend_dir, "tests", "golden", "golden_baseline_v1.json")


def load_golden_dataset() -> dict:
    with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run_legacy_pipeline(query_item: dict, user_id: int) -> dict:
    """
    Run the legacy SmartEngine pipeline against a single benchmark query.
    Uses the golden dataset candidate pool (not live DB data) for reproducibility.
    Returns legacy_top10 ids, mrr, ndcg10.
    """
    from ml.recommendation.domain import (
        RecommendationRequest,
        RecommendationCandidate,
        CandidateSet,
    )
    from ml.engines.smart_engine import SmartEngine
    from ml.recommendation.shadow_evaluator import ShadowEvaluator

    req_data = query_item["request"]
    expected_candidates = query_item["expected_relevant_candidates"]

    req = RecommendationRequest(
        user_id=user_id,
        title=req_data["title"],
        description=req_data["description"],
        technologies=req_data["technologies"],
        max_recommendations=10,
    )

    # Build candidate pool: expected candidates + noise (same as test suite)
    candidates = []
    relevance_map = {}

    for exp in expected_candidates:
        cid = exp["id"]
        rank = exp["expected_rank"]
        rel_score = max(1.0, 4.0 - rank)  # rank 1→3.0, 2→2.0, 3→1.0
        relevance_map[cid] = rel_score

        candidates.append(
            RecommendationCandidate(
                candidate_id=cid,
                content_type="bookmark",
                title=exp["title"],
                url=f"http://example.com/item/{cid}",
                notes=exp["title"],
                extracted_text=exp["title"],
                technologies=req_data["technologies"].split(", "),
            )
        )

    # Noise candidates
    for noise_id in range(900, 910):
        candidates.append(
            RecommendationCandidate(
                candidate_id=noise_id,
                content_type="bookmark",
                title=f"Unrelated Topic {noise_id}",
                url=f"http://example.com/unrelated/{noise_id}",
                notes="Unrelated content",
                extracted_text="Unrelated text",
                technologies=["UnrelatedTech"],
            )
        )

    engine = SmartEngine()
    evaluator = ShadowEvaluator()
    candidate_set = CandidateSet(candidates=candidates)
    results = engine.generate(req, candidate_set)
    ranked_ids = [r.candidate_id for r in results]

    top_expected_id = expected_candidates[0]["id"]
    mrr = evaluator.compute_mrr(ranked_ids, top_expected_id)
    ndcg = evaluator.compute_ndcg_at_k(ranked_ids, relevance_map, k=10)

    return {
        "query_id": query_item["id"],
        "query": req_data["title"],
        "legacy_top10": ranked_ids[:10],
        "legacy_mrr": round(mrr, 6),
        "legacy_ndcg10": round(ndcg, 6),
    }


def generate_baseline(user_id: int = 1, output_path: str = DEFAULT_OUTPUT_PATH, dry_run: bool = False):
    dataset = load_golden_dataset()
    queries = dataset.get("benchmark_queries", [])

    print(f"\nGenerating golden baseline from {len(queries)} benchmark queries...")
    print(f"  Engine: SmartEngine (legacy pipeline)")
    print(f"  Output: {output_path}")
    print(f"  Dry-run: {dry_run}\n")

    baseline_queries = []
    mrr_scores = []
    ndcg_scores = []

    for item in queries:
        result = run_legacy_pipeline(item, user_id)
        baseline_queries.append(result)
        mrr_scores.append(result["legacy_mrr"])
        ndcg_scores.append(result["legacy_ndcg10"])
        print(f"  [{item['id']}] MRR={result['legacy_mrr']:.4f}  NDCG@10={result['legacy_ndcg10']:.4f}  "
              f"Top3={result['legacy_top10'][:3]}")

    avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0.0
    avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0

    baseline = {
        "version": "1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_from": "unified_recommendation_orchestrator.py (SmartEngine)",
        "note": (
            "FROZEN BASELINE — do not regenerate from live traffic. "
            "This is the permanent Gate 1 regression target per ADR-006. "
            "To update, generate golden_baseline_v2.json and amend the ADR."
        ),
        "queries": baseline_queries,
        "aggregate": {
            "avg_mrr": round(avg_mrr, 6),
            "avg_ndcg10": round(avg_ndcg, 6),
            "query_count": len(queries),
        },
    }

    print(f"\n  Aggregate MRR:    {avg_mrr:.4f}")
    print(f"  Aggregate NDCG@10: {avg_ndcg:.4f}")

    if dry_run:
        print("\n[DRY RUN] Baseline not written.")
        print(json.dumps(baseline, indent=2))
        return

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2)

    print(f"\n[OK] Baseline written to: {output_path}")
    print("     Commit this file to version control immediately.")
    print("     Do NOT regenerate without creating a new version (v2, v3...).")


def main():
    parser = argparse.ArgumentParser(description="Generate frozen golden baseline for ADR-006 Gate 1")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    generate_baseline(user_id=args.user_id, output_path=args.output, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
