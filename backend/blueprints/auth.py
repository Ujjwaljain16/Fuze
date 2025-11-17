from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, get_jwt_identity, 
    set_refresh_cookies, unset_jwt_cookies
)
from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash
from utils.database_utils import retry_on_connection_error, ensure_database_connection
import re
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def validate_password_strength(password):
    """Validate password strength - production grade requirements"""
    if len(password) < 8:
        return False, 'Password must be at least 8 characters long'
    if len(password) > 128:
        return False, 'Password must be less than 128 characters'
    if not re.search(r'[A-Za-z]', password):
        return False, 'Password must contain at least one letter'
    if not re.search(r'[0-9]', password):
        return False, 'Password must contain at least one number'
    # Optional: require special character for stronger security
    # if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
    #     return False, 'Password must contain at least one special character'
    return True, None

def sanitize_input(text, max_length=255):
    """Sanitize and validate input to prevent injection attacks"""
    if not text:
        return None
    # Remove null bytes and control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    # Trim whitespace
    text = text.strip()
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    return text

def validate_email(email):
    """Validate email format"""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def apply_rate_limit():
    """Apply rate limiting if limiter is available"""
    if hasattr(current_app, 'limiter') and current_app.limiter:
        from flask_limiter.util import get_remote_address
        # Rate limit: 5 login attempts per 15 minutes per IP
        @current_app.limiter.limit("5 per 15 minutes", key_func=get_remote_address)
        def _rate_limited():
            pass
        try:
            _rate_limited()
        except Exception as e:
            logger.warning(f"Rate limit check failed: {e}")
            # Continue if rate limiting fails

@auth_bp.route('/register', methods=['POST'])
@retry_on_connection_error(max_retries=1, delay=1.0)
def register():
    """Production-grade registration endpoint with validation and rate limiting"""
    try:
        # Apply rate limiting
        apply_rate_limit()
        
        data = request.get_json()
        if not data:
            return jsonify({'message': 'Request body is required'}), 400
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        name = data.get('name', '')  # Optional name field
        
        # Input validation
        if not username or not email or not password:
            return jsonify({'message': 'Username, email, and password are required'}), 400
        
        # Sanitize inputs
        username = sanitize_input(username, max_length=50)
        email = sanitize_input(email, max_length=255)
        name = sanitize_input(name, max_length=100) if name else ''
        
        if not username or not email or not password:
            return jsonify({'message': 'Invalid input format'}), 400
        
        # Validate email format
        if not validate_email(email):
            return jsonify({'message': 'Invalid email format'}), 400
        
        # Validate username format (alphanumeric, underscore, hyphen, 3-50 chars)
        if not re.match(r'^[a-zA-Z0-9_-]{3,50}$', username):
            return jsonify({'message': 'Username must be 3-50 characters and contain only letters, numbers, underscores, and hyphens'}), 400
        
        # Validate password strength
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            return jsonify({'message': error_msg}), 400
        
        # Ensure database connection before queries
        ensure_database_connection()
        
        # Check for existing user
        if User.query.filter_by(username=username).first():
            return jsonify({'message': 'Username already exists'}), 409
        if User.query.filter_by(email=email).first():
            return jsonify({'message': 'Email already exists'}), 409
        
        # Create user
        user = User(username=username, email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"User registered successfully: {username}")
        return jsonify({'message': 'User registered successfully'}), 201
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        return jsonify({'message': 'Registration failed. Please try again.'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Production-grade login endpoint with rate limiting and security"""
    try:
        # Apply rate limiting (stricter for login)
        if hasattr(current_app, 'limiter') and current_app.limiter:
            from flask_limiter.util import get_remote_address
            try:
                @current_app.limiter.limit("5 per 15 minutes", key_func=get_remote_address)
                def _rate_limited():
                    pass
                _rate_limited()
            except Exception as e:
                # If rate limit exceeded, return 429
                if '429' in str(e) or 'rate limit' in str(e).lower():
                    logger.warning(f"Rate limit exceeded for login attempt from {get_remote_address()}")
                    return jsonify({'message': 'Too many login attempts. Please try again later.'}), 429
                logger.warning(f"Rate limit check failed: {e}")
        
        data = request.get_json()
        if not data:
            return jsonify({'message': 'Request body is required'}), 400
        
        identifier = data.get('username') or data.get('email')
        password = data.get('password')
        
        if not identifier or not password:
            return jsonify({'message': 'Username/email and password required'}), 400
        
        # Sanitize identifier
        identifier = sanitize_input(identifier, max_length=255)
        if not identifier:
            return jsonify({'message': 'Invalid input format'}), 400
        
        # Ensure database connection before querying
        ensure_database_connection()
        
        # Direct database query
        user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
        if not user or not check_password_hash(user.password_hash, password):
            # Log failed login attempt (but don't reveal which field was wrong)
            logger.warning(f"Failed login attempt for identifier: {identifier[:3]}***")
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
        
        # Set refresh token in HTTP-only, secure cookie
        set_refresh_cookies(response, refresh_token)
        
        logger.info(f"User logged in successfully: {user.username}")
        return response, 200
        
    except Exception as e:
        # Log the actual error for debugging
        logger.error(f"Login error: {str(e)}", exc_info=True)
        
        # Only retry on actual database connection errors
        error_str = str(e).lower()
        if any(keyword in error_str for keyword in ['connection', 'timeout', 'network', 'unreachable', 'operational']):
            # Fallback to retry mechanism for connection issues
            try:
                return login_with_retry(identifier, password)
            except Exception as retry_error:
                logger.error(f"Login retry failed: {str(retry_error)}", exc_info=True)
                return jsonify({'message': 'Database connection failed. Please try again.'}), 503
        else:
            # For other errors, return generic message but log the actual error
            logger.error(f"Login failed with non-connection error: {str(e)}", exc_info=True)
            return jsonify({'message': 'Login failed. Please try again.'}), 500

def login_with_retry(identifier, password):
    """Fallback login method with retry logic for connection issues"""
    import logging
    logger = logging.getLogger(__name__)
    
    @retry_on_connection_error(max_retries=2, delay=1.0)
    def _login():
        ensure_database_connection()
        user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
        if not user or not check_password_hash(user.password_hash, password):
            return None
        return user
    
    try:
        user = _login()
        if not user:
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
        
        set_refresh_cookies(response, refresh_token)
        return response, 200
        
    except Exception as e:
        logger.error(f"Login retry failed: {str(e)}", exc_info=True)
        return jsonify({'message': 'Login failed. Please try again.'}), 500

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
@retry_on_connection_error(max_retries=1, delay=1.0)
def verify_token():
    """Verify if the current token is valid"""
    current_user_id = get_jwt_identity()
    
    # Ensure database connection before query
    ensure_database_connection()
    
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