# -*- coding: utf-8 -*-
"""
SPDX-License-Identifier: Apache-2.0

Schema-driven interactive prompting utilities.

This module converts Pydantic annotations and JSON Schema definitions into
interactive CLI prompts, including nested objects, arrays, enums, optional
fields, and local `$ref` resolution. It is the shared input pipeline used by
commands that need structured request payloads.
"""

# Standard
from typing import Annotated, Any, Callable, Dict, get_args, get_origin, get_type_hints, List, Optional, Tuple, Union

import json

# Third-Party
from pydantic import BaseModel
from rich.console import Console

import typer

# Local
from cforge.common.console import get_console
from cforge.common.errors import CLIError
from cforge.common.schema_validation import validate_instance, validate_instance_against_subschema, validate_schema

_INT_SENTINEL_DEFAULT = -4231415


def _format_prompt_indent(indt: str) -> str:
    """Render indentation in a dim style for readability."""
    return f"[dim]{indt}[/dim]" if indt else indt


def _next_prompt_indent(indt: str) -> str:
    """Return the next indentation level."""
    if not indt:
        return "|-"
    return f"{indt}-"


def _build_prompt_text(
    field_name: str,
    description: Optional[str],
    default: Any,
    default_is_set: bool,
    is_required: bool,
    include_falsy_default: bool = True,
) -> str:
    """Build prompt text for a field."""
    prompt_text = field_name
    if description and description != field_name:
        prompt_text += f" ({description})"

    has_default = default_is_set and default is not None and (include_falsy_default or bool(default))
    if has_default:
        try:
            default_text = json.dumps(default)
        except TypeError:
            default_text = str(default)
        prompt_text += f" [default: {default_text}]"

    if not is_required:
        prompt_text += " [optional]"
    return prompt_text


def _prompt_include_field(console: Console, field_name: str, field_indent: str) -> bool:
    """Prompt whether to include an optional field."""
    formatted_field_indent = _format_prompt_indent(field_indent)
    console.print(f"{formatted_field_indent}[dim]Include {field_name}?[/dim] ", end="")
    return typer.confirm("", default=False)


def _prompt_boolean_value(
    console: Console,
    field_indent: str,
    prompt_text: str,
    default: bool,
    show_default: bool,
) -> bool:
    """Prompt for a boolean field value."""
    formatted_field_indent = _format_prompt_indent(field_indent)
    console.print(f"{formatted_field_indent}{prompt_text}", end="")
    return typer.prompt("", default=default, type=bool, show_default=show_default)


def _prompt_integer_value(
    console: Console,
    field_indent: str,
    prompt_text: str,
    default: Any,
    show_default: bool,
) -> int:
    """Prompt for an integer field value."""
    formatted_field_indent = _format_prompt_indent(field_indent)
    console.print(f"{formatted_field_indent}{prompt_text}", end="")
    return typer.prompt("", type=int, default=default, show_default=show_default)


def _prompt_string_value(
    console: Console,
    field_indent: str,
    prompt_text: str,
    default: str,
    show_default: bool,
) -> str:
    """Prompt for a string field value."""
    formatted_field_indent = _format_prompt_indent(field_indent)
    console.print(f"{formatted_field_indent}{prompt_text}", end="")
    return typer.prompt("", type=str, default=default, show_default=show_default)


