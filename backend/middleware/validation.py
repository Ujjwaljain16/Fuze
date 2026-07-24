"""
Production JSON Schema Validation Middleware for Flask
Supports strict type checking (bool vs int), nested schemas, list item validation,
regex pattern matching, custom validators, coercion, string sanitization, and extra field rejection.
"""

import re
from typing import Dict, Any, List, Optional, Tuple, Callable, Type
from functools import wraps
from flask import request, jsonify, g
from core.logging_config import get_logger

logger = get_logger(__name__)


def compile_schema(schema: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Validate and pre-compile schema rules at startup.
    Ensures regexes are pre-compiled and type definitions are valid.
    """
    if not isinstance(schema, dict):
        raise ValueError("Schema must be a dictionary")

    compiled = {}
    for field_name, rules in schema.items():
        if not isinstance(rules, dict):
            raise ValueError(f"Rules for field '{field_name}' must be a dictionary")

        field_rules = dict(rules)

        # Pre-compile regex patterns if present
        pattern = field_rules.get('pattern')
        if pattern and isinstance(pattern, str):
            field_rules['_compiled_pattern'] = re.compile(pattern)

        # Recursively compile nested schema if present
        nested_schema = field_rules.get('schema')
        if nested_schema:
            field_rules['_compiled_schema'] = compile_schema(nested_schema)

        compiled[field_name] = field_rules

    return compiled


def _validate_value(field_name: str, value: Any, rules: Dict[str, Any]) -> Tuple[List[str], Any]:
    """Validate and optionally coerce/strip a single field value against rules."""
    errors = []
    current_value = value

    # Coercion
    coerce_fn = rules.get('coerce')
    if coerce_fn and callable(coerce_fn) and current_value is not None:
        try:
            current_value = coerce_fn(current_value)
        except (ValueError, TypeError):
            errors.append(f"Field '{field_name}' could not be converted to {coerce_fn.__name__}")
            return errors, current_value

    # Type validation
    expected_type = rules.get('type')
    if expected_type:
        # Strict boolean vs integer check (since bool is subclass of int in Python)
        if expected_type is int:
            if type(current_value) is not int:
                errors.append(f"Field '{field_name}' must be of type int")
                return errors, current_value
        elif expected_type is bool:
            if type(current_value) is not bool:
                errors.append(f"Field '{field_name}' must be of type bool")
                return errors, current_value
        else:
            if not isinstance(current_value, expected_type):
                type_name = getattr(expected_type, '__name__', str(expected_type))
                errors.append(f"Field '{field_name}' must be of type {type_name}")
                return errors, current_value

    # String validation & sanitization
    if isinstance(current_value, str):
        if rules.get('strip', True):
            current_value = current_value.strip()

        min_len = rules.get('min_length')
        if min_len is not None and len(current_value) < min_len:
            errors.append(f"Field '{field_name}' must be at least {min_len} characters")

        max_len = rules.get('max_length')
        if max_len is not None and len(current_value) > max_len:
            errors.append(f"Field '{field_name}' cannot exceed {max_len} characters")

        compiled_pattern = rules.get('_compiled_pattern')
        if compiled_pattern and not compiled_pattern.search(current_value):
            errors.append(f"Field '{field_name}' does not match required pattern")

    # Numeric min/max validation
    if isinstance(current_value, (int, float)) and type(current_value) is not bool:
        min_val = rules.get('min')
        if min_val is not None and current_value < min_val:
            errors.append(f"Field '{field_name}' is below minimum value of {min_val}")

        max_val = rules.get('max')
        if max_val is not None and current_value > max_val:
            errors.append(f"Field '{field_name}' exceeds maximum value of {max_val}")

    # Allowed values validation
    allowed = rules.get('allowed_values')
    if allowed is not None and current_value not in allowed:
        errors.append(f"Field '{field_name}' must be one of {allowed}")

    # List item validation
    if isinstance(current_value, list) and 'item_type' in rules:
        item_type = rules['item_type']
        for i, item in enumerate(current_value):
            if item_type is int:
                if type(item) is not int:
                    errors.append(f"Item at index {i} in list '{field_name}' must be of type int")
            elif item_type is bool:
                if type(item) is not bool:
                    errors.append(f"Item at index {i} in list '{field_name}' must be of type bool")
            elif not isinstance(item, item_type):
                type_name = getattr(item_type, '__name__', str(item_type))
                errors.append(f"Item at index {i} in list '{field_name}' must be of type {type_name}")

    # Nested dictionary validation
    if isinstance(current_value, dict) and '_compiled_schema' in rules:
        nested_errors, sanitized_nested = _validate_dict(
            current_value,
            rules['_compiled_schema'],
            allow_extra_fields=rules.get('allow_extra_fields', False),
            field_prefix=f"{field_name}."
        )
        errors.extend(nested_errors)
        current_value = sanitized_nested

    # Custom validator function
    custom_validator = rules.get('validator')
    if custom_validator and callable(custom_validator):
        valid, msg = custom_validator(current_value)
        if not valid:
            errors.append(msg or f"Field '{field_name}' failed custom validation")

    return errors, current_value


def _validate_dict(
    data: Dict[str, Any],
    compiled_schema: Dict[str, Dict[str, Any]],
    allow_extra_fields: bool = False,
    field_prefix: str = ""
) -> Tuple[List[str], Dict[str, Any]]:
    """Recursively validate a dictionary against a pre-compiled schema."""
    errors = []
    sanitized_data = dict(data)

    # Check extra fields if prohibited
    if not allow_extra_fields:
        extra_fields = set(data.keys()) - set(compiled_schema.keys())
        if extra_fields:
            for extra in sorted(extra_fields):
                errors.append(f"Unexpected field '{field_prefix}{extra}' in JSON payload")

    for field_name, rules in compiled_schema.items():
        full_field_name = f"{field_prefix}{field_name}"
        is_required = rules.get('required', False)

        if field_name not in data:
            if is_required:
                errors.append(f"Missing required field '{full_field_name}'")
            continue

        value = data[field_name]

        if value is None:
            if is_required:
                errors.append(f"Field '{full_field_name}' cannot be null")
            continue

        field_errors, sanitized_val = _validate_value(full_field_name, value, rules)
        errors.extend(field_errors)
        sanitized_data[field_name] = sanitized_val

    return errors, sanitized_data


def validate_json(schema: Dict[str, Dict[str, Any]], allow_extra_fields: bool = True):
    """
    Decorator to validate JSON request payload against a schema dictionary.

    Args:
        schema: Field rules dictionary
        allow_extra_fields: If False, rejects requests containing extra un-declared fields
    """
    compiled_schema = compile_schema(schema)

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json(silent=True)

            if data is None:
                logger.debug("json_validation_failed", extra={"reason": "missing_or_invalid_json"})
                return jsonify({'error': 'Invalid or missing JSON data'}), 400

            if not isinstance(data, dict):
                logger.debug("json_validation_failed", extra={"reason": "payload_not_a_json_object"})
                return jsonify({'error': 'JSON payload must be an object'}), 400

            errors, sanitized_data = _validate_dict(data, compiled_schema, allow_extra_fields=allow_extra_fields)

            if errors:
                logger.debug("json_validation_failed", extra={"error_count": len(errors)})
                return jsonify({
                    'error': 'Validation failed',
                    'details': errors
                }), 400

            g.validated_data = sanitized_data
            return f(*args, **kwargs)
        return decorated_function
    return decorator
