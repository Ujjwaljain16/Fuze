from flask import Blueprint, request, jsonify, make_response
from extensions import limiter
import os
import requests
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, get_jwt_identity,
    set_access_cookies, set_refresh_cookies, unset_jwt_cookies
)
from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash
from utils.database_utils import retry_on_connection_error
import re
import random
import string
from core.logging_config import get_logger
from sqlalchemy import text, func
from sqlalchemy.exc import IntegrityError
import bcrypt

from uow.unit_of_work import UnitOfWork
from services.auth_service import AuthService, AuthenticationFailed, RegistrationFailed

logger = get_logger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def get_auth_service(uow):
    return AuthService(uow)

# Optimized password hashing using bcrypt
# Work factor 12 = ~300ms (perfect balance of security and performance)
# bcrypt is memory-hard and industry standard
BCRYPT_WORK_FACTOR = 12

def hash_password(password):
    """Generate bcrypt password hash - ~300ms, memory-hard, industry standard"""
    if isinstance(password, str):
        password = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=BCRYPT_WORK_FACTOR)
    hashed = bcrypt.hashpw(password, salt)
    return hashed.decode('utf-8')  # Store as string in database

def verify_password(password_hash, password):
    """Verify password against bcrypt hash - supports both bcrypt and old werkzeug hashes"""
    if isinstance(password, str):
        password = password.encode('utf-8')
    
    # Check if it's a bcrypt hash (starts with $2b$)
    if password_hash.startswith('$2b$') or password_hash.startswith('$2a$') or password_hash.startswith('$2y$'):
        # bcrypt hash - fast verification (~300ms)
        if isinstance(password_hash, str):
            password_hash = password_hash.encode('utf-8')
        return bcrypt.checkpw(password, password_hash)
    else:
        # Legacy werkzeug hash - slow but maintain backward compatibility
        # Users will be automatically migrated to bcrypt on next login
        return check_password_hash(password_hash, password.decode('utf-8') if isinstance(password, bytes) else password)

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

# apply_rate_limit function removed - standard decorators used instead

# ============================================================================
# ROBUST USERNAME DETECTION SYSTEM
# ============================================================================

def check_username_availability(username):
    """
    Fast, scalable username availability check with case-insensitive support.
    Returns (is_available, exact_match_exists, case_insensitive_match)
    """
    if not username:
        return False, False, None

    username_lower = username.lower().strip()

    try:
        # Use raw SQL for optimal performance with case-insensitive check
        result = db.session.execute(text("""
            SELECT
                COUNT(*) as exact_count,
                COUNT(*) FILTER (WHERE LOWER(username) = :username_lower) as case_insensitive_count,
                (SELECT username FROM users WHERE LOWER(username) = :username_lower LIMIT 1) as existing_username
            FROM users
            WHERE username = :username_exact OR LOWER(username) = :username_lower
        """), {
            'username_exact': username,
            'username_lower': username_lower
        }).fetchone()

        exact_count = result[0]
        case_insensitive_count = result[1]
        existing_username = result[2]

        is_available = exact_count == 0
        exact_match_exists = exact_count > 0
        case_insensitive_match = existing_username

        return is_available, exact_match_exists, case_insensitive_match

    except Exception:
        logger.error("username_availability_check_failed", username=username)
        # Fallback to ORM query if raw SQL fails
        try:
            exact_match = User.query.filter_by(username=username).first()
            case_insensitive_match = User.query.filter(func.lower(User.username) == username_lower).first()

            is_available = exact_match is None
            exact_match_exists = exact_match is not None
            case_insensitive_match = case_insensitive_match.username if case_insensitive_match else None

            return is_available, exact_match_exists, case_insensitive_match
        except Exception:
            logger.error("fallback_username_check_failed", username=username)
            # Conservative approach: assume unavailable on error
            return False, True, None

