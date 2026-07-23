"""
Input validation middleware for API endpoints
"""
from core.logging_config import get_logger
from functools import wraps
from flask import request, jsonify

logger = get_logger(__name__)

def validate_json(schema):
    """
    Decorator to validate JSON request body against a schema dictionary.
    
    Schema format:
    {
        'field_name': {
            'type': str | int | float | bool | list | dict,
            'required': True | False,
            'min_length': int,
            'max_length': int,
            'allowed_values': list,
            'min': int | float,
            'max': int | float
        }
    }
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json()
            if not data:
                logger.debug("json_validation_failed", reason="missing_data")
                return jsonify({'error': 'Invalid or missing JSON data'}), 400
            
            errors = []
            
            for field_name, rules in schema.items():
                is_required = rules.get('required', False)
                
                if field_name not in data:
                    if is_required:
                        errors.append(f"Missing required field '{field_name}'")
                    continue
                
                value = data[field_name]
                
                # Skip validation for optional null/None values
                if value is None:
                    if is_required:
                        errors.append(f"Field '{field_name}' cannot be null")
                    continue
                
                # Type validation
                expected_type = rules.get('type')
                if expected_type and not isinstance(value, expected_type):
                    errors.append(f"Field '{field_name}' must be of type {expected_type.__name__}")
                    continue
                
                # String length validation
                if isinstance(value, str):
                    min_len = rules.get('min_length')
                    max_len = rules.get('max_length')
                    
                    if min_len and len(value) < min_len:
                        errors.append(f"Field '{field_name}' must be at least {min_len} characters")
                    if max_len and len(value) > max_len:
                        errors.append(f"Field '{field_name}' cannot exceed {max_len} characters")
                
                # Allowed values validation
                allowed = rules.get('allowed_values')
                if allowed and value not in allowed:
                    errors.append(f"Field '{field_name}' must be one of {allowed}")
                
                # Numeric min/max validation
                if isinstance(value, (int, float)):
                    min_val = rules.get('min')
                    max_val = rules.get('max')
                    
                    if min_val is not None and value < min_val:
                        errors.append(f"Field '{field_name}' is below minimum value of {min_val}")
                    if max_val is not None and value > max_val:
                        errors.append(f"Field '{field_name}' exceeds maximum value of {max_val}")
            
            if errors:
                logger.debug("json_validation_failed", errors=errors)
                return jsonify({
                    'error': 'Validation failed',
                    'details': errors
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
