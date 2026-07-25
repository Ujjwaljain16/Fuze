"""
RecommendationDataLayer: Encapsulates database candidate fetching via repositories and embedding utilities.
Guarantees engines never access raw SQLAlchemy models or execute direct database queries.

Two-stage retrieval (ADR-006, ITEM 2):
  When the 'two_stage_retrieval' feature flag is enabled, Stage 1 delegates to
  CandidateRetriever which executes a pgvector ANN query and populates
  candidate.embedding from the database vector column.

  When the flag is disabled (or the retriever fails), falls back to the original
  ORM-based path which does NOT populate candidate.embedding (vector scores = 0).
"""

from typing import List, Optional, Any, Dict
import logging
from ml.recommendation.domain import (
    RecommendationRequest,
    RecommendationCandidate,
    CandidateSet,
    Embedding,
)

logger = logging.getLogger(__name__)


class RecommendationDataLayer:
    """Standardized Data Access Abstraction for Recommendation Engines."""

    def __init__(self, uow=None):
        self.uow = uow
        self._embedding_model = None

    def fetch_candidate_set(
        self,
        request: RecommendationRequest,
        user_id: int,
        limit: int = 100,
    ) -> CandidateSet:
        """
        Fetch candidates for recommendation scoring.

        Routes to ANN-based CandidateRetriever when 'two_stage_retrieval' flag is
        enabled and a query_embedding is present on the request.
        Falls back to ORM path otherwise.
        """
        if not self.uow:
            logger.warning(
                "RecommendationDataLayer initialized without UnitOfWork; returning empty CandidateSet."
            )
            return CandidateSet(candidates=[])

        # Check feature flag for two-stage retrieval
        try:
            from core.feature_flags import is_enabled
            use_two_stage = is_enabled("two_stage_retrieval", user_id=user_id)
        except Exception:
            use_two_stage = False

        if use_two_stage and request.query_embedding is not None:
            try:
                from ml.recommendation.retrieval import CandidateRetriever
                retriever = CandidateRetriever(uow=self.uow)
                candidate_set = retriever.fetch_ann_candidates(
                    request=request,
                    user_id=user_id,
                    k=limit,
                )
                logger.debug(
                    "data_layer_two_stage_retrieval_used",
                    extra={"user_id": user_id, "candidates": len(candidate_set)},
                )
                # Also append project candidates (projects not in ANN index)
                project_candidates = self._fetch_project_candidates(user_id, limit=20)
                candidate_set.candidates.extend(project_candidates)
                return candidate_set
            except Exception as exc:
                logger.warning(
                    "data_layer_two_stage_retrieval_failed_falling_back",
                    extra={"error": str(exc), "user_id": user_id},
                )

        # Original ORM path (flag off, or fallback)
        return self._fetch_orm_candidates(user_id, limit)

    # ------------------------------------------------------------------
    # Private: original ORM path (preserved exactly)
    # ------------------------------------------------------------------

    def _fetch_orm_candidates(self, user_id: int, limit: int) -> CandidateSet:
        """Original flat ORM fetch — does not populate candidate.embedding."""
        candidates: List[RecommendationCandidate] = []

        try:
            # 1. Fetch user saved content / bookmarks
            bookmarks = self.uow.bookmarks.get_user_bookmarks(user_id=user_id, limit=limit)
            for bm in bookmarks:
                tech_list = []
                notes = getattr(bm, "notes", "") or ""
                extracted = getattr(bm, "extracted_text", "") or ""

                if hasattr(bm, "analysis") and bm.analysis and getattr(bm.analysis, "technologies", None):
                    raw_techs = bm.analysis.technologies
                    if isinstance(raw_techs, list):
                        tech_list = raw_techs
                    elif isinstance(raw_techs, str):
                        tech_list = [t.strip() for t in raw_techs.split(",") if t.strip()]

                title = getattr(bm, "title", "") or getattr(bm, "url", "") or "Untitled"
                url = getattr(bm, "url", "") or "http://localhost/bookmark"

                # Attempt to load embedding from ORM model
                embedding = self._load_embedding_from_model(bm)

                candidates.append(
                    RecommendationCandidate(
                        candidate_id=getattr(bm, "id", 0),
                        content_type="bookmark",
                        title=title,
                        url=url,
                        notes=notes,
                        extracted_text=extracted,
                        technologies=tech_list,
                        embedding=embedding,
                    )
                )

            # 2. Fetch user projects
            project_candidates = self._fetch_project_candidates(user_id, limit=limit)
            candidates.extend(project_candidates)

        except Exception as e:
            logger.error(
                f"Error fetching candidate set in RecommendationDataLayer: {e}", exc_info=True
            )

        return CandidateSet(candidates=candidates)

    def _fetch_project_candidates(self, user_id: int, limit: int = 20) -> List[RecommendationCandidate]:
        """Fetch project candidates (not ANN-indexed; always via ORM)."""
        candidates = []
        try:
            projects = self.uow.projects.get_user_projects(user_id=user_id, limit=limit)
            for proj in projects:
                tech_list = []
                raw_techs = getattr(proj, "technologies", "") or ""
                if isinstance(raw_techs, str) and raw_techs:
                    tech_list = [t.strip() for t in raw_techs.split(",") if t.strip()]
                elif isinstance(raw_techs, list):
                    tech_list = raw_techs

                title = getattr(proj, "title", "") or "Untitled Project"
                desc = getattr(proj, "description", "") or ""

                candidates.append(
                    RecommendationCandidate(
                        candidate_id=getattr(proj, "id", 0),
                        content_type="project",
                        title=title,
                        url=f"http://localhost/projects/{getattr(proj, 'id', 0)}",
                        notes=desc,
                        extracted_text=desc,
                        technologies=tech_list,
                        embedding=None,  # Projects not yet in ANN index
                    )
                )
        except Exception as e:
            logger.error(f"Error fetching project candidates: {e}", exc_info=True)
        return candidates

    @staticmethod
    def _load_embedding_from_model(bm) -> Optional[Embedding]:
        """
        Attempt to load embedding from an ORM model instance.
        Handles both list format (pgvector returns list) and ndarray.
        Returns None if embedding is absent or invalid.
        """
        import numpy as np

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
            if vector.ndim != 1 or len(vector) == 0:
                return None
            return Embedding(vector=vector)
        except Exception:
            return None
