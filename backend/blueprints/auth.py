from flask import Blueprint, request, jsonify, current_app
import os
import time
import uuid
import requests
from datetime import datetime, timedelta
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, get_jwt_identity,
    get_jwt, decode_token, set_refresh_cookies, unset_jwt_cookies
)
from models import db, User, TokenFamily
from utils.database_utils import retry_on_connection_error
from middleware.rate_limiting import limiter
import re
import logging
import random
import string
from sqlalchemy import text, func
from sqlalchemy.exc import IntegrityError
import bcrypt

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

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

    if any(password_hash.startswith(p) for p in _BCRYPT_PREFIXES):
        if isinstance(password_hash, str):
            password_hash = password_hash.encode('utf-8')
        return bcrypt.checkpw(password, password_hash)
    else:
        # Legacy werkzeug hash — keep backward compat; migrated to bcrypt on next login
        from werkzeug.security import check_password_hash as _wp_check
        return _wp_check(password_hash, password.decode('utf-8') if isinstance(password, bytes) else password)


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
    return True, None

def sanitize_input(text, max_length=255):
    """Sanitize and validate input to prevent injection attacks"""
    if not text:
        return None
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    text = text.strip()
    if len(text) > max_length:
        text = text[:max_length]
    return text

def validate_email(email):
    """Validate email format"""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# ---------------------------------------------------------------------------
# Security constants
# ---------------------------------------------------------------------------
_BCRYPT_PREFIXES = ('$2b$', '$2a$', '$2y$')

# Pre-computed bcrypt hash of the word "dummy" (rounds=12).
# Used to neutralise timing attacks on the user-not-found path.
# Safe to commit — it never authenticates anyone.
_TIMING_DUMMY_HASH = "$2b$12$AoiBV.KGmITlyHz1NWAY3eFksSfQnfebA9Fpmla92wdkacTPAf8hu"

def _constant_time_fail(password: str) -> None:
    """Always fails. Runs bcrypt so user-not-found timing == wrong-password timing."""
    pw = password.encode('utf-8') if isinstance(password, str) else password
    bcrypt.checkpw(pw, _TIMING_DUMMY_HASH.encode('utf-8'))

MAX_FAILED_ATTEMPTS = 10
LOCKOUT_MINUTES = 30


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
                COUNT(*) FILTER (WHERE username = :username_exact) as exact_count,
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

    except Exception as e:
        logger.error(f"Username availability check failed: {e}")
        # Fallback to ORM query if raw SQL fails
        try:
            exact_match = User.query.filter_by(username=username).first()
            case_insensitive_match = User.query.filter(func.lower(User.username) == username_lower).first()

            is_available = exact_match is None
            exact_match_exists = exact_match is not None
            case_insensitive_match = case_insensitive_match.username if case_insensitive_match else None

            return is_available, exact_match_exists, case_insensitive_match
        except Exception as e2:
            logger.error(f"Fallback username check also failed: {e2}")
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

    except Exception as e:
        logger.error(f"Bulk username check failed: {e}")
        # Fallback: check each username individually
        return {uname: check_username_availability(uname)[0] for uname in usernames}

@auth_bp.route('/check-username', methods=['POST'])
@limiter.limit("30 per minute")
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

    except Exception as e:
        logger.error(f"Username check error: {e}")
        return jsonify({'available': False, 'error': 'Service temporarily unavailable'}), 500

