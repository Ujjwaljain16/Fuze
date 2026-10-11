"""
Account Blueprint
Lets a user download everything they stored and delete their account.
"""

import json
import time
from datetime import datetime, timezone

from flask import Blueprint, Response, jsonify, request
from core.http_errors import error_response
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required, unset_jwt_cookies

from blueprints.auth import RECENT_SIGN_IN_SECONDS
from core.sessions import session_started_at
from core.logging_config import get_logger
from middleware.rate_limiting import limiter
from services.account_service import AccountService, has_usable_password, purge_user_redis
from services.auth_service import AuthService
from uow.unit_of_work import UnitOfWork

logger = get_logger(__name__)

account_bp = Blueprint('account', __name__, url_prefix='/api/account')


def _block_current_access_token(jwt_data: dict) -> None:
    """Sessions are revoked by family; this also covers the token making the request."""
    exp = jwt_data.get('exp')  # absent when access tokens are configured not to expire
    ttl = max(int(exp - time.time()), 1) if exp else 24 * 3600
    try:
        from utils.redis_utils import redis_cache
        redis_cache.client.setex(f"revoked_jti:{jwt_data['jti']}", ttl, "1")
    except Exception as e:
        logger.warning("account_delete_jti_block_failed", error=str(e))


@account_bp.route('', methods=['DELETE'])
@jwt_required()
@limiter.limit("5 per 15 minutes")
def delete_account():
    """Delete the signed-in account and everything it owns, after re-authentication."""
    user_id = int(get_jwt_identity())
    jwt_data = get_jwt()
    data = request.get_json(silent=True) or {}

    try:
        with UnitOfWork() as uow:
            user = uow.users.get_by_id(user_id)
            if not user:
                return error_response('user_not_found', 'User not found', 404)

            # As for set-password: an account created by Google sign-in has no password its owner
            # knows, so a recent sign-in stands in for it. Failures are 403, not 401: the session
            # is valid, and a 401 makes the SPA refresh the token and silently retry.
            if has_usable_password(user):
                password = data.get('password')
                if not password:
                    return error_response('password_required', 'Password is required', 400)
                if not AuthService(None).verify_password(user.password_hash, password):
                    logger.warning("account_delete_wrong_password", user_id=user_id)
                    return error_response('invalid_password', 'Password is incorrect', 403)
            elif time.time() - session_started_at(uow, jwt_data) > RECENT_SIGN_IN_SECONDS:
                return error_response('recent_sign_in_required', 'Please sign in again to delete your account', 403)

            AccountService(uow).delete_account(user_id)
    except Exception:
        logger.exception("account_delete_failed", user_id=user_id)
        return error_response('internal_error', 'Failed to delete account', 500)

    _block_current_access_token(jwt_data)
    purge_user_redis(user_id)

    response = jsonify({'message': 'Account deleted'})
    unset_jwt_cookies(response)
    return response, 200


@account_bp.route('/export', methods=['GET'])
@jwt_required()
@limiter.limit("5 per hour")
def export_account():
    """Download the signed-in user's data as a JSON file."""
    user_id = int(get_jwt_identity())
    try:
        with UnitOfWork() as uow:
            export = AccountService(uow).export_user_data(user_id)
    except Exception:
        logger.exception("account_export_failed", user_id=user_id)
        return error_response('internal_error', 'Failed to export data', 500)
    if export is None:
        return error_response('user_not_found', 'User not found', 404)

    filename = f"fuze-export-{datetime.now(timezone.utc):%Y-%m-%d}.json"
    logger.info("account_exported", user_id=user_id, bookmarks=len(export['bookmarks']))
    return Response(
        json.dumps(export, ensure_ascii=False, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename={filename}', 'Cache-Control': 'no-store'},
    )
