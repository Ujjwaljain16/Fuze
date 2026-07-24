import os
import json
import heapq
import numpy as np
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

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")

supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("supabase_search_client_connected")
    except Exception as e:
        logger.warning("supabase_search_client_connection_failed", extra={"error": str(e)})
        supabase_client = None


class SearchService:
    """
    Production Search Service providing text, PostgreSQL pgvector semantic search,
    and Supabase vector search with robust fallback mechanics.
    """

    def __init__(self, uow: UnitOfWork, client=None):
        self.uow = uow
        self.supabase_client = client or supabase_client

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
        """Perform vector search via Supabase RPC if available, or top-K heap ranking fallback."""
        limit = max(1, min(limit, MAX_SEARCH_LIMIT))
        clean_query = self._validate_query(query)
        if not clean_query:
            return self._fallback_response(user_id, query or "", limit, "Empty search query")

        client = self.supabase_client
        if not client:
            return self._fallback_response(user_id, clean_query, limit, "Supabase search client unavailable")

        try:
            query_embedding = get_embedding(clean_query)
            if query_embedding is None:
                raise RuntimeError("Failed to generate query embedding")

            query_embedding_list = query_embedding.tolist() if hasattr(query_embedding, 'tolist') else list(query_embedding)

            # 1. Try Supabase RPC match_documents if available
            try:
                rpc_res = client.rpc(
                    'match_documents',
                    {
                        'query_embedding': query_embedding_list,
                        'filter_user_id': user_id,
                        'match_count': limit
                    }
                ).execute()
                if rpc_res and isinstance(rpc_res.data, list) and rpc_res.data:
                    return {
                        'query': clean_query,
                        'results': rpc_res.data,
                        'total': len(rpc_res.data),
                        'source': 'supabase_rpc',
                        'message': 'AI vector search completed via Supabase RPC'
                    }
            except Exception:
                pass

            # 2. Fallback table query with heap top-K evaluation
            response = client.table(SUPABASE_TABLE).select(
                'id, user_id, url, title, notes, extracted_text, embedding'
            ).eq('user_id', user_id).not_.is_("embedding", "null").limit(500).execute()

            bookmarks = response.data or []
            if not bookmarks:
                return {
                    'query': clean_query,
                    'results': [],
                    'total': 0,
                    'source': 'supabase',
                    'message': 'No bookmarks with embeddings found'
                }

            query_vec = np.array(query_embedding_list)
            norm_q = np.linalg.norm(query_vec)

            def get_bookmark_item(bookmark):
                try:
                    embedding_str = bookmark.get('embedding')
                    if not embedding_str:
                        return None

                    bookmark_embedding = json.loads(embedding_str) if isinstance(embedding_str, str) else embedding_str
                    if not bookmark_embedding or len(bookmark_embedding) != len(query_embedding_list):
                        return None

                    vec2 = np.array(bookmark_embedding)
                    norm2 = np.linalg.norm(vec2)

                    similarity = 0.0 if (norm_q == 0 or norm2 == 0) else float(np.dot(query_vec, vec2) / (norm_q * norm2))
                    similarity_percentage = max(0.0, min(100.0, (similarity + 1.0) * 50.0))

                    extracted_text = bookmark.get('extracted_text', '') or ''
                    snippet = extracted_text[:200] + '...' if len(extracted_text) > 200 else extracted_text

                    return {
                        'id': bookmark['id'],
                        'user_id': bookmark['user_id'],
                        'url': bookmark['url'],
                        'title': bookmark['title'],
                        'content_snippet': snippet,
                        'similarity': similarity,
                        'similarity_percentage': similarity_percentage,
                        'relevance_score': similarity_percentage,
                        'search_type': 'AI Vector Similarity'
                    }
                except Exception:
                    return None

            items = [item for bookmark in bookmarks if (item := get_bookmark_item(bookmark)) is not None]
            top_results = heapq.nlargest(limit, items, key=lambda x: x['similarity'])

            return {
                'query': clean_query,
                'results': top_results,
                'total': len(top_results),
                'source': 'supabase',
                'message': 'AI-powered semantic search completed successfully'
            }

        except Exception as e:
            logger.exception("supabase_semantic_search_failed", extra={"user_id": user_id, "error": str(e)})
            return self._fallback_response(user_id, clean_query, limit, "Using fallback search (Supabase failed)")

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
