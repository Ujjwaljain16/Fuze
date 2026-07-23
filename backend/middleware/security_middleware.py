"""
Production Security Middleware for Fuze Application
Implements RLS-like behavior at application level:
- Validates user ownership of resources
- Ensures database queries include user_id filter
- Sanitizes and validates input data
"""

import re
from functools import wraps
from flask import request, jsonify, g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from core.logging_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# USER DATA ISOLATION (RLS-like behavior)
# ============================================================================

def get_current_user_id() -> int:
    """
    Get authenticated user ID from JWT token.
    Raises ValueError if not authenticated.
    """
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        if not user_id:
            raise ValueError("Invalid token: user ID not found")
        return int(user_id)
    except Exception as e:
        raise ValueError(f"Authentication required: {str(e)}")

def require_user_context(func):
    """
    Decorator that sets user context in Flask 'g' object.
    Ensures user is authenticated and user_id is available throughout the request.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            user_id = get_current_user_id()
            g.user_id = user_id
            
            return func(*args, **kwargs)
        except Exception as e:
            logger.error("security_context_failed", error=str(e))
            return jsonify({'error': 'Authentication failed'}), 401
    
    return wrapper

def validate_user_owns_resource(user_id: int, resource_user_id: int) -> bool:
    """
    Validate that user owns the resource (RLS check)
    """
    if user_id != resource_user_id:
        logger.warning("security_resource_ownership_denied", user_id=user_id, resource_owner_id=resource_user_id)
        return False
    return True

# ============================================================================
# INPUT SANITIZATION AND VALIDATION
# ============================================================================

# Patterns for detecting SQL injection
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|EXEC|EXECUTE)\b)",
    r"(\b(UNION|JOIN|HAVING)\b)",
    r"(--|#|/\*|\*/)",
    r"(\bOR\s+1\s*=\s*1\b)",
    r"(\bAND\s+1\s*=\s*1\b)",
    r"(;)",
    r"(\bSLEEP\b|\bBENCHMARK\b|\bWAITFOR\b)"
]

# Patterns for detecting XSS
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
    r"(<embed[^>]*>)"
]

def validate_input(data: dict, field_rules: dict = None) -> tuple[bool, str]:
    """
    Validate input data against security patterns
    
    Args:
        data: Dictionary of input data
        field_rules: Field-specific rules override, e.g., {'url': {'check_sql_injection': False}}
    """
    if not isinstance(data, dict):
        return True, ""
    
    # Default validation rules
    default_rules = {
        'max_string_length': 10000,
        'check_sql_injection': True,
        'check_xss': True
    }
    
    # Fields that can contain large text (don't limit length stringently)
    large_text_fields = {'extracted_text', 'content', 'description', 'notes', 'body', 'text'}
    
    # URL fields - skip standard SQL injection check as URLs can contain legitimate keywords
    url_fields = {'url', 'source_url', 'link', 'image_url', 'avatar_url'}
    
    # User content fields - title, notes, etc. can legitimately contain SQL keywords
    user_content_fields = {'title', 'description', 'name', 'notes', 'content', 'text', 'body', 'extracted_text'}
    
    for key, value in data.items():
        if isinstance(value, str):
            # Get field-specific rules or use defaults
            field_specific_rules = {}
            if field_rules and key in field_rules:
                field_specific_rules = field_rules[key]
            elif field_rules and not any(k in field_rules for k in data.keys()):
                field_specific_rules = field_rules
            
            # Merge with defaults
            rules = {**default_rules, **field_specific_rules}
            
            # Check length
            max_length = rules.get('max_string_length')
            if max_length is not None and key not in large_text_fields and len(value) > max_length:
                return False, f"Field {key} exceeds maximum length"
            
            # SQL injection check
            check_sql = rules.get('check_sql_injection', True)
            if check_sql:
                if key in user_content_fields:
                    dangerous_patterns = [
                        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\s+.*\bFROM\b)",
                        r"(\bUNION\s+SELECT\b)",
                        r"(\b';?\s*(--|#|/\*))",
                        r"(\bOR\s+1\s*=\s*1\b)",
                        r"(\bAND\s+1\s*=\s*1\b)",
                    ]
                    for pattern in dangerous_patterns:
                        if re.search(pattern, value, re.IGNORECASE):
                            logger.warning("security_sql_injection_detected_content", field=key)
                            return False, f"Invalid characters in field {key}"
                elif key in url_fields:
                    dangerous_patterns = [
                        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\s+.*\bFROM\b)",
                        r"(\bUNION\s+SELECT\b)",
                        r"(\b';?\s*(--|#|/\*))",
                    ]
                    for pattern in dangerous_patterns:
                        if re.search(pattern, value, re.IGNORECASE):
                            logger.warning("security_sql_injection_detected_url", field=key)
                            return False, f"Invalid characters in field {key}"
                else:
                    for pattern in SQL_INJECTION_PATTERNS:
                        if re.search(pattern, value, re.IGNORECASE):
                            logger.warning("security_sql_injection_detected", field=key)
                            return False, f"Invalid characters in field {key}"
            
            # Check XSS
            check_xss = rules.get('check_xss', True)
            if check_xss and key not in {'extracted_text', 'content', 'body', 'text'}:
                for pattern in XSS_PATTERNS:
                    if re.search(pattern, value, re.IGNORECASE):
                        logger.warning("security_xss_detected", field=key)
                        return False, f"Invalid content in field {key}"
        
        elif isinstance(value, dict):
            is_valid, error = validate_input(value, field_rules)
            if not is_valid:
                return False, error
    
    return True, ""

def sanitize_string(value: str) -> str:
    """
    Sanitize string input
    """
    if not isinstance(value, str):
        return str(value)
    
    # Remove null bytes
    value = value.replace('\x00', '')
    
    # Trim whitespace
    value = value.strip()
    
    return value

# ============================================================================
# REQUEST VALIDATION MIDDLEWARE
# ============================================================================

def validate_request_data(required_fields: list = None, optional_fields: list = None, field_rules: dict = None):
    """
    Decorator to validate request data
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if request.method in ['POST', 'PUT', 'PATCH']:
                data = request.get_json() or {}
                
                if required_fields:
                    missing_fields = [field for field in required_fields if field not in data]
                    if missing_fields:
                        return jsonify({
                            'error': 'Missing required fields',
                            'missing_fields': missing_fields
                        }), 400
                
                is_valid, error = validate_input(data, field_rules=field_rules)
                if not is_valid:
                    return jsonify({'error': error}), 400
                
                large_text_fields = {'extracted_text', 'content', 'description', 'notes', 'body', 'text'}
                for key, value in data.items():
                    if isinstance(value, str):
                        if key in large_text_fields:
                            data[key] = value.replace('\x00', '')
                        else:
                            data[key] = sanitize_string(value)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

def get_client_identifier():
    """
    Get unique identifier for rate limiting
    """
    try:
        user_id = get_jwt_identity()
        if user_id:
            return f"user:{user_id}"
    except:
        pass
    
    return f"ip:{request.remote_addr}"

def add_security_headers(response):
    """
    Add security headers to response
    """
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https:; "
        "frame-ancestors 'none';"
    )
    
    return response
