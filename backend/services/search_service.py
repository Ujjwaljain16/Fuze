import heapq
import math
from typing import List, Dict, Any, Optional
from sqlalchemy import or_
from sqlalchemy.exc import OperationalError, ProgrammingError
from models import SavedContent
from uow.unit_of_work import UnitOfWork
from utils.embedding_utils import get_embedding
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

    def semantic_search(self, user_id: int, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Perform vector semantic search using pgvector when available, with ranking fallback."""
        limit = max(1, min(limit, MAX_SEARCH_LIMIT))
        clean_query = self._validate_query(query)
        if not clean_query:
            return []

        query_embedding = get_embedding(clean_query)
        if query_embedding is None:
            raise RuntimeError("Failed to generate query embedding")

        session = self.uow.session
        results = []

        try:
            results = session.query(SavedContent).filter_by(user_id=user_id).filter(
                SavedContent.embedding.isnot(None)
            ).order_by(
                SavedContent.embedding.op('<=>')(query_embedding)
            ).limit(limit).all()
        except (OperationalError, ProgrammingError) as db_err:
            session.rollback()
            logger.info("pgvector_search_fallback_trigger", extra={"user_id": user_id, "error": str(db_err)})
            results = self._fallback_semantic_ranking(user_id, clean_query, limit)
        except Exception as e:
            session.rollback()
            logger.error("semantic_search_unexpected_failure", extra={"user_id": user_id, "error": str(e)})
            results = self._fallback_semantic_ranking(user_id, clean_query, limit)

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

    def _fallback_semantic_ranking(self, user_id: int, query: str, limit: int) -> List[SavedContent]:
        """Rank candidates using word overlap and phrase matching when vector search is unavailable."""
        session = self.uow.session
        bookmarks = session.query(SavedContent).filter_by(user_id=user_id).order_by(
            SavedContent.saved_at.desc()
        ).limit(max(limit * 5, 50)).all()

        if not bookmarks:
            return []

        query_words = set(query.lower().split())

        def score_content(content):
            text_val = f"{content.title or ''} {content.notes or ''}".lower()
            content_words = set(text_val.split())
            overlap = len(query_words.intersection(content_words))
            exact_match = 10 if query.lower() in text_val else 0
            return overlap * 2 + exact_match

        return heapq.nlargest(limit, bookmarks, key=score_content)

    def supabase_semantic_search(self, user_id: int, query: str, limit: int = 10) -> Dict[str, Any]:
        """Meaning-based search over the user's passages (best passage shown as the snippet).

        Name kept for the existing endpoint. Users whose content has no passage chunks yet are
        served by document-level vector search.
        """
        limit = max(1, min(limit, MAX_SEARCH_LIMIT))
        clean_query = self._validate_query(query)
        if not clean_query:
            return self._fallback_response(user_id, query or "", limit, "Empty search query")

        session = self.uow.session
        try:
            from services.hybrid_search import semantic_search as passage_search, user_has_chunks
            if session.get_bind().dialect.name != 'postgresql' or not user_has_chunks(session, user_id):
                return self._fallback_response(user_id, clean_query, limit, "Searching whole documents (passages not indexed yet)")

            hits = passage_search(session, user_id, clean_query, limit=limit)
            results = []
            for h in hits:
                relevance = h.get("rerank_score")
                pct = round(100 / (1 + math.exp(-relevance)), 1) if relevance is not None else round(100 * max(0.0, h["similarity"]), 1)
                snippet = " ".join((h.get("passage") or "").split())
                results.append({
                    'id': h["content_id"],
                    'user_id': user_id,
                    'url': h.get("url"),
                    'title': h.get("title"),
                    'content_snippet': snippet[:300] + ('…' if len(snippet) > 300 else ''),
                    'similarity': h["similarity"],
                    'similarity_percentage': pct,
                    'relevance_score': pct,
                    'search_type': 'Semantic passage search',
                })
            return {
                'query': clean_query,
                'results': results,
                'total': len(results),
                'source': 'passages',
                'message': 'Semantic search completed',
            }
        except Exception as e:
            session.rollback()
            logger.exception("passage_search_failed", extra={"user_id": user_id, "error": str(e)})
            return self._fallback_response(user_id, clean_query, limit, "Using document-level search")

    def _fallback_response(self, user_id: int, query: str, limit: int, message: str) -> Dict[str, Any]:
        """Format fallback response matching frontend search expectations."""
        results = self.semantic_search(user_id, query, limit)
        formatted_results = [
            {
                'id': r['id'],
                'user_id': user_id,
                'url': r['url'],
                'title': r['title'],
                'content_snippet': r['description'] or '',
                'distance': 0.0,
                'relevance_score': 100.0
            }
            for r in results
        ]
        return {
            'query': query,
            'results': formatted_results,
            'total': len(formatted_results),
            'source': 'fallback',
            'message': message
        }
