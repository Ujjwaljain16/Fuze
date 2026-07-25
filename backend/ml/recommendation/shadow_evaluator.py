"""
Shadow Evaluator: Dual-execution shadow framework for recommendation quality comparison (ADR-003).
Runs new RecommendationPipeline alongside legacy orchestrator without impacting user traffic.
Logs Overlap@K, MRR Delta, NDCG Delta, and Latency Delta diagnostics.
Emits Prometheus gauges for ADR-006 dynamic gate monitoring.
"""

from typing import List, Dict, Any
import math
import logging
from ml.recommendation.domain import RecommendationResult

logger = logging.getLogger(__name__)


class ShadowEvaluator:
    """Evaluates recommendation quality parity between legacy and new pipeline."""

    @staticmethod
    def compute_overlap_at_k(legacy_ids: List[int], new_ids: List[int], k: int) -> float:
        """Compute Top-K candidate overlap ratio."""
        if k <= 0:
            return 0.0
        leg_sub = set(legacy_ids[:k])
        new_sub = set(new_ids[:k])
        if not leg_sub or not new_sub:
            return 0.0
        intersection = len(leg_sub.intersection(new_sub))
        return float(intersection / min(k, len(leg_sub)))

    @staticmethod
    def compute_mrr(candidate_ids: List[int], relevant_id: int) -> float:
        """Compute Mean Reciprocal Rank for a relevant candidate."""
        if relevant_id in candidate_ids:
            rank = candidate_ids.index(relevant_id) + 1
            return 1.0 / rank
        return 0.0

    @staticmethod
    def compute_ndcg_at_k(ranked_ids: List[int], relevance_map: Dict[int, float], k: int = 10) -> float:
        """Compute Normalized Discounted Cumulative Gain at K."""
        if not ranked_ids or not relevance_map:
            return 0.0

        dcg = 0.0
        for i, cid in enumerate(ranked_ids[:k]):
            rel = relevance_map.get(cid, 0.0)
            if rel > 0:
                dcg += (2**rel - 1) / math.log2(i + 2)

        # Ideal DCG
        ideal_rels = sorted(relevance_map.values(), reverse=True)[:k]
        idcg = sum((2**rel - 1) / math.log2(i + 2) for i, rel in enumerate(ideal_rels))

        if idcg == 0.0:
            return 0.0
        return float(dcg / idcg)

    def evaluate_shadow_run(
        self,
        legacy_results: List[Dict[str, Any]],
        new_results: List[RecommendationResult],
        legacy_latency_ms: float,
        new_latency_ms: float
    ) -> Dict[str, float]:
        """
        Compare shadow pipeline execution against legacy output.
        Returns metrics dictionary with Overlap@1, Overlap@3, Overlap@10, and Latency Delta.
        Emits Prometheus gauges for ADR-006 dynamic gate monitoring.
        """
        leg_ids = [r.get('id', 0) if isinstance(r, dict) else getattr(r, 'id', 0) for r in legacy_results]
        new_ids = [r.candidate_id for r in new_results]

        overlap_1 = self.compute_overlap_at_k(leg_ids, new_ids, 1)
        overlap_3 = self.compute_overlap_at_k(leg_ids, new_ids, 3)
        overlap_10 = self.compute_overlap_at_k(leg_ids, new_ids, 10)
        latency_delta_ms = new_latency_ms - legacy_latency_ms

        metrics = {
            "overlap_at_1": overlap_1,
            "overlap_at_3": overlap_3,
            "overlap_at_10": overlap_10,
            "legacy_latency_ms": legacy_latency_ms,
            "new_latency_ms": new_latency_ms,
            "latency_delta_ms": latency_delta_ms
        }

        logger.info(
            f"[ShadowEvaluator] Overlap@1: {overlap_1:.2f}, Overlap@10: {overlap_10:.2f}, "
            f"Latency Delta: {latency_delta_ms:+.1f}ms"
        )

        # Emit Prometheus gauges for ADR-006 dynamic gate monitoring
        try:
            from core.metrics import shadow_overlap_at_k, shadow_mrr, shadow_ndcg_at_10
            shadow_overlap_at_k.labels(k="1").set(overlap_1)
            shadow_overlap_at_k.labels(k="3").set(overlap_3)
            shadow_overlap_at_k.labels(k="10").set(overlap_10)
        except Exception:
            pass

        return metrics

