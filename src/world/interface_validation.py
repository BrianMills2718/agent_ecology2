"""Interface validation for artifact invocations.

Extracted from executor.py as part of Plan #181 (Split Large Core Files).

This module provides argument validation against artifact interface schemas:
- Type coercion (string "5" -> int 5) per Plan #160
- Positional/named argument conversion
- JSON Schema validation per Plan #86

The functions here are used by SafeExecutor when invoking artifacts.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import jsonschema


# Logger for interface validation
_logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result from interface validation (Plan #86).

    Attributes:
        valid: Whether the arguments matched the interface schema
        proceed: Whether to proceed with the invocation
        skipped: Whether validation was skipped entirely
        error_message: Description of validation failure (if any)
        coerced_args: Plan #160 - Args with types coerced (e.g., "5" -> 5)
    """
    valid: bool
    proceed: bool
    skipped: bool
    error_message: str
    coerced_args: dict[str, Any] | None = None


def _coerce_types_from_schema(args: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    """Coerce argument types based on schema expectations.

    Plan #160: LLMs often send "5" instead of 5 when schema expects integer.
    This auto-converts string representations to proper types.

    Args:
        args: Dict of argument name -> value
        schema: JSON schema with properties defining expected types

    Returns:
        Dict with types coerced where safe to do so.
    """
    if not isinstance(args, dict):
        return args

    properties = schema.get("properties", {})
    coerced = dict(args)  # Copy to avoid mutating original

    for prop_name, prop_schema in properties.items():
        if prop_name not in coerced:
            continue

        value = coerced[prop_name]
        expected_type = prop_schema.get("type")

        # Coerce string to integer
        if expected_type == "integer" and isinstance(value, str):
            try:
                coerced[prop_name] = int(value)
            except ValueError:
                pass  # Keep original if not a valid integer

        # Coerce string to number (float)
        elif expected_type == "number" and isinstance(value, str):
            try:
                coerced[prop_name] = float(value)
            except ValueError:
                pass  # Keep original if not a valid number

        # Coerce string to boolean
        elif expected_type == "boolean" and isinstance(value, str):
            if value.lower() in ("true", "1", "yes"):
                coerced[prop_name] = True
            elif value.lower() in ("false", "0", "no"):
                coerced[prop_name] = False

    return coerced


def convert_positional_to_named_args(
    interface: dict[str, Any] | None,
    method_name: str,
    args: list[Any],
) -> dict[str, Any]:
    """Convert positional args list to named args dict based on interface schema.

    When agents pass args as a list like ["genesis_ledger"], and the interface
    schema expects named properties like {"artifact_id": "..."}, this function
    maps positional arguments to the expected property names.

    Args:
        interface: The artifact's interface definition (MCP-compatible format)
        method_name: The method being invoked
        args: Positional arguments as a list

    Returns:
        Dict mapping property names to values, or {"args": args} as fallback
    """
    if not interface or not args:
        return {"args": args} if args else {}

    # Get tools array from interface
    tools = interface.get("tools", [])
    if not tools:
        return {"args": args}

    # Find the method schema
    method_schema = None
    for tool in tools:
        if tool.get("name") == method_name:
            method_schema = tool
            break

    if method_schema is None:
        return {"args": args}

    # Get inputSchema
    input_schema = method_schema.get("inputSchema")
    if not input_schema or input_schema.get("type") != "object":
        return {"args": args}

    # Get property names - prefer 'required' order, then fall back to 'properties' keys
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])

    # Use required fields first (in order), then add any non-required properties
    param_names: list[str] = list(required)
    for prop_name in properties.keys():
        if prop_name not in param_names:
            param_names.append(prop_name)

    if not param_names:
        return {"args": args}

    # Plan #112: Schema-aware JSON parsing
    # LLMs often output "[1,2,3]" as a string instead of actual array [1,2,3]
    # BUT: Only parse if the schema expects object/array, not string
    # This fixes agents passing valid JSON strings that get incorrectly parsed
    def maybe_parse_json(value: Any, expected_type: str | None) -> Any:
        """Try to parse string as JSON only if schema expects object/array."""
        # Don't parse if schema expects a string - the JSON string IS the value
        if expected_type == "string":
            return value
        if isinstance(value, str) and len(value) >= 2:
            first_char = value[0]
            if first_char in '[{':
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    pass  # Not valid JSON, keep as string
        return value

    # Map positional args to property names
    result: dict[str, Any] = {}
    for i, arg in enumerate(args):
        if i < len(param_names):
            param_name = param_names[i]
            # Get expected type from schema to avoid parsing strings that should stay strings
            param_schema = properties.get(param_name, {})
            expected_type = param_schema.get("type") if isinstance(param_schema, dict) else None
            result[param_name] = maybe_parse_json(arg, expected_type)
        else:
            # More args than properties - can't map, fall back
            _logger.debug(
                "More positional args (%d) than schema properties (%d) for method '%s'",
                len(args), len(param_names), method_name
            )
            return {"args": args}

    return result