def _validate_pydantic_schema_dict_key_types(schema_class: type[BaseModel]) -> None:
    """Reject dict fields with non-string keys (JSON object keys are always strings)."""
    visited_models: set[type[BaseModel]] = set()

    def _unwrap_annotated(annotation: Any) -> Any:
        """Return the underlying type for Annotated[T, ...] annotations."""
        origin = get_origin(annotation)
        if origin is Annotated:
            args = get_args(annotation)
            if not args:  # pragma: no cover - defensive for patched typing helpers
                return annotation
            return args[0]
        return annotation

    def _resolve_type_hints(model_class: type[BaseModel]) -> Dict[str, Any]:
        """Resolve type hints for a Pydantic model, keeping Annotated extras."""
        try:
            return get_type_hints(model_class, include_extras=True)
        except Exception:  # pragma: no cover - defensive fallback for complex forward refs
            return {}

    def _visit_annotation(annotation: Any) -> None:
        """Walk annotation trees to find dict key types and nested models."""
        annotation = _unwrap_annotated(annotation)
        origin = get_origin(annotation)

        if origin is Union:
            for arg in get_args(annotation):
                if arg is type(None):
                    continue
                _visit_annotation(arg)
            return

        if origin in {list, set, frozenset, tuple}:
            for arg in get_args(annotation):
                _visit_annotation(arg)
            return

        if origin is dict:
            args = get_args(annotation)
            dict_key_type = _unwrap_annotated(args[0]) if len(args) > 0 else str
            if dict_key_type is not str:
                raise CLIError("Only string keys are supported")
            if len(args) > 1:
                _visit_annotation(args[1])
            return

        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            _visit_model(annotation)
            return

    def _visit_model(model_class: type[BaseModel]) -> None:
        """Visit model field annotations recursively, avoiding cycles."""
        if model_class in visited_models:
            return
        visited_models.add(model_class)

        resolved_hints = _resolve_type_hints(model_class)
        for field_name, field_info in model_class.model_fields.items():
            annotation = resolved_hints.get(field_name, field_info.annotation)
            _visit_annotation(annotation)

    _visit_model(schema_class)


def _as_schema_dict(value: Any) -> Dict[str, Any]:
    """Return a schema dictionary, coercing unknown values to an empty schema."""
    return value if isinstance(value, dict) else {}


def _resolve_json_pointer(root_schema: Dict[str, Any], ref: str) -> Dict[str, Any]:
    """Resolve a local JSON Pointer reference against the root schema."""
    if not ref.startswith("#/"):
        raise CLIError(f"Only local schema references are supported: {ref}")

    pointer_tokens = ref[2:].split("/")
    current: Any = root_schema

    for raw_token in pointer_tokens:
        token = raw_token.replace("~1", "/").replace("~0", "~")

        if isinstance(current, dict):
            if token not in current:
                raise CLIError(f"Schema reference not found: {ref}")
            current = current[token]
            continue

        if isinstance(current, list):
            try:
                index = int(token)
            except ValueError:
                raise CLIError(f"Invalid array index in schema reference: {ref}")
            if index < 0 or index >= len(current):
                raise CLIError(f"Schema reference index out of bounds: {ref}")
            current = current[index]
            continue

        raise CLIError(f"Schema reference path is invalid: {ref}")

    if not isinstance(current, dict):
        raise CLIError(f"Schema reference does not resolve to an object schema: {ref}")

    return current


def _resolve_ref_schema(root_schema: Dict[str, Any], field_schema: Dict[str, Any], resolving: Tuple[str, ...] = ()) -> Dict[str, Any]:
    """Resolve $ref in schema and merge sibling keys as overrides."""
    if not isinstance(field_schema, dict):
        return {}

    ref_value = field_schema.get("$ref")
    if not isinstance(ref_value, str):
        return field_schema

    if ref_value in resolving:
        ref_chain = " -> ".join([*resolving, ref_value])
        raise CLIError(f"Cyclic schema reference detected: {ref_chain}")

    resolved_schema = _resolve_ref_schema(root_schema, _resolve_json_pointer(root_schema, ref_value), resolving + (ref_value,))
    merged_schema = resolved_schema.copy()
    merged_schema.update({key: value for key, value in field_schema.items() if key != "$ref"})
    return merged_schema


