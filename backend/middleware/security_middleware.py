"""
User Authorization & Input Security Middleware
Implements user data isolation checks, input validation, and security headers:
- Validates user ownership of resources
- Ensures request data is sanitized and stored on Flask g.validated_data
- Adds modern HTTP security headers (HSTS, CSP, COOP, CORP, Nosniff)
"""

import re
from functools import wraps
from typing import Tuple, Dict, Any, Optional, List
from flask import request, jsonify, g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException
from core.logging_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# USER DATA ISOLATION & AUTHORIZATION
# ============================================================================

def get_current_user_id() -> int:
    """
    Get authenticated user ID from JWT token.
    Raises ValueError if missing or invalid.
    """
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()

        if user_id is None:
            raise ValueError("Invalid token: user ID not found")

        if isinstance(user_id, dict):
            user_id = user_id.get('id') or user_id.get('user_id')

        if user_id is None:
            raise ValueError("Invalid token payload structure")

        return int(user_id)
    except JWTExtendedException as jwt_err:
        raise ValueError(f"Authentication failed: {str(jwt_err)}")
    except (TypeError, ValueError) as err:
        raise ValueError(f"Invalid user identity: {str(err)}")


def require_user_context(func):
    """
    Decorator that sets user context in Flask 'g' object.
    Ensures user is authenticated and g.user_id is available throughout the request.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            user_id = get_current_user_id()
            g.user_id = user_id
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception("security_context_failed")
            return jsonify({'error': 'Authentication failed'}), 401

    return wrapper


def validate_user_owns_resource(user_id: int, resource_user_id: int) -> bool:
    """
    Validate that the authenticated user owns the resource.
    """
    if user_id != resource_user_id:
        logger.warning("security_resource_ownership_denied", extra={"user_id": user_id, "resource_owner_id": resource_user_id})
        return False
    return True


# ============================================================================
# INPUT SANITIZATION AND VALIDATION
# ============================================================================

DANGEROUS_SQL_PATTERNS = [
    r"(\bUNION\s+SELECT\b)",
    r"(\b';?\s*(--|#|/\*))",
    r"(\bOR\s+1\s*=\s*1\b)",
    r"(\bAND\s+1\s*=\s*1\b)",
    r"(\b(DROP|TRUNCATE|ALTER)\s+TABLE\b)",
    r"(\bEXEC\s*\(|\bEXECUTE\s+)",
]

XSS_PATTERNS = [
    r"(<script[^>]*>.*?</script>)",
    r"(javascript:)",
    r"(vbscript:)",
    r"(onload\s*=)",
    r"(onerror\s*=)",
    r"(onclick\s*=)",
    r"(onmouseover\s*=)",
    r"(<iframe[^>]*>)",
    r"(<object[^>]*>)",
    r"(<embed[^>]*>)",
]


def validate_input(data: Any, field_rules: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """
    Recursively validate input dictionaries and lists against length bounds, SQL structural injection, and XSS patterns.
    """
    if isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                is_valid, error = validate_input(item, field_rules)
                if not is_valid:
                    return False, error
        return True, ""

    if not isinstance(data, dict):
        return True, ""

    default_rules = {
        'max_string_length': 10000,
        'check_sql_injection': True,
        'check_xss': True
    }

    large_text_fields = {'extracted_text', 'content', 'description', 'notes', 'body', 'text'}

    for key, value in data.items():
        if isinstance(value, str):
            field_specific_rules = {}
            if field_rules and key in field_rules:
                field_specific_rules = field_rules[key]

            rules = {**default_rules, **field_specific_rules}

            max_length = rules.get('max_string_length')
            if max_length is not None and key not in large_text_fields and len(value) > max_length:
                return False, f"Field {key} exceeds maximum length"

            # Check structural SQL injection
            if rules.get('check_sql_injection', True):
                for pattern in DANGEROUS_SQL_PATTERNS:
                    if re.search(pattern, value, re.IGNORECASE):
                        logger.warning("security_sql_injection_detected", extra={"field": key})
                        return False, f"Invalid characters in field {key}"

            # Check XSS
            if rules.get('check_xss', True) and key not in {'extracted_text', 'content', 'body', 'text'}:
                for pattern in XSS_PATTERNS:
                    if re.search(pattern, value, re.IGNORECASE):
                        logger.warning("security_xss_detected", extra={"field": key})
                        return False, f"Invalid content in field {key}"

        elif isinstance(value, (dict, list)):
            is_valid, error = validate_input(value, field_rules)
            if not is_valid:
                return False, error

    return True, ""


def sanitize_string(value: str) -> str:
    """Sanitize string input by stripping null bytes and leading/trailing whitespace."""
    if not isinstance(value, str):
        return str(value)
    return value.replace('\x00', '').strip()


# ============================================================================
# REQUEST VALIDATION MIDDLEWARE
# ============================================================================

def validate_request_data(required_fields: Optional[List[str]] = None, optional_fields: Optional[List[str]] = None, field_rules: Optional[Dict[str, Any]] = None):
    """
    Decorator to validate JSON request payloads and store sanitized result in Flask g.validated_data.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if request.method in ['POST', 'PUT', 'PATCH']:
                data = request.get_json(silent=True) or {}

                if required_fields:
                    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
                    if missing_fields:
                        return jsonify({
                            'error': 'Missing required fields',
                            'missing_fields': missing_fields
                        }), 400

                is_valid, error = validate_input(data, field_rules=field_rules)
                if not is_valid:
                    return jsonify({'error': error}), 400

                large_text_fields = {'extracted_text', 'content', 'description', 'notes', 'body', 'text'}
                sanitized_data = {}
                for key, value in data.items():
                    if isinstance(value, str):
                        if key in large_text_fields:
                            sanitized_data[key] = value.replace('\x00', '')
                        else:
                            sanitized_data[key] = sanitize_string(value)
                    else:
                        sanitized_data[key] = value

                g.validated_data = sanitized_data

            return func(*args, **kwargs)

        return wrapper
    return decorator


def get_client_identifier() -> str:
    """Get unique identifier for client requests using JWT identity or remote IP."""
    try:
        identity = get_jwt_identity()
        if identity:
            return f"user:{identity}"
    except (JWTExtendedException, RuntimeError):
        pass

    return f"ip:{request.remote_addr}"


def add_security_headers(response):
    """Add modern security headers to HTTP response."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https:; "
        "frame-ancestors 'none';"
    )
    return response
