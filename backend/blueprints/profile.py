from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash

profile_bp = Blueprint('profile', __name__, url_prefix='/api')

@profile_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    return jsonify({
        'id': user.id, 
        'username': user.username, 
        'technology_interests': user.technology_interests,
        'created_at': user.created_at.isoformat() if user.created_at else None
    }), 200

@profile_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = int(get_jwt_identity())
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
    
    # Verify current password
    if not check_password_hash(user.password_hash, current_password):
        return jsonify({'message': 'Current password is incorrect'}), 400
    
    # Update password
    user.password_hash = generate_password_hash(new_password)
    
    try:
        db.session.commit()
        return jsonify({'message': 'Password changed successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error changing password: {str(e)}'}), 500 