def generate_username_suggestions(base_username, max_suggestions=5):
    """
    Generate smart username suggestions when the desired username is taken.
    Returns list of available username suggestions.
    """
    if not base_username:
        return []

    base_username = base_username.lower().strip()
    suggestions = []

    # Strategy 1: Add numbers
    for i in range(1, max_suggestions + 1):
        suggestion = f"{base_username}{i}"
        if len(suggestion) <= 50:  # Respect username length limit
            is_available, _, _ = check_username_availability(suggestion)
            if is_available:
                suggestions.append(suggestion)
                if len(suggestions) >= max_suggestions:
                    break

    if len(suggestions) >= max_suggestions:
        return suggestions

    # Strategy 2: Add random 2-letter combinations
    if len(suggestions) < max_suggestions:
        consonants = 'bcdfghjklmnpqrstvwxyz'
        vowels = 'aeiou'

        for _ in range(max_suggestions - len(suggestions)):
            # Generate pattern like: base_username + consonant + vowel + number
            consonant = random.choice(consonants)
            vowel = random.choice(vowels)
            number = random.randint(1, 99)
            suggestion = f"{base_username}{consonant}{vowel}{number}"

            if len(suggestion) <= 50:
                is_available, _, _ = check_username_availability(suggestion)
                if is_available:
                    suggestions.append(suggestion)

    # Strategy 3: Add underscores with numbers
    if len(suggestions) < max_suggestions:
        for i in range(1, max_suggestions - len(suggestions) + 1):
            suggestion = f"{base_username}_{i}"
            if len(suggestion) <= 50:
                is_available, _, _ = check_username_availability(suggestion)
                if is_available:
                    suggestions.append(suggestion)

    return suggestions[:max_suggestions]

def bulk_check_usernames(usernames):
    """
    Efficiently check availability of multiple usernames in a single query.
    Returns dict of {username: is_available}
    """
    if not usernames:
        return {}

    # Normalize usernames for case-insensitive check
    username_data = [(uname, uname.lower().strip()) for uname in usernames]

    try:
        # Single query to check all usernames
        placeholders = ','.join([f'(:uname{i}, :lower{i})' for i in range(len(username_data))])
        params = {}
        for i, (uname, uname_lower) in enumerate(username_data):
            params[f'uname{i}'] = uname
            params[f'lower{i}'] = uname_lower

        query = f"""
            SELECT DISTINCT uname as username
            FROM (
                SELECT unnest(ARRAY[{','.join([f':uname{i}' for i in range(len(username_data))])}]) as uname
            ) input_usernames
            WHERE LOWER(uname) IN (
                SELECT LOWER(username) FROM users WHERE LOWER(username) IN (
                    {','.join([f':lower{i}' for i in range(len(username_data))])}
                )
            )
        """

        result = db.session.execute(text(query), params)
        taken_usernames = {row[0].lower() for row in result}

        # Return availability for each requested username
        return {uname: uname.lower() not in taken_usernames for uname, _ in username_data}

    except Exception:
        logger.error("bulk_username_check_failed", count=len(usernames))
        # Fallback: check each username individually
        return {uname: check_username_availability(uname)[0] for uname in usernames}

@auth_bp.route('/check-username', methods=['POST'])
@retry_on_connection_error(max_retries=1, delay=1.0)
def check_username():
    """Fast username availability check endpoint"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()

        if not username:
            return jsonify({'available': False, 'error': 'Username is required'}), 400

        # Validate format first
        if not re.match(r'^[a-zA-Z0-9_-]{3,50}$', username):
            return jsonify({
                'available': False,
                'error': 'Username must be 3-50 characters and contain only letters, numbers, underscores, and hyphens'
            }), 400

        is_available, exact_match, case_insensitive_match = check_username_availability(username)

        response = {
            'available': is_available,
            'username': username
        }

        if not is_available:
            response['suggestions'] = generate_username_suggestions(username, 3)

            if case_insensitive_match and case_insensitive_match != username:
                response['case_insensitive_conflict'] = case_insensitive_match

        return jsonify(response), 200

    except Exception:
        logger.error("username_check_route_failed")
        return jsonify({'available': False, 'error': 'Service temporarily unavailable'}), 500

@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per 15 minutes")
@retry_on_connection_error(max_retries=1, delay=1.0)
def register():
    """Production-grade registration endpoint delegating to AuthService"""
    try:
        data = request.get_json() or {}
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        # 1. Validation (Request/Protocol Level)
        if not username or not email or not password:
            return jsonify({'message': 'Username, email, and password are required'}), 400
        
        username = sanitize_input(username, max_length=50)
        email = sanitize_input(email, max_length=255)
        
        if not validate_email(email):
            return jsonify({'message': 'Invalid email format'}), 400
        
        if not re.match(r'^[a-zA-Z0-9_-]{3,50}$', username):
            return jsonify({'message': 'Username must be 3-50 characters and alphanumeric/hyphen'}), 400

        # 2. Business Execution
        with UnitOfWork() as uow:
            auth_service = get_auth_service(uow)
            
            # Strength validation in service
            is_valid, error_msg = auth_service.validate_password_strength(password)
            if not is_valid:
                return jsonify({'message': error_msg}), 400
                
            try:
                auth_service.register(username, email, password)
                # Success - UoW will commit and dispatch UserRegistered event
            except RegistrationFailed as e:
                return jsonify({'message': str(e)}), 400
            except IntegrityError as e:
                # DB Level uniqueness catch
                uow.session.rollback()
                error_str = str(e).lower()
                if 'username' in error_str:
                    return jsonify({'message': 'Username already exists', 'suggestions': generate_username_suggestions(username, 3)}), 409
                if 'email' in error_str:
                    return jsonify({'message': 'Email already exists'}), 409
                raise

        logger.info("user_registered", username=username)
        return jsonify({'message': 'User registered successfully'}), 201
        
    except Exception as e:
        logger.error("registration_failed", error=str(e))
        return jsonify({'message': 'Registration failed. Please try again.'}), 500

@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """Verify JWT token is valid and return user info - used by Chrome extension"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
            return jsonify({'message': 'User not found'}), 404

        return jsonify({
            'valid': True,
            'user': user.to_dict(),
            'message': 'Token is valid'
        }), 200

    except Exception as e:
        logger.error("auth_token_verification_failed", error=str(e))
        return jsonify({'message': 'Token verification failed'}), 401

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per 15 minutes")
def login():
    """Production-grade login endpoint delegating to AuthService"""
    try:
        data = request.get_json() or {}
        identifier = data.get('username') or data.get('email')
        password = data.get('password')
        
        if not identifier or not password:
            return jsonify({'message': 'Username/email and password required'}), 400
        
        identifier = sanitize_input(identifier, max_length=255)
        
        with UnitOfWork() as uow:
            auth_service = get_auth_service(uow)
            try:
                user = auth_service.authenticate(identifier, password)
            except AuthenticationFailed:
                return jsonify({'message': 'Invalid credentials'}), 401

            # Generate tokens (Blueprint responsibility)
            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))
            
            logger.info("user_logged_in", username=user.username, user_id=user.id)
            
            response = make_response(jsonify({
                'message': 'Login successful',
                'user': user.to_dict()
            }))
            
            set_access_cookies(response, access_token)
            set_refresh_cookies(response, refresh_token)
            
            return response, 200
            
    except Exception as e:
        logger.error("login_route_failed", error=str(e))
        return jsonify({'message': 'Login failed. Please try again.'}), 500


