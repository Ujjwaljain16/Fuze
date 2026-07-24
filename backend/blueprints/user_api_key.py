from typing import Optional
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
from models import db, User
from utils.redis_utils import redis_cache
from core.logging_config import get_logger

logger = get_logger(__name__)

STATUS_CACHE_TTL = 300  # 5 minutes
TEST_RATE_LIMIT_TTL = 60  # 1 minute
TEST_MAX_CALLS_PER_MINUTE = 5


def get_multi_user_api_manager():
    """Lazy import for MultiUserAPIManager functions to avoid circular dependencies"""
    try:
        from services.multi_user_api_manager import (
            add_user_api_key,
            get_user_api_stats,
            check_user_rate_limit,
            get_user_api_key,
            api_manager
        )
        return add_user_api_key, get_user_api_stats, check_user_rate_limit, get_user_api_key, api_manager
    except ImportError:
        logger.exception("multi_user_api_manager_import_failed")
        raise


user_api_key_bp = Blueprint('user_api_key', __name__, url_prefix='/api/user')


def _get_authenticated_user_id() -> Optional[int]:
    """Safely extract user_id integer from JWT identity"""
    identity = get_jwt_identity()
    if identity is None:
        return None
    try:
        return int(identity)
    except (TypeError, ValueError):
        return None


def _invalidate_user_api_key_cache(user_id: int):
    """Safely invalidate user's cached API key status in Redis"""
    try:
        if redis_cache and redis_cache.connected:
            cache_key = f"api_key_status:{user_id}"
            redis_cache.redis_client.delete(cache_key)
    except Exception as e:
        logger.warning("api_key_status_cache_invalidation_failed", extra={"user_id": user_id, "error": str(e)})


@user_api_key_bp.route('/api-key', methods=['POST'])
@jwt_required()
def add_api_key():
    """Add or update user's Gemini API key"""
    user_id = _get_authenticated_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        add_user_api_key, _, _, _, api_manager = get_multi_user_api_manager()

        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({'error': 'JSON payload required'}), 400

        api_key = data.get('api_key')
        api_key_name = str(data.get('api_key_name', 'Default Key')).strip()[:100]

        if not api_key or not isinstance(api_key, str):
            return jsonify({'error': 'API key is required and must be a string'}), 400

        api_key = api_key.strip()

        # Format validation
        if len(api_key) < 20 or not api_key.startswith('AIzaSy'):
            logger.warning("invalid_api_key_format", extra={"user_id": user_id})
            return jsonify({'error': 'Invalid API key format. Must be a valid Gemini API key starting with AIzaSy.'}), 400

        # Add API key for user
        success = add_user_api_key(user_id, api_key, api_key_name)

        if success:
            if user_id in api_manager.user_api_keys:
                api_manager.load_user_api_keys()

            _invalidate_user_api_key_cache(user_id)

            return jsonify({
                'message': 'API key added successfully',
                'user_id': user_id,
                'api_key_name': api_key_name
            }), 200
        else:
            return jsonify({'error': 'Failed to add API key'}), 500

    except Exception:
        db.session.rollback()
        logger.exception("add_api_key_failed", extra={"user_id": user_id})
        return jsonify({'error': 'Internal server error'}), 500


@user_api_key_bp.route('/api-key', methods=['GET'])
@jwt_required()
def get_api_key_info():
    """Get user's API key information (without exposing the actual key)"""
    user_id = _get_authenticated_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        user = db.session.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        metadata = getattr(user, 'user_metadata', {}) or {}
        api_key_info = metadata.get('api_key', {})

        if not api_key_info:
            return jsonify({
                'has_api_key': False,
                'message': 'No API key configured'
            }), 200

        return jsonify({
            'has_api_key': True,
            'api_key_name': api_key_info.get('name', 'Unknown'),
            'status': api_key_info.get('status', 'unknown'),
            'created_at': api_key_info.get('created_at'),
            'last_used': api_key_info.get('last_used')
        }), 200

    except Exception:
        logger.exception("get_api_key_info_failed", extra={"user_id": user_id})
        return jsonify({'error': 'Internal server error'}), 500


@user_api_key_bp.route('/api-key', methods=['DELETE'])
@jwt_required()
def remove_api_key():
    """Remove user's API key"""
    user_id = _get_authenticated_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        _, _, _, get_user_api_key, api_manager = get_multi_user_api_manager()

        user = db.session.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        metadata = dict(user.user_metadata) if user.user_metadata else {}

        if 'api_key' in metadata:
            try:
                api_key = get_user_api_key(user_id)
                if api_key:
                    from services.api_key_revocation_manager import get_revocation_manager
                    revocation_manager = get_revocation_manager()
                    revocation_manager.revoke_api_key(api_key, user_id=user_id)
            except Exception as rev_err:
                logger.warning("api_key_revocation_failed", extra={"user_id": user_id, "error": str(rev_err)})

            del metadata['api_key']
            user.user_metadata = metadata

            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(user, 'user_metadata')

            db.session.flush()
            db.session.commit()

            if user_id in api_manager.user_api_keys:
                del api_manager.user_api_keys[user_id]

            _invalidate_user_api_key_cache(user_id)

            return jsonify({
                'message': 'API key removed and revoked successfully'
            }), 200
        else:
            return jsonify({
                'message': 'No API key to remove'
            }), 200

    except Exception:
        db.session.rollback()
        logger.exception("remove_api_key_failed", extra={"user_id": user_id})
        return jsonify({'error': 'Internal server error'}), 500


