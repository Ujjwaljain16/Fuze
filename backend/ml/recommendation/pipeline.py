"""
RecommendationPipeline: Lifecycle Coordinator for recommendation requests.
Enforces Anti-God Pipeline Rules (ADR-002):
- ALLOWED: Lifecycle coordination, strategy routing, Redis cache lookup/store, latency metrics, fallbacks.
- FORBIDDEN: Direct vector similarity math, DB SQL queries, BM25 scoring, Gemini prompt templates.
"""

from typing import List, Optional, Dict, Any
import time
import logging
from ml.recommendation.domain import (
    RecommendationRequest,
    RecommendationCandidate,
    CandidateSet,
    RecommendationResult
)
from ml.recommendation.data_layer import RecommendationDataLayer
from ml.engines.base_engine import BaseRecommendationEngine
from ml.engines.smart_engine import SmartEngine

logger = logging.getLogger(__name__)


class RecommendationPipeline:
    """Lifecycle Coordinator & Strategy Executor."""

    def __init__(
        self,
        data_layer: Optional[RecommendationDataLayer] = None,
        default_engine: Optional[BaseRecommendationEngine] = None,
        redis_cache: Optional[Any] = None
    ):
        self.data_layer = data_layer or RecommendationDataLayer()
        self.default_engine = default_engine or SmartEngine()
        self.redis_cache = redis_cache

    def run(self, request: RecommendationRequest) -> List[RecommendationResult]:
        """
        Execute recommendation lifecycle pipeline:
        1. Cache Lookup Stage
        2. Candidate Retrieval Stage (via DataLayer)
        3. Strategy Scoring Stage (via Engine Strategy)
        4. Cache Persistence Stage
        """
        start_time = time.time()
        cache_key = f"fuze:recommendation:{request.user_id}:{request.request_id}"

        # Import metrics (no-op stubs if prometheus_client not installed)
        try:
            from core.metrics import recommendation_latency, cache_hit_total, cache_miss_total, recommendation_requests_total
        except Exception:
            recommendation_latency = cache_hit_total = cache_miss_total = recommendation_requests_total = None

        # 1. Cache Lookup Stage
        if self.redis_cache:
            try:
                cached_data = self.redis_cache.get_cache(cache_key)
                if cached_data:
                    logger.debug(f"[Pipeline] Cache HIT for key {cache_key}")
                    if cache_hit_total:
                        try:
                            cache_hit_total.labels(cache_type="recommendations").inc()
                        except Exception:
                            pass
                    # Deserialization of cached results if available
            except Exception as cache_err:
                logger.warning(f"[Pipeline] Cache lookup failed: {cache_err}")

        if self.redis_cache:
            try:
                cache_miss_total and cache_miss_total.labels(cache_type="recommendations").inc()
            except Exception:
                pass

        # 2. Candidate Retrieval Stage (via RecommendationDataLayer)
        retrieval_start = time.time()
        candidate_set = self.data_layer.fetch_candidate_set(
            request=request,
            user_id=request.user_id,
            limit=100
        )
        retrieval_ms = (time.time() - retrieval_start) * 1000

        if recommendation_latency:
            try:
                recommendation_latency.labels(
                    engine=self.default_engine.__class__.__name__,
                    stage="retrieval",
                ).observe((time.time() - retrieval_start))
            except Exception:
                pass

        if not candidate_set or len(candidate_set) == 0:
            logger.info(f"[Pipeline] No candidates retrieved for user {request.user_id}; returning empty list.")
            return []

        # 3. Strategy Scoring Stage (via BaseRecommendationEngine strategy)
        scoring_start = time.time()
        engine = self.default_engine
        results = engine.generate(request=request, candidates=candidate_set)

        if recommendation_latency:
            try:
                recommendation_latency.labels(
                    engine=engine.__class__.__name__,
                    stage="scoring",
                ).observe((time.time() - scoring_start))
            except Exception:
                pass

        # 4. Cache Persistence Stage
        if self.redis_cache and results:
            try:
                self.redis_cache.set_cache(cache_key, [r.__dict__ for r in results], ttl=1800)
            except Exception as cache_err:
                logger.warning(f"[Pipeline] Cache store failed: {cache_err}")

        elapsed_ms = (time.time() - start_time) * 1000

        if recommendation_latency:
            try:
                recommendation_latency.labels(
                    engine=engine.__class__.__name__,
                    stage="full",
                ).observe((time.time() - start_time))
            except Exception:
                pass

        if recommendation_requests_total:
            try:
                recommendation_requests_total.labels(
                    engine=engine.__class__.__name__,
                    result="success" if results else "empty"
                ).inc()
            except Exception:
                pass

        logger.info(
            f"[Pipeline] Executed lifecycle in {elapsed_ms:.1f}ms: "
            f"{len(results)} results generated for user {request.user_id} using {engine.__class__.__name__}"
        )

        return results

