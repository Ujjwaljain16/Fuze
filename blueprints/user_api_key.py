#!/usr/bin/env python3
"""
User API Key Management Blueprint
Handles user API key operations through REST API
"""

from flask import Blueprint, request, jsonify
from functools import wraps
import jwt
import os
from datetime import datetime
from models import db, User
from multi_user_api_manager import add_user_api_key, get_user_api_stats, check_user_rate_limit

# Create blueprint
user_api_key_bp = Blueprint('user_api_key', __name__, url_prefix='/api/user')

def require_auth(f):
    """Decorator to require JWT authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            # Decode JWT token (you'll need to implement this based on your auth system)
            # For now, we'll use a simple user_id extraction
            payload = jwt.decode(token, os.environ.get('JWT_SECRET', 'your-secret-key'), algorithms=['HS256'])
            user_id = payload.get('user_id')
            
            if not user_id:
                return jsonify({'error': 'Invalid token'}), 401
            
            # Add user_id to request context
            request.user_id = user_id
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        except Exception as e:
            return jsonify({'error': f'Authentication error: {str(e)}'}), 401
    
    return decorated_function

@user_api_key_bp.route('/api-key', methods=['POST'])
@require_auth
def add_api_key():
    """Add or update user's API key"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        api_key = data.get('api_key')
        api_key_name = data.get('api_key_name', 'My API Key')
        user_id = request.user_id
        
        if not api_key:
            return jsonify({'error': 'API key is required'}), 400
        
        # Validate API key format
        if not api_key.startswith('AIza') or len(api_key) < 30:
            return jsonify({'error': 'Invalid API key format'}), 400
        
        # Add API key for user
        success = add_user_api_key(user_id, api_key, api_key_name)
        
        if success:
            return jsonify({
                'message': 'API key added successfully',
                'user_id': user_id,
                'api_key_name': api_key_name
            }), 200
        else:
            return jsonify({'error': 'Failed to add API key'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@user_api_key_bp.route('/api-key', methods=['GET'])
@require_auth
def get_api_key_info():
    """Get user's API key information (without exposing the actual key)"""
    try:
        user_id = request.user_id
        
        # Get API key info from database
        user = db.session.query(User).filter_by(id=user_id).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        metadata = getattr(user, 'metadata', {}) or {}
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
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@user_api_key_bp.route('/api-key', methods=['DELETE'])
@require_auth
def remove_api_key():
    """Remove user's API key"""
    try:
        user_id = request.user_id
        
        # Get user and remove API key info
        user = db.session.query(User).filter_by(id=user_id).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        metadata = getattr(user, 'metadata', {}) or {}
        
        if 'api_key' in metadata:
            del metadata['api_key']
            user.metadata = metadata
            db.session.commit()
            
            return jsonify({
                'message': 'API key removed successfully'
            }), 200
        else:
            return jsonify({
                'message': 'No API key to remove'
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@user_api_key_bp.route('/api-key/status', methods=['GET'])
@require_auth
def get_api_key_status():
    """Get user's API key status and usage statistics"""
    try:
        user_id = request.user_id
        
        # Get comprehensive API stats
        stats = get_user_api_stats(user_id)
        
        if not stats:
            return jsonify({
                'has_api_key': False,
                'api_key_status': 'none',
                'requests_today': 0,
                'requests_this_month': 0,
                'daily_limit': 1500,
                'monthly_limit': 45000,
                'can_make_request': False,
                'message': 'No API key configured'
            }), 200
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@user_api_key_bp.route('/api-key/test', methods=['POST'])
@require_auth
def test_api_key():
    """Test if user's API key is valid"""
    try:
        user_id = request.user_id
        
        # Get user's API key
        user = db.session.query(User).filter_by(id=user_id).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        metadata = getattr(user, 'metadata', {}) or {}
        api_key_info = metadata.get('api_key', {})
        
        if not api_key_info:
            return jsonify({
                'valid': False,
                'message': 'No API key configured'
            }), 200
        
        # Test the API key by making a simple request
        try:
            from gemini_utils import GeminiAnalyzer
            from multi_user_api_manager import get_user_api_key
            
            api_key = get_user_api_key(user_id)
            
            if not api_key:
                return jsonify({
                    'valid': False,
                    'message': 'API key not found'
                }), 200
            
            # Test with Gemini
            analyzer = GeminiAnalyzer(api_key=api_key)
            test_response = analyzer.model.generate_content("Test connection")
            
            if test_response and test_response.text:
                return jsonify({
                    'valid': True,
                    'message': 'API key is valid and working'
                }), 200
            else:
                return jsonify({
                    'valid': False,
                    'message': 'API key test failed'
                }), 200
                
        except Exception as test_error:
            return jsonify({
                'valid': False,
                'message': f'API key test failed: {str(test_error)}'
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@user_api_key_bp.route('/api-key/usage', methods=['GET'])
@require_auth
def get_api_usage():
    """Get detailed API usage statistics"""
    try:
        user_id = request.user_id
        
        # Get rate limit status
        rate_status = check_user_rate_limit(user_id)
        
        # Get API stats
        stats = get_user_api_stats(user_id)
        
        # Combine information
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
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# Register blueprint with app
def init_app(app):
    app.register_blueprint(user_api_key_bp) 