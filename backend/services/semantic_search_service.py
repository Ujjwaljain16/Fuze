import logging
from dataclasses import dataclass
from core.logging_config import get_logger
from utils.embedding_utils import get_embedding
from repositories.bookmark_repository import BookmarkRepository

logger = get_logger(__name__)

@dataclass
class SemanticSearchResult:
    id: str
    title: str
    url: str
    notes: str
    quality_score: float
    similarity: float
    created_at: str

class SemanticSearchService:
    """
    Performs server-side vector similarity search via Supabase RPC.
    
    Architecture:
      Client query → embed_async() [~10ms] 
      → match_user_content RPC [~5-15ms with HNSW index]
      → return ranked results
    
    Total latency: ~20-30ms vs previous ~800ms+ Python loop.
    """

    def __init__(self, supabase_client, config):
        self._supabase = supabase_client
        self._config = config
        self._logger = get_logger(__name__)

    def search(
        self,
        user_id: str,
        query: str,
        limit: int = 20,
        threshold: float = 0.25,
    ) -> list[SemanticSearchResult]:
        """
        Main semantic search entry point.
        Embeds query then calls server-side RPC for similarity search.
        """
        if not query or not query.strip():
            return []
        
        if limit > 100:
            limit = 100  # hard cap — prevent expensive queries
        
        # Step 1: Embed the query (async, non-blocking)
        try:
            query_embedding = get_embedding(query.strip())
        except Exception as e:
            self._logger.error(
                "semantic_search_embed_failed",
                error=str(e),
                user_id=user_id,
            )
            return []
        
        # Step 2: Server-side vector similarity via RPC
        try:
            result = self._supabase.rpc(
                "match_user_content",
                {
                    "query_embedding": query_embedding.tolist() if hasattr(query_embedding, 'tolist') else list(query_embedding),
                    "target_user_id": str(user_id),
                    "match_threshold": threshold,
                    "match_count": limit,
                }
            ).execute()
            
            self._logger.info(
                "semantic_search_complete",
                user_id=user_id,
                query_length=len(query),
                result_count=len(result.data) if result.data else 0,
                threshold=threshold,
            )
            
            return [
                SemanticSearchResult(**row)
                for row in (result.data or [])
            ]
        
        except Exception as e:
            self._logger.error(
                "semantic_search_rpc_failed",
                error=str(e),
                user_id=user_id,
            )
            return []

    def search_for_task(
        self,
        user_id: str,
        project_id: str,
        query_embedding: list[float],
        limit: int = 30,
    ) -> list[SemanticSearchResult]:
        """Task-specific search using match_task_content RPC."""
        try:
            result = self._supabase.rpc(
                "match_task_content",
                {
                    "query_embedding": query_embedding,
                    "target_user_id": str(user_id),
                    "target_project_id": str(project_id),
                    "match_count": limit,
                }
            ).execute()
            return [SemanticSearchResult(**row) for row in (result.data or [])]
        except Exception as e:
            self._logger.error("task_search_failed", error=str(e))
            return []
