"""
ml/recommendation/retrieval.py
================================
CandidateRetriever: Stage 1 of the two-stage retrieval pipeline.

Executes an ANN (Approximate Nearest Neighbor) query using the pgvector HNSW index
on saved_content.embedding to fetch the top-K most semantically similar candidates.
Populates RecommendationCandidate.embedding from the database row so Stage 2
(RecommendationScorer) can compute vector similarity scores.

Fallback behaviour:
  If the query_embedding is absent (None), or if the ANN query fails (e.g. pgvector
  not available), falls back to a plain ORM fetch ordered by recency. This means the
  pipeline degrades gracefully to BM25 + tech overlap scoring only.

  Candidates with embedding IS NULL are included via a secondary query appended
  after the ANN results, so legacy bookmarks (not yet backfilled) are not silently
  excluded from recommendations.

Design contract (ADR-002):
  - No direct math or scoring in this class.
  - Returns RecommendationCandidate domain objects only.
  - No Redis calls. No Gemini calls.
"""

from typing import List, Optional
import numpy as np
import logging

from ml.recommendation.domain import (
    RecommendationRequest,
    RecommendationCandidate,
    CandidateSet,
    Embedding,
)

logger = logging.getLogger(__name__)


class CandidateRetriever:
    """
    Stage 1: ANN pre-filter using pgvector HNSW index.

    fetch_ann_candidates(request, user_id, k=100):
      - Executes cosine ANN search via saved_content.embedding <=> query_vector
      - Returns top-K candidates with embedding populated
      - Falls back to recency-ordered fetch if ANN unavailable
    """

    def __init__(self, uow=None):
        self.uow = uow

    def fetch_ann_candidates(
        self,
        request: RecommendationRequest,
        user_id: int,
        k: int = 100,
    ) -> CandidateSet:
        """
        Execute Stage 1 ANN retrieval.

        Returns a CandidateSet of up to k candidates with .embedding populated
        from the database vector column.
        """
        if not self.uow:
            logger.warning("CandidateRetriever has no UnitOfWork; returning empty CandidateSet")
            return CandidateSet(candidates=[])

        query_embedding: Optional[Embedding] = request.query_embedding

        if query_embedding is not None:
            try:
                return self._ann_query(user_id, query_embedding, k)
            except Exception as exc:
                logger.warning(
                    "candidate_retriever_ann_failed_falling_back",
                    extra={"error": str(exc), "user_id": user_id},
                )

        # Fallback: recency-ordered ORM fetch (no vector scoring)
        return self._fallback_fetch(user_id, k)

    # ------------------------------------------------------------------
    # Private: ANN query via pgvector <=> operator
    # ------------------------------------------------------------------

    def _ann_query(
        self,
        user_id: int,
        query_embedding: Embedding,
        k: int,
    ) -> CandidateSet:
        """
        Execute ANN search using the HNSW index on saved_content.embedding.
        Uses raw SQL via SQLAlchemy text() to access the pgvector <=> operator
        and retrieve the embedding bytes for re-ranking.
        """
        from sqlalchemy import text
        from models import db

        query_vector = query_embedding.vector.tolist()
        query_vector_str = f"[{','.join(str(v) for v in query_vector)}]"

        # Fetch embedded candidates ordered by cosine distance (ANN via HNSW)
        ann_sql = text("""
            SELECT
                sc.id,
                sc.title,
                sc.url,
                sc.notes,
                sc.extracted_text,
                sc.embedding::text AS embedding_text,
                ca.technologies
            FROM saved_content sc
            LEFT JOIN content_analysis ca ON ca.saved_content_id = sc.id
            WHERE sc.user_id = :user_id
              AND sc.embedding IS NOT NULL
            ORDER BY sc.embedding <=> CAST(:query_vector AS vector)
            LIMIT :k
        """)

        session = self.uow.session if hasattr(self.uow, 'session') else db.session

        rows = session.execute(ann_sql, {
            "user_id": user_id,
            "query_vector": query_vector_str,
            "k": k,
        }).fetchall()

        candidates = []
        ann_ids = set()

        for row in rows:
            embedding = self._parse_embedding(row.embedding_text)
            tech_list = self._parse_technologies(row.technologies)

            candidates.append(RecommendationCandidate(
                candidate_id=row.id,
                content_type="bookmark",
                title=row.title or row.url or "Untitled",
                url=row.url or "http://localhost/bookmark",
                notes=row.notes or "",
                extracted_text=row.extracted_text or "",
                technologies=tech_list,
                embedding=embedding,
            ))
            ann_ids.add(row.id)

        # Secondary query: append candidates with NULL embeddings so they are
        # not silently excluded (they will score 0 on vector similarity but
        # may still rank well on BM25 + tech overlap).
        null_candidates = self._fetch_null_embedding_candidates(
            user_id, session, exclude_ids=ann_ids, limit=max(0, k - len(candidates))
        )
        candidates.extend(null_candidates)

        logger.debug(
            "candidate_retriever_ann_complete",
            extra={
                "user_id": user_id,
                "ann_results": len(ann_ids),
                "null_embedding_fallback": len(null_candidates),
                "total": len(candidates),
            },
        )

        return CandidateSet(candidates=candidates)

    # ------------------------------------------------------------------
    # Private: ORM fallback (no vector column required)
    # ------------------------------------------------------------------

    def _fallback_fetch(self, user_id: int, k: int) -> CandidateSet:
        """
        Fallback: fetch candidates by recency when ANN is unavailable.
        Does not populate candidate.embedding (vector scores will be 0).
        """
        try:
            bookmarks = self.uow.bookmarks.get_user_bookmarks(user_id=user_id, limit=k)
            candidates = []
            for bm in bookmarks:
                tech_list = self._bm_tech_list(bm)
                title = getattr(bm, "title", "") or getattr(bm, "url", "") or "Untitled"
                url = getattr(bm, "url", "") or "http://localhost/bookmark"
                embedding = self._load_bm_embedding(bm)

                candidates.append(RecommendationCandidate(
                    candidate_id=getattr(bm, "id", 0),
                    content_type="bookmark",
                    title=title,
                    url=url,
                    notes=getattr(bm, "notes", "") or "",
                    extracted_text=getattr(bm, "extracted_text", "") or "",
                    technologies=tech_list,
                    embedding=embedding,
                ))
            return CandidateSet(candidates=candidates)
        except Exception as exc:
            logger.error(
                "candidate_retriever_fallback_failed",
                extra={"user_id": user_id, "error": str(exc)},
            )
            return CandidateSet(candidates=[])

    # ------------------------------------------------------------------
    # Private: helpers
    # ------------------------------------------------------------------

    def _fetch_null_embedding_candidates(
        self,
        user_id: int,
        session,
        exclude_ids: set,
        limit: int,
    ) -> List[RecommendationCandidate]:
        """Fetch bookmarks that have no embedding yet (backfill pending)."""
        if limit <= 0:
            return []
        try:
            from sqlalchemy import text
            sql = text("""
                SELECT sc.id, sc.title, sc.url, sc.notes, sc.extracted_text,
                       ca.technologies
                FROM saved_content sc
                LEFT JOIN content_analysis ca ON ca.saved_content_id = sc.id
                WHERE sc.user_id = :user_id
                  AND sc.embedding IS NULL
                ORDER BY sc.id DESC
                LIMIT :limit
            """)
            rows = session.execute(sql, {"user_id": user_id, "limit": limit}).fetchall()
            candidates = []
            for row in rows:
                if row.id in exclude_ids:
                    continue
                candidates.append(RecommendationCandidate(
                    candidate_id=row.id,
                    content_type="bookmark",
                    title=row.title or row.url or "Untitled",
                    url=row.url or "http://localhost/bookmark",
                    notes=row.notes or "",
                    extracted_text=row.extracted_text or "",
                    technologies=self._parse_technologies(row.technologies),
                    embedding=None,  # no embedding yet
                ))
            return candidates
        except Exception as exc:
            logger.warning(
                "candidate_retriever_null_fetch_error",
                extra={"error": str(exc)},
            )
            return []

    @staticmethod
    def _parse_embedding(embedding_text: Optional[str]) -> Optional[Embedding]:
        """
        Parse pgvector embedding from its text representation '[0.1,0.2,...]'.
        Returns an Embedding value object or None on failure.
        """
        if not embedding_text:
            return None
        try:
            clean = embedding_text.strip().strip("[]")
            vector = np.array([float(v) for v in clean.split(",")], dtype=np.float32)
            return Embedding(vector=vector)
        except Exception:
            return None

    @staticmethod
    def _parse_technologies(raw) -> List[str]:
        if not raw:
            return []
        if isinstance(raw, list):
            return raw
        if isinstance(raw, str):
            return [t.strip() for t in raw.split(",") if t.strip()]
        return []

    @staticmethod
    def _bm_tech_list(bm) -> List[str]:
        if hasattr(bm, "analysis") and bm.analysis and getattr(bm.analysis, "technologies", None):
            raw = bm.analysis.technologies
            if isinstance(raw, list):
                return raw
            if isinstance(raw, str):
                return [t.strip() for t in raw.split(",") if t.strip()]
        return []

    @staticmethod
    def _load_bm_embedding(bm) -> Optional[Embedding]:
        raw = getattr(bm, "embedding", None)
        if raw is None:
            return None
        try:
            if isinstance(raw, list):
                vector = np.array(raw, dtype=np.float32)
            elif isinstance(raw, np.ndarray):
                vector = raw.astype(np.float32)
            else:
                return None
            return Embedding(vector=vector)
        except Exception:
            return None
