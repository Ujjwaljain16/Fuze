from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, get_jwt_identity, 
    set_refresh_cookies, unset_jwt_cookies
)
from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    name = data.get('name', '')  # Optional name field
    
    if not username or not email or not password:
        return jsonify({'message': 'Username, email, and password are required'}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already exists'}), 409
    
    user = User(username=username, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User registered'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    identifier = data.get('username') or data.get('email')
    password = data.get('password')
    
    if not identifier or not password:
        return jsonify({'message': 'Username/email and password required'}), 400
    
    user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    
    response = jsonify({
        'access_token': access_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email
        }
    })
    
    # Set refresh token in HTTP-only cookie
    set_refresh_cookies(response, refresh_token)
    
    return response, 200

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify({'access_token': access_token}), 200

@auth_bp.route('/logout', methods=['POST'])
def logout():
    response = jsonify({'message': 'Logout successful'})
    unset_jwt_cookies(response)
    return response, 200

@auth_bp.route('/csrf-token', methods=['GET'])
def get_csrf_token_endpoint():
    """Get CSRF token for forms"""
    # For now, return a simple response since CSRF is optional
    # In a full CSRF implementation, you would generate a token here
    return jsonify({'csrf_token': 'csrf_disabled'}), 200

@auth_bp.route('/verify-token', methods=['POST'])
@jwt_required()
def verify_token():
    """Verify if the current token is valid"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    return jsonify({
        'valid': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email
        }
    }), 200

# Handle OPTIONS requests for CORS preflight
@auth_bp.route('/login', methods=['OPTIONS'])
@auth_bp.route('/register', methods=['OPTIONS'])
@auth_bp.route('/refresh', methods=['OPTIONS'])
@auth_bp.route('/logout', methods=['OPTIONS'])
@auth_bp.route('/csrf-token', methods=['OPTIONS'])
@auth_bp.route('/verify-token', methods=['OPTIONS'])
def handle_options():
    """Handle OPTIONS requests for CORS preflight"""
    return '', 200 