def convert_named_to_positional_args(
    interface: dict[str, Any] | None,
    method_name: str,
    args_dict: dict[str, Any],
) -> list[Any]:
    """Convert named args dict back to positional args list based on interface schema.

    Plan #160: After type coercion (which works on dicts), convert back to a list
    for genesis methods that expect positional arguments.

    Args:
        interface: The artifact's interface definition (MCP-compatible format)
        method_name: The method being invoked
        args_dict: Named arguments as a dict

    Returns:
        List of values in schema order (required fields first, then others)
    """
    if not interface or not args_dict:
        return list(args_dict.values()) if args_dict else []

    # Get tools array from interface
    tools = interface.get("tools", [])
    if not tools:
        return list(args_dict.values())

    # Find the method schema
    method_schema = None
    for tool in tools:
        if tool.get("name") == method_name:
            method_schema = tool
            break

    if method_schema is None:
        return list(args_dict.values())

    # Get inputSchema
    input_schema = method_schema.get("inputSchema")
    if not input_schema or input_schema.get("type") != "object":
        return list(args_dict.values())

    # Get property names in order - prefer 'required' order, then 'properties' keys
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])

    # Use required fields first (in order), then add any non-required properties
    param_names: list[str] = list(required)
    for prop_name in properties.keys():
        if prop_name not in param_names:
            param_names.append(prop_name)

    # Build positional args list in schema order
    result: list[Any] = []
    for param_name in param_names:
        if param_name in args_dict:
            result.append(args_dict[param_name])

    return result


