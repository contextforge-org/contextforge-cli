# -*- coding: utf-8 -*-
"""Tests for cforge.common.prompting."""

# Standard
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from unittest.mock import patch

# Third-Party
from pydantic import BaseModel, Field
import pytest

# First-Party
from cforge.common.errors import CLIError
from cforge.common.prompting import (
    _build_pydantic_field_schema,
    _infer_schema_type,
    _INT_SENTINEL_DEFAULT,
    prompt_for_json_schema,
    prompt_for_schema,
    _resolve_effective_schema,
    _resolve_ref_schema,
    _resolve_schema_type,
    _schema_contains_ref,
    _unwrap_optional_annotation,
)


class TestPromptForSchema:
    """Tests for prompt_for_schema function."""

    def test_prompt_with_prefilled_values(self, mock_console) -> None:
        """Test that prefilled values are used and not prompted."""

        class TestSchema(BaseModel):
            name: str
            description: str

        prefilled = {"name": "test_name", "description": "test_desc"}

        result = prompt_for_schema(TestSchema, prefilled=prefilled)

        # Should return prefilled values without prompting
        assert result == prefilled
        # Console should show the prefilled values
        assert mock_console.print.call_count >= 3  # Header + 2 fields

    def test_prompt_with_prefilled_datetime_and_none(self, mock_console) -> None:
        """Prefilled non-string values should not be rejected by prompt schema validation."""

        class TestSchema(BaseModel):
            name: str
            created_at: datetime
            last_used: Optional[datetime] = None

        prefilled = {"name": "test", "created_at": datetime.now(), "last_used": None}

        result = prompt_for_schema(TestSchema, prefilled=prefilled)

        assert result == prefilled

    def test_prompt_skips_internal_fields(self, mock_console) -> None:
        """Test that internal fields are skipped."""

        class TestSchema(BaseModel):
            name: str
            model_config: dict = {}  # Should be skipped
            auth_value: str = ""  # Should be skipped

        prefilled = {"name": "test"}

        result = prompt_for_schema(TestSchema, prefilled=prefilled)

        # Should only have the name field
        assert "name" in result
        assert "model_config" not in result
        assert "auth_value" not in result

    def test_prompt_with_string_field(self, mock_console) -> None:
        """Test prompting for string fields."""

        class TestSchema(BaseModel):
            name: str = Field(description="The name")

        with patch("typer.prompt", return_value="user_input"):
            result = prompt_for_schema(TestSchema)

            assert result["name"] == "user_input"

    def test_prompt_with_optional_field(self, mock_console) -> None:
        """Test prompting for optional fields."""

        class TestSchema(BaseModel):
            required_field: str
            optional_field: Optional[str] = None

        with patch("typer.prompt", side_effect=["required_value", ""]):
            result = prompt_for_schema(TestSchema)

            assert result["required_field"] == "required_value"
            # Optional field with empty input should not be in result
            assert "optional_field" not in result or result["optional_field"] == ""

    def test_prompt_with_bool_field(self, mock_console) -> None:
        """Test prompting for boolean fields."""

        class TestSchema(BaseModel):
            enabled: bool

        with patch("typer.confirm", return_value=True):
            with patch("typer.prompt", return_value=True):
                result = prompt_for_schema(TestSchema)

                assert result["enabled"] is True

    def test_prompt_with_optional_bool_field_declined(self, mock_console) -> None:
        """Test prompting for optional boolean field that is declined."""

        class TestSchema(BaseModel):
            enabled: Optional[bool] = None

        # First confirm returns False (don't include field)
        with patch("typer.confirm", return_value=False):
            result = prompt_for_schema(TestSchema)

            # Field should not be in result when declined
            assert "enabled" not in result

    def test_prompt_with_int_field(self, mock_console) -> None:
        """Test prompting for integer fields."""

        class TestSchema(BaseModel):
            count: int

        with patch("typer.prompt", return_value=42):
            result = prompt_for_schema(TestSchema)

            assert result["count"] == 42

    def test_prompt_with_int_field_empty_input(self, mock_console) -> None:
        """Test prompting for optional integer field with empty input."""

        class TestSchema(BaseModel):
            count: Optional[int] = None

        # Return sentinel to simulate skipping optional field
        with patch("typer.prompt", return_value=_INT_SENTINEL_DEFAULT):
            result = prompt_for_schema(TestSchema)

            # Field should not be in result when empty
            assert "count" not in result

    def test_prompt_with_list_field(self, mock_console) -> None:
        """Test prompting for list fields."""

        class TestSchema(BaseModel):
            tags: List[str]

        with patch("typer.prompt", return_value="tag1, tag2, tag3"):
            result = prompt_for_schema(TestSchema)

            assert result["tags"] == ["tag1", "tag2", "tag3"]

    def test_prompt_with_list_field_empty(self, mock_console) -> None:
        """Test prompting for list fields with empty input."""

        class TestSchema(BaseModel):
            tags: Optional[List[str]] = None

        with patch("typer.prompt", return_value=""):
            result = prompt_for_schema(TestSchema)

            # Empty input for list should not add the field
            assert "tags" not in result or result.get("tags") is None

    def test_prompt_dict_str_str(self, mock_console) -> None:
        """Test prompting for a string to string dict"""

        class TestSchema(BaseModel):
            key: Dict[str, str]

        with patch("typer.confirm", side_effect=["y", "y", ""]), patch("typer.prompt", side_effect=["k1", "v1", "k2", "v2"]):
            result = prompt_for_schema(TestSchema)

            # Empty input for list should not add the field
            assert result == {
                "key": {"k1": "v1", "k2": "v2"},
            }

    def test_prompt_with_nested_dicts(self, mock_console) -> None:
        """Test prompting for a nested dict with dict values"""

        class SubSchema(BaseModel):
            num: int

        class TestSchema(BaseModel):
            key: Dict[str, Any]
            sub: SubSchema
            sub_dict: Dict[str, SubSchema]

        with patch("typer.confirm", side_effect=["y", "y", "", "y", ""]), patch("typer.prompt", side_effect=["k1", '{"foo": 1}', "k2", "[1, 2, 3]", 42, "a-num", 123]):
            result = prompt_for_schema(TestSchema)

            # Empty input for list should not add the field
            assert result == {
                "key": {"k1": {"foo": 1}, "k2": [1, 2, 3]},
                "sub": {"num": 42},
                "sub_dict": {"a-num": {"num": 123}},
            }

    def test_prompt_list_of_sub_models(self, mock_console) -> None:
        """Test prompting for a list of sub pydantic models"""

        class SubSchema(BaseModel):
            num: int

        class TestSchema(BaseModel):
            nums: List[SubSchema]

        with patch("typer.confirm", side_effect=["y", "y", ""]), patch("typer.prompt", side_effect=[1, 2]):
            result = prompt_for_schema(TestSchema)

            # Empty input for list should not add the field
            assert result == {"nums": [{"num": 1}, {"num": 2}]}

    def test_prompt_with_default(self, mock_console) -> None:
        """Test prompting with defaults and make sure prompt string added."""

        class TestSchema(BaseModel):
            name: str = "foobar"
            some_val: int = 42

        with patch("typer.prompt", side_effect=["", 42]) as prompt_mock:
            prompt_for_schema(TestSchema)
            assert prompt_mock.call_count == 2
            assert prompt_mock.call_args_list[0][1]["default"] == "foobar"
            assert prompt_mock.call_args_list[1][1]["default"] == 42
            assert any("foobar" in call[0][0] for call in mock_console.print.call_args_list)
            assert any("42" in call[0][0] for call in mock_console.print.call_args_list)

    def test_prompt_missing_required_string(self, mock_console) -> None:
        """Test that an exception is raised if a required string is unset."""

        class TestSchema(BaseModel):
            foo: str

        with patch("typer.prompt", return_value=""):
            with pytest.raises(CLIError):
                prompt_for_schema(TestSchema)