def _infer_schema_type(field_schema: Dict[str, Any]) -> Optional[str]:
    """Infer schema type from direct JSON Schema keywords."""
    raw_type = field_schema.get("type")
    if isinstance(raw_type, str):
        return raw_type
    if isinstance(raw_type, list):
        valid_types = [item for item in raw_type if isinstance(item, str)]
        non_null_types = [item for item in valid_types if item != "null"]
        if non_null_types:
            first_non_null_type = non_null_types[0]
            if all(item == first_non_null_type for item in non_null_types):
                return first_non_null_type
            return "union"
        if "null" in valid_types:
            return "null"
    if isinstance(field_schema.get("properties"), dict):
        return "object"
    if "required" in field_schema:
        return "object"
    if isinstance(field_schema.get("items"), dict):
        return "array"
    if isinstance(field_schema.get("enum"), list):
        return "string"
    return None


def _schema_contains_ref(field_schema: Dict[str, Any], target_ref: str, visited: Optional[set[int]] = None) -> bool:
    """Return True when the schema tree contains the target local $ref."""
    if not isinstance(field_schema, dict):
        return False

    if visited is None:
        visited = set()
    schema_id = id(field_schema)
    if schema_id in visited:
        return False
    visited.add(schema_id)

    ref_value = field_schema.get("$ref")
    if isinstance(ref_value, str) and ref_value == target_ref:
        return True

    for value in field_schema.values():
        if isinstance(value, dict) and _schema_contains_ref(value, target_ref, visited):
            return True
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and _schema_contains_ref(item, target_ref, visited):
                    return True
    return False


def _resolve_effective_schema(
    root_schema: Dict[str, Any],
    field_schema: Dict[str, Any],
    resolving_refs: Tuple[str, ...] = (),
    collapse_nullable: bool = True,
) -> Dict[str, Any]:
    """Resolve refs and collapse only nullable anyOf/oneOf schemas."""
    if not isinstance(field_schema, dict):
        return {}

    ref_value = field_schema.get("$ref")
    if isinstance(ref_value, str):
        if ref_value in resolving_refs:
            return field_schema
        resolving_refs = (*resolving_refs, ref_value)

    resolved_schema = _resolve_ref_schema(root_schema, field_schema)
    if not collapse_nullable:
        return resolved_schema

    for combinator_key in ("anyOf", "oneOf"):
        options = resolved_schema.get(combinator_key)
        if not isinstance(options, list) or not options:
            continue

        resolved_options: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        for option in options:
            option_schema = _as_schema_dict(option)
            resolved_option = _resolve_effective_schema(root_schema, option_schema, resolving_refs, collapse_nullable)
            resolved_options.append((option_schema, resolved_option))

        non_null_options: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        has_null_option = False
        for option_schema, resolved_option in resolved_options:
            option_type = _resolve_schema_type(root_schema, resolved_option, resolving_refs)
            if option_type == "null":
                has_null_option = True
                continue
            non_null_options.append((option_schema, resolved_option))

        if len(non_null_options) == 1 and (has_null_option or len(resolved_options) == 1):
            selected_option, selected_resolved_option = non_null_options[0]
            option_ref = selected_option.get("$ref")
            if isinstance(option_ref, str) and _schema_contains_ref(selected_resolved_option, option_ref):
                # Keep nullable wrapper so recursive schemas retain a terminating null path.
                return resolved_schema

            merged_schema = selected_resolved_option.copy()
            merged_schema.update({key: value for key, value in resolved_schema.items() if key not in {"anyOf", "oneOf"}})
            return merged_schema

        return resolved_schema
    return resolved_schema


