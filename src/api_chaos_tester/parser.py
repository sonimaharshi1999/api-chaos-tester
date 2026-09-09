# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""
OpenAPI specification parser.
Reads OpenAPI 3.x YAML/JSON specs and converts them into internal
ApiEndpoint models for test generation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from api_chaos_tester.models import (
    ApiEndpoint,
    ApiParameter,
    HttpMethod,
    ParameterLocation,
    ParameterType,
)


_OPENAPI_TYPE_MAP: dict[str, ParameterType] = {
    "string": ParameterType.STRING,
    "integer": ParameterType.INTEGER,
    "number": ParameterType.NUMBER,
    "boolean": ParameterType.BOOLEAN,
    "array": ParameterType.ARRAY,
    "object": ParameterType.OBJECT,
}

_VALID_METHODS = {m.value.lower() for m in HttpMethod}


def _resolve_ref(spec: dict[str, Any], ref: str) -> dict[str, Any]:
    """Resolve a JSON $ref pointer within the spec."""
    parts = ref.lstrip("#/").split("/")
    node: Any = spec
    for part in parts:
        node = node[part]
    return node  # type: ignore[return-value]


def _resolve_schema(spec: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    """Recursively resolve $ref in a schema dict."""
    if "$ref" in schema:
        return _resolve_ref(spec, schema["$ref"])
    return schema


def _parse_parameter_type(schema: dict[str, Any]) -> ParameterType:
    """Convert an OpenAPI schema type string to our ParameterType enum."""
    raw = schema.get("type", "string")
    return _OPENAPI_TYPE_MAP.get(raw, ParameterType.STRING)


def _extract_parameter(
    spec: dict[str, Any], param_def: dict[str, Any]
) -> ApiParameter:
    """Convert an OpenAPI parameter definition to an ApiParameter."""
    if "$ref" in param_def:
        param_def = _resolve_ref(spec, param_def["$ref"])

    schema = _resolve_schema(spec, param_def.get("schema", {}))
    location_raw = param_def.get("in", "query")
    location = ParameterLocation(location_raw)

    return ApiParameter(
        name=param_def.get("name", "unknown"),
        location=location,
        param_type=_parse_parameter_type(schema),
        required=param_def.get("required", False),
        description=param_def.get("description", ""),
        default=schema.get("default"),
        enum_values=schema.get("enum", []),
        min_value=schema.get("minimum"),
        max_value=schema.get("maximum"),
        min_length=schema.get("minLength"),
        max_length=schema.get("maxLength"),
        pattern=schema.get("pattern"),
        format=schema.get("format"),
    )


def _extract_body_params(
    spec: dict[str, Any], request_body: dict[str, Any]
) -> tuple[list[ApiParameter], dict[str, Any] | None]:
    """Extract parameters from a request body definition."""
    if "$ref" in request_body:
        request_body = _resolve_ref(spec, request_body["$ref"])

    content = request_body.get("content", {})
    json_content = content.get("application/json", {})
    schema = json_content.get("schema", {})
    schema = _resolve_schema(spec, schema)

    params: list[ApiParameter] = []
    required_fields = set(schema.get("required", []))
    properties = schema.get("properties", {})

    for prop_name, prop_schema in properties.items():
        prop_schema = _resolve_schema(spec, prop_schema)
        params.append(
            ApiParameter(
                name=prop_name,
                location=ParameterLocation.BODY,
                param_type=_parse_parameter_type(prop_schema),
                required=prop_name in required_fields,
                description=prop_schema.get("description", ""),
                default=prop_schema.get("default"),
                enum_values=prop_schema.get("enum", []),
                min_value=prop_schema.get("minimum"),
                max_value=prop_schema.get("maximum"),
                min_length=prop_schema.get("minLength"),
                max_length=prop_schema.get("maxLength"),
                pattern=prop_schema.get("pattern"),
                format=prop_schema.get("format"),
            )
        )

    return params, schema if properties else None


def parse_openapi_spec(spec_path: str | Path) -> list[ApiEndpoint]:
    """
    Parse an OpenAPI 3.x spec file and return a list of ApiEndpoint models.

    Args:
        spec_path: Path to the YAML or JSON OpenAPI spec file.

    Returns:
        List of parsed API endpoints.

    Raises:
        FileNotFoundError: If the spec file does not exist.
        ValueError: If the spec is not valid OpenAPI 3.x.
    """
    path = Path(spec_path)
    if not path.exists():
        raise FileNotFoundError(f"OpenAPI spec not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        spec: dict[str, Any] = yaml.safe_load(fh)

    if not spec:
        raise ValueError("Empty OpenAPI spec file")

    openapi_version = spec.get("openapi", "")
    if not openapi_version.startswith("3."):
        raise ValueError(
            f"Only OpenAPI 3.x is supported, got version: {openapi_version!r}"
        )

    endpoints: list[ApiEndpoint] = []
    paths = spec.get("paths", {})

    for path_str, path_item in paths.items():
        # Collect path-level parameters
        path_level_params = path_item.get("parameters", [])

        for method_str, operation in path_item.items():
            if method_str in ("parameters", "summary", "description", "$ref"):
                continue
            if method_str not in _VALID_METHODS:
                continue
            if not isinstance(operation, dict):
                continue

            method = HttpMethod(method_str.upper())

            # Parse parameters (path-level + operation-level)
            all_param_defs = path_level_params + operation.get("parameters", [])
            parameters = [_extract_parameter(spec, p) for p in all_param_defs]

            # Parse request body
            body_schema: dict[str, Any] | None = None
            if "requestBody" in operation:
                body_params, body_schema = _extract_body_params(
                    spec, operation["requestBody"]
                )
                parameters.extend(body_params)

            # Parse response codes
            responses = operation.get("responses", {})
            response_codes = []
            for code_str in responses:
                try:
                    response_codes.append(int(code_str))
                except ValueError:
                    pass  # skip 'default' or other non-numeric keys

            endpoints.append(
                ApiEndpoint(
                    path=path_str,
                    method=method,
                    operation_id=operation.get("operationId"),
                    summary=operation.get("summary", ""),
                    description=operation.get("description", ""),
                    parameters=parameters,
                    request_body_schema=body_schema,
                    response_codes=sorted(response_codes),
                    tags=operation.get("tags", []),
                )
            )

    return endpoints


def parse_openapi_from_dict(spec: dict[str, Any]) -> list[ApiEndpoint]:
    """
    Parse an OpenAPI spec already loaded as a dictionary.

    This is useful for testing or when the spec is fetched from a URL.
    """
    # Write to a temp string and re-parse to reuse the same logic
    # but we can also just inline the logic. For simplicity, we inline.
    if not spec.get("openapi", "").startswith("3."):
        raise ValueError("Only OpenAPI 3.x is supported")

    endpoints: list[ApiEndpoint] = []
    paths = spec.get("paths", {})

    for path_str, path_item in paths.items():
        path_level_params = path_item.get("parameters", [])

        for method_str, operation in path_item.items():
            if method_str in ("parameters", "summary", "description", "$ref"):
                continue
            if method_str not in _VALID_METHODS:
                continue
            if not isinstance(operation, dict):
                continue

            method = HttpMethod(method_str.upper())
            all_param_defs = path_level_params + operation.get("parameters", [])
            parameters = [_extract_parameter(spec, p) for p in all_param_defs]

            body_schema: dict[str, Any] | None = None
            if "requestBody" in operation:
                body_params, body_schema = _extract_body_params(
                    spec, operation["requestBody"]
                )
                parameters.extend(body_params)

            responses = operation.get("responses", {})
            response_codes = []
            for code_str in responses:
                try:
                    response_codes.append(int(code_str))
                except ValueError:
                    pass

            endpoints.append(
                ApiEndpoint(
                    path=path_str,
                    method=method,
                    operation_id=operation.get("operationId"),
                    summary=operation.get("summary", ""),
                    description=operation.get("description", ""),
                    parameters=parameters,
                    request_body_schema=body_schema,
                    response_codes=sorted(response_codes),
                    tags=operation.get("tags", []),
                )
            )

    return endpoints