@auth_bp.route('/register', methods=['POST'])
@limiter.limit("10 per hour")
@retry_on_connection_error(max_retries=1, delay=1.0)
def register():
    """Production-grade registration endpoint with validation and rate limiting"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'Request body is required'}), 400

        username = data.get('username')
        email    = data.get('email')
        password = data.get('password')
        name     = data.get('name', '')

        if not username or not email or not password:
            return jsonify({'message': 'Username, email, and password are required'}), 400

        # Sanitize + normalize
        username = sanitize_input(username, max_length=50)
        email    = sanitize_input(email, max_length=255)
        email    = email.strip().lower() if email else None
        name     = sanitize_input(name, max_length=100) if name else ''

        if not username or not email:
            return jsonify({'message': 'Invalid input format'}), 400

        if not validate_email(email):
            return jsonify({'message': 'Invalid email format'}), 400

        if not re.match(r'^[a-zA-Z0-9_-]{3,50}$', username):
            return jsonify({'message': 'Username must be 3-50 characters and contain only letters, numbers, underscores, and hyphens'}), 400

        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            return jsonify({'message': error_msg}), 400

        # Username availability check
        is_available, exact_match, case_insensitive_match = check_username_availability(username)
        if not is_available:
            suggestions = generate_username_suggestions(username, 3)
            response = {'message': 'An account already exists with those credentials.'}
            if suggestions:
                response['suggestions'] = suggestions
            if case_insensitive_match and case_insensitive_match != username:
                response['case_insensitive_conflict'] = case_insensitive_match
            return jsonify(response), 409

        # Email availability (security: use func.lower to be consistent)
        if User.query.filter(func.lower(User.email) == email).first():
            logger.info(f"Register blocked — email exists: {email[:3]}***")
            return jsonify({'message': 'An account already exists with those credentials.'}), 409

        # Create user via AuthService
        try:
            from uow.unit_of_work import UnitOfWork
            from services.auth_service import AuthService
            
            with UnitOfWork() as uow:
                auth_service = AuthService(uow)
                user = auth_service.register(username=username, email=email, password=password)
                
            logger.info(f"User registered: {username}")
            return jsonify({'message': 'User registered successfully'}), 201

        except IntegrityError as e:
            db.session.rollback()
            error_str = str(e).lower()
            if 'username' in error_str and 'unique' in error_str:
                suggestions = generate_username_suggestions(username, 3)
                resp = {'message': 'An account already exists with those credentials.'}
                if suggestions:
                    resp['suggestions'] = suggestions
                return jsonify(resp), 409
            elif 'email' in error_str and 'unique' in error_str:
                return jsonify({'message': 'An account already exists with those credentials.'}), 409
            logger.error(f"IntegrityError during registration: {e}")
            return jsonify({'message': 'Registration failed. Please try again.'}), 409

        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error during user creation: {e}")
            return jsonify({'message': 'Registration failed. Please try again.'}), 500

    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        return jsonify({'message': 'Registration failed. Please try again.'}), 500

@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """Verify JWT token is valid and return user info"""
    try:
        current_user_id = get_jwt_identity()
        user = db.session.get(User, current_user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404
        return jsonify({'valid': True, 'user': user.to_dict(), 'message': 'Token is valid'}), 200
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return jsonify({'message': 'Token verification failed'}), 401

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per 15 minutes")
def login():
    """Production-grade login with timing-safe auth, account lockout, and token families."""
    start_time = time.time()

    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'Request body is required'}), 400

        identifier = data.get('username') or data.get('email')
        password   = data.get('password')

        if not identifier or not password:
            return jsonify({'message': 'Username/email and password required'}), 400

        # Normalize and sanitize
        identifier = sanitize_input(identifier.strip().lower(), max_length=255)
        if not identifier:
            return jsonify({'message': 'Invalid input format'}), 400

        # DB lookup via AuthService
        try:
            from uow.unit_of_work import UnitOfWork
            from services.auth_service import AuthService
            
            with UnitOfWork() as uow:
                auth_service = AuthService(uow)
                user = auth_service.get_user_for_login(identifier)
        except Exception as db_error:
            logger.error(f"DB error during login: {db_error}")
            return jsonify({'message': 'Database connection failed. Please try again.'}), 503

        # Timing-safe: always run bcrypt even when user not found
        if not user:
            _constant_time_fail(password)
            return jsonify({'message': 'Invalid credentials'}), 401

        # Account lockout check — return generic 401 to prevent user enumeration
        now = datetime.utcnow()
        if user.account_locked_until and user.account_locked_until > now:
            remaining = int((user.account_locked_until - now).total_seconds() / 60)
            logger.warning(
                f"Login blocked — account locked: user_id={user.id} "
                f"remaining={remaining}m ip={request.remote_addr}"
            )
            _constant_time_fail(password)  # neutralize timing difference
            return jsonify({'message': 'Invalid credentials'}), 401

        # Password verification
        if not verify_password(user.password_hash, password):
            # Increment failed counter
            user.failed_login_count = (user.failed_login_count or 0) + 1
            user.last_failed_login  = now
            if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
                user.account_locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
                logger.warning(f"Account locked: user_id={user.id} after {MAX_FAILED_ATTEMPTS} attempts")
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
            logger.warning(f"Failed login for: {identifier[:3]}***")
            return jsonify({'message': 'Invalid credentials'}), 401

        # Successful login — reset lockout counter
        if user.failed_login_count:
            user.failed_login_count  = 0
            user.account_locked_until = None
            user.last_failed_login    = None

        # Auto-migrate legacy password hashes to bcrypt
        if not any(user.password_hash.startswith(p) for p in _BCRYPT_PREFIXES):
            try:
                user.password_hash = hash_password(password)
                logger.info(f"Password migrated to bcrypt: user_id={user.id}")
            except Exception as migrate_error:
                logger.warning(f"Password migration failed: {migrate_error}")

        # Create tokens
        family_id     = str(uuid.uuid4())
        access_token  = create_access_token(
            identity=str(user.id),
            additional_claims={'family_id': family_id}
        )
        refresh_token = create_refresh_token(
            identity=str(user.id),
            additional_claims={'family_id': family_id}
        )

        # Persist token family for rotation/reuse detection
        try:
            family = TokenFamily(
                user_id=user.id,
                family_id=family_id,
                current_jti=decode_token(refresh_token)['jti']
            )
            db.session.add(family)
            db.session.commit()
        except Exception as tf_err:
            logger.error(f"TokenFamily persist failed: {tf_err}")
            db.session.rollback()
            # Non-fatal — proceed without family tracking this time

        response = jsonify({
            'access_token': access_token,
            'user': {
                'id':       user.id,
                'username': user.username,
                'email':    user.email
            }
        })
        set_refresh_cookies(response, refresh_token)

        elapsed = (time.time() - start_time) * 1000
        logger.info(f"Login success: user_id={user.id} ({elapsed:.0f}ms)")
        return response, 200

    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        error_str = str(e).lower()
        if any(kw in error_str for kw in ['connection', 'timeout', 'network', 'unreachable', 'operational']):
            return jsonify({'message': 'Database connection failed. Please try again.'}), 503
        return jsonify({'message': 'Login failed. Please try again.'}), 500


def login_with_retry(identifier, password):
    """Fallback login method with retry logic for connection issues"""
    import logging
    logger = logging.getLogger(__name__)
    
    @retry_on_connection_error(max_retries=2, delay=1.0)
    def _login():
        # SQLAlchemy connection pool handles connection management
        user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
        if not user or not verify_password(user.password_hash, password):
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


@auth_bp.route('/set-password', methods=['POST'])
@jwt_required()
def set_password():
    """Allow logged-in users (including OAuth users) to set or change their password.
    Request JSON: { "current_password": "..." (optional if no password set), "new_password": "..." }
    """
    try:
        user_id = get_jwt_identity()
        user    = db.session.get(User, user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404

        data             = request.get_json() or {}
        new_password     = data.get('new_password')
        current_password = data.get('current_password')

        if not new_password:
            return jsonify({'message': 'New password is required'}), 400

        # Require current password if one is already set
        if user.password_hash:
            if not current_password:
                return jsonify({'message': 'Current password required'}), 400
            if not verify_password(user.password_hash, current_password):
                return jsonify({'message': 'Current password is incorrect'}), 401

        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            return jsonify({'message': error_msg}), 400

        new_hash = hash_password(new_password)   # bcrypt — not werkzeug
        
        from uow.unit_of_work import UnitOfWork
        from services.auth_service import AuthService
        
        with UnitOfWork() as uow:
            auth_service = AuthService(uow)
            auth_service.update_password(user_id, new_hash)
            
        return jsonify({'message': 'Password updated successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Set password error: {e}", exc_info=True)
        return jsonify({'message': 'Failed to update password'}), 500


@auth_bp.route('/update-username', methods=['POST'])
@jwt_required()
def update_username():
    """Allow logged-in users to change their username with uniqueness checks."""
    try:
        user_id  = get_jwt_identity()
        user     = db.session.get(User, user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404

        data         = request.get_json() or {}
        new_username = data.get('new_username', '').strip()
        if not new_username:
            return jsonify({'message': 'New username is required'}), 400

        if not re.match(r'^[a-zA-Z0-9_-]{3,50}$', new_username):
            return jsonify({'message': 'Username must be 3-50 characters and contain only letters, numbers, underscores, and hyphens'}), 400

        is_available, exact_match, case_insensitive_match = check_username_availability(new_username)
        if not is_available:
            suggestions = generate_username_suggestions(new_username, 3)
            response = {'message': 'An account already exists with those credentials.', 'suggestions': suggestions}
            if case_insensitive_match and case_insensitive_match != new_username:
                response['case_insensitive_conflict'] = case_insensitive_match
            return jsonify(response), 409

        try:
            from uow.unit_of_work import UnitOfWork
            from services.auth_service import AuthService
            
            with UnitOfWork() as uow:
                user = uow.users.get_by_id(user_id)
                if not user:
                    return jsonify({'message': 'User not found'}), 404
                    
                auth_service = AuthService(uow)
                auth_service.update_username(user, new_username)
                
            return jsonify({'message': 'Username updated successfully', 'username': new_username}), 200
        except IntegrityError:
            # db.session.rollback() is handled by UoW
            suggestions = generate_username_suggestions(new_username, 3)
            return jsonify({'message': 'An account already exists with those credentials.', 'suggestions': suggestions}), 409

    except Exception as e:
        db.session.rollback()
        logger.error(f"Update username error: {e}", exc_info=True)
        return jsonify({'message': 'Failed to update username'}), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token with rotation and reuse detection."""
    jwt_data  = get_jwt()
    identity  = get_jwt_identity()
    old_jti   = jwt_data['jti']
    family_id = jwt_data.get('family_id')

    if not family_id:
        # Old token issued before family tracking — fall back to simple rotation
        new_access = create_access_token(identity=identity)
        return jsonify({'access_token': new_access}), 200

    # Load family
    family = TokenFamily.query.filter_by(family_id=family_id).first()
    if not family or family.revoked:
        logger.warning(f"Refresh on revoked/missing family: user={identity} family={family_id}")
        return jsonify({'message': 'Session expired. Please log in again.'}), 401

    # Reuse detection: token jti doesn't match current valid jti → replay attack
    if family.current_jti != old_jti:
        family.revoked        = True
        family.revoked_reason = 'reuse_detected'
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
        logger.warning(f"Refresh token reuse — family revoked: user={identity} family={family_id}")
        return jsonify({'message': 'Session compromised. Please log in again.'}), 401

    # Issue new tokens (same family)
    new_access  = create_access_token(
        identity=identity,
        additional_claims={'family_id': family_id}
    )
    new_refresh = create_refresh_token(
        identity=identity,
        additional_claims={'family_id': family_id}
    )
    new_jti = decode_token(new_refresh)['jti']

    # Blacklist old refresh jti + update family
    try:
        from utils.redis_utils import redis_cache
        redis_cache.client.setex(f"revoked_jti:{old_jti}", 60 * 60 * 24 * 30, "1")
    except Exception as e:
        logger.warning(f"Could not blacklist old refresh jti: {e}")

    try:
        family.current_jti  = new_jti
        family.last_used_at = datetime.utcnow()
        db.session.commit()
    except Exception:
        db.session.rollback()

    response = jsonify({'access_token': new_access})
    set_refresh_cookies(response, new_refresh)
    return response, 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout: blacklist current access token JTI + revoke token family."""
    try:
        jwt_data  = get_jwt()
        jti       = jwt_data['jti']
        exp       = jwt_data['exp']
        family_id = jwt_data.get('family_id')
        ttl       = max(int(exp - time.time()), 1)

        # Blacklist access token
        try:
            from utils.redis_utils import redis_cache
            redis_cache.client.setex(f"revoked_jti:{jti}", ttl, "1")
        except Exception as e:
            logger.warning(f"Could not blacklist JTI on logout: {e}")

        # Revoke token family → invalidates all refresh tokens for this session
        if family_id:
            try:
                family = TokenFamily.query.filter_by(family_id=family_id).first()
                if family and not family.revoked:
                    family.revoked        = True
                    family.revoked_reason = 'logout'
                    db.session.commit()
            except Exception as e:
                logger.warning(f"Could not revoke token family on logout: {e}")
                db.session.rollback()

        response = jsonify({'message': 'Logout successful'})
        unset_jwt_cookies(response)
        return response, 200
    except Exception as e:
        logger.error(f"Logout error: {e}", exc_info=True)
        response = jsonify({'message': 'Logout successful'})
        unset_jwt_cookies(response)
        return response, 200

@auth_bp.route('/verify-token', methods=['POST'])
@jwt_required()
@retry_on_connection_error(max_retries=1, delay=1.0)
def verify_token_status():
    """Verify if the current token is valid"""
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    return jsonify({
        'valid': True,
        'user': {'id': user.id, 'username': user.username, 'email': user.email}
    }), 200


from flask_cors import cross_origin


def _generate_unique_username(base: str) -> str:
    """
    Generate a unique username sequentially (john → john1 → john2).
    Falls back to UUID suffix only if 100 iterations fail.
    Zero extra queries on the happy path.
    """
    base = re.sub(r'[^a-zA-Z0-9_-]', '', base.split('@')[0])[:44].strip('_-') or 'user'
    candidate = base
    for i in range(1, 100):
        if not User.query.filter(func.lower(User.username) == candidate.lower()).first():
            return candidate
        candidate = f"{base}{i}"
    return f"{base}_{uuid.uuid4().hex[:6]}"


@auth_bp.route('/supabase-oauth', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True, origins=["https://itsfuze.vercel.app", "http://localhost:3000", "http://localhost:5173"])
@retry_on_connection_error(max_retries=1, delay=1.0)
def supabase_oauth():
    """Exchange a Supabase OAuth access token for a local application session.
    Frontend POST JSON: { "access_token": "..." }
    """
    try:
        data         = request.get_json() or {}
        access_token = data.get('access_token')
        if not access_token:
            return jsonify({'message': 'access_token is required'}), 400

        SUPABASE_URL = os.environ.get('SUPABASE_URL')
        if not SUPABASE_URL:
            return jsonify({'message': 'Supabase not configured'}), 503

        # Use anon key — service role key must never be in user-facing request flows
        anon_key = os.environ.get('SUPABASE_ANON_KEY', '')
        if not anon_key:
            logger.warning("SUPABASE_ANON_KEY not set — OAuth token verification may fail")

        user_info_url = SUPABASE_URL.rstrip('/') + '/auth/v1/user'
        headers = {
            'Authorization': f'Bearer {access_token}',
            'apikey': anon_key,
        }

        resp = requests.get(user_info_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"Supabase token verification failed: {resp.status_code}")
            return jsonify({'message': 'Invalid Supabase token'}), 401

        supa_user = resp.json()
        raw_email = (
            supa_user.get('email')
            or (supa_user.get('user') or {}).get('email', '')
        )
        email = raw_email.strip().lower() if raw_email else ''

        if not email or not validate_email(email):
            return jsonify({'message': 'Unable to determine valid user email from Supabase'}), 400

        name = (
            (supa_user.get('user') or {}).get('user_metadata', {}).get('full_name')
            if isinstance(supa_user.get('user'), dict)
            else None
        )

        # Find or create local user
        user = User.query.filter(func.lower(User.email) == email).first()
        if not user:
            username     = _generate_unique_username(email)
            random_pw    = ''.join(random.choices(string.ascii_letters + string.digits, k=24))
            provider_id  = supa_user.get('id') or (supa_user.get('user') or {}).get('id')

            user = User(
                username=username,
                email=email,
                password_hash=hash_password(random_pw),   # bcrypt placeholder
                user_metadata={'supabase_user_id': provider_id},
                provider_name='google',
                provider_user_id=provider_id
            )
            try:
                db.session.add(user)
                db.session.commit()
            except IntegrityError as e:
                db.session.rollback()
                logger.warning(f"IntegrityError creating OAuth user: {e}")
                existing = (
                    User.query.filter(func.lower(User.email) == email).first()
                    or (User.query.filter_by(provider_user_id=provider_id).first() if provider_id else None)
                )
                if existing:
                    user = existing
                else:
                    logger.error("Could not recover from IntegrityError — no existing user found")
                    return jsonify({'message': 'Failed to create user account'}), 500
            except Exception as e:
                db.session.rollback()
                logger.error(f"Failed to create OAuth user: {e}")
                return jsonify({'message': 'Failed to create user account'}), 500
        else:
            # Update provider info if missing
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

        # Issue local tokens with family tracking
        family_id     = str(uuid.uuid4())
        access        = create_access_token(
            identity=str(user.id),
            additional_claims={'family_id': family_id}
        )
        refresh       = create_refresh_token(
            identity=str(user.id),
            additional_claims={'family_id': family_id}
        )
        try:
            family = TokenFamily(
                user_id=user.id,
                family_id=family_id,
                current_jti=decode_token(refresh)['jti']
            )
            db.session.add(family)
            db.session.commit()
        except Exception as e:
            logger.warning(f"TokenFamily persist failed in OAuth: {e}")
            db.session.rollback()

        response = jsonify({
            'access_token': access,
            'user': {'id': user.id, 'username': user.username, 'email': user.email}
        })
        set_refresh_cookies(response, refresh)
        return response, 200

    except Exception as e:
        logger.error(f"Supabase OAuth error: {e}", exc_info=True)
        return jsonify({'message': 'OAuth sign-in failed'}), 500