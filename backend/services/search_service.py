import heapq
import math
from typing import List, Dict, Any, Optional

import numpy as np
from sqlalchemy import or_, text

from models import SavedContent
from uow.unit_of_work import UnitOfWork
from services.hybrid_search import _vec_literal
from utils.embedding_utils import active_embedding_model_name, calculate_cosine_similarity, embed_query
from utils.query_sanitizer import sanitize_like_query
from core.logging_config import get_logger

logger = get_logger(__name__)

MAX_SEARCH_LIMIT = 100
MAX_QUERY_LENGTH = 1000


class SearchService:
    """
    Search over a user's saved content: text search, document-level vector search, and
    passage-level semantic search.
    """

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def _validate_query(self, query: str) -> Optional[str]:
        """Validate and sanitize search query input length."""
        if not query or not isinstance(query, str) or not query.strip():
            return None
        clean_query = query.strip()
        if len(clean_query) > MAX_QUERY_LENGTH:
            clean_query = clean_query[:MAX_QUERY_LENGTH]
        return clean_query

    def text_search(self, user_id: int, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Perform text-based search across bookmark titles, notes, and extracted text."""
        limit = max(1, min(limit, MAX_SEARCH_LIMIT))
        clean_query = self._validate_query(query)
        if not clean_query:
            return []

        sanitized = sanitize_like_query(clean_query)
        if not sanitized:
            return []

        session = self.uow.session
        results = session.query(SavedContent).filter_by(user_id=user_id).filter(
            or_(
                SavedContent.title.ilike(f'%{sanitized}%', escape='\\'),
                SavedContent.notes.ilike(f'%{sanitized}%', escape='\\'),
                SavedContent.extracted_text.ilike(f'%{sanitized}%', escape='\\')
            )
        ).order_by(SavedContent.saved_at.desc()).limit(limit).all()

        return [
            {
                'id': content.id,
                'title': content.title,
                'url': content.url,
                'description': content.notes,
                'saved_at': content.saved_at.isoformat() if content.saved_at else None,
                'has_content': bool(content.extracted_text)
            }
            for content in results
        ]

    # ------------------------------------------------------------------ semantic search
    #
    # Meaning only: every ranking below is cosine similarity between the query embedding and
    # stored embeddings from the *same* model. Vectors from another model live in a different
    # space, so they are excluded rather than ranked.

    def _query_vector(self, query: str) -> np.ndarray:
        vec = np.asarray(embed_query(query), dtype=np.float32)
        if not np.any(vec):
            raise RuntimeError("Failed to generate query embedding")
        return vec

    def _document_hits(self, user_id: int, query_vec: np.ndarray, limit: int,
                       only_unchunked: bool = False) -> List[Dict[str, Any]]:
        """Bookmarks ranked by their document embedding: [{content row fields..., similarity}]."""
        session = self.uow.session
        model = active_embedding_model_name()
        if session.get_bind().dialect.name == 'postgresql':
            unchunked = ("AND NOT EXISTS (SELECT 1 FROM content_chunks c WHERE c.content_id = s.id "
                         "AND c.embedding_model = :model)") if only_unchunked else ""
            rows = session.execute(text(f"""
                SELECT s.id, s.title, s.url, s.notes, s.saved_at, s.extracted_text IS NOT NULL AS has_content,
                       1 - (s.embedding <=> CAST(:q AS vector)) AS similarity
                FROM saved_content s
                WHERE s.user_id = :uid AND s.embedding IS NOT NULL
                  AND s.embedding_metadata ->> 'model' = :model {unchunked}
                ORDER BY s.embedding <=> CAST(:q AS vector)
                LIMIT :k"""), {"q": _vec_literal(query_vec), "uid": user_id, "model": model, "k": limit}).mappings()
            return [dict(r, similarity=float(r["similarity"])) for r in rows]

        # Other databases (SQLite in development/tests): same cosine ranking, computed here.
        hits = []
        for content in session.query(SavedContent).filter(SavedContent.user_id == user_id,
                                                          SavedContent.embedding.isnot(None)):
            if (content.embedding_metadata or {}).get('model') != model:
                continue
            hits.append({'id': content.id, 'title': content.title, 'url': content.url, 'notes': content.notes,
                         'saved_at': content.saved_at, 'has_content': bool(content.extracted_text),
                         'similarity': calculate_cosine_similarity(query_vec, content.embedding)})
        return heapq.nlargest(limit, hits, key=lambda h: h['similarity'])

    def semantic_search(self, user_id: int, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Document-level vector search over the user's bookmarks."""
        limit = max(1, min(limit, MAX_SEARCH_LIMIT))
        clean_query = self._validate_query(query)
        if not clean_query:
            return []
        hits = self._document_hits(user_id, self._query_vector(clean_query), limit)
        return [
            {
                'id': h['id'],
                'title': h['title'],
                'url': h['url'],
                'description': h['notes'],
                'saved_at': h['saved_at'].isoformat() if h['saved_at'] else None,
                'has_content': bool(h['has_content']),
                'similarity': h['similarity'],
            }
            for h in hits
        ]

    def supabase_semantic_search(self, user_id: int, query: str, limit: int = 10) -> Dict[str, Any]:
        """Meaning-based search over the user's bookmarks (best passage shown as the snippet).

        Bookmarks with passage chunks are ranked by their best passage; bookmarks without chunks
        yet (still processing, or chunking failed) are ranked by their document embedding and
        merged in, so no saved item drops out of search. Name kept for the existing endpoint.
        """
        limit = max(1, min(limit, MAX_SEARCH_LIMIT))
        clean_query = self._validate_query(query)
        if not clean_query:
            return {'query': query or "", 'results': [], 'total': 0, 'source': 'none',
                    'message': 'Empty search query'}

        session = self.uow.session
        query_vec = self._query_vector(clean_query)
        results: List[Dict[str, Any]] = []

        if session.get_bind().dialect.name == 'postgresql':
            from services.hybrid_search import semantic_search as passage_search
            for h in passage_search(session, user_id, clean_query, limit=limit, query_vector=query_vec):
                relevance = h.get("rerank_score")
                snippet = " ".join((h.get("passage") or "").split())
                results.append(self._result(user_id, h["content_id"], h.get("url"), h.get("title"), snippet,
                                            h["similarity"], 'Semantic passage search', rerank_score=relevance))
            only_unchunked = True
        else:
            only_unchunked = False

        for h in self._document_hits(user_id, query_vec, limit, only_unchunked=only_unchunked):
            results.append(self._result(user_id, h['id'], h['url'], h['title'], h['notes'] or '',
                                        h['similarity'], 'Semantic document search'))

        results.sort(key=lambda r: r['similarity'], reverse=True)
        results = results[:limit]
        return {
            'query': clean_query,
            'results': results,
            'total': len(results),
            'source': 'semantic',
            'message': 'Semantic search completed',
        }

    @staticmethod
    def _result(user_id, content_id, url, title, snippet, similarity, search_type, rerank_score=None):
        if rerank_score is not None:
            pct = round(100 / (1 + math.exp(-rerank_score)), 1)
        else:
            pct = round(100 * max(0.0, similarity), 1)
        return {
            'id': content_id,
            'user_id': user_id,
            'url': url,
            'title': title,
            'content_snippet': snippet[:300] + ('…' if len(snippet) > 300 else ''),
            'similarity': similarity,
            'similarity_percentage': pct,
            'relevance_score': pct,
            'search_type': search_type,
        }
