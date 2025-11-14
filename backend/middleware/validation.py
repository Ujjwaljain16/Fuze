"""
Input validation middleware for API endpoints
"""
import logging
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)

def validate_json(schema):
    """
    Decorator to validate JSON request data against a schema
    
    Schema format:
    {
        'field_name': {
            'type': 'string' | 'int' | 'list' | 'dict',
            'required': bool,
            'maxlength': int,
            'minlength': int,
            'max': int,
            'min': int
        }
    }
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Invalid or missing JSON data'}), 400
            
            errors = []
            
            for field_name, field_schema in schema.items():
                field_value = data.get(field_name)
                
                # Check required fields
                if field_schema.get('required', False) and (field_value is None or field_value == ''):
                    errors.append(f"Field '{field_name}' is required")
                    continue
                
                # Skip validation if field is not provided and not required
                if field_value is None:
                    continue
                
                # Type validation
                expected_type = field_schema.get('type')
                if expected_type:
                    if expected_type == 'string' and not isinstance(field_value, str):
                        errors.append(f"Field '{field_name}' must be a string")
                        continue
                    elif expected_type == 'int' and not isinstance(field_value, int):
                        errors.append(f"Field '{field_name}' must be an integer")
                        continue
                    elif expected_type == 'list' and not isinstance(field_value, list):
                        errors.append(f"Field '{field_name}' must be a list")
                        continue
                    elif expected_type == 'dict' and not isinstance(field_value, dict):
                        errors.append(f"Field '{field_name}' must be an object")
                        continue
                
                # String length validation
                if isinstance(field_value, str):
                    maxlength = field_schema.get('maxlength')
                    minlength = field_schema.get('minlength')
                    
                    if maxlength and len(field_value) > maxlength:
                        errors.append(f"Field '{field_name}' exceeds maximum length of {maxlength}")
                    if minlength and len(field_value) < minlength:
                        errors.append(f"Field '{field_name}' is below minimum length of {minlength}")
                
                # Numeric range validation
                if isinstance(field_value, (int, float)):
                    max_val = field_schema.get('max')
                    min_val = field_schema.get('min')
                    
                    if max_val is not None and field_value > max_val:
                        errors.append(f"Field '{field_name}' exceeds maximum value of {max_val}")
                    if min_val is not None and field_value < min_val:
                        errors.append(f"Field '{field_name}' is below minimum value of {min_val}")
            
            if errors:
                return jsonify({
                    'error': 'Validation failed',
                    'details': errors
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator



