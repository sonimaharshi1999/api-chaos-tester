# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""
Shared test fixtures for the API Chaos Tester test suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from api_chaos_tester.models import (
    ApiEndpoint,
    ApiParameter,
    HttpMethod,
    ParameterLocation,
    ParameterType,
)


SAMPLES_DIR = Path(__file__).parent.parent / "samples"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


@pytest.fixture
def sample_spec_path() -> Path:
    """Path to the sample petstore OpenAPI spec."""
    return SAMPLES_DIR / "petstore.yaml"


@pytest.fixture
def templates_dir() -> Path:
    """Path to the templates directory."""
    return TEMPLATES_DIR


@pytest.fixture
def simple_get_endpoint() -> ApiEndpoint:
    """A simple GET endpoint with query parameters."""
    return ApiEndpoint(
        path="/items",
        method=HttpMethod.GET,
        operation_id="listItems",
        summary="List items",
        parameters=[
            ApiParameter(
                name="limit",
                location=ParameterLocation.QUERY,
                param_type=ParameterType.INTEGER,
                required=False,
                min_value=1,
                max_value=100,
            ),
            ApiParameter(
                name="q",
                location=ParameterLocation.QUERY,
                param_type=ParameterType.STRING,
                required=True,
                max_length=200,
            ),
        ],
        response_codes=[200, 400],
    )


@pytest.fixture
def post_endpoint() -> ApiEndpoint:
    """A POST endpoint with body parameters."""
    return ApiEndpoint(
        path="/items",
        method=HttpMethod.POST,
        operation_id="createItem",
        summary="Create an item",
        parameters=[
            ApiParameter(
                name="name",
                location=ParameterLocation.BODY,
                param_type=ParameterType.STRING,
                required=True,
                min_length=1,
                max_length=100,
            ),
            ApiParameter(
                name="price",
                location=ParameterLocation.BODY,
                param_type=ParameterType.NUMBER,
                required=True,
                min_value=0.01,
                max_value=99999.99,
            ),
            ApiParameter(
                name="active",
                location=ParameterLocation.BODY,
                param_type=ParameterType.BOOLEAN,
                required=False,
            ),
            ApiParameter(
                name="tags",
                location=ParameterLocation.BODY,
                param_type=ParameterType.ARRAY,
                required=False,
            ),
        ],
        response_codes=[201, 400, 422],
    )


@pytest.fixture
def path_param_endpoint() -> ApiEndpoint:
    """A GET endpoint with a path parameter."""
    return ApiEndpoint(
        path="/items/{itemId}",
        method=HttpMethod.GET,
        operation_id="getItem",
        summary="Get an item by ID",
        parameters=[
            ApiParameter(
                name="itemId",
                location=ParameterLocation.PATH,
                param_type=ParameterType.INTEGER,
                required=True,
                min_value=1,
            ),
        ],
        response_codes=[200, 404],
    )
