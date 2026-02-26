# -*- coding: utf-8 -*-
"""Copyright 2025
SPDX-License-Identifier: Apache-2.0

JSON Schema validation helpers.

This module centralizes jsonschema-based validation so callers can validate
full payloads or individual field values against sub-schemas while preserving
root-schema `$ref` resolution.
"""

# Standard
from typing import Any, Dict, Optional, Tuple

# Third-Party
from jsonschema import SchemaError
from jsonschema.exceptions import ValidationError
from jsonschema.validators import validator_for


def _error_sort_key(error: ValidationError) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """Sort errors deterministically by instance path then schema path."""
    return tuple(str(part) for part in error.path), tuple(str(part) for part in error.schema_path)


def _format_error_path(error: ValidationError) -> str:
    """Format an instance path in a compact jsonpath-like style."""
    if not error.path:
        return "$"

    segments = ["$"]
    for part in error.path:
        if isinstance(part, int):
            segments.append(f"[{part}]")
        else:
            segments.append(f".{part}")
    return "".join(segments)


def _format_validation_error(error: ValidationError) -> str:
    """Format a validation error for user-facing CLI messages."""
    location = _format_error_path(error)
    if location == "$":
        return error.message
    return f"{location}: {error.message}"


def _first_validation_error_message(errors: list[ValidationError]) -> Optional[str]:
    """Return a formatted first error message when validation fails."""
    if not errors:
        return None
    return _format_validation_error(errors[0])


def _build_root_validator(schema: Dict[str, Any]) -> Any:
    """Build a jsonschema validator from a root schema."""
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)
    return validator_cls(schema)


def validate_schema(schema: Dict[str, Any]) -> Optional[str]:
    """Validate a JSON Schema without validating a specific instance.

    Returns:
        A user-facing error message when invalid, otherwise ``None``.
    """
    if not isinstance(schema, dict):
        return "Input schema must be a JSON object"

    try:
        _build_root_validator(schema)
        return None
    except SchemaError as exc:
        return f"Invalid JSON Schema: {exc}"
    except Exception as exc:  # pragma: no cover - defensive fallback for validator internals
        return f"Schema validation failed: {exc}"


def validate_instance(schema: Dict[str, Any], instance: Any) -> Optional[str]:
    """Validate an instance against a full schema.

    Returns:
        A user-facing error message when invalid, otherwise ``None``.
    """
    if not isinstance(schema, dict):
        return "Input schema must be a JSON object"

    try:
        validator = _build_root_validator(schema)
        errors = sorted(validator.iter_errors(instance), key=_error_sort_key)
        return _first_validation_error_message(errors)
    except SchemaError as exc:
        return f"Invalid JSON Schema: {exc}"
    except Exception as exc:  # pragma: no cover - defensive fallback for validator internals
        return f"Schema validation failed: {exc}"


def validate_instance_against_subschema(root_schema: Dict[str, Any], subschema: Dict[str, Any], instance: Any) -> Optional[str]:
    """Validate an instance against a subschema with root `$ref` context.

    Returns:
        A user-facing error message when invalid, otherwise ``None``.
    """
    if not isinstance(root_schema, dict):
        return "Input schema must be a JSON object"
    if not isinstance(subschema, dict):
        return "Input schema must be a JSON object"

    try:
        root_validator = _build_root_validator(root_schema)
        root_validator.__class__.check_schema(subschema)
        subschema_validator = root_validator.evolve(schema=subschema)
        errors = sorted(subschema_validator.iter_errors(instance), key=_error_sort_key)
        return _first_validation_error_message(errors)
    except SchemaError as exc:
        return f"Invalid JSON Schema: {exc}"
    except Exception as exc:  # pragma: no cover - defensive fallback for validator internals
        return f"Schema validation failed: {exc}"
