from flask import Blueprint, request, jsonify
import os
import time
import uuid
import re
import logging
import requests
from datetime import datetime, timedelta
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, get_jwt_identity,
    get_jwt, decode_token, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
)
from flask_cors import cross_origin
from sqlalchemy.exc import IntegrityError
import bcrypt

from uow.unit_of_work import UnitOfWork
from services.auth_service import AuthService, AuthenticationFailed, RegistrationFailed
from utils.database_utils import retry_on_connection_error
from middleware.rate_limiting import limiter

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# ---------------------------------------------------------------------------
# Security Constants & Helpers
# ---------------------------------------------------------------------------
_BCRYPT_PREFIXES = ('$2b$', '$2a$', '$2y$')

# Pre-computed bcrypt hash of "dummy" for timing-attack mitigation
_TIMING_DUMMY_HASH = "$2b$12$AoiBV.KGmITlyHz1NWAY3eFksSfQnfebA9Fpmla92wdkacTPAf8hu"

def _constant_time_fail(password: str) -> None:
    """Always fails. Runs bcrypt so user-not-found timing == wrong-password timing."""
    pw = password.encode('utf-8') if isinstance(password, str) else password
    bcrypt.checkpw(pw, _TIMING_DUMMY_HASH.encode('utf-8'))

def hash_password(password: str) -> str:
    """Helper for password hashing - delegates to AuthService."""
    with UnitOfWork() as uow:
        return AuthService(uow).hash_password(password)

def verify_password(password_hash: str, password: str) -> bool:
    """Helper for password verification - delegates to AuthService."""
    with UnitOfWork() as uow:
        return AuthService(uow).verify_password(password_hash, password)

def sanitize_input(text: str, max_length: int = 255):
    """Sanitize and validate input to prevent injection attacks"""
    if not text:
        return None
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    text = text.strip()
    return text[:max_length] if len(text) > max_length else text

def validate_email(email: str) -> bool:
    """Validate email format"""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@auth_bp.route('/check-username', methods=['POST'])
@limiter.limit("30 per minute")
@retry_on_connection_error(max_retries=1, delay=1.0)
def check_username():
    """Fast username availability check endpoint"""
    try:
        data = request.get_json() or {}
        username = (data.get('username') or '').strip()

        if not username:
            return jsonify({'available': False, 'error': 'Username is required'}), 400

        if not re.match(r'^[a-zA-Z0-9_-]{3,50}$', username):
            return jsonify({
                'available': False,
                'error': 'Username must be 3-50 characters and contain only letters, numbers, underscores, and hyphens'
            }), 400

        with UnitOfWork() as uow:
            auth_service = AuthService(uow)
            is_available, exact_match, case_match = auth_service.check_username_availability(username)
            suggestions = []
            if not is_available:
                suggestions = auth_service.generate_username_suggestions(username, 3)

        response = {
            'available': is_available,
            'username': username
        }

        if not is_available:
            if suggestions:
                response['suggestions'] = suggestions
            if case_match and case_match != username:
                response['case_insensitive_conflict'] = case_match

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Username check error: {e}")
        return jsonify({'available': False, 'error': 'Service temporarily unavailable'}), 500


@auth_bp.route('/bulk-check-usernames', methods=['POST'])
@limiter.limit("20 per minute")
def bulk_check_usernames_endpoint():
    """Bulk username availability check endpoint using 1 DB batch query"""
    try:
        data = request.get_json() or {}
        usernames = data.get('usernames', [])
        if not usernames or not isinstance(usernames, list):
            return jsonify({'error': 'A list of usernames is required'}), 400

        with UnitOfWork() as uow:
            auth_service = AuthService(uow)
            results = auth_service.bulk_check_usernames(usernames)

        return jsonify({'results': results}), 200
    except Exception as e:
        logger.error(f"Bulk username check error: {e}")
        return jsonify({'error': 'Failed to process bulk username check'}), 500


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

        if not username or not email or not password:
            return jsonify({'message': 'Username, email, and password are required'}), 400

        username = sanitize_input(username, max_length=50)
        email    = sanitize_input(email, max_length=255)
        email    = email.strip().lower() if email else None

        if not username or not email:
            return jsonify({'message': 'Invalid input format'}), 400

        if not validate_email(email):
            return jsonify({'message': 'Invalid email format'}), 400

        if not re.match(r'^[a-zA-Z0-9_-]{3,50}$', username):
            return jsonify({'message': 'Username must be 3-50 characters and contain only letters, numbers, underscores, and hyphens'}), 400

        with UnitOfWork() as uow:
            auth_service = AuthService(uow)
            is_valid, error_msg = auth_service.validate_password_strength(password)
            if not is_valid:
                return jsonify({'message': error_msg}), 400

            is_available, _, case_match = auth_service.check_username_availability(username)
            if not is_available:
                suggestions = auth_service.generate_username_suggestions(username, 3)
                resp = {'message': 'An account already exists with those credentials.'}
                if suggestions:
                    resp['suggestions'] = suggestions
                if case_match and case_match != username:
                    resp['case_insensitive_conflict'] = case_match
                return jsonify(resp), 409

            if uow.users.get_by_email(email):
                logger.info(f"Register blocked — email exists: {email[:3]}***")
                return jsonify({'message': 'An account already exists with those credentials.'}), 409

            try:
                user = auth_service.register(username=username, email=email, password=password)
            except RegistrationFailed as rf_err:
                return jsonify({'message': str(rf_err)}), 400

        logger.info(f"User registered successfully: {username}")
        return jsonify({'message': 'User registered successfully'}), 201

    except IntegrityError as e:
        logger.warning(f"IntegrityError during registration: {e}")
        return jsonify({'message': 'An account already exists with those credentials.'}), 409
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        return jsonify({'message': 'Registration failed. Please try again.'}), 500


