from flask import Blueprint, request, jsonify
from core.http_errors import error_response
import os
import time
import uuid
import re
import logging
import requests
from datetime import datetime, timedelta
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt.exceptions import PyJWTError
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, get_jwt_identity,
    get_jwt, decode_token, set_access_cookies, set_refresh_cookies, unset_jwt_cookies, verify_jwt_in_request
)
from flask_cors import cross_origin
from sqlalchemy.exc import IntegrityError
import bcrypt

from uow.unit_of_work import UnitOfWork
from services.auth_service import AuthService, AuthenticationFailed, RegistrationFailed, AccountLinkRequired
from utils.database_utils import retry_on_connection_error
from middleware.rate_limiting import limiter
from utils.cooperative import run_cpu_bound

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
    run_cpu_bound(bcrypt.checkpw, pw, _TIMING_DUMMY_HASH.encode('utf-8'))

def hash_password(password: str) -> str:
    """Helper for password hashing - delegates to AuthService (no database session needed)."""
    return AuthService(None).hash_password(password)

def verify_password(password_hash: str, password: str) -> bool:
    """Helper for password verification - delegates to AuthService (no database session needed)."""
    return AuthService(None).verify_password(password_hash, password)

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
            return error_response('username_required', 'Username is required', 400, available=False)

        if not re.match(r'^[a-zA-Z0-9_-]{3,50}$', username):
            return error_response(
                'invalid_username',
                'Username must be 3-50 characters and contain only letters, numbers, underscores, and hyphens',
                400, available=False,
            )

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
        return error_response('internal_error', 'Service temporarily unavailable', 500, available=False)


@auth_bp.route('/bulk-check-usernames', methods=['POST'])
@limiter.limit("20 per minute")
def bulk_check_usernames_endpoint():
    """Bulk username availability check endpoint using 1 DB batch query"""
    try:
        data = request.get_json() or {}
        usernames = data.get('usernames', [])
        if not usernames or not isinstance(usernames, list):
            return error_response('usernames_required', 'A list of usernames is required', 400)

        with UnitOfWork() as uow:
            auth_service = AuthService(uow)
            results = auth_service.bulk_check_usernames(usernames)

        return jsonify({'results': results}), 200
    except Exception as e:
        logger.error(f"Bulk username check error: {e}")
        return error_response('internal_error', 'Failed to process bulk username check', 500)


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("10 per hour")
@retry_on_connection_error(max_retries=1, delay=1.0)
def register():
    """Production-grade registration endpoint with validation and rate limiting"""
    try:
        data = request.get_json()
        if not data:
            return error_response('missing_body', 'Request body is required', 400)

        username = data.get('username')
        email    = data.get('email')
        password = data.get('password')

        if not username or not email or not password:
            return error_response('missing_fields', 'Username, email, and password are required', 400)

        username = sanitize_input(username, max_length=50)
        email    = sanitize_input(email, max_length=255)
        email    = email.strip().lower() if email else None

        if not username or not email:
            return error_response('invalid_input', 'Invalid input format', 400)

        if not validate_email(email):
            return error_response('invalid_email', 'Invalid email format', 400)

        if not re.match(r'^[a-zA-Z0-9_-]{3,50}$', username):
            return error_response('invalid_username', 'Username must be 3-50 characters and contain only letters, numbers, underscores, and hyphens', 400)

        with UnitOfWork() as uow:
            auth_service = AuthService(uow)
            is_valid, error_msg = auth_service.validate_password_strength(password)
            if not is_valid:
                return error_response('weak_password', error_msg, 400)

            is_available, _, case_match = auth_service.check_username_availability(username)
            if not is_available:
                suggestions = auth_service.generate_username_suggestions(username, 3)
                extra = {}
                if suggestions:
                    extra['suggestions'] = suggestions
                if case_match and case_match != username:
                    extra['case_insensitive_conflict'] = case_match
                return error_response('account_exists', 'An account already exists with those credentials.', 409, **extra)

            if uow.users.get_by_email(email):
                logger.info(f"Register blocked — email exists: {email[:3]}***")
                return error_response('account_exists', 'An account already exists with those credentials.', 409)

            try:
                user = auth_service.register(username=username, email=email, password=password)
            except RegistrationFailed as rf_err:
                return error_response('registration_failed', str(rf_err), 400)

        logger.info(f"User registered successfully: {username}")
        return jsonify({'message': 'User registered successfully'}), 201

    except IntegrityError as e:
        logger.warning(f"IntegrityError during registration: {e}")
        return error_response('account_exists', 'An account already exists with those credentials.', 409)
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        return error_response('registration_failed', 'Registration failed. Please try again.', 500)