def validate_args_against_interface(
    interface: dict[str, Any] | None,
    method_name: str,
    args: dict[str, Any],
    validation_mode: str,
) -> ValidationResult:
    """Validate invocation arguments against artifact interface schema (Plan #86).

    Args:
        interface: The artifact's interface definition (MCP-compatible format)
        method_name: The method being invoked
        args: The arguments being passed
        validation_mode: One of 'none', 'warn', or 'strict'

    Returns:
        ValidationResult indicating whether to proceed
    """
    # Mode 'none' - skip all validation
    if validation_mode == "none":
        return ValidationResult(valid=True, proceed=True, skipped=True, error_message="")

    # No interface - skip validation
    if interface is None:
        return ValidationResult(valid=True, proceed=True, skipped=True, error_message="")

    # Get tools array from interface
    tools = interface.get("tools", [])
    if not tools:
        # No tools defined - skip validation
        return ValidationResult(valid=True, proceed=True, skipped=True, error_message="")

    # Find the method in tools
    method_schema = None
    for tool in tools:
        if tool.get("name") == method_name:
            method_schema = tool
            break

    if method_schema is None:
        # Plan #161: Improved error message - explain HOW to discover methods
        # Plan #160: Solution-first format so critical info survives truncation
        # Note: Removed "Tip: Call describe()" - it sent agents chasing non-executable artifacts
        available_methods = [t.get("name") for t in tools if t.get("name")]
        error_msg = (
            f"Use one of {available_methods} instead. "
            f"Method '{method_name}' does not exist on this artifact."
        )
        if validation_mode == "warn":
            _logger.warning("Interface validation: %s", error_msg)
            return ValidationResult(valid=False, proceed=True, skipped=False, error_message=error_msg)
        else:  # strict
            return ValidationResult(valid=False, proceed=False, skipped=False, error_message=error_msg)

    # Get inputSchema from method
    input_schema = method_schema.get("inputSchema")
    if input_schema is None:
        # No inputSchema - skip validation (method accepts anything)
        return ValidationResult(valid=True, proceed=True, skipped=True, error_message="")

    # Plan #160: Auto-coerce types before validation
    # LLMs often send "5" instead of 5 - coerce based on schema
    args = _coerce_types_from_schema(args, input_schema)

    # Validate args against inputSchema using jsonschema
    try:
        jsonschema.validate(instance=args, schema=input_schema)
        # Validation passed - return coerced args so caller can use them
        return ValidationResult(valid=True, proceed=True, skipped=False, error_message="", coerced_args=args)
    except jsonschema.ValidationError as e:
        # Validation failed - include full schema info so agents can fix their calls
        # Plan #160: Show complete method schema for self-correction
        base_error = str(e.message)
        required = set(input_schema.get("required", []))
        properties_schema = input_schema.get("properties", {})

        # Build concise schema summary: {prop: type*, prop2: type}
        # Required fields marked with *
        schema_parts: list[str] = []
        example_parts: list[str] = []
        for prop_name, prop_schema in list(properties_schema.items())[:6]:
            prop_type = prop_schema.get("type", "any")
            # Short type names
            type_abbrev = {"string": "str", "integer": "int", "number": "num",
                          "boolean": "bool", "array": "list", "object": "dict"}.get(prop_type, prop_type)
            req_marker = "*" if prop_name in required else ""
            schema_parts.append(f"{prop_name}: {type_abbrev}{req_marker}")

            # Build example value
            if prop_type == "string":
                example_parts.append(f'"{prop_name}": "value"')
            elif prop_type == "integer":
                example_parts.append(f'"{prop_name}": 1')
            elif prop_type == "number":
                example_parts.append(f'"{prop_name}": 1.0')
            elif prop_type == "boolean":
                example_parts.append(f'"{prop_name}": true')
            elif prop_type == "array":
                example_parts.append(f'"{prop_name}": []')
            else:
                example_parts.append(f'"{prop_name}": {{}}')

        schema_str = ", ".join(schema_parts)
        if len(properties_schema) > 6:
            schema_str += ", ..."

        example_str = ", ".join(example_parts[:4])
        if len(example_parts) > 4:
            example_str += ", ..."

        # Concise but complete error message
        error_msg = (
            f"{base_error}. "
            f"SCHEMA: {{{schema_str}}} (* = required). "
            f"EXAMPLE: invoke_artifact('{method_name}', [{{{example_str}}}])"
        )

        if validation_mode == "warn":
            _logger.warning("Interface validation failed for '%s': %s", method_name, error_msg)
            # Plan #160: Still return coerced args even on validation failure
            # So type coercion is applied even if other validation errors exist
            return ValidationResult(valid=False, proceed=True, skipped=False, error_message=error_msg, coerced_args=args)
        else:  # strict
            return ValidationResult(valid=False, proceed=False, skipped=False, error_message=error_msg)
    except jsonschema.SchemaError as e:
        # Schema itself is invalid - treat as skip
        error_msg = f"Invalid interface schema: {e.message}"
        _logger.error("Interface schema error: %s", error_msg)
        return ValidationResult(valid=False, proceed=True, skipped=False, error_message=error_msg)