def _resolve_schema_type(
    root_schema: Dict[str, Any],
    field_schema: Dict[str, Any],
    resolving_refs: Tuple[str, ...] = (),
) -> str:
    """Resolve schema type from JSON Schema type fields and structural hints."""
    if not isinstance(field_schema, dict):
        return "string"

    ref_value = field_schema.get("$ref")
    if isinstance(ref_value, str):
        if ref_value in resolving_refs:
            return "union"
        resolving_refs = (*resolving_refs, ref_value)

    field_schema = _resolve_ref_schema(root_schema, field_schema)
    direct_type = _infer_schema_type(field_schema)
    if direct_type is not None:
        return direct_type

    for combinator_key in ("anyOf", "oneOf"):
        options = field_schema.get(combinator_key)
        if not isinstance(options, list) or not options:
            continue

        option_results: List[Tuple[Dict[str, Any], str]] = []
        for option in options:
            option_schema = _as_schema_dict(option)
            option_type = _resolve_schema_type(root_schema, option_schema, resolving_refs)
            option_results.append((option_schema, option_type))

        non_null_results = [(option_schema, option_type) for option_schema, option_type in option_results if option_type != "null"]
        has_null_option = any(option_type == "null" for _, option_type in option_results)

        if not non_null_results:
            return "null"

        if len(non_null_results) == 1:
            non_null_option_schema, non_null_type = non_null_results[0]
            option_ref = non_null_option_schema.get("$ref")
            if has_null_option and isinstance(option_ref, str):
                resolved_non_null_option = _resolve_ref_schema(root_schema, non_null_option_schema)
                if _schema_contains_ref(resolved_non_null_option, option_ref):
                    # Keep recursive nullable refs as union prompts to avoid auto-generating empty objects.
                    return "union"
            return non_null_type
        return "union"

    return "string"