@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """Verify JWT token is valid and return user info"""
    try:
        current_user_id = int(get_jwt_identity())
        with UnitOfWork() as uow:
            user = uow.users.get_by_id(current_user_id)
            if not user:
                return error_response('user_not_found', 'User not found', 404)
            user_data = user.to_dict()
        return jsonify({'valid': True, 'user': user_data, 'message': 'Token is valid'}), 200
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return error_response('token_verification_failed', 'Token verification failed', 401)


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per 15 minutes")
def login():
    """Production-grade login with timing-safe auth, account lockout, and token families."""
    start_time = time.time()

    try:
        data = request.get_json()
        if not data:
            return error_response('missing_body', 'Request body is required', 400)

        identifier = data.get('username') or data.get('email')
        password   = data.get('password')

        if not identifier or not password:
            return error_response('missing_fields', 'Username/email and password required', 400)

        identifier = sanitize_input(identifier.strip().lower(), max_length=255)
        if not identifier:
            return error_response('invalid_input', 'Invalid input format', 400)

        with UnitOfWork() as uow:
            auth_service = AuthService(uow)
            user = auth_service.get_user_for_login(identifier)

            # Timing-safe: always run bcrypt even when user not found
            if not user:
                _constant_time_fail(password)
                return error_response('invalid_credentials', 'Invalid credentials', 401)

            from core import login_throttle
            client = request.remote_addr or 'unknown'

            # Lockout checks: this client for this account, then the account as a whole
            now = datetime.utcnow()
            locked = user.account_locked_until and user.account_locked_until > now
            if locked or login_throttle.client_blocked(user.id, client):
                logger.warning(f"Login blocked: user_id={user.id} account_locked={bool(locked)}")
                _constant_time_fail(password)
                return error_response('invalid_credentials', 'Invalid credentials', 401)

            # Password verification
            if not auth_service.verify_password(user.password_hash, password):
                throttled = login_throttle.record_client_failure(user.id, client)
                lockout_data = auth_service.record_failed_login(
                    user, lock_after=login_throttle.ACCOUNT_LIMIT_WITH_CLIENT_THROTTLE if throttled
                    else login_throttle.ACCOUNT_LIMIT_WITHOUT_CLIENT_THROTTLE)
                if lockout_data['is_locked']:
                    logger.warning(f"Account locked: user_id={user.id} after {lockout_data['failed_count']} attempts")
                return error_response('invalid_credentials', 'Invalid credentials', 401)

            # Successful login — reset lockout state
            login_throttle.clear_client_failures(user.id, client)
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
            'refresh_token': refresh_token,
            'user': user_data
        })
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)

        # Fire-and-forget cache warming (ITEM 6)
        try:
            from core.feature_flags import is_enabled
            if is_enabled('cache_warm_on_login', user_id=user_id):
                from services.task_queue import enqueue_cache_warm_job
                enqueue_cache_warm_job(user_id)
        except Exception as warm_err:
            logger.warning(f"cache_warm_enqueue_failed: {warm_err}")

        elapsed = (time.time() - start_time) * 1000
        logger.info(f"Login success: user_id={user_id} ({elapsed:.0f}ms)")
        return response, 200

    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        error_str = str(e).lower()
        if any(kw in error_str for kw in ['connection', 'timeout', 'network', 'unreachable', 'operational']):
            return error_response('database_unavailable', 'Database connection failed. Please try again.', 503)
        return error_response('login_failed', 'Login failed. Please try again.', 500)


RECENT_SIGN_IN_SECONDS = 15 * 60


@auth_bp.route('/set-password', methods=['POST'])
@jwt_required()
@limiter.limit("5 per 15 minutes")
def set_password():
    """Allow logged-in users to set or change their password."""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}
        new_password = data.get('new_password')
        current_password = data.get('current_password')

        if not new_password:
            return error_response('password_required', 'New password is required', 400)

        with UnitOfWork() as uow:
            auth_service = AuthService(uow)
            user = uow.users.get_by_id(user_id)
            if not user:
                return error_response('user_not_found', 'User not found', 404)

            meta = dict(user.user_metadata or {})
            # Accounts created by Google sign-in get a random password nobody knows, so asking for
            # the "current password" locked them out of ever setting one. For their first password,
            # a recent sign-in stands in for it.
            first_password_for_oauth_account = bool(meta.get('supabase_user_id')) and not meta.get('password_set')
            if first_password_for_oauth_account:
                from core.sessions import session_started_at
                # Measured from when the session began: a refreshed token's iat is always recent.
                # 403, not 401: a 401 makes the client refresh and retry.
                if time.time() - session_started_at(uow, get_jwt()) > RECENT_SIGN_IN_SECONDS:
                    return error_response('recent_sign_in_required', 'Please sign in again to set a password', 403)
            else:
                if not current_password:
                    return error_response('password_required', 'Current password required', 400)
                if not auth_service.verify_password(user.password_hash, current_password):
                    return error_response('invalid_password', 'Current password is incorrect', 401)

            is_valid, error_msg = auth_service.validate_password_strength(new_password)
            if not is_valid:
                return error_response('weak_password', error_msg, 400)

            new_hash = auth_service.hash_password(new_password)
            auth_service.update_password(user_id, new_hash)
            meta['password_set'] = True
            user.user_metadata = meta  # reassign: JSON columns don't track in-place changes
            from core import cache_keys
            from utils.redis_utils import redis_cache
            redis_cache.delete_cache(cache_keys.profile(user_id))

            from core.sessions import revoke_user_sessions
            revoke_user_sessions(uow, user_id, keep_family_id=get_jwt().get('family_id'))

        return jsonify({'message': 'Password updated successfully'}), 200

    except Exception as e:
        logger.error(f"Set password error: {e}", exc_info=True)
        return error_response('internal_error', 'Failed to update password', 500)