@auth_bp.route('/set-password', methods=['POST'])
@jwt_required()
def set_password():
    """Consistency fix: use AuthService for password setting"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        new_password = data.get('new_password')
        current_password = data.get('current_password')

        if not new_password:
            return jsonify({'message': 'New password is required'}), 400

        with UnitOfWork() as uow:
            auth_service = get_auth_service(uow)
            user = uow.users.get_by_id(user_id)
            if not user:
                return jsonify({'message': 'User not found'}), 404

            # Verify strength first
            is_valid, err = auth_service.validate_password_strength(new_password)
            if not is_valid:
                return jsonify({'message': err}), 400

            # If user has a password, verify it
            if user.password_hash:
                if not current_password:
                    return jsonify({'message': 'Current password required'}), 400
                if not auth_service.verify_password(user.password_hash, current_password):
                    return jsonify({'message': 'Current password is incorrect'}), 401

            user.password_hash = auth_service.hash_password(new_password)
        
        logger.info("auth_password_update_success", user_id=user_id)
        return jsonify({'message': 'Password updated successfully'}), 200

    except Exception as e:
        logger.error("password_update_failed", user_id=user_id, error=str(e))
        return jsonify({'message': 'Failed to update password'}), 500


@auth_bp.route('/update-username', methods=['POST'])
@jwt_required()
def update_username():
    """Consistency fix: delegate username updates to repo via UoW"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        new_username = data.get('new_username', '').strip()
        if not new_username:
            return jsonify({'message': 'New username is required'}), 400

        # Validate format
        if not re.match(r'^[a-zA-Z0-9_-]{3,50}$', new_username):
            return jsonify({'message': 'Username format invalid'}), 400

        with UnitOfWork() as uow:
            user = uow.users.get_by_id(user_id)
            if not user:
                return jsonify({'message': 'User not found'}), 404

            if not uow.users.is_username_available(new_username):
                suggestions = generate_username_suggestions(new_username, 3)
                return jsonify({'message': 'Username already exists', 'suggestions': suggestions}), 409

            user.username = new_username
            # UoW commits automatically
            
        logger.info("auth_username_update_success", user_id=user_id, new_username=new_username)
        return jsonify({'message': 'Username updated successfully', 'username': new_username}), 200

    except Exception as e:
        logger.error("username_update_failed", user_id=user_id, error=str(e))
        return jsonify({'message': 'Failed to update username'}), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    logger.info("auth_token_refresh_success", user_id=identity)
    
    response = make_response(jsonify({'message': 'Token refreshed'}))
    set_access_cookies(response, access_token)
    return response, 200

@auth_bp.route('/logout', methods=['POST'])
def logout():
    logger.info("auth_logout_success")
    response = make_response(jsonify({'message': 'Logout successful'}))
    unset_jwt_cookies(response)
    return response, 200

@auth_bp.route('/csrf-token', methods=['GET', 'OPTIONS'])
def get_csrf_token_endpoint():
    """Get CSRF token for forms - optimized for fast response"""
    # Handle OPTIONS preflight requests immediately
    if request.method == 'OPTIONS':
        return '', 200
    
    # For now, return a simple response since CSRF is optional
    # In a full CSRF implementation, you would generate a token here
    # This endpoint must respond quickly to avoid dashboard loading delays
    return jsonify({'csrf_token': 'csrf_disabled'}), 200

@auth_bp.route('/session-status', methods=['GET'])
def session_status():
    """Debug endpoint to verify session status without returning tokens"""
    access_present = 'access_token_cookie' in request.cookies
    refresh_present = 'refresh_token_cookie' in request.cookies
    csrf_present = 'csrf_access_token' in request.cookies
    
    return jsonify({
        'access_cookie': access_present,
        'refresh_cookie': refresh_present,
        'csrf_cookie': csrf_present,
        'is_authenticated': access_present
    }), 200