def _prompt_from_json_schema(
    schema: Dict[str, Any],
    prefilled: Optional[Dict[str, Any]] = None,
    indent: str = "",
    prompt_optional: bool = True,
    default_display_name: str = "Tool Arguments",
    validate_payload: bool = True,
) -> Dict[str, Any]:
    """Prompt recursively from schema dictionaries shared by both public APIs."""
    if not isinstance(schema, dict):
        raise CLIError("Input schema must be a JSON object")
    if prefilled is not None and not isinstance(prefilled, dict):
        raise CLIError("Prefilled input must be a JSON object")

    if validate_payload:
        schema_error = validate_schema(schema)
        if schema_error is not None:
            raise CLIError(schema_error)

    resolved_root_schema = _resolve_effective_schema(schema, schema)
    root_type = _resolve_schema_type(schema, resolved_root_schema)
    if root_type != "object":
        raise CLIError("Input schema must be an object schema")

    _MISSING = object()
    console = get_console()
    formatted_indent = _format_prompt_indent(indent)
    display_name = resolved_root_schema.get("title", default_display_name)
    if not isinstance(display_name, str) or not display_name:
        display_name = default_display_name

    console.print(f"\n{formatted_indent}[bold cyan]Creating {display_name}[/bold cyan]")
    if prompt_optional:
        console.print(f"{formatted_indent}[dim]Press Enter to skip optional fields[/dim]\n{formatted_indent}")
    else:
        console.print(f"{formatted_indent}[dim]Prompting for missing required fields only[/dim]\n{formatted_indent}")

    def _prompt_field_value(
        field_name: str,
        field_schema: Dict[str, Any],
        is_required: bool,
        field_indent: str,
        prefilled_value: Any = _MISSING,
    ) -> Tuple[Any, bool]:
        """Prompt for a single field value.

        Returns:
            tuple[value, included] where included indicates if field should be set.
        """
        field_schema = _resolve_effective_schema(schema, field_schema)
        schema_type = _resolve_schema_type(schema, field_schema)
        formatted_field_indent = _format_prompt_indent(field_indent)
        include_falsy_default = True
        prompt_text = _build_prompt_text(
            field_name=field_name,
            description=field_schema.get("description") if isinstance(field_schema.get("description"), str) else None,
            default=field_schema.get("default"),
            default_is_set="default" in field_schema,
            is_required=is_required,
            include_falsy_default=include_falsy_default,
        )

        def _format_string_default(default_value: Any) -> Tuple[str, bool]:
            """Return a default prompt value (as text) and whether to show it."""
            if default_value is None:
                return "", False
            if isinstance(default_value, str):
                return default_value, True
            return json.dumps(default_value), True

        def _prompt_string_with_default() -> Tuple[Optional[str], bool]:
            """Prompt for a string value while honoring schema defaults and required-ness."""
            default_text, show_default = _format_string_default(field_schema.get("default"))
            value = _prompt_string_value(
                console=console,
                field_indent=field_indent,
                prompt_text=prompt_text,
                default=default_text,
                show_default=show_default,
            )
            if value == "":
                if is_required:
                    raise CLIError(f"Field '{field_name}' is required")
                return None, False
            return value, True

        if prefilled_value is not _MISSING:
            if schema_type == "object" and isinstance(prefilled_value, dict):
                console.print(f"{formatted_field_indent}[dim]{field_name}: (pre-filled object)[/dim]")
                return _prompt_object(field_schema, prefilled=prefilled_value, object_indent=_next_prompt_indent(field_indent)), True
            if schema_type == "array" and isinstance(prefilled_value, list):
                console.print(f"{formatted_field_indent}[dim]{field_name}: (pre-filled array)[/dim]")
                array_values, include_array = _prompt_array(field_name, field_schema, is_required, field_indent, prefilled=prefilled_value)
                return array_values, include_array
            console.print(f"{formatted_field_indent}[dim]{field_name}: {prefilled_value} (pre-filled)[/dim]")
            return prefilled_value, True

        if not is_required and not prompt_optional:
            return None, False

        enum_values = field_schema.get("enum")
        if isinstance(enum_values, list) and enum_values:
            enum_text = ", ".join(json.dumps(value) for value in enum_values)
            console.print(f"{formatted_field_indent}{prompt_text} [choices: {enum_text}]", end="")

            default_value = field_schema.get("default")
            default_text = ""
            show_default = False
            if default_value is not None:
                default_text = default_value if isinstance(default_value, str) else json.dumps(default_value)
                show_default = True

            raw_value = typer.prompt("", type=str, default=default_text, show_default=show_default)
            if raw_value == "":
                if is_required:
                    raise CLIError(f"Field '{field_name}' is required")
                return None, False

            parsed_value: Any
            try:
                parsed_value = json.loads(raw_value)
            except json.JSONDecodeError:
                parsed_value = raw_value

            if parsed_value in enum_values:
                return parsed_value, True
            if raw_value in enum_values:
                return raw_value, True

            raise CLIError(f"Field '{field_name}' must be one of: {enum_text}")

        if schema_type == "object":
            if not is_required and prompt_optional and not _prompt_include_field(console, field_name, field_indent):
                return None, False
            console.print(f"{formatted_field_indent}[yellow]{prompt_text}[/yellow]")
            return _prompt_object(field_schema, prefilled=None, object_indent=_next_prompt_indent(field_indent)), True

        if schema_type == "array":
            return _prompt_array(field_name, field_schema, is_required, field_indent)

        if schema_type == "boolean":
            if not is_required and prompt_optional and not _prompt_include_field(console, field_name, field_indent):
                return None, False
            default_val = field_schema.get("default")
            bool_default = default_val if isinstance(default_val, bool) else False
            return (
                _prompt_boolean_value(
                    console=console,
                    field_indent=field_indent,
                    prompt_text=prompt_text,
                    default=bool_default,
                    show_default=True,
                ),
                True,
            )

        if schema_type == "integer":
            default_val = field_schema.get("default")
            default_prompt: Any = "" if is_required else _INT_SENTINEL_DEFAULT
            show_default = False
            if isinstance(default_val, int):
                default_prompt = default_val
                show_default = True
            value = _prompt_integer_value(
                console=console,
                field_indent=field_indent,
                prompt_text=prompt_text,
                default=default_prompt,
                show_default=show_default,
            )
            if value == _INT_SENTINEL_DEFAULT:
                if is_required:
                    raise CLIError(f"Field '{field_name}' is required")
                return None, False
            return value, True

        if schema_type == "number":
            default_val = field_schema.get("default")
            default_text = ""
            show_default = False
            if isinstance(default_val, (int, float)):
                default_text = str(float(default_val))
                show_default = True
            raw_value = _prompt_string_value(
                console=console,
                field_indent=field_indent,
                prompt_text=prompt_text,
                default=default_text,
                show_default=show_default,
            )
            if raw_value == "":
                if is_required:
                    raise CLIError(f"Field '{field_name}' is required")
                return None, False
            try:
                return float(raw_value), True
            except ValueError:
                raise CLIError(f"Field '{field_name}' must be a number")

        if schema_type == "null":
            return None, True

        if schema_type == "union":
            raw_value, include_raw = _prompt_string_with_default()
            if not include_raw:
                return None, False

            parsed_value: Any
            try:
                parsed_value = json.loads(raw_value)
            except json.JSONDecodeError:
                parsed_value = raw_value

            validation_error = validate_instance_against_subschema(schema, field_schema, parsed_value)
            if validation_error is None:
                return parsed_value, True

            raise CLIError(f"Field '{field_name}' is invalid: {validation_error}")

        value, include_value = _prompt_string_with_default()
        if not include_value:
            return None, False
        return value, True

    def _prompt_array(
        field_name: str,
        field_schema: Dict[str, Any],
        is_required: bool,
        field_indent: str,
        prefilled: Optional[List[Any]] = None,
    ) -> Tuple[List[Any], bool]:
        """Prompt for array values."""
        field_schema = _resolve_effective_schema(schema, field_schema)
        formatted_field_indent = _format_prompt_indent(field_indent)
        item_schema = _resolve_effective_schema(schema, _as_schema_dict(field_schema.get("items")))
        item_type = _resolve_schema_type(schema, item_schema)

        if prefilled is None and item_type != "string" and not is_required and prompt_optional:
            if not _prompt_include_field(console, field_name, field_indent):
                return [], False

        values: List[Any] = []

        if prefilled is not None:
            nested_indent = _next_prompt_indent(field_indent)
            for idx, entry in enumerate(prefilled):
                if item_type == "object" and isinstance(entry, dict):
                    values.append(_prompt_object(item_schema, prefilled=entry, object_indent=nested_indent))
                elif item_type == "array" and isinstance(entry, list):
                    nested_values, _ = _prompt_array(f"{field_name}[{idx}]", item_schema, is_required=True, field_indent=nested_indent, prefilled=entry)
                    values.append(nested_values)
                else:
                    values.append(entry)
            return values, True

        if item_type == "string":
            console.print(f"{formatted_field_indent}[dim]Enter comma-separated values, or press Enter to skip[/dim] ", end="")
            csv_value = typer.prompt("", default="", show_default=False)
            if csv_value:
                return [value.strip() for value in csv_value.split(",") if value.strip()], True
            if is_required:
                return [], True
            return [], False

        nested_indent = _next_prompt_indent(field_indent)
        while True:
            console.print(f"{formatted_field_indent}[dim]Add an entry to {field_name}?[/dim] ", end="")
            if not typer.confirm("", default=False):
                break
            entry, _ = _prompt_field_value("item", item_schema, is_required=True, field_indent=nested_indent)
            values.append(entry)

        if values:
            return values, True
        return [], True

    def _prompt_additional_properties(
        object_indent: str,
        assign_value: Callable[[str, str], None],
    ) -> None:
        """Prompt for additional object properties using a supplied value handler."""
        while True:
            formatted_object_indent = _format_prompt_indent(object_indent)
            next_indent = _next_prompt_indent(object_indent)
            formatted_next_indent = _format_prompt_indent(next_indent)
            console.print(f"{formatted_object_indent}[dim]Add an extra field?[/dim] ", end="")
            if not typer.confirm("", default=False):
                break
            console.print(f"{formatted_next_indent}Enter key", end="")
            key = typer.prompt("", type=str)
            assign_value(key, next_indent)

    def _prompt_object(field_schema: Dict[str, Any], prefilled: Optional[Dict[str, Any]], object_indent: str) -> Dict[str, Any]:
        """Prompt for object fields recursively."""
        field_schema = _resolve_effective_schema(schema, field_schema)
        data = prefilled.copy() if prefilled else {}
        properties = field_schema.get("properties")
        required = field_schema.get("required")
        properties_dict = properties if isinstance(properties, dict) else {}
        required_fields = {field for field in required if isinstance(field, str)} if isinstance(required, list) else set()

        for field_name, field_details in properties_dict.items():
            field_def = _resolve_effective_schema(schema, _as_schema_dict(field_details))
            has_prefilled = field_name in data
            current_value = data[field_name] if has_prefilled else _MISSING
            value, include_value = _prompt_field_value(
                field_name=field_name,
                field_schema=field_def,
                is_required=field_name in required_fields,
                field_indent=object_indent,
                prefilled_value=current_value,
            )
            if include_value:
                data[field_name] = value

        additional_properties = field_schema.get("additionalProperties")
        if isinstance(additional_properties, dict) and prompt_optional:
            additional_properties_schema = _resolve_effective_schema(schema, additional_properties)

            def _assign_typed_value(key: str, next_indent: str) -> None:
                """Prompt for and assign a typed additional property value."""
                value, _ = _prompt_field_value(key, additional_properties_schema, is_required=True, field_indent=next_indent)
                data[key] = value

            _prompt_additional_properties(object_indent, _assign_typed_value)
        elif additional_properties is True and prompt_optional:

            def _assign_json_value(key: str, next_indent: str) -> None:
                """Prompt for and assign a JSON additional property value."""
                formatted_next_indent = _format_prompt_indent(next_indent)
                console.print(f"{formatted_next_indent}Enter JSON value", end="")
                raw_value = typer.prompt("", type=str)
                try:
                    data[key] = json.loads(raw_value)
                except json.JSONDecodeError:
                    data[key] = raw_value

            _prompt_additional_properties(object_indent, _assign_json_value)

        return data

    prompted_payload = _prompt_object(resolved_root_schema, prefilled=prefilled, object_indent=indent)
    if validate_payload:
        payload_validation_error = validate_instance(schema, prompted_payload)
        if payload_validation_error is not None:
            raise CLIError(f"Prompted payload is invalid: {payload_validation_error}")
    return prompted_payload


