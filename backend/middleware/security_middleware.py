#!/usr/bin/env python3
"""
Security Middleware for Production
==================================

Implements RLS-like behavior at application level:
- User data isolation
- Input validation
- SQL injection prevention
- XSS prevention
"""

import re
import logging
from functools import wraps
from flask import request, jsonify, g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

logger = logging.getLogger(__name__)

# ============================================================================
# USER DATA ISOLATION (RLS-like behavior)
# ============================================================================

def require_user_context(func):
    """
    Decorator to ensure user_id is always present and validated
    Enforces RLS-like behavior at application level
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get user_id from JWT token
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            
            if not user_id:
                return jsonify({'error': 'Authentication required'}), 401
            
            # Convert to int and validate
            try:
                user_id = int(user_id)
                if user_id <= 0:
                    raise ValueError("Invalid user_id")
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid user ID'}), 401
            
            # Store in Flask g for easy access
            g.current_user_id = user_id
            
            # Ensure user_id is in kwargs for database queries
            kwargs['user_id'] = user_id
            
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in require_user_context: {e}")
            return jsonify({'error': 'Authentication failed'}), 401
    
    return wrapper

def validate_user_owns_resource(user_id: int, resource_user_id: int):
    """
    Validate that user owns the resource (RLS check)
    """
    if user_id != resource_user_id:
        logger.warning(f"User {user_id} attempted to access resource owned by {resource_user_id}")
        return False
    return True

# ============================================================================
# INPUT VALIDATION
# ============================================================================

# SQL injection patterns
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
    r"(--|#|/\*|\*/)",
    r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
    r"(\bUNION\s+SELECT\b)",
    r"(\b';?\s*(--|#))",
]

# XSS patterns
XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript:",
    r"on\w+\s*=",
    r"<iframe[^>]*>",
    r"<object[^>]*>",
    r"<embed[^>]*>",
]

def validate_input(data: dict, field_rules: dict = None) -> tuple[bool, str]:
    """
    Validate input data against security rules
    
    Args:
        data: Input data dictionary
        field_rules: Field-specific validation rules (e.g., {'url': {'check_sql_injection': False}})
                    or global rules (e.g., {'max_string_length': 10000})
    
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Invalid input format"
    
    # Default validation rules
    default_rules = {
        'max_string_length': 10000,
        'check_sql_injection': True,
        'check_xss': True,
    }
    
    # Fields that should be exempt from SQL injection checks (URLs can contain SQL keywords)
    url_fields = {'url', 'link', 'href', 'source_url', 'redirect_url'}
    # Fields that can contain large text content (no length limit)
    large_text_fields = {'extracted_text', 'content', 'description', 'notes', 'body', 'text'}
    
    for key, value in data.items():
        if isinstance(value, str):
            # Get field-specific rules or use defaults
            field_specific_rules = {}
            if field_rules and key in field_rules:
                field_specific_rules = field_rules[key]
            elif field_rules and not any(k in field_rules for k in data.keys()):
                # If field_rules doesn't have field keys, treat as global rules
                field_specific_rules = field_rules
            
            # Merge with defaults
            rules = {**default_rules, **field_specific_rules}
            
            # Check length (skip for large text fields or if max_string_length is None)
            max_length = rules.get('max_string_length')
            if max_length is not None and key not in large_text_fields and len(value) > max_length:
                return False, f"Field {key} exceeds maximum length"
            
            # SQL injection check
            check_sql = rules.get('check_sql_injection', True)
            if check_sql:
                if key in url_fields:
                    # Only check for obvious SQL injection patterns in URLs (more strict)
                    dangerous_patterns = [
                        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\s+.*\bFROM\b)",
                        r"(\bUNION\s+SELECT\b)",
                        r"(\b';?\s*(--|#|/\*))",
                    ]
                    for pattern in dangerous_patterns:
                        if re.search(pattern, value, re.IGNORECASE):
                            logger.warning(f"Potential SQL injection detected in URL field {key}")
                            return False, f"Invalid characters in field {key}"
                else:
                    # For non-URL fields, use standard SQL injection checks
                    for pattern in SQL_INJECTION_PATTERNS:
                        if re.search(pattern, value, re.IGNORECASE):
                            logger.warning(f"Potential SQL injection detected in field {key}")
                            return False, f"Invalid characters in field {key}"
            
            # Check XSS (skip for extracted_text and content as they may contain HTML)
            check_xss = rules.get('check_xss', True)
            if check_xss and key not in {'extracted_text', 'content', 'body', 'text'}:
                for pattern in XSS_PATTERNS:
                    if re.search(pattern, value, re.IGNORECASE):
                        logger.warning(f"Potential XSS detected in field {key}")
                        return False, f"Invalid content in field {key}"
        
        elif isinstance(value, dict):
            # Recursively validate nested dictionaries
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
    
    Args:
        required_fields: List of required field names
        optional_fields: List of optional field names
        field_rules: Field-specific validation rules (e.g., {'url': {'check_sql_injection': False}})
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if request.method in ['POST', 'PUT', 'PATCH']:
                data = request.get_json() or {}
                
                # Check required fields
                if required_fields:
                    missing_fields = [field for field in required_fields if field not in data]
                    if missing_fields:
                        return jsonify({
                            'error': 'Missing required fields',
                            'missing_fields': missing_fields
                        }), 400
                
                # Validate all fields with field-specific rules
                is_valid, error = validate_input(data, field_rules=field_rules)
                if not is_valid:
                    return jsonify({'error': error}), 400
                
                # Sanitize string fields (but preserve extracted_text and content as-is)
                large_text_fields = {'extracted_text', 'content', 'description', 'notes', 'body', 'text'}
                for key, value in data.items():
                    if isinstance(value, str):
                        # For large text fields, only remove null bytes, don't sanitize heavily
                        if key in large_text_fields:
                            data[key] = value.replace('\x00', '')
                        else:
                            data[key] = sanitize_string(value)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

# ============================================================================
# RATE LIMITING HELPERS
# ============================================================================

def get_client_identifier():
    """
    Get unique identifier for rate limiting
    Uses user_id if authenticated, otherwise IP address
    """
    try:
        user_id = get_jwt_identity()
        if user_id:
            return f"user:{user_id}"
    except:
        pass
    
    # Fallback to IP address
    return f"ip:{request.remote_addr}"

# ============================================================================
# SECURITY HEADERS
# ============================================================================

def add_security_headers(response):
    """
    Add security headers to response
    """
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    
    # XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Content Security Policy
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https:; "
        "frame-ancestors 'none';"
    )
    
    return response

