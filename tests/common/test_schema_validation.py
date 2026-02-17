# -*- coding: utf-8 -*-
"""Tests for cforge.common.schema_validation."""

# First-Party
from cforge.common.schema_validation import validate_instance, validate_instance_against_subschema, validate_schema


class TestSchemaValidation:
    """Tests for JSON Schema validation helpers."""

    def test_validate_schema_valid_returns_none(self) -> None:
        """Valid schemas return no error message."""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        assert validate_schema(schema) is None

    def test_validate_schema_requires_object_schema(self) -> None:
        """Non-object schemas are rejected by guard clause."""
        assert validate_schema([]) == "Input schema must be a JSON object"  # type: ignore[arg-type]

    def test_validate_schema_invalid_schema_returns_error(self) -> None:
        """Invalid JSON Schemas return a schema-error message."""
        schema = {"type": 1}
        message = validate_schema(schema)
        assert isinstance(message, str)
        assert message.startswith("Invalid JSON Schema:")

    def test_validate_instance_valid_payload(self) -> None:
        """Valid payloads return no error message."""
        schema = {
            "type": "object",
            "properties": {"age": {"type": "integer"}},
            "required": ["age"],
        }

        assert validate_instance(schema, {"age": 2}) is None

    def test_validate_instance_reports_nested_path(self) -> None:
        """Invalid nested payloads include a JSON path in the message."""
        schema = {
            "type": "object",
            "properties": {"age": {"type": "integer"}},
            "required": ["age"],
        }

        message = validate_instance(schema, {"age": "two"})
        assert isinstance(message, str)
        assert "$.age" in message
        assert "integer" in message

    def test_validate_instance_reports_root_error(self) -> None:
        """Root-level validation failures report message without a path prefix."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }

        message = validate_instance(schema, {})
        assert isinstance(message, str)
        assert "required property" in message
        assert "$." not in message

    def test_validate_instance_requires_object_schema(self) -> None:
        """Non-object schemas are rejected by guard clause."""
        assert validate_instance([], {}) == "Input schema must be a JSON object"  # type: ignore[arg-type]

    def test_validate_instance_invalid_schema_returns_error(self) -> None:
        """Invalid JSON Schemas return a schema-error message."""
        schema = {"type": 1}

        message = validate_instance(schema, "x")
        assert isinstance(message, str)
        assert message.startswith("Invalid JSON Schema:")

    def test_validate_instance_against_subschema_with_ref_context(self) -> None:
        """Subschema validation resolves local refs from the provided root schema."""
        root_schema = {
            "type": "object",
            "$defs": {"Value": {"type": "integer"}},
            "properties": {"value": {"$ref": "#/$defs/Value"}},
        }
        subschema = {"$ref": "#/$defs/Value"}

        assert validate_instance_against_subschema(root_schema, subschema, 9) is None

        message = validate_instance_against_subschema(root_schema, subschema, "nine")
        assert isinstance(message, str)
        assert "integer" in message

    def test_validate_instance_against_subschema_requires_object_inputs(self) -> None:
        """Both root schema and subschema must be JSON objects."""
        assert validate_instance_against_subschema([], {}, 1) == "Input schema must be a JSON object"  # type: ignore[arg-type]
        assert validate_instance_against_subschema({}, [], 1) == "Input schema must be a JSON object"  # type: ignore[arg-type]

    def test_validate_instance_against_subschema_invalid_schema_returns_error(self) -> None:
        """Invalid subschemas produce a schema-error message."""
        root_schema = {"type": "object"}
        subschema = {"type": 1}

        message = validate_instance_against_subschema(root_schema, subschema, "x")
        assert isinstance(message, str)
        assert message.startswith("Invalid JSON Schema:")

    def test_validate_instance_against_subschema_formats_array_index_path(self) -> None:
        """Validation messages include numeric indices for array paths."""
        root_schema = {"type": "object"}
        subschema = {"type": "array", "items": {"type": "integer"}}

        message = validate_instance_against_subschema(root_schema, subschema, [1, "bad"])
        assert isinstance(message, str)
        assert "$[1]" in message