@user_api_key_bp.route('/api-key/status', methods=['GET'])
@jwt_required()
def get_api_key_status():
    """Get user's API key status and usage statistics (CACHED)"""
    user_id = _get_authenticated_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        _, get_user_api_stats, _, _, _ = get_multi_user_api_manager()

        cache_key = f"api_key_status:{user_id}"

        # Try to get from Redis cache
        if redis_cache and redis_cache.connected:
            try:
                import json
                cached_stats = redis_cache.redis_client.get(cache_key)
                if cached_stats:
                    return jsonify(json.loads(cached_stats)), 200
            except Exception as cache_err:
                logger.warning("api_key_status_cache_read_failed", extra={"user_id": user_id, "error": str(cache_err)})

        # Get stats from DB/Manager
        stats = get_user_api_stats(user_id)

        if not stats:
            response_data = {
                'has_api_key': False,
                'api_key_status': 'none',
                'requests_today': 0,
                'requests_this_month': 0,
                'daily_limit': 1500,
                'monthly_limit': 45000,
                'can_make_request': False,
                'message': 'No API key configured'
            }
        else:
            response_data = stats

        # Cache response for STATUS_CACHE_TTL
        if redis_cache and redis_cache.connected:
            try:
                import json
                redis_cache.redis_client.setex(
                    cache_key,
                    STATUS_CACHE_TTL,
                    json.dumps(response_data)
                )
            except Exception as cache_err:
                logger.warning("api_key_status_cache_write_failed", extra={"user_id": user_id, "error": str(cache_err)})

        return jsonify(response_data), 200

    except Exception:
        logger.exception("get_api_key_status_failed", extra={"user_id": user_id})
        return jsonify({'error': 'Internal server error'}), 500


@user_api_key_bp.route('/api-key/test', methods=['POST'])
@jwt_required()
def test_api_key():
    """Test if user's API key is valid"""
    user_id = _get_authenticated_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    # Redis-backed rate limiting for test endpoint to prevent abuse
    if redis_cache and redis_cache.connected:
        try:
            rate_key = f"api_key_test_rate:{user_id}"
            call_count = redis_cache.redis_client.incr(rate_key)
            if call_count == 1:
                redis_cache.redis_client.expire(rate_key, TEST_RATE_LIMIT_TTL)
            if call_count > TEST_MAX_CALLS_PER_MINUTE:
                return jsonify({'error': 'Too many test requests. Please wait a minute.'}), 429
        except Exception as rate_err:
            logger.warning("api_key_test_rate_limit_check_failed", extra={"user_id": user_id, "error": str(rate_err)})

    try:
        _, _, _, get_user_api_key, api_manager = get_multi_user_api_manager()

        api_key = get_user_api_key(user_id)

        if not api_key or api_key == os.environ.get('GEMINI_API_KEY'):
            user = db.session.query(User).filter_by(id=user_id).first()
            if user:
                metadata = user.user_metadata or {}
                api_key_info = metadata.get('api_key', {})
                if not api_key_info:
                    return jsonify({
                        'valid': False,
                        'message': 'No API key configured. Using default key.'
                    }), 200

        try:
            from utils.gemini_utils import GeminiAnalyzer

            if not api_key:
                return jsonify({
                    'valid': False,
                    'message': 'API key not found'
                }), 200

            analyzer = GeminiAnalyzer(api_key=api_key)
            test_response = analyzer.model.generate_content("Test")

            if test_response and hasattr(test_response, 'text') and test_response.text:
                return jsonify({
                    'valid': True,
                    'message': 'API key is valid and working',
                    'is_user_key': user_id in api_manager.user_api_keys
                }), 200
            else:
                return jsonify({
                    'valid': False,
                    'message': 'API key validation failed'
                }), 200

        except Exception as test_error:
            logger.warning("api_key_test_validation_failed", extra={"user_id": user_id, "error": str(test_error)})
            return jsonify({
                'valid': False,
                'message': 'API key validation failed'
            }), 200

    except Exception:
        logger.exception("test_api_key_failed", extra={"user_id": user_id})
        return jsonify({'error': 'Internal server error'}), 500


@user_api_key_bp.route('/api-key/usage', methods=['GET'])
@jwt_required()
def get_api_usage():
    """Get detailed API usage statistics"""
    user_id = _get_authenticated_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        _, get_user_api_stats, check_user_rate_limit, _, _ = get_multi_user_api_manager()

        rate_status = check_user_rate_limit(user_id)
        stats = get_user_api_stats(user_id)

        usage_info = {
            'user_id': user_id,
            'rate_limits': rate_status,
            'usage_stats': stats,
            'limits': {
                'requests_per_minute': 15,
                'requests_per_day': 1500,
                'requests_per_month': 45000
            }
        }

        return jsonify(usage_info), 200

    except Exception:
        logger.exception("get_api_usage_failed", extra={"user_id": user_id})
        return jsonify({'error': 'Internal server error'}), 500


def init_app(app):
    app.register_blueprint(user_api_key_bp)