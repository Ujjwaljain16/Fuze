from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.embedding_utils import get_embedding
from uow.unit_of_work import UnitOfWork
from services.search_service import SearchService, MAX_QUERY_LENGTH, MAX_SEARCH_LIMIT
from core.logging_config import get_logger

from middleware.rate_limiting import limiter
from core.logging_config import get_logger

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
        return jsonify({'message': 'Query is required'}), 400

    if len(query) > MAX_QUERY_LENGTH:
        return jsonify({'message': f'Query exceeds maximum length of {MAX_QUERY_LENGTH} characters'}), 400

    try:
        with UnitOfWork() as uow:
            service = SearchService(uow)
            results = service.semantic_search(user_id, query, limit)

        return jsonify({
            'query': query,
            'results': results,
            'total': len(results)
        }), 200
    except Exception:
        logger.exception("semantic_search_failed", extra={"user_id": user_id})
        return jsonify({'message': 'Search temporarily unavailable'}), 503


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
        return jsonify({'message': f'Query exceeds maximum length of {MAX_QUERY_LENGTH} characters'}), 400

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
        return jsonify({'message': 'Search temporarily unavailable'}), 503


@search_bp.route('/supabase-semantic', methods=['POST'])
@jwt_required()
def supabase_semantic_search():
    """Supabase vector search endpoint with local fallback."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    query = str(data.get('query', '')).strip()

    try:
        limit = int(data.get('limit', 10))
    except (TypeError, ValueError):
        limit = 10
    limit = max(1, min(limit, MAX_SEARCH_LIMIT))

    if not query:
        return jsonify({'message': 'Query is required'}), 400

    if len(query) > MAX_QUERY_LENGTH:
        return jsonify({'message': f'Query exceeds maximum length of {MAX_QUERY_LENGTH} characters'}), 400

    try:
        with UnitOfWork() as uow:
            service = SearchService(uow)
            response_data = service.supabase_semantic_search(user_id, query, limit)

        return jsonify(response_data), 200
    except Exception:
        logger.exception("supabase_semantic_search_route_failed", extra={"user_id": user_id})
        return jsonify({'message': 'Search temporarily unavailable'}), 503


@search_bp.route('/rpc-semantic', methods=['POST'])
@jwt_required()
@limiter.limit("30 per minute")
def rpc_semantic_search():
    """
    Postgres-native semantic search via RPC function (ITEM 1).

    Feature-flag gated: only active when 'search_rpc' flag is enabled for this user.
    Falls back to /api/search/semantic (Python path) if flag is off or RPC fails.

    Rollout: 0% → 5% → 20% → 50% → 100% via feature flag percentage rollout.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    query = str(data.get('query', '')).strip()

    try:
        limit = int(data.get('limit', 20))
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(limit, MAX_SEARCH_LIMIT))

    if not query:
        return jsonify({'message': 'Query is required'}), 400

    if len(query) > MAX_QUERY_LENGTH:
        return jsonify({'message': f'Query exceeds maximum length of {MAX_QUERY_LENGTH} characters'}), 400

    # Feature flag check
    try:
        from core.feature_flags import is_enabled
        if not is_enabled('search_rpc', user_id=user_id):
            # Fall back to Python-side semantic search
            with UnitOfWork() as uow:
                service = SearchService(uow)
                results = service.semantic_search(user_id, query, limit)
            return jsonify({
                'query': query,
                'results': results,
                'total': len(results),
                'engine': 'python_fallback',
            }), 200
    except Exception as flag_err:
        logger.warning("rpc_search_flag_check_failed", extra={"error": str(flag_err)})

    try:
        # Generate query embedding
        query_embedding = get_embedding(query)
        if query_embedding is None:
            raise ValueError("Embedding generation returned None")

        with UnitOfWork() as uow:
            from services.rpc_search_service import RpcSearchService
            rpc_service = RpcSearchService(uow)
            use_hybrid = data.get('hybrid', False)

            if use_hybrid:
                results = rpc_service.hybrid_search(user_id, query, query_embedding, limit)
            else:
                results = rpc_service.semantic_search(user_id, query, query_embedding, limit)

        return jsonify({
            'query': query,
            'results': results,
            'total': len(results),
            'engine': 'rpc_hybrid' if use_hybrid else 'rpc_semantic',
        }), 200

    except Exception:
        logger.exception("rpc_semantic_search_failed", extra={"user_id": user_id})
        # Fallback to Python path on any RPC error
        try:
            with UnitOfWork() as uow:
                service = SearchService(uow)
                results = service.semantic_search(user_id, query, limit)
            return jsonify({
                'query': query,
                'results': results,
                'total': len(results),
                'engine': 'python_fallback_after_rpc_error',
            }), 200
        except Exception:
            return jsonify({'message': 'Search temporarily unavailable'}), 503