class TestPromptForJsonSchema:
    """Tests for prompt_for_json_schema function."""

    def test_prompt_for_json_schema_required_only_with_prefilled(self, mock_console) -> None:
        """Test prompting only missing required fields when prefilled data exists."""
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        }
        prefilled = {"limit": 10}

        with patch("typer.prompt", return_value="search term") as mock_prompt:
            result = prompt_for_json_schema(schema, prefilled=prefilled, prompt_optional=False)

        assert result["query"] == "search term"
        assert result["limit"] == 10
        assert mock_prompt.call_count == 1

    def test_prompt_for_json_schema_skips_optional_fields_when_required_only(self, mock_console) -> None:
        """Test optional fields are skipped entirely in required-only mode."""
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
        }

        with patch("typer.prompt") as mock_prompt:
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {}
        mock_prompt.assert_not_called()

    def test_prompt_for_json_schema_prompts_optional_fields(self, mock_console) -> None:
        """Test optional fields are prompted in full interactive mode."""
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
        }

        with patch("typer.prompt", return_value="search term"):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result["query"] == "search term"

    def test_prompt_for_json_schema_prefilled_nested_object_prompts_missing_required(self, mock_console) -> None:
        """Test nested required fields are prompted when parent object is prefilled."""
        schema = {
            "type": "object",
            "properties": {
                "config": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "timeout": {"type": "integer"},
                    },
                    "required": ["name"],
                }
            },
            "required": ["config"],
        }
        prefilled = {"config": {"timeout": 30}}

        with patch("typer.prompt", return_value="tool-name") as mock_prompt:
            result = prompt_for_json_schema(schema, prefilled=prefilled, prompt_optional=False)

        assert result == {"config": {"timeout": 30, "name": "tool-name"}}
        assert mock_prompt.call_count == 1

    def test_prompt_for_json_schema_requires_object_schema(self, mock_console) -> None:
        """Test non-object root schema raises a CLIError."""
        schema = {"type": "string"}

        with pytest.raises(CLIError):
            prompt_for_json_schema(schema)

    def test_prompt_for_json_schema_resolves_ref_object(self, mock_console) -> None:
        """Test object fields referenced via $ref are prompted as objects."""
        schema = {
            "type": "object",
            "$defs": {
                "NestedArgs": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                    "required": ["name"],
                }
            },
            "properties": {
                "config": {"$ref": "#/$defs/NestedArgs"},
            },
            "required": ["config"],
        }

        with patch("typer.prompt", return_value="nested-name") as mock_prompt:
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"config": {"name": "nested-name"}}
        assert mock_prompt.call_count == 1

    def test_prompt_for_json_schema_resolves_ref_array(self, mock_console) -> None:
        """Test array fields referenced via $ref are prompted as arrays."""
        schema = {
            "type": "object",
            "$defs": {
                "TagList": {
                    "type": "array",
                    "items": {"type": "string"},
                }
            },
            "properties": {
                "tags": {"$ref": "#/$defs/TagList"},
            },
            "required": ["tags"],
        }

        with patch("typer.confirm", side_effect=[True, True, False]), patch("typer.prompt", side_effect=["one", "two"]):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"tags": ["one", "two"]}

    def test_prompt_for_json_schema_missing_ref_raises(self, mock_console) -> None:
        """Test missing local $ref path raises a CLIError."""
        schema = {
            "type": "object",
            "$defs": {},
            "properties": {
                "config": {"$ref": "#/$defs/DoesNotExist"},
            },
            "required": ["config"],
        }

        with pytest.raises(CLIError, match="Schema reference not found"):
            prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_external_ref_raises(self, mock_console) -> None:
        """Test non-local $ref values are rejected."""
        schema = {
            "type": "object",
            "properties": {
                "config": {"$ref": "https://example.com/schema.json#/$defs/Config"},
            },
            "required": ["config"],
        }

        with pytest.raises(CLIError, match="Only local schema references are supported"):
            prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_cyclic_ref_raises(self, mock_console) -> None:
        """Test cyclic $ref graphs raise a CLIError."""
        schema = {
            "type": "object",
            "$defs": {
                "Node": {"$ref": "#/$defs/Node"},
            },
            "properties": {
                "node": {"$ref": "#/$defs/Node"},
            },
            "required": ["node"],
        }

        with pytest.raises(CLIError, match="Cyclic schema reference detected"):
            prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_non_object_input_schema_raises(self, mock_console) -> None:
        """Test non-dictionary schemas are rejected."""
        with pytest.raises(CLIError, match="Input schema must be a JSON object"):
            prompt_for_json_schema(["not", "an", "object"])  # type: ignore[arg-type]

    def test_prompt_for_json_schema_non_object_prefilled_raises(self, mock_console) -> None:
        """Test non-dictionary prefilled payloads are rejected."""
        schema = {
            "type": "object",
            "properties": {"query": {"type": "string"}},
        }

        with pytest.raises(CLIError, match="Prefilled input must be a JSON object"):
            prompt_for_json_schema(schema, prefilled=["bad"])  # type: ignore[arg-type]

    def test_prompt_for_json_schema_ref_resolving_to_scalar_raises(self, mock_console) -> None:
        """Test $ref pointers resolving to scalar nodes are rejected."""
        schema = {
            "type": "object",
            "$defs": {
                "Config": {
                    "type": "object",
                    "properties": {"kind": {"type": "string"}},
                }
            },
            "properties": {
                "config": {"$ref": "#/$defs/Config/type"},
            },
            "required": ["config"],
        }

        with pytest.raises(CLIError, match="does not resolve to an object schema"):
            prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_ref_invalid_array_index_raises(self, mock_console) -> None:
        """Test invalid array indexes in local $ref pointers are rejected."""
        schema = {
            "type": "object",
            "$defs": {
                "Variants": [{"type": "string"}],
            },
            "properties": {
                "value": {"$ref": "#/$defs/Variants/not-an-index"},
            },
            "required": ["value"],
        }

        with pytest.raises(CLIError, match="Invalid array index in schema reference"):
            prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_handles_nullable_integer_type_lists(self, mock_console) -> None:
        """Test `type` lists like [null, integer] prompt using the concrete type."""
        schema = {
            "type": "object",
            "properties": {
                "limit": {"type": ["null", "integer"]},
            },
            "required": ["limit"],
        }

        with patch("typer.prompt", return_value=7):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"limit": 7}

    def test_prompt_for_json_schema_handles_nullable_integer_any_of(self, mock_console) -> None:
        """Test anyOf nullable integers prompt using integer type instead of string fallback."""
        schema = {
            "type": "object",
            "properties": {
                "limit": {
                    "anyOf": [{"type": "null"}, {"type": "integer"}],
                },
            },
            "required": ["limit"],
        }

        with patch("typer.prompt", return_value=7) as mock_prompt:
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"limit": 7}
        assert mock_prompt.call_args.kwargs.get("type") is int

    def test_prompt_for_json_schema_handles_one_of_object_with_null(self, mock_console) -> None:
        """Test oneOf object/null schemas prompt nested object fields."""
        schema = {
            "type": "object",
            "properties": {
                "config": {
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                            "required": ["name"],
                        },
                        {"type": "null"},
                    ]
                },
            },
            "required": ["config"],
        }

        with patch("typer.prompt", return_value="alpha"):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"config": {"name": "alpha"}}

    def test_prompt_for_json_schema_handles_any_of_array_with_null(self, mock_console) -> None:
        """Test anyOf array/null schemas are prompted as arrays."""
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "anyOf": [
                        {"type": "null"},
                        {"type": "array", "items": {"type": "string"}},
                    ]
                },
            },
            "required": ["tags"],
        }

        with patch("typer.confirm", side_effect=[True, False]), patch("typer.prompt", return_value="tag-one"):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"tags": ["tag-one"]}

    def test_prompt_for_json_schema_handles_one_of_integer_or_string_string_value(self, mock_console) -> None:
        """Test oneOf with multiple non-null variants accepts valid string input."""
        schema = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [{"type": "integer"}, {"type": "string"}],
                },
            },
            "required": ["value"],
        }

        with patch("typer.prompt", return_value="alpha"):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"value": "alpha"}

    def test_prompt_for_json_schema_handles_one_of_integer_or_string_integer_value(self, mock_console) -> None:
        """Test oneOf with multiple non-null variants accepts parsed integer input."""
        schema = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [{"type": "integer"}, {"type": "string"}],
                },
            },
            "required": ["value"],
        }

        with patch("typer.prompt", return_value="7"):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"value": 7}

    def test_prompt_for_json_schema_handles_type_array_integer_or_string_string_value(self, mock_console) -> None:
        """Test type-array unions accept valid string input."""
        schema = {
            "type": "object",
            "properties": {
                "value": {
                    "type": ["integer", "string"],
                },
            },
            "required": ["value"],
        }

        with patch("typer.prompt", return_value="alpha"):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"value": "alpha"}

    def test_prompt_for_json_schema_handles_type_array_integer_or_string_integer_value(self, mock_console) -> None:
        """Test type-array unions accept parsed integer input."""
        schema = {
            "type": "object",
            "properties": {
                "value": {
                    "type": ["integer", "string"],
                },
            },
            "required": ["value"],
        }

        with patch("typer.prompt", return_value="12"):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"value": 12}

    def test_prompt_for_json_schema_multi_variant_union_rejects_unmatched_type(self, mock_console) -> None:
        """Test union prompts reject values that do not match any variant types."""
        schema = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [{"type": "integer"}, {"type": "boolean"}],
                },
            },
            "required": ["value"],
        }

        with patch("typer.prompt", return_value="alpha"):
            with pytest.raises(CLIError, match="Field 'value' is invalid"):
                prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_object_union_requires_branch_fields(self, mock_console) -> None:
        """Test object unions reject payloads that satisfy no branch required fields."""
        schema = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [
                        {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
                        {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
                    ]
                },
            },
            "required": ["value"],
        }

        with patch("typer.prompt", return_value="{}"):
            with pytest.raises(CLIError, match="Field 'value' is invalid"):
                prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_object_union_accepts_matching_branch(self, mock_console) -> None:
        """Test object unions accept a payload matching one branch schema."""
        schema = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [
                        {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
                        {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
                    ]
                },
            },
            "required": ["value"],
        }

        with patch("typer.prompt", return_value='{"name":"alpha"}'):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"value": {"name": "alpha"}}

    def test_prompt_for_json_schema_discriminated_union_const_accepts_matching_branch(self, mock_console) -> None:
        """Test oneOf discriminator branches using const validate correctly."""
        schema = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {
                                "kind": {"const": "a"},
                                "count": {"type": "integer"},
                            },
                            "required": ["kind", "count"],
                        },
                        {
                            "type": "object",
                            "properties": {
                                "kind": {"const": "b"},
                                "name": {"type": "string"},
                            },
                            "required": ["kind", "name"],
                        },
                    ]
                },
            },
            "required": ["value"],
        }

        with patch("typer.prompt", return_value='{"kind":"a","count":1}'):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"value": {"kind": "a", "count": 1}}

    def test_prompt_for_json_schema_discriminated_union_const_rejects_invalid_discriminator(self, mock_console) -> None:
        """Test oneOf discriminator branches reject unmatched const values."""
        schema = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {
                                "kind": {"const": "a"},
                                "count": {"type": "integer"},
                            },
                            "required": ["kind", "count"],
                        },
                        {
                            "type": "object",
                            "properties": {
                                "kind": {"const": "b"},
                                "name": {"type": "string"},
                            },
                            "required": ["kind", "name"],
                        },
                    ]
                },
            },
            "required": ["value"],
        }

        with patch("typer.prompt", return_value='{"kind":"c","count":1}'):
            with pytest.raises(CLIError, match="Field 'value' is invalid"):
                prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_union_optional_blank_skips_field(self, mock_console) -> None:
        """Test optional union fields are skipped when blank input is provided."""
        schema = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [{"type": "integer"}, {"type": "string"}],
                    "default": {"nested": 1},
                },
            },
        }

        with patch("typer.prompt", return_value=""):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {}

    def test_prompt_for_json_schema_union_required_blank_raises(self, mock_console) -> None:
        """Test required union fields reject blank input."""
        schema = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [{"type": "integer"}, {"type": "string"}],
                    "default": {"nested": 1},
                },
            },
            "required": ["value"],
        }

        with patch("typer.prompt", return_value=""):
            with pytest.raises(CLIError, match="Field 'value' is required"):
                prompt_for_json_schema(schema, prompt_optional=False)

    def test_resolve_effective_schema_preserves_multi_variant_union(self) -> None:
        """Test effective schema resolver does not collapse multi-variant unions."""
        schema = {
            "oneOf": [{"type": "integer"}, {"type": "string"}],
            "description": "multi-type",
        }

        result = _resolve_effective_schema({}, schema)

        assert "oneOf" in result
        assert result["description"] == "multi-type"

    def test_resolve_schema_type_type_list_multiple_non_null_returns_union(self) -> None:
        """Test type lists with multiple non-null entries resolve to union."""
        schema = {"type": ["integer", "string", "null"]}
        assert _resolve_schema_type({}, schema) == "union"

    def test_resolve_effective_schema_recursive_any_of_ref_does_not_raise(self) -> None:
        """Test recursive anyOf refs are handled without recursion errors."""
        schema = {
            "type": "object",
            "$defs": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "next": {
                            "anyOf": [{"type": "null"}, {"$ref": "#/$defs/Node"}],
                        }
                    },
                }
            },
            "properties": {"node": {"$ref": "#/$defs/Node"}},
            "required": ["node"],
        }
        next_schema = schema["$defs"]["Node"]["properties"]["next"]

        result = _resolve_effective_schema(schema, next_schema)
        assert isinstance(result, dict)

    def test_resolve_effective_schema_preserves_nullable_recursive_ref_branch(self) -> None:
        """Test nullable combinator is not collapsed when non-null branch is recursive."""
        schema = {
            "type": "object",
            "$defs": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "next": {
                            "anyOf": [{"type": "null"}, {"$ref": "#/$defs/Node"}],
                        }
                    },
                    "required": ["next"],
                }
            },
            "properties": {
                "next": {
                    "anyOf": [{"type": "null"}, {"$ref": "#/$defs/Node"}],
                }
            },
            "required": ["next"],
        }

        next_schema = schema["properties"]["next"]
        result = _resolve_effective_schema(schema, next_schema)

        assert "anyOf" in result
        assert isinstance(result["anyOf"], list)

    def test_resolve_schema_type_recursive_nullable_ref_returns_union(self) -> None:
        """Test recursive nullable refs resolve to union type for prompting."""
        schema = {
            "type": "object",
            "$defs": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "next": {
                            "anyOf": [{"type": "null"}, {"$ref": "#/$defs/Node"}],
                        }
                    },
                    "required": ["next"],
                }
            },
            "properties": {
                "next": {
                    "anyOf": [{"type": "null"}, {"$ref": "#/$defs/Node"}],
                }
            },
            "required": ["next"],
        }

        next_schema = schema["properties"]["next"]
        assert _resolve_schema_type(schema, next_schema) == "union"

    def test_resolve_schema_type_non_recursive_nullable_ref_returns_inner_type(self) -> None:
        """Test nullable non-recursive refs resolve to their concrete type."""
        schema = {
            "type": "object",
            "$defs": {
                "Value": {"type": "integer"},
            },
            "properties": {
                "value": {"anyOf": [{"type": "null"}, {"$ref": "#/$defs/Value"}]},
            },
            "required": ["value"],
        }

        value_schema = schema["properties"]["value"]
        assert _resolve_schema_type(schema, value_schema) == "integer"

    def test_prompt_for_json_schema_recursive_nullable_required_field_accepts_null(self, mock_console) -> None:
        """Test recursive nullable required fields prompt as union and accept explicit null."""
        schema = {
            "type": "object",
            "$defs": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "next": {
                            "anyOf": [{"type": "null"}, {"$ref": "#/$defs/Node"}],
                        }
                    },
                    "required": ["next"],
                }
            },
            "properties": {
                "next": {
                    "anyOf": [{"type": "null"}, {"$ref": "#/$defs/Node"}],
                }
            },
            "required": ["next"],
        }

        with patch("typer.prompt", return_value="null"):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"next": None}

    def test_resolve_effective_schema_non_dict_input_returns_empty_schema(self) -> None:
        """Test effective schema resolver returns empty schema for non-dict input."""
        assert _resolve_effective_schema({}, "not-a-schema") == {}  # type: ignore[arg-type]

    def test_resolve_schema_type_non_dict_input_defaults_to_string(self) -> None:
        """Test schema type resolver defaults to string for non-dict inputs."""
        assert _resolve_schema_type({}, "not-a-schema") == "string"  # type: ignore[arg-type]

    def test_resolve_schema_type_ref_updates_resolution_stack(self) -> None:
        """Test schema type resolver handles non-cyclic refs via resolving stack."""
        schema = {"$defs": {"Value": {"type": "integer"}}}
        ref_schema = {"$ref": "#/$defs/Value"}
        assert _resolve_schema_type(schema, ref_schema) == "integer"

    def test_resolve_effective_schema_ref_cycle_guard_returns_original_ref_schema(self) -> None:
        """Test effective schema resolver short-circuits on repeated ref in stack."""
        schema = {"$defs": {"Loop": {"type": "string"}}}
        ref_schema = {"$ref": "#/$defs/Loop"}
        assert _resolve_effective_schema(schema, ref_schema, resolving_refs=("#/$defs/Loop",)) == ref_schema

    def test_resolve_schema_type_ref_cycle_guard_returns_union(self) -> None:
        """Test schema type resolver short-circuits repeated refs as union."""
        schema = {"$defs": {"Loop": {"type": "string"}}}
        ref_schema = {"$ref": "#/$defs/Loop"}
        assert _resolve_schema_type(schema, ref_schema, resolving_refs=("#/$defs/Loop",)) == "union"

    def test_infer_schema_type_required_without_properties_returns_object(self) -> None:
        """Test direct required-key inference resolves to object."""
        assert _infer_schema_type({"required": ["id"]}) == "object"

    def test_resolve_effective_schema_can_skip_nullable_collapse(self) -> None:
        """Test caller can preserve nullable combinator wrappers."""
        schema = {
            "anyOf": [{"type": "null"}, {"type": "integer"}],
            "description": "nullable value",
        }

        result = _resolve_effective_schema({}, schema, collapse_nullable=False)

        assert "anyOf" in result
        assert result["description"] == "nullable value"

    def test_schema_contains_ref_non_dict_returns_false(self) -> None:
        """Test ref search helper returns false for non-dict input."""
        assert not _schema_contains_ref("not-a-schema", "#/$defs/Node")  # type: ignore[arg-type]

    def test_schema_contains_ref_handles_self_referential_schema(self) -> None:
        """Test ref search helper avoids infinite loops on self-referential dicts."""
        recursive_schema: Dict[str, Any] = {}
        recursive_schema["self"] = recursive_schema
        assert not _schema_contains_ref(recursive_schema, "#/$defs/Node")

    def test_schema_contains_ref_list_without_dicts_continues_search(self) -> None:
        """Test ref search helper continues after list entries without dict values."""
        schema = {
            "items": [1, "x", True],
            "next": {"$ref": "#/$defs/Node"},
        }
        assert _schema_contains_ref(schema, "#/$defs/Node")

    def test_prompt_for_json_schema_ref_index_out_of_bounds_raises(self, mock_console) -> None:
        """Test out-of-bounds array indexes in local $ref pointers are rejected."""
        schema = {
            "type": "object",
            "$defs": {
                "Variants": [{"type": "string"}],
            },
            "properties": {
                "value": {"$ref": "#/$defs/Variants/1"},
            },
            "required": ["value"],
        }

        with pytest.raises(CLIError, match="Schema reference index out of bounds"):
            prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_ref_valid_array_index_resolves(self, mock_console) -> None:
        """Test valid array indexes in local $ref pointers resolve correctly."""
        schema = {
            "type": "object",
            "x-variants": [
                {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                }
            ],
            "properties": {
                "value": {"$ref": "#/x-variants/0"},
            },
            "required": ["value"],
        }

        with patch("typer.prompt", return_value="selected"):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"value": {"name": "selected"}}

    def test_prompt_for_json_schema_ref_path_invalid_raises(self, mock_console) -> None:
        """Test local $ref traversal fails on invalid scalar path traversal."""
        schema = {
            "type": "object",
            "$defs": {
                "Scalar": 1,
            },
            "properties": {
                "value": {"$ref": "#/$defs/Scalar/child"},
            },
            "required": ["value"],
        }

        with pytest.raises(CLIError, match="Schema reference path is invalid"):
            prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_nested_with_non_empty_indent(self, mock_console) -> None:
        """Test nested prompting works with a non-empty root indent."""
        schema = {
            "type": "object",
            "properties": {
                "config": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                    "required": ["name"],
                }
            },
            "required": ["config"],
        }

        with patch("typer.prompt", return_value="nested-name"):
            result = prompt_for_json_schema(schema, indent="|", prompt_optional=False)

        assert result == {"config": {"name": "nested-name"}}

    def test_prompt_for_json_schema_fallback_title_and_prompt_text_metadata(self, mock_console) -> None:
        """Test fallback display title and prompt metadata formatting branches."""
        schema = {
            "type": "object",
            "title": "",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                    "default": "seed",
                }
            },
            "required": ["query"],
        }

        with patch("typer.prompt", return_value="manual"):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"query": "manual"}

    def test_prompt_for_json_schema_optional_object_decline(self, mock_console) -> None:
        """Test optional object fields can be skipped."""
        schema = {
            "type": "object",
            "properties": {
                "config": {
                    "properties": {
                        "name": {"type": "string"},
                    },
                }
            },
        }

        with patch("typer.confirm", return_value=False):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {}

    def test_prompt_for_json_schema_optional_object_included(self, mock_console) -> None:
        """Test optional object fields can be included and prompted."""
        schema = {
            "type": "object",
            "properties": {
                "config": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                    "required": ["name"],
                }
            },
        }

        with patch("typer.confirm", return_value=True), patch("typer.prompt", return_value="chosen"):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {"config": {"name": "chosen"}}

    def test_prompt_for_json_schema_object_inferred_from_required_keyword(self, mock_console) -> None:
        """Test object type inference from `required` when `type` is missing."""
        schema = {
            "type": "object",
            "properties": {
                "meta": {
                    "properties": {"id": {"type": "string"}},
                    "required": ["id"],
                }
            },
            "required": ["meta"],
        }

        with patch("typer.prompt", return_value="abc"):
            result = prompt_for_json_schema(schema, prompt_optional=False)
        assert result == {"meta": {"id": "abc"}}

    def test_prompt_for_json_schema_optional_array_inferred_and_declined(self, mock_console) -> None:
        """Test optional arrays inferred from `items` can be skipped."""
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "items": {"type": "string"},
                }
            },
        }

        with patch("typer.confirm", return_value=False):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {}

    def test_prompt_for_json_schema_type_list_non_string_falls_back_to_items(self, mock_console) -> None:
        """Test invalid type-list schemas are rejected by JSON Schema validation."""
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": [1],
                    "items": {"type": "string"},
                }
            },
        }

        with patch("typer.confirm", return_value=False):
            with pytest.raises(CLIError, match="Invalid JSON Schema"):
                prompt_for_json_schema(schema, prompt_optional=True)

    def test_prompt_for_json_schema_optional_array_include_no_entries(self, mock_console) -> None:
        """Test optional arrays can be included with no entries."""
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                }
            },
        }

        with patch("typer.confirm", side_effect=[True, False]):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {"tags": []}

    def test_prompt_for_json_schema_optional_array_collects_multiple_entries(self, mock_console) -> None:
        """Test array entry prompting loops correctly for multiple values."""
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "integer"},
                }
            },
        }

        with patch("typer.confirm", side_effect=[True, True, True, False]), patch("typer.prompt", side_effect=[1, 2]):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {"tags": [1, 2]}

    def test_prompt_for_json_schema_prefilled_array_of_objects_validates_entries(self, mock_console) -> None:
        """Test prefilled object-array entries recurse and remain schema-valid."""
        schema = {
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    },
                }
            },
            "required": ["rows"],
        }
        prefilled = {"rows": [{"name": "row-one"}, {"name": "row-two"}]}

        result = prompt_for_json_schema(schema, prefilled=prefilled, prompt_optional=False)
        assert result == prefilled

    def test_prompt_for_json_schema_prefilled_array_of_objects_invalid_entry_raises(self, mock_console) -> None:
        """Test invalid prefilled object-array entries fail final schema validation."""
        schema = {
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    },
                }
            },
            "required": ["rows"],
        }
        prefilled = {"rows": [{"name": "row-one"}, "raw-entry"]}

        with pytest.raises(CLIError, match="Prompted payload is invalid"):
            prompt_for_json_schema(schema, prefilled=prefilled, prompt_optional=False)

    def test_prompt_for_json_schema_prefilled_array_of_arrays_validates_entries(self, mock_console) -> None:
        """Test prefilled nested arrays recurse through nested item schemas."""
        schema = {
            "type": "object",
            "properties": {
                "matrix": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
                }
            },
            "required": ["matrix"],
        }
        prefilled = {"matrix": [[1, 2], [3]]}

        result = prompt_for_json_schema(schema, prefilled=prefilled, prompt_optional=False)
        assert result == prefilled

    def test_prompt_for_json_schema_prefilled_array_of_arrays_invalid_entry_raises(self, mock_console) -> None:
        """Test invalid prefilled nested arrays fail final schema validation."""
        schema = {
            "type": "object",
            "properties": {
                "matrix": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
                }
            },
            "required": ["matrix"],
        }
        prefilled = {"matrix": [[1, 2], 3]}

        with pytest.raises(CLIError, match="Prompted payload is invalid"):
            prompt_for_json_schema(schema, prefilled=prefilled, prompt_optional=False)

    def test_prompt_for_json_schema_enum_uses_raw_string_match(self, mock_console) -> None:
        """Test enum prompts accept raw values when JSON parsing changes type."""
        schema = {
            "type": "object",
            "properties": {
                "mode": {
                    "enum": ["1"],
                    "default": "1",
                }
            },
            "required": ["mode"],
        }

        with patch("typer.prompt", return_value="1"):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"mode": "1"}

    def test_prompt_for_json_schema_enum_uses_json_parsed_match(self, mock_console) -> None:
        """Test enum prompts accept values that match after JSON parsing."""
        schema = {
            "type": "object",
            "properties": {
                "priority": {
                    "enum": [1, 2],
                }
            },
            "required": ["priority"],
        }

        with patch("typer.prompt", return_value="1"):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"priority": 1}

    def test_prompt_for_json_schema_optional_enum_blank_is_skipped(self, mock_console) -> None:
        """Test optional enum fields are skipped when left blank."""
        schema = {
            "type": "object",
            "properties": {
                "mode": {"enum": ["enforce", "disabled"]},
            },
        }

        with patch("typer.prompt", return_value=""):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {}

    def test_prompt_for_json_schema_required_enum_blank_raises(self, mock_console) -> None:
        """Test required enum fields reject blank values."""
        schema = {
            "type": "object",
            "properties": {
                "mode": {"enum": ["enforce", "disabled"]},
            },
            "required": ["mode"],
        }

        with patch("typer.prompt", return_value=""):
            with pytest.raises(CLIError, match="Field 'mode' is required"):
                prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_invalid_enum_value_raises(self, mock_console) -> None:
        """Test invalid enum values raise a clear error."""
        schema = {
            "type": "object",
            "properties": {
                "mode": {"enum": ["enforce", "disabled"]},
            },
            "required": ["mode"],
        }

        with patch("typer.prompt", return_value="invalid"):
            with pytest.raises(CLIError, match="must be one of"):
                prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_optional_boolean_include_and_prompt(self, mock_console) -> None:
        """Test optional booleans prompt when included."""
        schema = {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "default": True,
                }
            },
        }

        with patch("typer.confirm", return_value=True), patch("typer.prompt", return_value=False):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {"enabled": False}

    def test_prompt_for_json_schema_optional_boolean_decline(self, mock_console) -> None:
        """Test optional booleans can be skipped by declining inclusion."""
        schema = {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                }
            },
        }

        with patch("typer.confirm", return_value=False):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {}

    def test_prompt_for_json_schema_required_boolean_prompts_directly(self, mock_console) -> None:
        """Test required booleans prompt without inclusion confirmation."""
        schema = {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                }
            },
            "required": ["enabled"],
        }

        with patch("typer.prompt", return_value=True):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"enabled": True}

    def test_prompt_for_json_schema_integer_with_default(self, mock_console) -> None:
        """Test integer prompts with integer defaults."""
        schema = {
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "default": 3,
                }
            },
            "required": ["count"],
        }

        with patch("typer.prompt", return_value=7):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"count": 7}

    def test_prompt_for_json_schema_required_integer_sentinel_raises(self, mock_console) -> None:
        """Test required integers reject sentinel-equivalent empty values."""
        schema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
            },
            "required": ["count"],
        }

        with patch("typer.prompt", return_value=_INT_SENTINEL_DEFAULT):
            with pytest.raises(CLIError, match="Field 'count' is required"):
                prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_optional_integer_sentinel_is_skipped(self, mock_console) -> None:
        """Test optional integers are skipped when sentinel-equivalent value is returned."""
        schema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
            },
        }

        with patch("typer.prompt", return_value=_INT_SENTINEL_DEFAULT):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {}

    def test_prompt_for_json_schema_number_with_default(self, mock_console) -> None:
        """Test number prompts parse float values and respect defaults."""
        schema = {
            "type": "object",
            "properties": {
                "score": {
                    "type": "number",
                    "default": 1.5,
                }
            },
            "required": ["score"],
        }

        with patch("typer.prompt", return_value="2.25"):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"score": 2.25}

    def test_prompt_for_json_schema_required_number_blank_raises(self, mock_console) -> None:
        """Test required numbers reject blank input."""
        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
            },
            "required": ["score"],
        }

        with patch("typer.prompt", return_value=""):
            with pytest.raises(CLIError, match="Field 'score' is required"):
                prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_optional_number_blank_is_skipped(self, mock_console) -> None:
        """Test optional numbers are skipped when blank input is provided."""
        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
            },
        }

        with patch("typer.prompt", return_value=""):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {}

    def test_prompt_for_json_schema_invalid_number_raises(self, mock_console) -> None:
        """Test invalid numeric input raises a number-specific error."""
        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
            },
            "required": ["score"],
        }

        with patch("typer.prompt", return_value="not-a-number"):
            with pytest.raises(CLIError, match="Field 'score' must be a number"):
                prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_nullable_type_list_with_only_null(self, mock_console) -> None:
        """Test union-like type lists containing only null resolve to None."""
        schema = {
            "type": "object",
            "properties": {
                "empty_value": {"type": ["null"]},
            },
            "required": ["empty_value"],
        }

        result = prompt_for_json_schema(schema, prompt_optional=False)
        assert result == {"empty_value": None}

    def test_prompt_for_json_schema_string_default_non_string_value(self, mock_console) -> None:
        """Test string-like fallback prompts render non-string defaults."""
        schema = {
            "type": "object",
            "properties": {
                "payload": {
                    "default": {"kind": "map"},
                }
            },
            "required": ["payload"],
        }

        with patch("typer.prompt", return_value='{"ok":true}'):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"payload": '{"ok":true}'}

    def test_prompt_for_json_schema_required_fallback_string_blank_raises(self, mock_console) -> None:
        """Test required fallback string fields reject blank input."""
        schema = {
            "type": "object",
            "properties": {
                "name": {},
            },
            "required": ["name"],
        }

        with patch("typer.prompt", return_value=""):
            with pytest.raises(CLIError, match="Field 'name' is required"):
                prompt_for_json_schema(schema, prompt_optional=False)

    def test_prompt_for_json_schema_optional_fallback_string_blank_is_skipped(self, mock_console) -> None:
        """Test optional fallback string fields are skipped when blank."""
        schema = {
            "type": "object",
            "properties": {
                "name": {},
            },
        }

        with patch("typer.prompt", return_value=""):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {}

    def test_prompt_for_json_schema_additional_properties_schema(self, mock_console) -> None:
        """Test `additionalProperties` schema prompts for typed extra fields."""
        schema = {
            "type": "object",
            "additionalProperties": {"type": "integer"},
        }

        with patch("typer.confirm", side_effect=[True, False]), patch("typer.prompt", side_effect=["max_items", 10]):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {"max_items": 10}

    def test_prompt_for_json_schema_additional_properties_true_json_and_raw(self, mock_console) -> None:
        """Test `additionalProperties: true` parses JSON and falls back to raw strings."""
        schema = {
            "type": "object",
            "additionalProperties": True,
        }

        with patch("typer.confirm", side_effect=[True, True, False]), patch("typer.prompt", side_effect=["alpha", '{"nested": 1}', "beta", "raw-text"]):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {"alpha": {"nested": 1}, "beta": "raw-text"}

    def test_prompt_for_json_schema_required_csv_array_blank_returns_empty_list(self, mock_console) -> None:
        """Test required CSV-style arrays return an empty list on blank input."""
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "x-array-input": "csv",
                }
            },
            "required": ["tags"],
        }

        with patch("typer.prompt", return_value=""):
            result = prompt_for_json_schema(schema, prompt_optional=False)

        assert result == {"tags": []}

    def test_prompt_for_json_schema_optional_array_skip_include_prompt_no_entries(self, mock_console) -> None:
        """Test optional arrays can skip include prompt and return no value when no entries are added."""
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "x-array-skip-include-prompt": True,
                }
            },
        }

        with patch("typer.confirm", return_value=False):
            result = prompt_for_json_schema(schema, prompt_optional=True)

        assert result == {}

    def test_build_pydantic_field_schema_rejects_non_string_dict_keys(self) -> None:
        """Test dict fields with non-string keys are rejected for prompting."""
        with pytest.raises(CLIError, match="Only string keys are supported"):
            _build_pydantic_field_schema(dict[int, str])

    def test_resolve_ref_schema_non_dict_input_returns_empty_schema(self) -> None:
        """Test resolve helper defensively returns empty schema for non-dict input."""
        result = _resolve_ref_schema({}, "not-a-dict")  # type: ignore[arg-type]
        assert result == {}

    def test_unwrap_optional_annotation_union_only_none_returns_annotation(self) -> None:
        """Test Optional unwrapping keeps annotation when union has no non-None members."""
        marker: object = object()
        with patch("cforge.common.prompting.get_origin", return_value=Union), patch("cforge.common.prompting.get_args", return_value=(type(None),)):
            assert _unwrap_optional_annotation(marker) is marker

    def test_resolve_schema_type_any_of_all_null_returns_null(self) -> None:
        """Test schema type resolver returns null when all anyOf variants are null."""
        schema = {"anyOf": [{"type": "null"}, {"type": "null"}]}
        assert _resolve_schema_type({}, schema) == "null"

    def test_resolve_schema_type_one_of_prefers_non_null_variant(self) -> None:
        """Test schema type resolver returns first non-null type from oneOf variants."""
        schema = {"oneOf": [{"type": "null"}, {"type": "integer"}]}
        assert _resolve_schema_type({}, schema) == "integer"
