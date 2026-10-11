from flask import Blueprint, request, jsonify
from core.http_errors import error_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from uow.unit_of_work import UnitOfWork
from services.search_service import SearchService, MAX_QUERY_LENGTH, MAX_SEARCH_LIMIT
from core.logging_config import get_logger

from middleware.rate_limiting import limiter

logger = get_logger(__name__)

search_bp = Blueprint('search', __name__, url_prefix='/api/search')


@search_bp.route('/semantic', methods=['POST'])
@jwt_required()
@limiter.limit("30 per minute")
def semantic_search():
    """Vector-based semantic search endpoint with robust fallback."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    query = str(data.get('query', '')).strip()

    try:
        limit = int(data.get('limit', 10))
    except (TypeError, ValueError):
        limit = 10
    limit = max(1, min(limit, MAX_SEARCH_LIMIT))

    if not query:
        return error_response('query_required', 'Query is required', 400)

    if len(query) > MAX_QUERY_LENGTH:
        return error_response('query_too_long', f'Query exceeds maximum length of {MAX_QUERY_LENGTH} characters', 400)

    try:
        with UnitOfWork() as uow:
            found = SearchService(uow).supabase_semantic_search(user_id, query, limit)

        results = [
            {'id': r['id'], 'title': r['title'], 'url': r['url'], 'description': r.get('content_snippet', ''),
             'relevance_score': r.get('relevance_score')}
            for r in found['results']
        ]
        return jsonify({
            'query': query,
            'results': results,
            'total': len(results)
        }), 200
    except Exception:
        logger.exception("semantic_search_failed", extra={"user_id": user_id})
        return error_response('search_unavailable', 'Search temporarily unavailable', 503)


@search_bp.route('/text', methods=['GET'])
@jwt_required()
def text_search():
    """Deterministic text search endpoint with LIKE escaping and pagination bounding."""
    user_id = int(get_jwt_identity())
    query = request.args.get('q', '').strip()

    try:
        limit = int(request.args.get('limit', 10))
    except (TypeError, ValueError):
        limit = 10
    limit = max(1, min(limit, MAX_SEARCH_LIMIT))

    if not query:
        return jsonify({'query': '', 'results': [], 'total': 0}), 200

    if len(query) > MAX_QUERY_LENGTH:
        return error_response('query_too_long', f'Query exceeds maximum length of {MAX_QUERY_LENGTH} characters', 400)

    try:
        with UnitOfWork() as uow:
            service = SearchService(uow)
            results = service.text_search(user_id, query, limit)

        return jsonify({
            'query': query,
            'results': results,
            'total': len(results)
        }), 200
    except Exception:
        logger.exception("text_search_failed", extra={"user_id": user_id})
        return error_response('search_unavailable', 'Search temporarily unavailable', 503)


@search_bp.route('/supabase-semantic', methods=['POST'])
@jwt_required()
def supabase_semantic_search():
    """Semantic search (passages, with document-level fallback). Name kept for the frontend."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    query = str(data.get('query', '')).strip()

    try:
        limit = int(data.get('limit', 10))
    except (TypeError, ValueError):
        limit = 10
    limit = max(1, min(limit, MAX_SEARCH_LIMIT))

    if not query:
        return error_response('query_required', 'Query is required', 400)

    if len(query) > MAX_QUERY_LENGTH:
        return error_response('query_too_long', f'Query exceeds maximum length of {MAX_QUERY_LENGTH} characters', 400)

    try:
        with UnitOfWork() as uow:
            service = SearchService(uow)
            response_data = service.supabase_semantic_search(user_id, query, limit)

        return jsonify(response_data), 200
    except Exception:
        logger.exception("supabase_semantic_search_route_failed", extra={"user_id": user_id})
        return error_response('search_unavailable', 'Search temporarily unavailable', 503)

