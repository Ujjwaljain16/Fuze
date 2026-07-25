"""
RecommendationScorer: Pure, deterministic recommendation scoring functions.
Contains zero database queries, zero Redis calls, zero network requests, and zero side effects.
"""

from typing import List, Dict, Optional, Set
import numpy as np
import math
from ml.recommendation.domain import (
    RecommendationRequest,
    RecommendationCandidate,
    RecommendationScore,
    ScoreBreakdown,
    ReasonTag
)


class RecommendationScorer:
    """Pure recommendation scoring engine."""

    @staticmethod
    def compute_vector_similarity(vec_a: Optional[np.ndarray], vec_b: Optional[np.ndarray]) -> float:
        """Compute cosine similarity between two 1D numpy arrays."""
        if vec_a is None or vec_b is None:
            return 0.0
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        similarity = float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
        return max(0.0, min(1.0, similarity))

    @staticmethod
    def compute_bm25_score(query_tokens: List[str], doc_tokens: List[str], k1: float = 1.5, b: float = 0.75) -> float:
        """Pure BM25 relevance score between query tokens and document tokens."""
        if not query_tokens or not doc_tokens:
            return 0.0

        query_set = set(t.lower() for t in query_tokens if t)
        doc_list = [t.lower() for t in doc_tokens if t]
        if not query_set or not doc_list:
            return 0.0

        doc_len = len(doc_list)
        avg_len = max(1.0, doc_len)  # Normalized single-doc BM25 estimation
        score = 0.0

        for token in query_set:
            tf = doc_list.count(token)
            if tf > 0:
                # Term frequency weighting
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (doc_len / avg_len))
                score += numerator / denominator

        # Normalize score between [0.0, 1.0] using sigmoid transform
        normalized = 1.0 / (1.0 + math.exp(-score + 1.0))
        return max(0.0, min(1.0, float(normalized)))

    @staticmethod
    def compute_technology_overlap(req_techs: List[str], candidate_techs: List[str]) -> float:
        """Compute Jaccard similarity index on technology stack lists."""
        if not req_techs or not candidate_techs:
            return 0.0

        req_set = set(t.strip().lower() for t in req_techs if t)
        cand_set = set(t.strip().lower() for t in candidate_techs if t)

        if not req_set or not cand_set:
            return 0.0

        intersection = len(req_set.intersection(cand_set))
        union = len(req_set.union(cand_set))
        if union == 0:
            return 0.0

        return max(0.0, min(1.0, float(intersection / union)))

    def score_candidate(
        self,
        request: RecommendationRequest,
        candidate: RecommendationCandidate,
        weights: Optional[Dict[str, float]] = None
    ) -> RecommendationScore:
        """
        Pure scoring method combining vector similarity, BM25 text relevance, and technology overlap.
        Returns a RecommendationScore entity with detailed ScoreBreakdown.
        """
        if weights is None:
            weights = {
                'vector': 0.4,
                'bm25': 0.3,
                'tech': 0.3
            }

        # 1. Technology overlap
        req_tech_list = [t.strip() for t in request.technologies.split(',') if t.strip()] if request.technologies else []
        tech_score = self.compute_technology_overlap(req_tech_list, candidate.technologies)

        # 2. BM25 text relevance
        req_text = f"{request.title} {request.description}".strip()
        cand_text = f"{candidate.title} {candidate.notes} {candidate.extracted_text}".strip()
        bm25_score = self.compute_bm25_score(req_text.split(), cand_text.split())

        # 3. Vector similarity (if embeddings present)
        vector_score = 0.0
        if request.query_embedding and candidate.embedding:
            vector_score = self.compute_vector_similarity(
                request.query_embedding.vector,
                candidate.embedding.vector
            )

        # Weighted total
        total = (
            weights.get('vector', 0.4) * vector_score +
            weights.get('bm25', 0.3) * bm25_score +
            weights.get('tech', 0.3) * tech_score
        )

        reason_tags = []
        if tech_score > 0.5:
            reason_tags.append(ReasonTag(tag="MATCH_TECH_STACK", description="Strong technology stack match"))
        if vector_score > 0.7:
            reason_tags.append(ReasonTag(tag="HIGH_SEMANTIC_SIMILARITY", description="High semantic similarity"))

        breakdown = ScoreBreakdown(
            vector_similarity=vector_score,
            bm25_relevance=bm25_score,
            technology_match=tech_score
        )

        return RecommendationScore(
            candidate_id=candidate.candidate_id,
            total_score=total,
            breakdown=breakdown,
            reason_tags=reason_tags
        )
