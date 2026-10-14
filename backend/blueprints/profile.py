"""
User Profile Blueprint
Handles user profile fetching, updating, and password management.
"""

import re
from flask import Blueprint, request, jsonify
from core.http_errors import error_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from models import db, User
from core import cache_keys
from utils.redis_utils import redis_cache
from core.logging_config import get_logger
from middleware.rate_limiting import limiter
from utils.timefmt import iso_utc

logger = get_logger(__name__)

profile_bp = Blueprint('profile', __name__, url_prefix='/api')

MAX_TECH_INTERESTS_LENGTH = 1000
USERNAME_REGEX = r'^[a-zA-Z0-9_-]{3,50}$'

def _execute_profile_update(user: User, data: dict):
    """
    Shared DRY helper to validate and update user profile.
    Handles username, technology interests, uniqueness check, DB commit, and cache invalidation.
    """
    if 'username' in data and data['username']:
        new_username = str(data['username']).strip()
        if not re.match(USERNAME_REGEX, new_username):
            return error_response('invalid_username', 'Username must be 3-50 characters and contain only letters, numbers, underscores, and hyphens', 400)

        # Usernames are stored lowercase and unique regardless of case (as at registration). Your own current
        # name is never "taken", so saving the form unchanged, or changing only the interests, works.
        new_username = new_username.lower()
        existing_user = db.session.query(User).filter(
            func.lower(User.username) == new_username,
            User.id != user.id
        ).first()
        if existing_user:
            return error_response('username_taken', 'Username already taken', 400)
        user.username = new_username

    if 'technology_interests' in data:
        raw_tech = data['technology_interests']
        if raw_tech:
            tech_str = str(raw_tech).strip()
            if len(tech_str) > MAX_TECH_INTERESTS_LENGTH:
                return error_response('technology_interests_too_long', f'Technology interests cannot exceed {MAX_TECH_INTERESTS_LENGTH} characters', 400)
            user.technology_interests = tech_str
        else:
            user.technology_interests = None

    try:
        db.session.commit()

        # Invalidate profile cache
        try:
            if redis_cache and redis_cache.connected:
                redis_cache.delete_cache(cache_keys.profile(user.id))
        except Exception as cache_err:
            logger.warning("profile_cache_invalidation_failed", user_id=user.id, error=str(cache_err))

        return jsonify({
            'message': 'Profile updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'technology_interests': user.technology_interests,
                'created_at': iso_utc(user.created_at)
            }
        }), 200

    except IntegrityError:
        db.session.rollback()
        return error_response('username_taken', 'Username already taken', 400)
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("profile_update_db_failed", user_id=user.id)
        return error_response('internal_error', 'Failed to update profile', 500)


@profile_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get logged-in user profile with Redis caching."""
    user_id = int(get_jwt_identity())
    cache_key = cache_keys.profile(user_id)

    # Try cache
    if redis_cache and redis_cache.connected:
        try:
            cached_profile = redis_cache.get(cache_key)
            if cached_profile:
                return jsonify(cached_profile), 200
        except Exception as cache_err:
            logger.warning("profile_cache_read_failed", user_id=user_id, error=str(cache_err))

    user = db.session.get(User, user_id)
    if not user:
        return error_response('user_not_found', 'User not found', 404)

    profile_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'technology_interests': user.technology_interests,
        'google_connected': bool(user.provider_user_id),
        # Google-created accounts start with a random password nobody knows.
        'has_password': not (user.user_metadata or {}).get('supabase_user_id')
                        or bool((user.user_metadata or {}).get('password_set')),
        'created_at': iso_utc(user.created_at)
    }

    if redis_cache and redis_cache.connected:
        try:
            redis_cache.set_cache(cache_key, profile_data, ttl=300)
        except Exception as cache_err:
            logger.warning("profile_cache_write_failed", user_id=user_id, error=str(cache_err))

    return jsonify(profile_data), 200


@profile_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile for logged-in user."""
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return error_response('user_not_found', 'User not found', 404)
    data = request.get_json(silent=True) or {}
    return _execute_profile_update(user, data)


@profile_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """Update user profile - compatibility endpoint (strictly authorized to self)."""
    current_user_id = int(get_jwt_identity())
    if current_user_id != user_id:
        logger.warning("unauthorized_profile_update_attempt", current_user_id=current_user_id, target_user_id=user_id)
        return error_response('forbidden', 'Unauthorized', 403)

    user = db.session.get(User, user_id)
    if not user:
        return error_response('user_not_found', 'User not found', 404)

    data = request.get_json(silent=True) or {}
    return _execute_profile_update(user, data)


@profile_bp.route('/users/<int:user_id>/password', methods=['PUT'])
@jwt_required()
@limiter.limit("5 per 15 minutes")
def change_password(user_id):
    """Change user password with validation and authorization checks."""
    current_user_id = int(get_jwt_identity())

    if current_user_id != user_id:
        logger.warning("unauthorized_password_change_attempt", current_user_id=current_user_id, target_user_id=user_id)
        return error_response('forbidden', 'Unauthorized', 403)

    user = db.session.get(User, user_id)
    if not user:
        return error_response('user_not_found', 'User not found', 404)

    data = request.get_json(silent=True) or {}
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return error_response('missing_fields', 'Current password and new password are required', 400)

    if len(str(new_password)) < 8:
        return error_response('weak_password', 'New password must be at least 8 characters long', 400)

    from blueprints.auth import verify_password, hash_password

    if not verify_password(user.password_hash, current_password):
        logger.warning("password_change_incorrect_current", user_id=user_id)
        return error_response('invalid_password', 'Current password is incorrect', 400)

    user.password_hash = hash_password(new_password)

    try:
        # Whoever else held a session (e.g. someone who knew the old password) loses it now.
        from flask_jwt_extended import get_jwt
        from core.sessions import revoke_user_sessions
        from uow.unit_of_work import UnitOfWork
        db.session.commit()
        with UnitOfWork() as uow:
            ended = revoke_user_sessions(uow, user_id, keep_family_id=get_jwt().get('family_id'))
        logger.info("password_changed_successfully", user_id=user_id, other_sessions_ended=ended)
        return jsonify({'message': 'Password changed successfully'}), 200
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("password_change_db_failed", user_id=user_id)
        return error_response('internal_error', 'Failed to change password', 500)