def _strip_schema_internal_properties(schema: Dict[str, Any], skip_fields: set[str]) -> Dict[str, Any]:
    """Return a shallow copy of a root object schema without internal prompt-only fields."""
    schema_copy = schema.copy()
    properties = schema_copy.get("properties")
    if isinstance(properties, dict):
        properties_copy = properties.copy()
        for field in skip_fields:
            properties_copy.pop(field, None)
        schema_copy["properties"] = properties_copy

    required = schema_copy.get("required")
    if isinstance(required, list):
        schema_copy["required"] = [field for field in required if isinstance(field, str) and field not in skip_fields]

    return schema_copy


def prompt_for_schema(schema_class: type[BaseModel], prefilled: Optional[Dict[str, Any]] = None, indent: str = "") -> Dict[str, Any]:
    """Interactively prompt user for fields based on a Pydantic schema."""
    _validate_pydantic_schema_dict_key_types(schema_class)
    schema = _strip_schema_internal_properties(schema_class.model_json_schema(), {"auth_value", "model_config"})
    # The prompt schema is intentionally lossy (e.g., datetime fields become strings),
    # so validating the prompted payload against it can reject values that would be
    # valid after normal Pydantic validation/coercion.
    return _prompt_from_json_schema(
        schema,
        prefilled=prefilled,
        indent=indent,
        prompt_optional=True,
        default_display_name=schema_class.__name__,
        validate_payload=False,
    )


def prompt_for_json_schema(
    schema: Dict[str, Any],
    prefilled: Optional[Dict[str, Any]] = None,
    indent: str = "",
    prompt_optional: bool = True,
) -> Dict[str, Any]:
    """Interactively prompt user for fields based on a JSON Schema object."""
    return _prompt_from_json_schema(schema, prefilled=prefilled, indent=indent, prompt_optional=prompt_optional, default_display_name="Tool Arguments")