@auth_bp.route('/verify-token', methods=['POST'])
@jwt_required()
@retry_on_connection_error(max_retries=1, delay=1.0)
def verify_token_status():
    """Verify if the current token is valid using UoW"""
    current_user_id = get_jwt_identity()
    
    with UnitOfWork() as uow:
        user = uow.users.get_by_id(current_user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        logger.info("auth_verify_token_status_success", user_id=current_user_id)
        return jsonify({
            'valid': True,
            'user': user.to_dict()
        }), 200

@auth_bp.route('/supabase-oauth', methods=['POST'])
@retry_on_connection_error(max_retries=1, delay=1.0)
def supabase_oauth():
    """Exchange a Supabase OAuth access token for a local application session.

    Frontend should POST JSON: { "access_token": "..." }
    The endpoint verifies the token with Supabase's `/auth/v1/user` endpoint,
    then creates or finds a local `User` and issues local JWT tokens.
    """
    try:
        data = request.get_json() or {}
        access_token = data.get('access_token')
        if not access_token:
            return jsonify({'message': 'access_token is required'}), 400

        SUPABASE_URL = os.environ.get('SUPABASE_URL')
        if not SUPABASE_URL:
            return jsonify({'message': 'Supabase not configured'}), 503

        # Call Supabase to get user info
        user_info_url = SUPABASE_URL.rstrip('/') + '/auth/v1/user'
        headers = {
            'Authorization': f'Bearer {access_token}',
            'apikey': os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
        }

        resp = requests.get(user_info_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.warning("supabase_token_verification_failed", status_code=resp.status_code)
            return jsonify({'message': 'Invalid Supabase token'}), 401

        supa_user = resp.json()
        email = supa_user.get('email') or supa_user.get('user', {}).get('email')
        name = supa_user.get('user', {}).get('user_metadata', {}).get('full_name') if isinstance(supa_user.get('user'), dict) else None

        if not email:
            return jsonify({'message': 'Unable to determine user email from Supabase'}), 400

        # Find or create local user
        user = User.query.filter_by(email=email).first()
        if not user:
            # generate a username from email
            base_username = email.split('@')[0]
            username = base_username
            # Ensure username uniqueness
            i = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{i}"
                i += 1

            # Create a random password hash placeholder
            random_pw = ''.join(random.choices(string.ascii_letters + string.digits, k=24))
            pw_hash = generate_password_hash(random_pw)

            provider_id = supa_user.get('id') or (supa_user.get('user') or {}).get('id')
            user = User(
                username=username,
                email=email,
                password_hash=pw_hash,
                user_metadata={'supabase_user_id': provider_id},
                provider_name='google',
                provider_user_id=provider_id
            )
            try:
                db.session.add(user)
                db.session.commit()
            except IntegrityError as e:
                # Handle race condition where another request created the user concurrently
                db.session.rollback()
                logger.warning("supabase_oauth_integrity_error", error=str(e))
                # If email already exists, fetch that user and continue
                try:
                    existing = User.query.filter_by(email=email).first()
                    if existing:
                        user = existing
                    else:
                        # As a fallback try by provider_user_id if available
                        prov_id = supa_user.get('id') or (supa_user.get('user') or {}).get('id')
                        if prov_id:
                            existing = User.query.filter_by(provider_user_id=prov_id).first()
                            if existing:
                                user = existing
                            else:
                                logger.error("supabase_oauth_recovery_failed", reason="existing_user_not_found")
                                return jsonify({'message': 'Failed to create user account'}), 500
                        else:
                            logger.error("supabase_oauth_recovery_failed", reason="no_provider_id")
                            return jsonify({'message': 'Failed to create user account'}), 500
                except Exception as qerr:
                    db.session.rollback()
                    logger.error("supabase_oauth_recovery_exception", error=str(qerr))
                    return jsonify({'message': 'Failed to create user account'}), 500
            except Exception as e:
                db.session.rollback()
                logger.error("supabase_oauth_creation_failed", error=str(e))
                return jsonify({'message': 'Failed to create user account'}), 500

        else:
            # If user exists but provider info missing, update it
            try:
                provider_id = supa_user.get('id') or (supa_user.get('user') or {}).get('id')
                updated = False
                if not getattr(user, 'provider_user_id', None) and provider_id:
                    user.provider_user_id = provider_id
                    updated = True
                if not getattr(user, 'provider_name', None):
                    user.provider_name = 'google'
                    updated = True
                if updated:
                    db.session.add(user)
                    db.session.commit()
            except Exception:
                db.session.rollback()

        # Issue local JWT tokens and set cookies
        access = create_access_token(identity=str(user.id))
        refresh = create_refresh_token(identity=str(user.id))

        response = make_response(jsonify({
            'message': 'OAuth login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        }))
        
        set_access_cookies(response, access)
        set_refresh_cookies(response, refresh)
        
        return response, 200

    except Exception as e:
        logger.error("supabase_oauth_failed", error=str(e))
        return jsonify({'message': 'OAuth sign-in failed'}), 500

# Note: OPTIONS requests are automatically handled by flask-cors
# No manual OPTIONS handlers needed - they can cause conflicts 