@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """Verify JWT token is valid and return user info"""
    try:
        current_user_id = int(get_jwt_identity())
        with UnitOfWork() as uow:
            user = uow.users.get_by_id(current_user_id)
            if not user:
                return jsonify({'message': 'User not found'}), 404
            user_data = user.to_dict()
        return jsonify({'valid': True, 'user': user_data, 'message': 'Token is valid'}), 200
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

        identifier = sanitize_input(identifier.strip().lower(), max_length=255)
        if not identifier:
            return jsonify({'message': 'Invalid input format'}), 400

        with UnitOfWork() as uow:
            auth_service = AuthService(uow)
            user = auth_service.get_user_for_login(identifier)

            # Timing-safe: always run bcrypt even when user not found
            if not user:
                _constant_time_fail(password)
                return jsonify({'message': 'Invalid credentials'}), 401

            # Account lockout check
            now = datetime.utcnow()
            if user.account_locked_until and user.account_locked_until > now:
                remaining = int((user.account_locked_until - now).total_seconds() / 60)
                logger.warning(f"Login blocked — account locked: user_id={user.id} remaining={remaining}m")
                _constant_time_fail(password)
                return jsonify({'message': 'Invalid credentials'}), 401

            # Password verification
            if not auth_service.verify_password(user.password_hash, password):
                lockout_data = auth_service.record_failed_login(user)
                if lockout_data['is_locked']:
                    logger.warning(f"Account locked: user_id={user.id} after {lockout_data['failed_count']} attempts")
                return jsonify({'message': 'Invalid credentials'}), 401

            # Successful login — reset lockout state
            auth_service.record_successful_login(user)

            # Auto-migrate legacy password hashes to bcrypt
            if not any(user.password_hash.startswith(p) for p in _BCRYPT_PREFIXES):
                try:
                    user.password_hash = auth_service.hash_password(password)
                    uow.users.add(user)
                    logger.info(f"Password migrated to bcrypt: user_id={user.id}")
                except Exception as migrate_error:
                    logger.warning(f"Password migration failed: {migrate_error}")

            # Issue tokens with family tracking inside UoW
            from models import TokenFamily
            family_id = str(uuid.uuid4())
            access_token = create_access_token(identity=str(user.id), additional_claims={'family_id': family_id})
            refresh_token = create_refresh_token(identity=str(user.id), additional_claims={'family_id': family_id})

            try:
                family = TokenFamily(
                    user_id=user.id,
                    family_id=family_id,
                    current_jti=decode_token(refresh_token)['jti']
                )
                uow.token_families.add(family)
            except Exception as tf_err:
                logger.error(f"TokenFamily persist failed: {tf_err}")

            user_id = user.id
            user_data = {'id': user.id, 'username': user.username, 'email': user.email}

        response = jsonify({
            'access_token': access_token,
            'user': user_data
        })
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)

        elapsed = (time.time() - start_time) * 1000
        logger.info(f"Login success: user_id={user_id} ({elapsed:.0f}ms)")
        return response, 200

    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        error_str = str(e).lower()
        if any(kw in error_str for kw in ['connection', 'timeout', 'network', 'unreachable', 'operational']):
            return jsonify({'message': 'Database connection failed. Please try again.'}), 503
        return jsonify({'message': 'Login failed. Please try again.'}), 500


@auth_bp.route('/set-password', methods=['POST'])
@jwt_required()
def set_password():
    """Allow logged-in users to set or change their password."""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}
        new_password = data.get('new_password')
        current_password = data.get('current_password')

        if not new_password:
            return jsonify({'message': 'New password is required'}), 400

        with UnitOfWork() as uow:
            auth_service = AuthService(uow)
            user = uow.users.get_by_id(user_id)
            if not user:
                return jsonify({'message': 'User not found'}), 404

            if user.password_hash:
                if not current_password:
                    return jsonify({'message': 'Current password required'}), 400
                if not auth_service.verify_password(user.password_hash, current_password):
                    return jsonify({'message': 'Current password is incorrect'}), 401

            is_valid, error_msg = auth_service.validate_password_strength(new_password)
            if not is_valid:
                return jsonify({'message': error_msg}), 400

            new_hash = auth_service.hash_password(new_password)
            auth_service.update_password(user_id, new_hash)

        return jsonify({'message': 'Password updated successfully'}), 200

    except Exception as e:
        logger.error(f"Set password error: {e}", exc_info=True)
        return jsonify({'message': 'Failed to update password'}), 500


