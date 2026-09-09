# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""Tests for OpenAPI spec parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from api_chaos_tester.models import HttpMethod, ParameterLocation, ParameterType
from api_chaos_tester.parser import parse_openapi_from_dict, parse_openapi_spec


class TestParseOpenAPISpec:
    def test_parse_sample_spec(self, sample_spec_path: Path) -> None:
        endpoints = parse_openapi_spec(sample_spec_path)
        assert len(endpoints) > 0

        # Check that known endpoints exist
        paths = {(e.path, e.method) for e in endpoints}
        assert ("/pets", HttpMethod.GET) in paths
        assert ("/pets", HttpMethod.POST) in paths
        assert ("/pets/{petId}", HttpMethod.GET) in paths
        assert ("/search", HttpMethod.GET) in paths

    def test_parse_parameters(self, sample_spec_path: Path) -> None:
        endpoints = parse_openapi_spec(sample_spec_path)
        list_pets = next(
            e for e in endpoints if e.path == "/pets" and e.method == HttpMethod.GET
        )
        param_names = {p.name for p in list_pets.parameters}
        assert "limit" in param_names
        assert "species" in param_names

        limit_param = next(p for p in list_pets.parameters if p.name == "limit")
        assert limit_param.param_type == ParameterType.INTEGER
        assert limit_param.min_value == 1
        assert limit_param.max_value == 100

    def test_parse_body_parameters(self, sample_spec_path: Path) -> None:
        endpoints = parse_openapi_spec(sample_spec_path)
        create_pet = next(
            e for e in endpoints if e.path == "/pets" and e.method == HttpMethod.POST
        )
        body_params = [
            p for p in create_pet.parameters if p.location == ParameterLocation.BODY
        ]
        assert len(body_params) > 0
        body_names = {p.name for p in body_params}
        assert "name" in body_names
        assert "species" in body_names

    def test_parse_response_codes(self, sample_spec_path: Path) -> None:
        endpoints = parse_openapi_spec(sample_spec_path)
        create_pet = next(
            e for e in endpoints if e.path == "/pets" and e.method == HttpMethod.POST
        )
        assert 201 in create_pet.response_codes
        assert 400 in create_pet.response_codes

    def test_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            parse_openapi_spec("/nonexistent/path.yaml")

    def test_parse_from_dict(self) -> None:
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {
                "/hello": {
                    "get": {
                        "operationId": "sayHello",
                        "parameters": [
                            {
                                "name": "name",
                                "in": "query",
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        endpoints = parse_openapi_from_dict(spec)
        assert len(endpoints) == 1
        assert endpoints[0].path == "/hello"
        assert endpoints[0].parameters[0].name == "name"

    def test_invalid_version(self) -> None:
        spec = {
            "swagger": "2.0",
            "info": {"title": "Old", "version": "1.0.0"},
            "paths": {},
        }
        with pytest.raises(ValueError, match="Only OpenAPI 3.x"):
            parse_openapi_from_dict(spec)