@auth_bp.route('/update-username', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def update_username():
    """Allow logged-in users to change their username with uniqueness checks."""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}
        new_username = data.get('new_username', '').strip()

        if not new_username:
            return error_response('username_required', 'New username is required', 400)

        if not re.match(r'^[a-zA-Z0-9_-]{3,50}$', new_username):
            return error_response('invalid_username', 'Username must be 3-50 characters and contain only letters, numbers, underscores, and hyphens', 400)

        with UnitOfWork() as uow:
            auth_service = AuthService(uow)
            user = uow.users.get_by_id(user_id)
            if not user:
                return error_response('user_not_found', 'User not found', 404)

            is_available, exact_match, case_match = auth_service.check_username_availability(new_username)
            if not is_available:
                suggestions = auth_service.generate_username_suggestions(new_username, 3)
                extra = {'suggestions': suggestions}
                if case_match and case_match != new_username:
                    extra['case_insensitive_conflict'] = case_match
                return error_response('account_exists', 'An account already exists with those credentials.', 409, **extra)

            try:
                auth_service.update_username(user, new_username)
            except IntegrityError:
                suggestions = auth_service.generate_username_suggestions(new_username, 3)
                return error_response('account_exists', 'An account already exists with those credentials.', 409, suggestions=suggestions)

        return jsonify({'message': 'Username updated successfully', 'username': new_username}), 200

    except Exception as e:
        logger.error(f"Update username error: {e}", exc_info=True)
        return error_response('internal_error', 'Failed to update username', 500)


def _verify_refresh_token() -> bool:
    """Accept the refresh token from the Authorization header, else from the refresh cookie.

    The SPA is served from a different site than the API, so the SameSite=Lax refresh cookie is
    not sent on its requests; it sends the refresh token in the header instead. Older clients
    sent the *access* token in that header, which must not shadow a valid refresh cookie.
    """
    for locations in (['headers'], ['cookies']):
        try:
            verify_jwt_in_request(refresh=True, locations=locations)
            return True
        except (JWTExtendedException, PyJWTError):
            continue
    return False


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """Refresh access token with rotation and reuse detection."""
    if not _verify_refresh_token():
        return error_response('invalid_refresh_token', 'Refresh token missing or invalid', 401)
    jwt_data  = get_jwt()
    identity  = get_jwt_identity()
    old_jti   = jwt_data['jti']
    family_id = jwt_data.get('family_id')

    if not family_id:
        # Pre-rotation token: it belongs to no session that could ever be revoked.
        return error_response('invalid_refresh_token', 'Session expired. Please log in again.', 401)

    with UnitOfWork() as uow:
        family = uow.token_families.get_family(family_id, lock=True)
        if not family or family.revoked:
            logger.warning(f"Refresh on revoked/missing family: user={identity} family={family_id}")
            return error_response('invalid_refresh_token', 'Session expired. Please log in again.', 401)

        if family.current_jti != old_jti:
            uow.token_families.revoke_family(family_id, 'reuse_detected')
            from core.sessions import mark_family_revoked
            mark_family_revoked(family_id)
            logger.warning(f"Refresh token reuse — family revoked: user={identity} family={family_id}")
            return error_response('session_compromised', 'Session compromised. Please log in again.', 401)

        new_access = create_access_token(identity=identity, additional_claims={'family_id': family_id})
        new_refresh = create_refresh_token(identity=identity, additional_claims={'family_id': family_id})
        new_jti = decode_token(new_refresh)['jti']

        try:
            from utils.redis_utils import redis_cache
            redis_cache.client.setex(f"revoked_jti:{old_jti}", 60 * 60 * 24 * 30, "1")
        except Exception as e:
            logger.warning(f"Could not blacklist old refresh jti: {e}")

        uow.token_families.update_current_jti(family_id, new_jti)

    response = jsonify({'access_token': new_access, 'refresh_token': new_refresh})
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
        exp       = jwt_data.get('exp')  # absent when access tokens are configured not to expire
        family_id = jwt_data.get('family_id')
        ttl       = max(int(exp - time.time()), 1) if exp else 24 * 3600

        try:
            from utils.redis_utils import redis_cache
            redis_cache.client.setex(f"revoked_jti:{jti}", ttl, "1")
        except Exception as e:
            logger.warning(f"Could not blacklist JTI on logout: {e}")

        if family_id:
            try:
                with UnitOfWork() as uow:
                    uow.token_families.revoke_family(family_id, 'logout')
                from core.sessions import mark_family_revoked
                mark_family_revoked(family_id)
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
            return error_response('user_not_found', 'User not found', 404)
        user_data = {'id': user.id, 'username': user.username, 'email': user.email}
    return jsonify({'valid': True, 'user': user_data}), 200