@auth_bp.route('/update-username', methods=['POST'])
@jwt_required()
def update_username():
    """Allow logged-in users to change their username with uniqueness checks."""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}
        new_username = data.get('new_username', '').strip()

        if not new_username:
            return jsonify({'message': 'New username is required'}), 400

        if not re.match(r'^[a-zA-Z0-9_-]{3,50}$', new_username):
            return jsonify({'message': 'Username must be 3-50 characters and contain only letters, numbers, underscores, and hyphens'}), 400

        with UnitOfWork() as uow:
            auth_service = AuthService(uow)
            user = uow.users.get_by_id(user_id)
            if not user:
                return jsonify({'message': 'User not found'}), 404

            is_available, exact_match, case_match = auth_service.check_username_availability(new_username)
            if not is_available:
                suggestions = auth_service.generate_username_suggestions(new_username, 3)
                resp = {'message': 'An account already exists with those credentials.', 'suggestions': suggestions}
                if case_match and case_match != new_username:
                    resp['case_insensitive_conflict'] = case_match
                return jsonify(resp), 409

            try:
                auth_service.update_username(user, new_username)
            except IntegrityError:
                suggestions = auth_service.generate_username_suggestions(new_username, 3)
                return jsonify({'message': 'An account already exists with those credentials.', 'suggestions': suggestions}), 409

        return jsonify({'message': 'Username updated successfully', 'username': new_username}), 200

    except Exception as e:
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
        new_access = create_access_token(identity=identity)
        return jsonify({'access_token': new_access}), 200

    with UnitOfWork() as uow:
        family = uow.token_families.get_family(family_id, lock=True)
        if not family or family.revoked:
            logger.warning(f"Refresh on revoked/missing family: user={identity} family={family_id}")
            return jsonify({'message': 'Session expired. Please log in again.'}), 401

        if family.current_jti != old_jti:
            uow.token_families.revoke_family(family_id, 'reuse_detected')
            logger.warning(f"Refresh token reuse — family revoked: user={identity} family={family_id}")
            return jsonify({'message': 'Session compromised. Please log in again.'}), 401

        new_access = create_access_token(identity=identity, additional_claims={'family_id': family_id})
        new_refresh = create_refresh_token(identity=identity, additional_claims={'family_id': family_id})
        new_jti = decode_token(new_refresh)['jti']

        try:
            from utils.redis_utils import redis_cache
            redis_cache.client.setex(f"revoked_jti:{old_jti}", 60 * 60 * 24 * 30, "1")
        except Exception as e:
            logger.warning(f"Could not blacklist old refresh jti: {e}")

        uow.token_families.update_current_jti(family_id, new_jti)

    response = jsonify({'access_token': new_access})
    set_access_cookies(response, new_access)
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

        try:
            from utils.redis_utils import redis_cache
            redis_cache.client.setex(f"revoked_jti:{jti}", ttl, "1")
        except Exception as e:
            logger.warning(f"Could not blacklist JTI on logout: {e}")

        if family_id:
            try:
                with UnitOfWork() as uow:
                    uow.token_families.revoke_family(family_id, 'logout')
            except Exception as e:
                logger.warning(f"Could not revoke token family on logout: {e}")

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
    current_user_id = int(get_jwt_identity())
    with UnitOfWork() as uow:
        user = uow.users.get_by_id(current_user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404
        user_data = {'id': user.id, 'username': user.username, 'email': user.email}
    return jsonify({'valid': True, 'user': user_data}), 200


@auth_bp.route('/supabase-oauth', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True, origins=["https://itsfuze.vercel.app", "http://localhost:3000", "http://localhost:5173"])
@retry_on_connection_error(max_retries=1, delay=1.0)
def supabase_oauth():
    """Exchange a Supabase OAuth access token for a local application session."""
    try:
        data = request.get_json() or {}
        access_token = data.get('access_token')
        if not access_token:
            return jsonify({'message': 'access_token is required'}), 400

        SUPABASE_URL = os.environ.get('SUPABASE_URL')
        if not SUPABASE_URL:
            return jsonify({'message': 'Supabase not configured'}), 503

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
        raw_email = supa_user.get('email') or (supa_user.get('user') or {}).get('email', '')
        email = raw_email.strip().lower() if raw_email else ''

        if not email or not validate_email(email):
            return jsonify({'message': 'Unable to determine valid user email from Supabase'}), 400

        # Run complete OAuth user resolution & token family generation inside UoW
        with UnitOfWork() as uow:
            auth_service = AuthService(uow)
            user, access, refresh = auth_service.handle_supabase_oauth(supa_user)
            user_data = {'id': user.id, 'username': user.username, 'email': user.email}

        response = jsonify({
            'access_token': access,
            'user': user_data
        })
        set_access_cookies(response, access)
        set_refresh_cookies(response, refresh)
        return response, 200

    except Exception as e:
        logger.error(f"Supabase OAuth error: {e}", exc_info=True)
        return jsonify({'message': 'OAuth sign-in failed'}), 500