"""
services/rpc_search_service.py
================================
Thin Python wrapper around Postgres search_bookmarks_semantic_v1() and
search_bookmarks_hybrid_v1() RPC functions.

These functions execute HNSW ANN search entirely inside PostgreSQL.
Python only serializes the embedding vector and deserializes result rows.

Routing:
  Controlled by the 'search_rpc' feature flag (core/feature_flags.py).
  The /api/search/semantic route in blueprints/search.py checks the flag
  and delegates to this service when enabled.

Rollout strategy (ADR-006 ITEM 1):
  0% → 5% → 20% → 50% → 100% via feature flag percentage rollout.
  Each stage held for 24h minimum. Latency p99 monitored via Prometheus.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import text
from core.logging_config import get_logger

logger = get_logger(__name__)

MAX_QUERY_LENGTH = 500
MAX_RPC_LIMIT = 50


class RpcSearchService:
    """Executes Postgres-native semantic and hybrid search via RPC functions."""

    def __init__(self, uow):
        self.uow = uow

    def semantic_search(
        self,
        user_id: int,
        query: str,
        query_embedding: List[float],
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Execute search_bookmarks_semantic_v1() — pure ANN cosine distance.
        Returns results ordered by semantic similarity (closest first).
        """
        limit = max(1, min(limit, MAX_RPC_LIMIT))

        try:
            vector_str = f"[{','.join(str(v) for v in query_embedding)}]"

            sql = text("""
                SELECT id, title, url, notes, extracted_text, distance
                FROM search_bookmarks_semantic_v1(
                    :user_id,
                    CAST(:embedding AS vector(384)),
                    :limit
                )
            """)

            rows = self.uow.session.execute(sql, {
                "user_id": user_id,
                "embedding": vector_str,
                "limit": limit,
            }).fetchall()

            return [
                {
                    "id": row.id,
                    "title": row.title or "",
                    "url": row.url or "",
                    "notes": row.notes or "",
                    "similarity": round(1.0 - float(row.distance) / 2.0, 4),
                    "source": "rpc_semantic",
                }
                for row in rows
            ]

        except Exception as exc:
            logger.error(
                "rpc_search_semantic_failed",
                extra={"user_id": user_id, "error": str(exc)},
            )
            raise

    def hybrid_search(
        self,
        user_id: int,
        query: str,
        query_embedding: List[float],
        limit: int = 20,
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Execute search_bookmarks_hybrid_v1() — vector similarity + ts_rank text search.
        Returns results ordered by hybrid score.
        """
        limit = max(1, min(limit, MAX_RPC_LIMIT))

        try:
            vector_str = f"[{','.join(str(v) for v in query_embedding)}]"

            sql = text("""
                SELECT id, title, url, notes, extracted_text, hybrid_score
                FROM search_bookmarks_hybrid_v1(
                    :user_id,
                    CAST(:embedding AS vector(384)),
                    :text_query,
                    :limit,
                    :vector_weight,
                    :text_weight
                )
            """)

            rows = self.uow.session.execute(sql, {
                "user_id": user_id,
                "embedding": vector_str,
                "text_query": query[:MAX_QUERY_LENGTH],
                "limit": limit,
                "vector_weight": vector_weight,
                "text_weight": text_weight,
            }).fetchall()

            return [
                {
                    "id": row.id,
                    "title": row.title or "",
                    "url": row.url or "",
                    "notes": row.notes or "",
                    "hybrid_score": round(float(row.hybrid_score), 4),
                    "source": "rpc_hybrid",
                }
                for row in rows
            ]

        except Exception as exc:
            logger.error(
                "rpc_search_hybrid_failed",
                extra={"user_id": user_id, "error": str(exc)},
            )
            raise