def _supabase_unavailable():
    return error_response('auth_provider_unavailable', 'Sign-in service is unavailable, please try again', 503)


def _fetch_supabase_user(access_token):
    """Resolve a Supabase access token to its user, or return an error response.

    Only a rejected token is a 401. A Supabase outage (5xx, rate limit, timeout, connection
    error) is a 503, so the client retries instead of treating a valid sign-in as a bad token.
    """
    if not access_token:
        return None, error_response('access_token_required', 'access_token is required', 400)
    supabase_url = os.environ.get('SUPABASE_URL')
    if not supabase_url:
        return None, error_response('auth_provider_unavailable', 'Supabase not configured', 503)
    try:
        resp = requests.get(
            supabase_url.rstrip('/') + '/auth/v1/user',
            headers={'Authorization': f'Bearer {access_token}', 'apikey': os.environ.get('SUPABASE_ANON_KEY', '')},
            timeout=10,
        )
    except requests.RequestException as e:
        logger.warning(f"Supabase user lookup failed: {e.__class__.__name__}")
        return None, _supabase_unavailable()
    if resp.status_code >= 500 or resp.status_code == 429:
        logger.warning(f"Supabase user lookup unavailable: {resp.status_code}")
        return None, _supabase_unavailable()
    if resp.status_code != 200:
        logger.warning(f"Supabase token verification failed: {resp.status_code}")
        return None, error_response('invalid_oauth_token', 'Invalid Supabase token', 401)
    supa_user = resp.json()
    raw_email = supa_user.get('email') or (supa_user.get('user') or {}).get('email', '')
    if not raw_email or not validate_email(raw_email.strip().lower()):
        return None, error_response('oauth_email_missing', 'Unable to determine valid user email from Supabase', 400)
    return supa_user, None


@auth_bp.route('/supabase-oauth', methods=['POST', 'OPTIONS'])
@retry_on_connection_error(max_retries=1, delay=1.0)
def supabase_oauth():
    """Exchange a Supabase OAuth access token for a local application session."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        supa_user, error = _fetch_supabase_user((request.get_json(silent=True) or {}).get('access_token'))
        if error:
            return error

        with UnitOfWork() as uow:
            user, access, refresh = AuthService(uow).handle_supabase_oauth(supa_user)
            user_data = {'id': user.id, 'username': user.username, 'email': user.email}

        response = jsonify({
            'access_token': access,
            'refresh_token': refresh,
            'user': user_data
        })
        set_access_cookies(response, access)
        set_refresh_cookies(response, refresh)
        return response, 200

    except AccountLinkRequired as e:
        return error_response('account_link_required', str(e), 409)
    except (AuthenticationFailed, RegistrationFailed) as e:
        return error_response('oauth_rejected', str(e), 403)
    except Exception as e:
        logger.error(f"Supabase OAuth error: {e}", exc_info=True)
        return error_response('oauth_failed', 'OAuth sign-in failed', 500)


@auth_bp.route('/link-oauth', methods=['POST'])
@jwt_required()
def link_oauth():
    """Connect a Google identity to the signed-in account (the only way to join an existing account)."""
    try:
        supa_user, error = _fetch_supabase_user((request.get_json(silent=True) or {}).get('access_token'))
        if error:
            return error
        with UnitOfWork() as uow:
            user = AuthService(uow).link_supabase_identity(int(get_jwt_identity()), supa_user)
            user_data = {'id': user.id, 'username': user.username, 'email': user.email,
                         'provider_name': user.provider_name}
        from core import cache_keys
        from utils.redis_utils import redis_cache
        redis_cache.delete_cache(cache_keys.profile(user_data['id']))
        return jsonify({'message': 'Google account connected', 'user': user_data}), 200
    except (AuthenticationFailed, RegistrationFailed) as e:
        return error_response('link_rejected', str(e), 403)
    except Exception as e:
        logger.error(f"OAuth link error: {e}", exc_info=True)
        return error_response('link_failed', 'Could not connect Google account', 500)
