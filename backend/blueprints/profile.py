from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User
from sqlalchemy.exc import IntegrityError
import logging

logger = logging.getLogger(__name__)

profile_bp = Blueprint('profile', __name__, url_prefix='/api')

@profile_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get user profile - optimized with caching"""
    from utils.redis_utils import redis_cache
    
    user_id = int(get_jwt_identity())
    
    # PRODUCTION OPTIMIZATION: Cache profile data (changes infrequently)
    cache_key = f"profile:{user_id}"
    cached_profile = redis_cache.get(cache_key) if redis_cache else None
    
    if cached_profile:
        return jsonify(cached_profile), 200
    
    # Fast database query (primary key lookup - very fast)
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    profile_data = {
        'id': user.id, 
        'username': user.username, 
        'technology_interests': user.technology_interests,
        'created_at': user.created_at.isoformat() if user.created_at else None
    }
    
    # Cache for 5 minutes (profile doesn't change often)
    if redis_cache:
        redis_cache.set_cache(cache_key, profile_data, ttl=300)
    
    return jsonify(profile_data), 200

@profile_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    data = request.get_json()
    
    if 'username' in data and data['username']:
        new_username = data['username'].strip()
        # Check if username is already taken by another user
        existing_user = User.query.filter(
            User.username == new_username,
            User.id != user_id
        ).first()
        if existing_user:
            return jsonify({'message': 'Username already taken'}), 400
        user.username = new_username
    
    if 'technology_interests' in data:
        user.technology_interests = data['technology_interests'].strip() if data['technology_interests'] else None
    
    try:
        db.session.commit()
        
        # PRODUCTION OPTIMIZATION: Invalidate profile cache after update
        try:
            from utils.redis_utils import redis_cache
            if redis_cache:
                cache_key = f"profile:{user.id}"
                redis_cache.delete_cache(cache_key)
        except Exception as cache_error:
            # Don't fail profile update if cache invalidation fails
            logger.warning(f"Failed to invalidate profile cache: {cache_error}")
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'technology_interests': user.technology_interests
            }
        }), 200
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'message': 'Username already taken'}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating profile: {e}", exc_info=True)
        return jsonify({'message': f'Error updating profile: {str(e)}'}), 500

@profile_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """Update user profile - compatibility endpoint for frontend"""
    current_user_id = int(get_jwt_identity())
    
    # Ensure user can only update their own profile
    if current_user_id != user_id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    data = request.get_json()
    
    if 'username' in data and data['username']:
        user.username = data['username'].strip()
    
    if 'technology_interests' in data:
        user.technology_interests = data['technology_interests'].strip() if data['technology_interests'] else None
    
    try:
        db.session.commit()
        
        # PRODUCTION OPTIMIZATION: Invalidate profile cache after update
        from utils.redis_utils import redis_cache
        if redis_cache:
            cache_key = f"profile:{user.id}"
            redis_cache.delete_cache(cache_key)
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'technology_interests': user.technology_interests
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating profile: {str(e)}'}), 500

@profile_bp.route('/users/<int:user_id>/password', methods=['PUT'])
@jwt_required()
def change_password(user_id):
    """Change user password"""
    current_user_id = int(get_jwt_identity())
    
    # Ensure user can only change their own password
    if current_user_id != user_id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({'message': 'Current password and new password are required'}), 400
    
    # Import bcrypt functions from auth blueprint
    from blueprints.auth import verify_password, hash_password
    
    # Verify current password using bcrypt-compatible verification
    if not verify_password(user.password_hash, current_password):
        return jsonify({'message': 'Current password is incorrect'}), 400
    
    # Update password using bcrypt
    user.password_hash = hash_password(new_password)
    
    try:
        db.session.commit()
        return jsonify({'message': 'Password changed successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error changing password: {str(e)}'}), 500 